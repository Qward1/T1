"""# OpenAI Codex Full Implementation Prompt — Smart Support System (SciBox Hackathon)

## 🎯 Objective

Build a **complete intelligent support system** using Python (FastAPI backend) and React (Vite + TypeScript frontend) that:
1. Classifies customer requests into categories and subcategories.
2. Extracts entities (NER).
3. Retrieves and ranks FAQ template answers.
4. Generates final responses (in Russian) based strictly on templates.
5. Includes a **web interface** for support agents.
6. Uses **SciBox API** (OpenAI-compatible) for LLM calls and embeddings.
7. Implements **local Git commits** after every major module creation.

All code comments must be written **in English**.

---

## 🧩 General Architecture

**Tech Stack:**
- **Backend:** Python 3.11, FastAPI, FAISS, OpenAI client (SciBox API), Pandas, Pydantic, Docker.
- **Frontend:** React + Vite + TypeScript.
- **Database:** JSON/FAISS index (no external DB).
- **Containerization:** Docker + docker-compose.

**Core Flow:**
1. Request → Classification + NER (LLM via SciBox)
2. Embedding Search → FAISS index of FAQ answers
3. Re-ranking → Rule-based (and optionally LLM)
4. Final Response → Template adaptation (LLM)
5. UI → Interactive operator interface

---

## 🧱 Backend Tasks

### 1. `settings.py`
- Use `pydantic.BaseSettings` to load env variables:
  - `SCIBOX_API_KEY`
  - `SCIBOX_BASE_URL`
  - `FAQ_PATH`
- Fail with clear error if missing.
- **Commit:** `feat(settings): add env config and validation`

### 2. `scibox_client.py`
- Wrapper around `openai.OpenAI` with:
  - `chat()` → chat/completions using `Qwen2.5-72B-Instruct-AWQ`
  - `embed()` → embeddings using `bge-m3`
- Load API key + base_url from `settings.py`
- **Commit:** `feat(client): create SciBox API wrapper`

### 3. `build_index.py`
- Read `smart_support_vtb_belarus_faq_final.xlsx`.
- Build records JSON: category, subcategory, audience, question, answer.
- Generate embeddings for each question.
- Normalize vectors and build FAISS index.
- Save `faq_records.json` + `faq.index`.
- **Commit:** `feat(index): build FAISS index from FAQ table`

### 4. `classifiers.py`
- Function `classify_and_ner(text: str) -> dict`
- Prompt template:
You are a classifier. Return JSON:
{"category": "", "subcategory": "", "confidence": 0.0, "entities": {...}}

markdown
Всегда показывать подробности

Копировать код
- Extract entities: product, currency, amount, date, problem, geo.
- Validate JSON output.
- **Commit:** `feat(nlp): add classification and NER module`

### 5. `recommenders.py`
- Functions:
- `retrieve(text, top_k=10)` → FAISS search.
- `rerank(candidates, meta)` → rule-based sorting by score.
- `finalize(template, entities)` → rewrite via LLM (no hallucinations).
- **Commit:** `feat(recommender): add retrieval and ranking logic`

### 6. `api.py`
- FastAPI endpoints:
- `/healthz` → OK check.
- `/analyze` → classify + retrieve + return top3.
- `/respond` → finalize answer.
- `/feedback` → save feedback JSONL.
- Enable CORS for frontend.
- **Commit:** `feat(api): add FastAPI endpoints`

### 7. Docker + Compose
- Create `Dockerfile.backend`, `docker-compose.yml`.
- Backend runs `uvicorn app.api:app --host 0.0.0.0 --port 8000`
- Auto-run index build at startup.
- **Commit:** `chore(docker): add backend Docker setup`

---

## 🧭 Frontend Tasks

### 1. Scaffold Vite + React + TypeScript
- Components:
- `AnalyzeForm` → textarea + submit
- `ResultPanel` → shows classification & confidence
- `EntityEditor` → key/value edit
- `Recommendations` → list of top-3 answers
- `FinalAnswer` → editable + copy button + feedback
- **Commit:** `feat(frontend): scaffold React app`

### 2. API Client (`lib/api.ts`)
```ts
export async function analyze(text: string) { /* calls /analyze */ }
export async function respond(data: any) { /* calls /respond */ }
export async function feedback(data: any) { /* calls /feedback */ }
Add error handling and loading states.

Commit: feat(frontend): add API client

3. Styling
Minimal CSS / Tailwind.

Responsive two-column layout (input → result).

Spinners and error handling.

Commit: style(frontend): improve UI/UX

4. Docker
Dockerfile.frontend: build Vite app, serve with serve -s dist.

Commit: chore(docker): add frontend Docker build

🧰 Git Workflow
Use Conventional Commits:

bash
Всегда показывать подробности

Копировать код
git init
git add .
git commit -m "chore: initial commit"
git add backend/app/settings.py
git commit -m "feat(settings): add env config"
git add backend/app/scibox_client.py
git commit -m "feat(client): implement SciBox API wrapper"
git add backend/app/build_index.py
git commit -m "feat(index): build FAISS index"
git add backend/app/classifiers.py
git commit -m "feat(nlp): classification and NER"
git add backend/app/recommenders.py
git commit -m "feat(recommender): retrieval and ranking"
git add backend/app/api.py
git commit -m "feat(api): FastAPI endpoints"
git add frontend/*
git commit -m "feat(frontend): create React interface"
git add Dockerfile.* docker-compose.yml
git commit -m "chore(docker): finalize containerization"
🚀 Run Instructions
bash
Всегда показывать подробности

Копировать код
# Build and run
docker compose up --build
# Backend → http://localhost:8000
# Frontend → http://localhost:8080
✅ Acceptance Criteria
Classification & entity extraction accurate on 3 test inputs.

Recommendations are relevant and grounded in FAQ.

Frontend displays category, subcategory, confidence, top-3 answers.

Final answer editable & copyable.

Feedback stored in backend.

All modules tracked with proper Git commits.

🔒 Safety & Guardrails
No hallucinations — output only from FAQ.

Mask PII in logs.

Deterministic responses (temperature=0).

Clear error messages in UI.

"""