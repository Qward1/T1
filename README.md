# Smart Support (VTB Belarus)

End-to-end assistant for support agents: classifies customer messages, finds the best FAQ templates, and assembles final answers strictly on templates.

---

## Requirements

- Python 3.11+
- Node.js 18+ and npm
- Docker (optional)
- SciBox API token (SCIBOX_API_KEY)

---

## Environment Setup

1. Copy the sample environment file:
   `ash
   cp .env.example .env
   `
2. Update .env (local run example on Windows):
   `ini
   SCIBOX_API_KEY=your_scibox_token
   SCIBOX_BASE_URL=https://llm.t1v.scibox.tech/v1
   FAQ_PATH=C:\Users\Admin\Desktop\T1\smart_support_vtb_belarus_faq_final.xlsx
   `
   *In containers set FAQ_PATH=/app/data/smart_support_vtb_belarus_faq_final.xlsx.*
3. Install backend dependencies:
   `ash
   py -3 -m pip install -r backend/requirements.txt
   `

---

## One-command local launch (backend + frontend)

Use the helper script – it rebuilds the FAQ index, starts FastAPI and launches Vite dev server:

`ash
py -3 scripts/start_local.py
`

- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- Stop with Ctrl+C.

At the first run the script installs frontend dependencies (
pm install).

---

## Docker Compose alternative

1. Ensure FAQ_PATH=/app/data/smart_support_vtb_belarus_faq_final.xlsx in .env.
2. Start containers:
   `ash
   docker compose up --build
   `

Services:
- backend > http://localhost:8000
- frontend > http://localhost:8080

---

## Key features

1. **Two-step zero-shot classification** (category + subcategory) with product hints extracted from the request.
2. **Segmented semantic search** by category/subcategory with fallback to the whole FAQ when confidence is low.
3. **Template finalisation** – LLM rewrites the selected template with detected entities only.
4. **Runtime analytics** – operators can mark “Correct/Incorrect” for classification and “Yes/No” for templates. Accuracy per category/subcategory, template score, and recent history are stored in SQLite and shown in the “Analytics” panel.
5. **Request history** – every submitted answer (Send answer) is logged for auditing.

---

## Databases & files

- ackend/data/faq.db – FAQ catalogue imported from Excel.
- ackend/data/faq_embeddings.npy – normalised embeddings for FAQ questions.
- ackend/data/stats.db – analytics storage (classification votes, template votes, history).
- ackend/data/feedback.jsonl – raw operator feedback payloads (legacy endpoint).

---

## Useful commands

| Command | Description |
|---------|-------------|
| py -3 -m backend.app.build_index | Rebuild FAQ DB and embeddings |
| py -3 -m uvicorn backend.app.api:app --reload | Manual backend launch |
| cd frontend && npm run dev | Manual frontend launch |
| py -3 -m pip install -r backend/requirements.txt | Install/refresh backend deps |
| cd frontend && npm install | Install/refresh frontend deps |

---

## Troubleshooting

- **Failed to fetch on frontend** – backend is not running. Start scripts/start_local.py or launch Uvicorn manually.
- **Connection error while building the index** – check SciBox credentials and internet access.
- **SQLite file locked** – stop running backend processes (or DB viewers) and rerun the script.
- **Excel updated** – delete ackend/data/faq.db and ackend/data/faq_embeddings.npy, then run py -3 scripts/start_local.py again.

Enjoy supporting your agents with live analytics and template control!
