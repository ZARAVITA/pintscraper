"""
Pinterest Scraper Module — v4
Playwright-based async scraper.

Compatibilité :
    - Windows local     : auto-détection chromium-*/chrome-win/chrome.exe
    - macOS local       : auto-détection chromium-*/Chromium.app
    - Linux local       : auto-détection chromium-*/chrome-linux/chrome
    - Streamlit Cloud   : /usr/bin/chromium (paquet système via packages.txt)
    - Docker            : /usr/bin/chromium-browser
"""

import asyncio
import glob
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# nest_asyncio — fix Streamlit event loop
# ---------------------------------------------------------------------------
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    logger.warning("nest_asyncio non installé.")


# ---------------------------------------------------------------------------
# Auto-détection Chromium — couvre tous les environnements
# ---------------------------------------------------------------------------

def _find_chromium_executable() -> Optional[str]:
    """
    Cherche Chromium dans l'ordre :
    1. Variable PLAYWRIGHT_BROWSERS_PATH (tous OS)
    2. /opt/pw-browsers/ et ~/.cache/ms-playwright/ (Linux/Mac)
    3. AppData/Local/ms-playwright/ (Windows)
    4. Chromium système — /usr/bin/chromium (Streamlit Cloud, Docker)
    5. Google Chrome système
    """
    candidates = []

    # 1. PLAYWRIGHT_BROWSERS_PATH
    pw_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    if pw_path:
        candidates.extend(sorted(glob.glob(f"{pw_path}/chromium-*/chrome-linux/chrome"), reverse=True))
        candidates.extend(sorted(glob.glob(f"{pw_path}/chromium-*/chrome-win/chrome.exe"), reverse=True))
        candidates.extend(sorted(glob.glob(f"{pw_path}/chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium"), reverse=True))

    # 2. Linux — /opt/pw-browsers et ~/.cache/ms-playwright
    candidates.extend(sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"), reverse=True))
    home = str(Path.home())
    candidates.extend(sorted(glob.glob(f"{home}/.cache/ms-playwright/chromium-*/chrome-linux/chrome"), reverse=True))

    # 3. macOS
    candidates.extend(sorted(glob.glob(f"{home}/Library/Caches/ms-playwright/chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium"), reverse=True))

    # 4. Windows
    candidates.extend(sorted(glob.glob(f"{home}/AppData/Local/ms-playwright/chromium-*/chrome-win/chrome.exe"), reverse=True))

    # 5. Chromium système (Streamlit Cloud, Ubuntu, Debian, Docker)
    system_paths = [
        "/usr/bin/chromium",          # Streamlit Cloud (packages.txt)
        "/usr/bin/chromium-browser",  # Ubuntu/Debian
        "/snap/bin/chromium",         # Snap
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/opt/google/chrome/chrome",
        # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        # Windows
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    candidates.extend(system_paths)

    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            logger.info("✅ Chromium trouvé : %s", path)
            return path

    logger.warning("⚠️ Aucun Chromium trouvé — Playwright utilisera son défaut.")
    return None


CHROMIUM_PATH = _find_chromium_executable()


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Pin:
    keyword: str
    title: str
    description: str
    pin_url: str
    image_url: str
    position: int
    score: float = 0.0
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

class PinterestScraper:

    BASE_URL = "https://www.pinterest.com/search/pins/?q={query}&rs=typed"

    SELECTORS = {
        "pin_link": "a[href*='/pin/']",
    }

    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = 45_000,
        scroll_pause_ms: int = 2_500,
        max_scroll_attempts: int = 25,
        user_agent: Optional[str] = None,
        chromium_path: Optional[str] = None,
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
        self.chromium_path = chromium_path or CHROMIUM_PATH

    async def scrape(
        self,
        keyword: str,
        max_pins: int = 50,
        progress_callback: Optional[Callable] = None,
    ) -> list[Pin]:

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright non installé.\n"
                "Lancez : pip install playwright && playwright install chromium"
            )

        url = self.BASE_URL.format(query=quote_plus(keyword))
        logger.info("Scraping : %s | Chromium : %s", url, self.chromium_path or "défaut Playwright")

        async with async_playwright() as pw:
            launch_kwargs: dict = dict(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-gpu",
                    "--single-process",
                ],
            )
            if self.chromium_path:
                launch_kwargs["executable_path"] = self.chromium_path

            try:
                browser = await pw.chromium.launch(**launch_kwargs)
            except Exception as exc:
                raise RuntimeError(
                    f"Impossible de lancer Chromium.\n"
                    f"Chemin : {self.chromium_path or 'défaut Playwright'}\n"
                    f"→ Vérifiez que Chromium est installé.\n"
                    f"Erreur : {exc}"
                )

            context = await browser.new_context(
                user_agent=self.user_agent,
                viewport={"width": 1366, "height": 900},
                locale="en-US",
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = await context.new_page()

            try:
                await page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")
                await page.wait_for_timeout(3_000)
                logger.info("URL: %s | Titre: %s", page.url, await page.title())

                if "login" in page.url.lower():
                    logger.warning("Pinterest redirigé vers login.")

                await self._dismiss_overlays(page)
                pins = await self._collect_pins(page, keyword, max_pins, progress_callback)

            except Exception as exc:
                logger.error("Erreur scraping : %s", exc, exc_info=True)
                raise
            finally:
                await browser.close()

        return pins

    async def _dismiss_overlays(self, page) -> None:
        for sel in [
            "[data-test-id='closeup-close-button']",
            "button[aria-label='Close']",
            "button[aria-label='close']",
            "[data-test-id='cookie-banner'] button",
            "div[role='dialog'] button",
        ]:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=1_500):
                    await btn.click()
                    await page.wait_for_timeout(400)
            except Exception:
                pass

    async def _collect_pins(self, page, keyword, max_pins, progress_callback):
        seen_urls: set[str] = set()
        pins: list[Pin] = []
        stall_count = 0
        position = 1

        try:
            await page.wait_for_selector(self.SELECTORS["pin_link"], timeout=15_000)
        except Exception:
            logger.warning("Timeout sélecteur pins.")

        while len(pins) < max_pins and stall_count < self.max_scroll_attempts:
            raw_pins = await self._extract_pins_from_page(page, keyword)
            newly_added = 0

            for raw in raw_pins:
                if not raw.pin_url or raw.pin_url in seen_urls:
                    continue
                seen_urls.add(raw.pin_url)
                raw.position = position
                pins.append(raw)
                position += 1
                newly_added += 1
                if progress_callback:
                    try:
                        progress_callback(len(pins), max_pins)
                    except Exception:
                        pass
                if len(pins) >= max_pins:
                    break

            stall_count = 0 if newly_added > 0 else stall_count + 1
            if len(pins) >= max_pins:
                break

            await page.evaluate("window.scrollBy(0, window.innerHeight * 2.5)")
            await page.wait_for_timeout(self.scroll_pause_ms)

        logger.info("Collecte terminée : %d pins pour '%s'", len(pins), keyword)
        return pins[:max_pins]

    async def _extract_pins_from_page(self, page, keyword) -> list[Pin]:
        pins = []
        try:
            elements = await page.query_selector_all(self.SELECTORS["pin_link"])
        except Exception as exc:
            logger.error("query_selector_all : %s", exc)
            return pins
        for el in elements:
            try:
                pin = await self._parse_pin_element(el, keyword)
                if pin:
                    pins.append(pin)
            except Exception:
                pass
        return pins

    async def _parse_pin_element(self, el, keyword) -> Optional[Pin]:
        href = await el.get_attribute("href") or ""
        if "/pin/" not in href:
            return None
        pin_url = href if href.startswith("http") else f"https://www.pinterest.com{href}"

        img = await el.query_selector("img")
        image_url = ""
        if img:
            srcset = await img.get_attribute("srcset") or ""
            if srcset:
                parts = [p.strip().split(" ")[0] for p in srcset.split(",") if p.strip()]
                image_url = parts[-1] if parts else ""
            if not image_url:
                image_url = await img.get_attribute("src") or ""
            if image_url and "236x" in image_url:
                image_url = image_url.replace("236x", "736x")

        title = (await el.get_attribute("aria-label") or "").strip()
        if not title and img:
            title = (await img.get_attribute("alt") or "").strip()
        if not title:
            title = (await el.inner_text()).strip()[:120]

        if not image_url and not title:
            return None

        raw_text = (await el.inner_text()).strip()
        description = raw_text.replace(title, "", 1).strip()[:300] if title else raw_text[:300]

        return Pin(
            keyword=keyword,
            title=_clean_text(title),
            description=_clean_text(description),
            pin_url=pin_url,
            image_url=image_url,
            position=0,
        )


def _clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def scrape_sync(
    keyword: str,
    max_pins: int = 50,
    headless: bool = True,
    scroll_pause_ms: int = 2500,
    progress_callback: Optional[Callable] = None,
) -> list[Pin]:
    scraper = PinterestScraper(headless=headless, scroll_pause_ms=scroll_pause_ms)
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        scraper.scrape(keyword=keyword, max_pins=max_pins, progress_callback=progress_callback)
    )