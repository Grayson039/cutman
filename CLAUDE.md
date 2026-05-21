# Cutman — CLAUDE.md

## Project Overview

**Cutman** is a personal combat sports dashboard — one clean mobile app for every fight promotion, replacing the need to bounce between UFC.com, ESPN, Google, Reddit, and Tapology.

Tagline: *One app. Every promotion. All the fights.*

**Personal use only** — no commercial distribution, no App Store submission. This keeps legal risk at zero and lets us scrape public data freely.

---

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React Native |
| Backend | Python — FastAPI + BeautifulSoup |
| Database | Supabase (free tier) |
| Hosting | Render.com (free tier) |
| Data Sources | RSS feeds, Wikipedia, Tapology (scraped) |
| Version Control | GitHub |

**Target monthly cost: $0**

---

## MVP Features

| Feature | Description |
|---|---|
| Upcoming Fight Cards | All promotions — UFC, boxing, PFL, ONE Championship, more |
| Fight News | Headlines aggregated from top MMA/boxing outlets |
| Fighter Stats | Records, recent fights, rankings |
| Recent Results | What happened at the last event |
| Where To Watch | Network / streaming service per event |
| PPV Cost | Price clearly displayed per event |

---

## Build Roadmap

### Phase 0 — Ideation (Complete)
- Concept defined
- Competitor research completed
- Legal review completed (personal use = safe)
- Tech stack decided
- Project docs created

### Phase 1 — Data Layer (Current)
- [ ] GitHub repo initialized
- [ ] Python environment set up
- [ ] BeautifulSoup scraper for fight cards (Wikipedia/Tapology)
- [ ] RSS feed parser for news headlines
- [ ] Clean terminal output working

### Phase 2 — Backend
- [ ] FastAPI server scaffolded
- [ ] Scraping runs on schedule
- [ ] Supabase database connected
- [ ] API endpoints live on Render

### Phase 3 — Mobile App
- [ ] React Native project initialized
- [ ] Dashboard UI designed and built
- [ ] Connected to backend API
- [ ] Fight cards, news, results displaying
- [ ] Where to watch + PPV cost integrated

---

## Project Structure (Planned)

```
cutman/
├── backend/
│   ├── scrapers/        # BeautifulSoup scrapers
│   ├── parsers/         # RSS feed parsers
│   ├── api/             # FastAPI routes
│   └── main.py
├── mobile/              # React Native app
├── CLAUDE.md
└── README.md
```

---

## Why Personal Use Only?

- Zero legal risk (no trademark issues with UFC/boxing promotions)
- Zero API licensing costs
- No App Store approval needed
- Freedom to scrape public data without commercial risk
