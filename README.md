# 📊 LinkedIn Talent-Insights Extractor

Turn noisy **LinkedIn Talent Insights™ PDFs** into clean, structured JSON — and forecast headcount needs by role, using LLM + internal logic.

---

## 🚀 Overview

LinkedIn company PDFs contain goldmine data like:

* 📈 Headcount trends
* 🔁 Attrition
* 🧠 Skills breakdown
* 🌍 Location-based hiring
* 🧑‍💼 Role distribution

But extracting it programmatically? Nightmare.

> This repo automates the process:
>
> ✅ PDF → Text
> ✅ Text → Structured Insights
> ✅ Insights + Role → Forecasted Hiring Timeline + Justification

---

## 🛠️ Installation

```bash
git clone https://github.com/your-org/linkedin-insights-extractor.git
cd linkedin-insights-extractor

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env  # Set your OPENAI_API_KEY
```

---

## 🧪 How It Works

### 🔹 Phase 1: Extract JSON from LinkedIn Talent PDF

```bash
python -m linkedin_insights.cli /path/to/Microsoft_APAC.pdf
```

Returns structured company profile as JSON:

```json
{
  "company_profile": {
    "employees_current": 52431,
    "hires_last_12_months": 8280,
    ...
  }
}
```

---

### 🔹 Phase 2: Predict Headcount Timeline for a Role

```bash
python main.py /path/to/Microsoft_APAC.pdf --role "AI Engineer" -v
```

Returns forecasted timeline:

```text
Predicted 12‑month hires for AI Engineer: 3911
Forecast confidence: 0.6
```

And a table like:

| Timeframe  | Count | Reasoning                           |
| ---------- | ----- | ----------------------------------- |
| 0–1 month  | 326   | Urgent backfills for attrition...   |
| 1–3 months | 652   | Project ramp-ups & budget unlock... |
| ...        | ...   | ...                                 |

---

### 🔹 Run End-to-End Test (JSON + Prediction)

```bash
python tests.py "/path/to/Microsoft_APAC.pdf" --role "HR Manager" --run 5
```

---

## 📁 Folder Structure & File Purpose

```
linkedin-insights-extractor/
│
├── linkedin_insights/              # Core logic lives here
│   ├── __init__.py                 # Package init
│   ├── cli.py                      # CLI entrypoint for JSON extraction
│   ├── extractor.py                # Main controller: PDF → Text → LLM → JSON
│   ├── pdf_utils.py                # PDF-to-text converter (pdfplumber)
│   ├── openai_client.py            # Wrapper for OpenAI GPT API
│   ├── llm_utils.py                # Shared GPT calling + safety utils
│   ├── prompt_templates.py         # Prompts to extract structured fields
│   ├── prompt_templates_predictor.py # Prompts used in prediction/forecasting
│   ├── config.py                   # Defines time buckets and constants
│   ├── timeline_splitter.py        # Allocates headcount using weights + rounding
│   ├── timeline_allocator.py       # Legacy allocator (kept for reference)
│   ├── timeline_reasoning_llm.py   # Adds per-bucket LLM-generated justifications
│   ├── linkedin_insights_llm_predictor.py # Full pipeline: JSON → Forecast → Reasoning
│   ├── debug_text_dump.py          # Dumps raw text for manual debugging
│   └── utils.py                    # Misc helper functions
│
├── tests/                          # Test suite
│   ├── test_pdf_utils.py
│   ├── test_openai_client.py
│   └── test_extractor.py
│
├── requirements.txt                # Python dependencies
├── .env.example                    # Sample env with `OPENAI_API_KEY`
└── README.md                       # You're here.
```

---

## 💡 Features

* ✅ Robust PDF parsing via `pdfplumber`
* ✅ Modular GPT prompts for structured field extraction
* ✅ Configurable hiring timeline logic (bucket weights)
* ✅ Rounding logic ensures total sum equals predicted headcount
* ✅ Per-bucket reasoning using a **single GPT call**
* ✅ Verbose logging, test mode, and debugging scripts

---

## 🧪 Sample Use Cases

* 🤖 Build dashboards to show hiring trends per role
* 🔍 Benchmark attrition, hiring rate, and talent distribution
* 🧠 Forecast headcount needs based on real data + GPT logic
* 💼 Present hiring plans with LLM-backed justifications

---

## 🔐 Environment Setup

Edit `.env` with your OpenAI API key:

```env
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4o-mini-2024-07-18
```



