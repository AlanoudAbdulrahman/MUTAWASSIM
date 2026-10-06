# MUTAWASSIM — متوسّم

**MUTAWASSIM** is an AI-powered system for detecting and verifying misleading religious content, prioritizing claims by risk, and generating evidence-based reports from trusted Islamic sources.

It supports da’wah organizations, researchers, and media teams by turning religious content verification from a manual, reactive process into a structured, traceable, and source-grounded workflow.

> The AI understands the posts and finds the evidence; **the verdict always comes from an approved source**. The system never issues fatwas — anything without sufficient evidence is referred to an expert.

**Results on the labeled test sets (real model, `gpt-4o-mini`):** verdict accuracy **98%** · citation accuracy **100%** · misleading-content detection F1 **98%** · claim extraction F1 **100%**.

---

## Quick Start

```bash
# 1) Install (once)
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt  # everything the system needs, including the real model

# 2) Settings (once): copy the template, then set MOCK_MODE=0 and USE_LLM_EXTRACT=1 for the real model
copy .env.example .env           # macOS/Linux: cp .env.example .env

# 3) Run — opens http://localhost:8000 in your browser
python -m mutawassim
```

On Windows you can also **double-click `run.bat`**.

`requirements-full.txt` is optional: it adds a semantic layer to the religious-content filter and local embeddings (sentence-transformers, a large download). Without it the filter uses its keyword list, and verification works the same.

**The API key:** on your own machine the site uses `LLM_API_KEY` from `.env` or a system environment variable. Visitors of a public deployment enter **their own** OpenAI key in the site (see [Privacy & Security](#privacy--security)). Without any key, `MOCK_MODE=1` runs the whole system for free with simplified logic — useful for development, not for real results.

---

## The Website

| Page | What it shows |
|---|---|
| **التحقق — Verify** | Paste posts, upload JSON/CSV/demo files, or pick the demo sets. Results: KPIs, verdict donut, highest-risk claims, claim types, filters, an evidence card per claim (verdict, action, quoted source, risk breakdown), PDF and JSON export. |
| **أداء النظام — Performance** | The benchmark on the labeled test sets — **shared by everyone and re-run automatically whenever the code, data, or settings change** — plus the visitor's private usage statistics. |
| **السجل — History** | Every verification run, saved automatically and **private to the visitor's browser**. Re-open any run or delete it. |
| **المصادر المعتمدة — Sources** | The knowledge base the verdicts come from, searchable, with links. |

---

## How It Works

```text
Posts ─► Cleaning ─► Religious filter ─► Claim extraction (LLM)
                                              │
                                              ▼
       Report & card ◄─ Risk scoring ◄─ Verification ◄─ Hybrid retrieval
             │                         (source grading;   (keywords, then
             ▼                          LLM only when       meaning)
     Website · PDF · History            ambiguous)
```

### 1. Cleaning & filtering (`ingestion/`)
Normalizes text, drops empty and duplicate posts, keeps post ids unique, and keeps only religious content (keyword layer + a semantic layer in real mode).

### 2. Claim extraction (`extraction/`)
An LLM extracts every verifiable claim — attributed hadiths, quoted verses (even in a personal context), beliefs, historical facts, attributed sayings — while preserving negation and attribution. The search query is the quoted text itself. Questions are handled by type:

- *"Is this really a hadith?"* → the quoted text is extracted and verified.
- *"Is X halal/allowed?"* → **«سؤال عن حكم …»**, referred to an expert (the system never issues fatwas).
- Informational questions, dream interpretation, prayers, opinions, and greetings → ignored.

The post text is treated as untrusted data (prompt-injection resistant). Without `USE_LLM_EXTRACT=1`, extraction falls back to sentence splitting.

### 3. Hybrid retrieval (`retrieval/`)
1. **Keyword coverage** (Arabic normalization: diacritics, hamza, alef, ta marbuta) — exact matches take the source's grading directly.
2. **Semantic search** (OpenAI `text-embedding-3-small`, or local e5) when no keyword match is found.

Negation-aware: «يجوز» never matches «لا يجوز».

### 4. Verification (`verification/`)
| Status | Meaning | From source gradings |
|---|---|---|
| `confirmed` — مؤكد | Supported by an approved source | صحيح، حسن، نص قرآني |
| `weak` — ضعيف | Graded weak | ضعيف |
| `fabricated` — موضوع | Fabricated, baseless, or not a hadith | موضوع، باطل، لا أصل له، ليس بحديث |
| `needs_review` — يحتاج تحقق | Insufficient evidence → expert | — |

Ambiguous matches are judged by the LLM **from the retrieved evidence only**, with two code-level guards: the verdict must be backed by a retrieved source with that grading, and a claim that flips the source's negation is never confirmed. Example output:

```json
{
  "claim_id": "p2_c00",
  "status": "fabricated",
  "confidence": 0.85,
  "evidence": [
    {"source": "dorar.net/hadith", "url": "https://dorar.net/hadith/search?q=…",
     "ruling": "موضوع", "snippet": "حب الوطن من الإيمان"}
  ]
}
```

### 5. Risk scoring (`scoring/`)
```text
Risk = Spread × Severity × Sensitivity          (each 0..1)
```
- **Spread** = `1 − 0.8ⁿ`, where *n* is the number of distinct posts that mentioned the claim — including the visitor's earlier runs (spread over time).
- **Severity:** fabricated 1.0 · weak 0.6 · needs_review 0.4 · confirmed 0.
- **Sensitivity:** aqeedah & Quran 1.0 · shubha 0.9 · hadith 0.8 · attribution 0.7 · history 0.6 · other 0.5.

### 6. Reports (`reporting/`)
Each claim gets a card whose text is assembled **from the source itself** (no generated wording), so nothing can be hallucinated:

- **رد — respond:** confirmed claims, and weak/fabricated claims outside sensitive topics.
- **إحالة لمختص — refer to an expert:** insufficient evidence, weak/fabricated aqeedah or shubha claims, and religious-ruling questions.

Cards export to an Arabic PDF report (summary, risk-ordered cards, quoted evidence, source links).

---

## Trusted Sources

The current knowledge base (`data/sources/sources.json`): **60 hadiths from Dorar Al-Saniyyah** with their gradings, and **20 Quranic verses from Quranpedia**. Approved references for future expansion: Dorar Al-Saniyyah (tafseer, aqeedah, fiqh, history), Shamela, Dawa Center, Islamic Content.

Adding a source is a data change only — the system reads `sources.json` on start. Every `ruling` must contain a known grading (a test enforces this).

---

## Evaluation

| Benchmark | Metric | Result |
|---|---|---|
| Verification (100 labeled claims) | Verdict accuracy | **98%** |
| | Misleading-content detection — precision / recall / F1 | **100% / 97% / 98%** |
| | Citation rate — verdicts with a source link | **100%** |
| | Citation accuracy — the source's grading matches the verdict | **100%** |
| Extraction (gold posts) | Claim precision / recall / F1 | **100% / 100% / 100%** |
| | Ignoring non-claims (prayers, opinions, info questions) | **100%** |

The website re-runs these automatically after any change (`benchmark.py` fingerprints the code, data, and settings). From the command line:

```bash
python -m mutawassim.evaluation.evaluate               # verification
python -m mutawassim.evaluation.evaluate_extraction    # extraction
```

---

## Privacy & Security

- **Bring your own key:** public visitors verify with their own OpenAI key. It stays in their browser and is sent only with verification requests (header `X-LLM-Key`, HTTPS only). The server never stores or logs it. The owner's key (`LLM_API_KEY`) is used only as allowed by `SERVER_KEY_FOR` (default: the server machine only).
- **Private history without login:** each browser gets an anonymous identity (an `HttpOnly` cookie; the database stores only its hash). History, usage statistics, and spread-over-time are scoped to it. The benchmark and the sources are shared.
- **Limits:** batch size, post length, and upload size. Each visitor pays for their own usage with their own key.
- **Grounding guards:** prompt-injection resistance, a verdict must be backed by a source, negation flips are rejected.
- **Hardening:** strict Content-Security-Policy and security headers, generic error messages, upload size limit, `http(s)`-only links. The website's scripts and fonts are served locally — no third-party code.
- **Secrets:** `.env` and the local database are git-ignored. Never put a key in code.

---

## Configuration (`.env`)

| Setting | Default | Purpose |
|---|---|---|
| `MOCK_MODE` | `1` | `0` = real model |
| `LLM_API_KEY` | — | Owner's key (or a system environment variable) |
| `LLM_MODEL` | `gpt-4o-mini` | Chat model |
| `USE_LLM_EXTRACT` | `0` | `1` = extract claims with the LLM (recommended) |
| `EMBED_PROVIDER` | `openai` | `openai` or `local` (e5) |
| `SERVER_KEY_FOR` | `local` | Who may use `LLM_API_KEY`: `local` / `none` / `all` |
| `TRUST_LOCALHOST` | `1` | `0` behind a reverse proxy (see Deployment) |
| `MAX_POSTS` / `MAX_POST_CHARS` | `50` / `4000` | Batch limits |
| `AUTO_EVALUATE` | `1` | Re-run the benchmark after changes |
| `ADMIN_TOKEN` | — | Allows manual benchmark runs remotely |
| `EXPOSE_DOCS` | `1` | `0` hides `/docs` |

---

## Deployment (public)

With Docker (the image already has the public settings: real model, visitors bring their own key, no server key, docs hidden):

```bash
docker build -t mutawassim .
docker run -p 8000:8000 -v mutawassim-history:/app/mutawassim/data/history mutawassim
```

- The site must be served over **HTTPS** (any hosting platform provides it); visitor keys are refused over plain HTTP.
- The volume keeps visitors' saved history across restarts.
- No API key goes into the image. Optionally set `ADMIN_TOKEN` to re-run the benchmark from the site.

Without Docker, run the same command the image uses with those settings (`TRUST_LOCALHOST=0`, `SERVER_KEY_FOR=none`, `EXPOSE_DOCS=0`, `MOCK_MODE=0`, `USE_LLM_EXTRACT=1`):

```bash
uvicorn mutawassim.api.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*"
```

---

## Command-Line Tools

The system runs with one command, `python -m mutawassim` (`run.bat` is a double-click shortcut for it).
The tools below are optional, for development:

```bash
python -m mutawassim.reporting.pdf_report posts.json -o report.pdf
python -m mutawassim.verification.verify_cli "النظافة من الإيمان"
pytest -q                                              # tests (always in MOCK mode; never spend credit)
```

---

## Project Structure

```text
mutawassim/
├── __main__.py         one-command launcher (python -m mutawassim)
├── config.py           settings (.env)
├── schemas.py          shared data contract (Pydantic)
├── llm.py              model wrapper (per-request key)
├── pipeline.py         the full pipeline: run_pipeline / process_batch
├── storage.py          SQLite history (per visitor)
├── benchmark.py        automatic evaluation
├── serialize.py        results → JSON
├── ingestion/          cleaner, religious filter
├── extraction/         claim extractor (LLM prompt)
├── retrieval/          hybrid retriever, Arabic matching, embeddings
├── verification/       grounded verifier
├── scoring/            risk score
├── reporting/          response cards, Arabic PDF report, fonts
├── evaluation/         benchmarks
├── api/                FastAPI: endpoints, views, security
├── web/                React website (no build step)
├── data/               sources, test sets, demo posts
└── tests/              195 tests
```

---

## Tech Stack

- **AI & NLP:** Python, OpenAI (`gpt-4o-mini`, `text-embedding-3-small`), prompt engineering, RAG.
- **Retrieval:** hybrid keyword + semantic search with Arabic normalization.
- **Backend:** FastAPI, Pydantic, SQLite.
- **Frontend:** React (served by FastAPI, no build step), custom SVG charts.
- **Reports:** fpdf2 with HarfBuzz Arabic shaping.
- **Quality:** pytest (195 tests), automatic benchmarking.

---

## Development Responsibilities

- **Developer 1 — Data Cleaning & Claim Extraction:** dataset cleaning, text normalization, religious-content filtering, claim extraction, structured claim output.
- **Developer 2 — RAG & Verification:** source indexing, embeddings, semantic retrieval, evidence retrieval, grounded verification, source attribution.
- **Developer 3 — Risk Scoring, Reporting & Evaluation:** risk scoring, grounded report generation, evaluation, precision and recall, citation validation.
- **Developer 4 — Backend, Dashboard & Integration:** FastAPI, pipeline integration, dashboard, API integration, error handling, demo workflow.

---

## Design Principles

- **Traceability** — every result is linked to supporting evidence.
- **Grounding** — outputs rely on retrieved trusted sources; the model never judges from its own knowledge.
- **Transparency** — risk scoring is clear and interpretable.
- **Human Oversight** — unresolved or sensitive claims are escalated for expert review.

## Goal

MUTAWASSIM helps da’wah organizations move from delayed, manual responses to a proactive workflow where misleading religious claims are detected, verified, prioritized, and reviewed with clear supporting evidence.
