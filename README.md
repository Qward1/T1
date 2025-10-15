# FAQ Assistant

Р’ РїСЂРѕРµРєС‚Рµ СЃРѕР±СЂР°РЅС‹ FastAPI-Р±СЌРєРµРЅРґ Рё СЃС‚Р°С‚РёС‡РµСЃРєРёР№ С„СЂРѕРЅС‚РµРЅРґ РґР»СЏ Р±С‹СЃС‚СЂРѕРіРѕ РѕС‚РІРµС‚Р° РѕРїРµСЂР°С‚РѕСЂР° СЃР»СѓР¶Р±С‹ РїРѕРґРґРµСЂР¶РєРё РЅР° Р·Р°РїСЂРѕСЃС‹ РєР»РёРµРЅС‚РѕРІ.

## Р‘С‹СЃС‚СЂС‹Р№ СЃС‚Р°СЂС‚

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# РёР»Рё
source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

РЎРѕР·РґР°Р№С‚Рµ С„Р°Р№Р» `.env` (РїРѕ РЅРµРѕР±С…РѕРґРёРјРѕСЃС‚Рё) Рё РїСЂРѕРїРёС€РёС‚Рµ РѕР±СЏР·Р°С‚РµР»СЊРЅС‹Рµ РїРµСЂРµРјРµРЅРЅС‹Рµ РѕРєСЂСѓР¶РµРЅРёСЏ:

```env
SCIBOX_API_KEY=РІР°С€_api_РєР»СЋС‡
SCIBOX_BASE_URL=https://api.scibox.ai/v1
# FAQ_PATH=/path/to/faq.xlsx  # РЅСѓР¶РµРЅ С‚РѕР»СЊРєРѕ РґР»СЏ РїРµСЂРµСЃР±РѕСЂРєРё РёРЅРґРµРєСЃР°
```

## Р—Р°РїСѓСЃРє СЂР°Р·СЂР°Р±РѕС‚РєРё

```bash
make dev
```

РљРѕРјР°РЅРґР° РїРѕРґРЅРёРјР°РµС‚ `uvicorn` РЅР° `http://127.0.0.1:8000`. РћС‚РєСЂРѕР№С‚Рµ РІ Р±СЂР°СѓР·РµСЂРµ С„Р°Р№Р» `frontend/index_clean.html`, РёРЅС‚РµСЂС„РµР№СЃ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё РѕР±СЂР°С‰Р°РµС‚СЃСЏ Рє Р»РѕРєР°Р»СЊРЅРѕРјСѓ API.

## РџСЂРѕРІРµСЂРєРё

```bash
make fmt   # ruff + black
make test  # pytest + httpx
```

## РћСЃРЅРѕРІРЅС‹Рµ СЌРЅРґРїРѕРёРЅС‚С‹

- `POST /api/search` вЂ” СЃРµРјР°РЅС‚РёС‡РµСЃРєРёР№ РїРѕРёСЃРє FAQ.
- `POST /api/classify` вЂ” РєР»Р°СЃСЃРёС„РёРєР°С†РёСЏ Рё NER.
- `POST /api/feedback` вЂ” СЃР±РѕСЂ РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё.
- `GET /api/stats/summary` вЂ” Р°РіСЂРµРіРёСЂРѕРІР°РЅРЅР°СЏ СЃС‚Р°С‚РёСЃС‚РёРєР°.
- `POST /api/index/rebuild` вЂ” РїРµСЂРµСЃР±РѕСЂРєР° РёРЅРґРµРєСЃР° (С‚СЂРµР±СѓРµС‚ Р·Р°РіРѕР»РѕРІРѕРє `X-Admin-Token`).

## РЎС‚СЂСѓРєС‚СѓСЂР° РїСЂРѕРµРєС‚Р°

```
backend/          # FastAPI Рё Р±РёР·РЅРµСЃ-Р»РѕРіРёРєР°
frontend/         # СЃС‚Р°С‚РёС‡РµСЃРєРёР№ UI (index_clean.html + app.js)
data/             # sqlite Рё СЌРјР±РµРґРґРёРЅРіРё
tests/            # smoke-С‚РµСЃС‚С‹ API
```

## РџРµСЂРµСЃР±РѕСЂРєР° РёРЅРґРµРєСЃР°

РЈР±РµРґРёС‚РµСЃСЊ, С‡С‚Рѕ РІ `.env` СѓРєР°Р·Р°РЅ `FAQ_PATH` РЅР° Excel-С„Р°Р№Р» СЃ РёСЃС…РѕРґРЅС‹Рј FAQ, Р·Р°С‚РµРј:

```bash
python -m backend.build_index
```

РџРѕСЃР»Рµ РїРµСЂРµСЃР±РѕСЂРєРё РІС‹Р·РѕРІРёС‚Рµ `POST /api/index/rebuild`, С‡С‚РѕР±С‹ РѕР±РЅРѕРІРёС‚СЊ РєСЌС€ СЌРјР±РµРґРґРёРЅРіРѕРІ.
## Windows: run without make

If `make` is unavailable in PowerShell, bring everything up with:

```powershell
python dev.py
```

This starts the API at http://127.0.0.1:8000, the операторский интерфейс at http://127.0.0.1:3000/index_clean.html, and the клиентский чат at http://127.0.0.1:3001.

To run only the API:

```powershell
python -m hypercorn backend.api:app --reload --bind 127.0.0.1:8000
```

```powershell
python dev.py
```
