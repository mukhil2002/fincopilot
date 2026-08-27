# FinCopilot

AI-powered bookkeeping assistant for UK SME owners. Built as an MSc Financial Technology dissertation at the University of Birmingham.

## Live Demo

**URL:** https://fincopilot-deploy.vercel.app

**Demo Account**
| | |
|---|---|
| Email | demo@fincopilot.com |
| Password | Fincopilot2026 |

The demo account is pre-loaded with two months of transaction data (July and August 2026) for a small retail shop, including categorised transactions, anomaly detection, AI-generated summaries, Q&A, cash flow forecast, and PDF export.

---

## What It Does

Upload a bank statement CSV → AI categorises every transaction using Claude → ML detects anomalies → plain-English financial summary → natural language Q&A → 3-month cash flow forecast → downloadable PDF report.

---

## Research Questions

| RQ | Question |
|---|---|
| RQ1 | Does FinCopilot's plain-English AI output improve perceived ease and confidence for non-accountants? |
| RQ2 | Does zero-shot Claude outperform rule-based categorisation for ambiguous UK SME transactions? |
| RQ3 | Can Claude categorise accurately from the very first upload with no prior configuration? |
| RQ4 | Does a Claude-narrated cash flow forecast improve perceived ease vs raw numerical projections? |

---

## RQ2 Evaluation Results

| Dataset | Rule-Based | Claude (Zero-Shot) | Difference |
|---|---|---|---|
| Clean Business (100 transactions) | 88% | 96% | +8% |
| Ambiguous (100 transactions) | 19% | 66% | +47% |
| Mixed Sole Trader (100 transactions) | 66% | 76% | +10% |

**Benchmark comparison:**
- GPT-4o zero-shot: 60.4%
- Claude zero-shot (this study, ambiguous dataset): 66.0% → +5.6% above benchmark
- GPT-4o fine-tuned: 73.49%

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI/LLM | Claude API (claude-sonnet-4-6) |
| Backend | Python 3.12 + FastAPI + Uvicorn |
| Auth | Supabase JWT + Row Level Security |
| Database | PostgreSQL (Supabase hosted) |
| ML | scikit-learn Isolation Forest + scipy Z-score |
| Parsing | pandas + chardet |
| Forecast | numpy rolling average + Claude narrative |
| Frontend | React 18 + Vite + Tailwind CSS + Recharts |
| PDF | ReportLab |
| Backend hosting | Railway |
| Frontend hosting | Vercel |

---

## Supported Bank Formats

- Revolut (CSV export)
- Generic UK bank CSV (Date, Description, Amount columns)

---

## Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase account
- Anthropic API key



fincopilot/
├── backend/
│ ├── api/ ← FastAPI endpoints
│ ├── services/ ← Business logic (categoriser, parser, anomaly, forecast, report)
│ └── config.py ← 14 transaction categories, API keys
├── frontend/
│ └── src/
│ ├── pages/ ← Login, Signup, Dashboard
│ └── components/ ← UI components
├── scripts/
│ ├── run_evaluation.py ← RQ2 evaluation script
│ └── datasets/ ← 3 synthetic datasets for RQ2
└── results/ ← Evaluation output (timestamped CSVs)


---

## Key Features

- **AI Categorisation** — Claude zero-shot categorises every transaction into 14 UK SME categories
- **Anomaly Detection** — Three-method hybrid: Isolation Forest + Z-score + rule engine
- **Correction Learning** — User corrections are saved and applied automatically on future uploads
- **Financial Summary** — Claude generates a plain-English monthly summary
- **Q&A Chat** — Ask anything about your finances in natural language
- **Cash Flow Forecast** — 3-month projection with Claude narrative
- **PDF Export** — Full report downloadable as PDF
- **Bank CSV Support** — Revolut and generic UK bank formats

