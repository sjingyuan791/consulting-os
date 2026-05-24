# Consulting OS (MVP)

中小企業向け再生×戦略×ファイナンス診断システム。
Streamlit + Python + Supabase + OpenAI API を用いた意思決定支援ツール。

## Architecture Overview

### 1. Layers
- **Frontend**: Streamlit (Python-based UI)
  - `app.py`: Main entry & Auth
  - `pages/`: 00_home, 01_upload, 02_diagnosis_report
- **Backend (Core Logic)**: `core/` modules
  - **Financial Logic**: Deterministic calculation (RoA, D/E, etc.) using `pandas`.
  - **Text Analysis**: Map-Reduce summarization using OpenAI API.
  - **PDF Generation**: `reportlab` for pixel-perfect PDF reporting.
- **Database**: Supabase (PostgreSQL)
  - Manages Workspaces, Clients, and Diagnosis Histories.
  - **RLS (Row Level Security)** enforces data isolation by Workspace and User.

### 2. Data Flow
1. **Types**: Excel/CSV (Financials), PDF/Txt (Qualitative).
2. **Ingest**: Files uploaded -> Converted to Memory DF -> Normalized (`normalizers.py`).
3. **Analyze**: 
   - Financials -> Summarized Metrics (`analytics_financial.py`).
   - Texts -> Map-Reduce Summaries (`text_ingest.py` + OpenAI).
4. **Synthesize**: Summaries -> Final Logical Structure -> LLM Diagnosis (`report_json`).
5. **Output**: `report_json` -> JSON displayed -> PDF Generated (`report_pdf.py`).

## Setup Instructions

### 1. Supabase Setup
1. Create a new Supabase project.
2. Go to **SQL Editor** and paste the content of `supabase_schema.sql`. Run it.
3. Get your **Project URL** and **Service Role Key** (or Anon Key depending on implementation, here we use Client interaction so Anon Key is sufficient for frontend, Service Key for protected ops if needed, but RLS handles security).
   - *Note*: For this MVP, we use `SUPABASE_URL` and `SUPABASE_KEY` (Anon Key) in `.env`.

### 2. Local Environment
1. Python 3.9+ required.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `.env` file:
   ```env
   SUPABASE_URL="your-project-url"
   SUPABASE_KEY="your-anon-key"
   OPENAI_API_KEY="sk-..."
   ```

### 3. Run
```bash
streamlit run app.py
```

## Tech Stack
- **Languages**: Python 3
- **Frameworks**: Streamlit, Supabase-py, OpenAI, ReportLab, Pandas
- **Infrastructure**: Supabase (Auth, DB)

## Model Routing Strategy
To optimize for cost and performance, the system automatically routes tasks to different LLMs via `core/llm_router.py`:

| Task Type | Model | Use Case |
|-----------|-------|----------|
| **Light** | `gpt-4.1-mini` | Summarization, Chat, KPI Review |
| **Analysis** | `gpt-5.2` | Diagnosis, Strategy Logic, Chapter Generation |
| **Premium** | `gpt-5.2-pro` | Final Plan Integration, Bank Documents |
