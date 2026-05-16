# DocuLens 🔍

**Intelligent German document processing pipeline.**  
Upload any German PDF (invoice, contract, report) → extract structured fields → query in natural language.

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## What it does

| Input | Output |
|-------|--------|
| German PDF (text or scanned) | Structured JSON with extracted fields |
| Invoice | Rechnungsnummer, Datum, Betrag, IBAN, Parteien |
| Contract | Vertragsparteien, Laufzeit, Kündigungsfristen, KPIs |
| Report | Kennzahlen, Zeitraum, Zusammenfassung |

**Then ask questions in natural language:**
> "Welche Zahlungsfrist gilt?" → "30 Tage ab Rechnungsdatum (Seite 1)"

---

## Architecture

```
PDF Upload
    │
    ▼
┌─────────────────────────────────────┐
│  Layer 1 — Ingestion & Detection    │  ← You are here
│  PyMuPDF + Tesseract OCR            │
│  Auto-detects: text / scanned / mixed│
└─────────────────┬───────────────────┘
                  │
    ┌─────────────▼───────────────────┐
    │  Layer 2 — Embedding & Storage  │  (Week 2)
    │  sentence-transformers + FAISS  │
    └─────────────┬───────────────────┘
                  │
    ┌─────────────▼───────────────────┐
    │  Layer 3 — Structured Extraction│  (Week 3)
    │  Groq API + LangChain + Pydantic│
    └─────────────┬───────────────────┘
                  │
    ┌─────────────▼───────────────────┐
    │  Layer 4 — RAG Chat             │  (Week 4)
    │  FAISS retrieval + Groq LLM     │
    └─────────────┬───────────────────┘
                  │
    ┌─────────────▼───────────────────┐
    │  Layer 5 — API + UI + Deploy    │  (Week 5-6)
    │  FastAPI + Streamlit + HF Spaces│
    └─────────────────────────────────┘
```

---

## Setup (Windows + VS Code)

### 1. Install Tesseract

Download the Windows installer from:  
https://github.com/UB-Mannheim/tesseract/wiki

**Important:** During install, check "Additional language data" → select **German (deu)**.

After install, add to your PATH:
```
C:\Program Files\Tesseract-OCR\
```

Verify:
```bash
tesseract --version
tesseract --list-langs   # should show "deu" in the list
```

### 2. Clone and set up Python environment

```bash
git clone https://github.com/YOUR_USERNAME/doculens.git
cd doculens

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
```

### 3. Generate sample data and test

```bash
# Generate 5 synthetic German invoices
python -m src.utils.generate_samples

# Run the full test suite
pytest tests/ -v

# Quick manual test
python -c "
from src.ingestion import PDFRouter
router = PDFRouter()
result = router.process('data/samples/rechnung_001.pdf')
print(f'Type: {result.doc_type.value}')
print(f'Pages: {result.page_count}')
print(result.full_text[:300])
"
```

### 4. Try on Google Colab (no local install needed)

Open `notebooks/01_ingestion_layer.ipynb` in Google Colab.  
It handles all installation automatically.

---

## Project structure

```
doculens/
├── src/
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── pdf_router.py      ← Layer 1: PDF ingestion & routing
│   └── utils/
│       ├── __init__.py
│       └── generate_samples.py ← Synthetic German invoice generator
├── tests/
│   └── test_ingestion.py
├── notebooks/
│   └── 01_ingestion_layer.ipynb
├── data/
│   ├── samples/               ← Generated test PDFs
│   └── outputs/               ← Extraction results
├── requirements.txt
└── README.md
```

---

## Evaluation results

*Updated as each layer is completed.*

| Layer | Metric | Result |
|-------|--------|--------|
| Ingestion | Doc type classification accuracy | TBD |
| Extraction | Field extraction accuracy (30-doc set) | TBD |
| RAG | Answer relevance (human eval) | TBD |

---

## Data sources

All data is open-licensed — no NDA, fully public:

- **Synthetic invoices** — generated with `reportlab` + `Faker`, ground truth known
- **[openjur.de](https://openjur.de)** — 100k German court decisions, open license  
- **[Bundesanzeiger](https://bundesanzeiger.de)** — Official German federal gazette, public domain
- **[HuggingFace: German invoices dataset](https://huggingface.co/datasets/Aoschu/German_invoices_dataset)** — Real German invoice images

---

## Tech stack

| Component | Technology |
|-----------|-----------|
| Text PDFs | PyMuPDF (fitz) |
| Scanned PDFs | pdf2image + Tesseract OCR |
| Embeddings | sentence-transformers (multilingual, CPU) |
| Vector store | FAISS (local, no server) |
| LLM inference | Groq API (free tier) |
| Validation | Pydantic v2 |
| API | FastAPI |
| UI | Streamlit |
| Deployment | Hugging Face Spaces (free) |

---

## License

MIT
