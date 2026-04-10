# 📌 Pinterest Niche Scraper

A Streamlit-powered MVP for scraping Pinterest search results, identifying high-performing pins, and exporting structured data for AI content creation workflows.

---

## 🎯 What It Does

| Step | Description |
|------|-------------|
| 1 | Input a niche keyword (e.g. `fitness motivation`, `home decor`) |
| 2 | Playwright opens Pinterest search and scrolls to load pins |
| 3 | Extracts title, description, pin URL, image URL, position |
| 4 | Computes a performance **score** per pin |
| 5 | Displays results in an interactive Streamlit UI |
| 6 | Exports a styled **Excel file** ready for analysis or AI prompting |

---

## 🗂️ Project Structure

```
pinterest-scraper/
├── app.py                        # Streamlit entry point
├── scraper/
│   ├── __init__.py
│   └── pinterest_scraper.py      # Playwright-based async scraper
├── utils/
│   ├── __init__.py
│   ├── scoring.py                # Pin performance scoring logic
│   └── export.py                 # DataFrame → Excel conversion
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚙️ Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/your-username/pinterest-scraper.git
cd pinterest-scraper
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright browsers

> **This step is mandatory.** Playwright needs to download the Chromium binary.

```bash
playwright install chromium
```

If you also want Firefox / WebKit support (not required for this project):
```bash
playwright install
```

---

## 🚀 Running the App

```bash
streamlit run app.py
```

The app will open at [http://localhost:8501](http://localhost:8501).

---

## 🧠 How It Works

### Scraper (`scraper/pinterest_scraper.py`)

- Opens `https://www.pinterest.com/search/pins/?q={keyword}` in a headless Chromium browser
- Dismisses cookie banners / login prompts automatically
- Scrolls progressively, collecting new `<a href="/pin/...">` elements on each pass
- Extracts image URL (preferring high-res `srcset`), title (from `aria-label` or `alt`), and description (remaining visible text)
- Stops when `max_pins` is reached or no new pins appear after several scroll attempts

### Scoring (`utils/scoring.py`)

```
score = (1 / position) × POSITION_WEIGHT
       + repetition_factor × REPETITION_WEIGHT
```

| Signal | Meaning |
|--------|---------|
| `1 / position` | Higher-ranked pins score more |
| `repetition_factor` | Pins whose image appears multiple times get a bonus (organic traction signal) |

### Export (`utils/export.py`)

- Converts Pin dataclasses → Pandas DataFrame
- Cleans nulls, deduplicates by pin URL, sorts by score
- Generates a styled `.xlsx` file with Pinterest-red headers, alternating rows, frozen pane, and auto-filter

---

## 📊 Excel Output Columns

| Column | Description |
|--------|-------------|
| `keyword` | The search keyword used |
| `position` | Rank in search results |
| `score` | Performance proxy score |
| `title` | Pin title / aria label |
| `description` | Visible text below title |
| `pin_url` | Full Pinterest pin URL |
| `image_url` | Direct image URL (high-res) |

File name format: `pinterest_scraping_{keyword}.xlsx`

---

## ⚠️ Important Notes

- **Pinterest detects automation.** If you get 0 results:
  - Try disabling headless mode (uncheck in sidebar)
  - Increase scroll pause to 3000–5000 ms
  - Pinterest may show a login wall — the scraper attempts to dismiss it, but results aren't guaranteed
  - Using a residential proxy or logging in via cookies can significantly improve yield
- **Respect Pinterest's Terms of Service.** This tool is intended for research and educational use only.
- **Rate limiting:** Don't scrape thousands of pins in rapid succession.

---

## 🔮 Future Extensions (code already structured for these)

### NLP Analysis
```python
# utils/scoring.py — nlp_title_score() and keyword_density_score() are stubbed
# Add: pip install spacy && python -m spacy download en_core_web_sm
```

### Supabase Integration
```python
# utils/export.py — push_to_supabase() stub exists
# Add: pip install supabase
# Configure SUPABASE_URL + SUPABASE_KEY in .env
```

### Multi-keyword Batch Scraping
```python
# scraper/pinterest_scraper.py — scrape() accepts any keyword
# Wrap in a loop or use asyncio.gather() for parallel scraping
```

### Scheduling
```python
# Add: pip install apscheduler
# Schedule scrape_sync() calls via APScheduler or GitHub Actions
```

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| `playwright install` fails | Ensure Node.js isn't conflicting; try `pip install playwright --upgrade` |
| 0 pins returned | Pinterest login wall; try headless=False or increase scroll pause |
| `ModuleNotFoundError` | Ensure venv is activated and `pip install -r requirements.txt` was run |
| Excel file is empty | The scrape returned no data; see "0 pins" fix above |

---

## 📄 License

MIT — free to use, modify, and distribute. Attribution appreciated.
