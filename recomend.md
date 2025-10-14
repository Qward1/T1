Task:
Enhance the existing customer-support assistant code (the one provided earlier) by adding a hybrid FAQ retrieval pipeline that combines zero-shot classification, semantic search, and a fallback mechanism.
Additionally, modify the data storage layer so that the Excel file smart_support_vtb_belarus_faq_final.xlsx is automatically imported into a SQLite database, and all lookups are performed via SQL queries instead of reading Excel files directly.

🎯 High-level goal

Transform the existing system into a smarter and more structured assistant for VTB Belarus bank support, which:

Uses zero-shot classification to detect both main category and subcategory of the user request.

Performs semantic search only within that filtered category/subcategory.

If the classifier’s confidence is low (< 0.5), performs a fallback semantic search across the entire FAQ base.

Loads all FAQ data (categories, subcategories, sample questions, answers) from a SQLite database automatically populated from the Excel file.

🧩 Subtasks for Codex
1. Database layer (SQLite)

Create a new module (e.g. faq_database.py) that:

Automatically loads smart_support_vtb_belarus_faq_final.xlsx into a local SQLite database (e.g. faq.db) on the first run.

Reads the following columns:

"Основная категория" → field: category

"Подкатегория" → field: subcategory

"Пример вопроса" → field: question

"Шаблонный ответ" → field: answer

Creates a table faq_records with columns:
id, category, subcategory, question, answer, and optionally a precomputed embedding column (for caching).

Provides helper functions:

def get_all_categories() -> list[str]: ...
def get_subcategories(category: str) -> list[str]: ...
def get_faq_records(category: str | None = None, subcategory: str | None = None) -> list[dict]: ...


Use sqlite3 or SQLAlchemy for ORM-style access.

2. Zero-shot classification module

Add a new file, e.g. zero_shot_classifier.py.

It should:

Use the existing get_scibox_client() (OpenAI-compatible API).

Implement two functions:

def classify_category(text: str, categories: list[str]) -> tuple[str, float]:
    """Return (predicted_category, confidence)."""

def classify_subcategory(text: str, subcategories: list[str]) -> tuple[str, float]:
    """Return (predicted_subcategory, confidence)."""


Use a prompt-based zero-shot classification approach, e.g.:

You are a text classifier. Given the following user request and possible categories,
choose exactly one that best fits the meaning.

Possible categories: {list of categories}
Request: "{text}"
Respond only with a JSON like {"category": "...", "confidence": 0.0}.


Parse the model output and normalize confidence (0.0–1.0).

3. Semantic search logic (filtered FAISS search)

Modify the existing retrieval logic in faq_retriever.py:

When retrieving results, filter FAQ entries based on the predicted category and subcategory from the classifier.

Build a FAISS index dynamically for that subset only.

If classifier confidence < 0.5, perform the search over all FAQ entries as a fallback.

Keep normalization and similarity scoring as before.

4. Updated pipeline (classify_and_search.py)

Create a new orchestrator module that performs the entire process:

Receive the user’s message.

Retrieve all possible categories from the DB.

Run zero-shot classification → (category, category_conf).

Retrieve subcategories for that category and run subcategory classification → (subcategory, subcat_conf).

If either confidence < 0.5 → mark low_confidence = True.

Run semantic search:

If low_confidence is True → search across all data.

Else → search within the predicted category + subcategory only.

Use the best-matched FAQ record’s answer template and call the existing finalize() function to insert entity values and return the final response.

5. Optional improvements

Cache embeddings in the SQLite DB to avoid recomputation.

Add a simple logging decorator to measure classification and retrieval time.

Add error handling for missing or empty columns.

Optionally expose a function like:

def smart_support_response(user_text: str) -> str:
    """Full end-to-end pipeline: classify → search → finalize."""