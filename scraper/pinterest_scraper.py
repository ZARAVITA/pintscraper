"""
Pinterest Scraper Module
Uses Playwright to scrape Pinterest search results dynamically.
Designed to be extended with authentication, proxies, or multi-keyword support.
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote_plus

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Pin:
    """Represents a single Pinterest pin with all extracted metadata."""
    keyword: str
    title: str
    description: str
    pin_url: str
    image_url: str
    position: int
    # Filled later by scoring module
    score: float = 0.0
    # Future: board_name, repins, saves, creator, etc.
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Scraper class
# ---------------------------------------------------------------------------

class PinterestScraper:
    """
    Async scraper for Pinterest search results using Playwright.

    Usage:
        scraper = PinterestScraper(headless=True)
        pins = await scraper.scrape(keyword="fitness", max_pins=50)
    """

    BASE_URL = "https://www.pinterest.com/search/pins/?q={query}&rs=typed"

    # CSS selectors — Pinterest changes its DOM frequently; centralise them here.
    SELECTORS = {
        "pin_container": "[data-test-id='pin']",
        "pin_link": "a[href*='/pin/']",
        "image": "img",
        "title": "[data-test-id='pin-title'], h3, [aria-label]",
    }

    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = 30_000,
        scroll_pause_ms: int = 2_000,
        max_scroll_attempts: int = 20,
        user_agent: Optional[str] = None,
    ):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.scroll_pause_ms = scroll_pause_ms
        self.max_scroll_attempts = max_scroll_attempts
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def scrape(
        self,
        keyword: str,
        max_pins: int = 50,
        progress_callback=None,
    ) -> list[Pin]:
        """
        Main entry point. Returns a list of Pin objects.

        Args:
            keyword: Search term.
            max_pins: Target number of pins (actual count may differ slightly).
            progress_callback: Optional callable(current, total) for UI updates.
        """
        url = self.BASE_URL.format(query=quote_plus(keyword))
        pins: list[Pin] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent=self.user_agent,
                viewport={"width": 1280, "height": 900},
                locale="en-US",
            )
            page = await context.new_page()

            try:
                logger.info("Navigating to %s", url)
                await page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")

                # Dismiss cookie / login dialogs if they appear
                await self._dismiss_overlays(page)

                pins = await self._collect_pins(
                    page, keyword, max_pins, progress_callback
                )

            except PlaywrightTimeoutError as exc:
                logger.error("Page load timeout: %s", exc)
            except Exception as exc:
                logger.error("Unexpected scraping error: %s", exc, exc_info=True)
            finally:
                await browser.close()

        return pins

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _dismiss_overlays(self, page) -> None:
        """Attempt to close login prompts or cookie banners."""
        close_selectors = [
            "[data-test-id='closeup-close-button']",
            "button[aria-label='Close']",
            "[data-test-id='cookie-banner'] button",
        ]
        for sel in close_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=2_000):
                    await btn.click()
                    await page.wait_for_timeout(500)
            except Exception:
                pass

    async def _collect_pins(
        self,
        page,
        keyword: str,
        max_pins: int,
        progress_callback,
    ) -> list[Pin]:
        """
        Scroll the page progressively and extract pins until max_pins is reached
        or no new content appears.
        """
        seen_urls: set[str] = set()
        pins: list[Pin] = []
        scroll_attempts = 0
        position = 1

        await page.wait_for_timeout(3_000)  # Let initial pins render

        while len(pins) < max_pins and scroll_attempts < self.max_scroll_attempts:
            # Extract pins currently visible in DOM
            raw_pins = await self._extract_pins_from_page(page, keyword)

            newly_added = 0
            for raw in raw_pins:
                if raw.pin_url in seen_urls:
                    continue
                seen_urls.add(raw.pin_url)
                raw.position = position
                pins.append(raw)
                position += 1
                newly_added += 1

                if progress_callback:
                    progress_callback(len(pins), max_pins)

                if len(pins) >= max_pins:
                    break

            logger.debug(
                "Scroll %d: found %d new pins (total %d / %d)",
                scroll_attempts, newly_added, len(pins), max_pins,
            )

            if newly_added == 0:
                scroll_attempts += 1
            else:
                scroll_attempts = 0  # reset stall counter on progress

            # Scroll down to load more
            await page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
            await page.wait_for_timeout(self.scroll_pause_ms)

        logger.info("Collected %d pins for keyword '%s'", len(pins), keyword)
        return pins[:max_pins]

    async def _extract_pins_from_page(self, page, keyword: str) -> list[Pin]:
        """
        Parse the current DOM state and return Pin objects for every
        pin element found.
        """
        pins: list[Pin] = []

        # Grab all anchor tags that point to a pin page
        pin_elements = await page.query_selector_all("a[href*='/pin/']")

        for el in pin_elements:
            try:
                pin = await self._parse_pin_element(el, keyword)
                if pin:
                    pins.append(pin)
            except Exception as exc:
                logger.debug("Failed to parse pin element: %s", exc)

        return pins

    async def _parse_pin_element(self, el, keyword: str) -> Optional[Pin]:
        """
        Extract data from a single anchor element.
        Returns None if essential data is missing.
        """
        # --- Pin URL ---
        href = await el.get_attribute("href") or ""
        if "/pin/" not in href:
            return None

        pin_url = href if href.startswith("http") else f"https://www.pinterest.com{href}"

        # Deduplicate by URL at element level (full dedup is done above)
        # --- Image URL ---
        img = await el.query_selector("img")
        image_url = ""
        if img:
            # Prefer srcset (higher res) over src
            srcset = await img.get_attribute("srcset") or ""
            if srcset:
                # Take the last (largest) URL from srcset
                parts = [p.strip().split(" ")[0] for p in srcset.split(",") if p.strip()]
                image_url = parts[-1] if parts else ""
            if not image_url:
                image_url = await img.get_attribute("src") or ""

        # --- Title ---
        title = ""
        aria_label = await el.get_attribute("aria-label") or ""
        if aria_label:
            title = aria_label.strip()

        if not title:
            # Try alt text on the image
            if img:
                title = (await img.get_attribute("alt") or "").strip()

        if not title:
            # Fallback: any visible text inside the anchor
            title = (await el.inner_text()).strip()[:120]

        # Skip elements that aren't actual pins (e.g. navigation links)
        if not image_url and not title:
            return None

        # --- Description ---
        # Pinterest rarely exposes descriptions in search cards;
        # we extract whatever text is visible beyond the title.
        raw_text = (await el.inner_text()).strip()
        description = _extract_description(raw_text, title)

        return Pin(
            keyword=keyword,
            title=_clean_text(title),
            description=_clean_text(description),
            pin_url=pin_url,
            image_url=image_url,
            position=0,  # assigned by caller
        )


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """Remove excess whitespace and non-printable characters."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_description(raw_text: str, title: str) -> str:
    """
    Attempt to extract description by removing the title portion
    from the raw inner text of the element.
    """
    if not raw_text or not title:
        return ""
    desc = raw_text.replace(title, "", 1).strip()
    return desc[:300]  # Cap length


# ---------------------------------------------------------------------------
# Sync wrapper (convenience for non-async callers)
# ---------------------------------------------------------------------------

def scrape_sync(keyword: str, max_pins: int = 50, progress_callback=None) -> list[Pin]:
    """
    Synchronous wrapper around the async scraper.
    Useful for Streamlit which runs in a sync context.
    """
    return asyncio.run(
        PinterestScraper().scrape(
            keyword=keyword,
            max_pins=max_pins,
            progress_callback=progress_callback,
        )
    )