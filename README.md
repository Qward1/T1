# Smart Support (VTB Belarus)

Интеллектуальный помощник операторов поддержки: классифицирует обращения, ищет релевантные FAQ и собирает финальный ответ строго по шаблонам.

---

## Требования

- Python 3.11+ (проверено на 3.13)
- Node.js ≥ 18 и npm
- Установленный Docker (опционально, для контейнерного запуска)
- Токен SciBox (`SCIBOX_API_KEY`)

---

## Настройка окружения

1. Скопируйте переменные окружения:
   ```bash
   cp .env.example .env
   ```
2. Отредактируйте `.env`:
   ```ini
   SCIBOX_API_KEY=ваш_ключ
   SCIBOX_BASE_URL=https://llm.t1v.scibox.tech/v1
   FAQ_PATH=C:\Users\Admin\Desktop\T1\smart_support_vtb_belarus_faq_final.xlsx
   ```
   > Для работы в контейнере замените `FAQ_PATH` на `/app/data/smart_support_vtb_belarus_faq_final.xlsx`.
3. Установите зависимости backend (один раз):
   ```bash
   py -3 -m pip install -r backend/requirements.txt
   ```

---

## Единый локальный запуск (backend + frontend)

Скрипт `scripts/start_local.py` автоматически:
- обновляет SQLite-базу и эмбеддинги (`backend/data/faq.db`, `faq_embeddings.npy`);
- запускает FastAPI (`http://localhost:8000`);
- запускает Vite (`http://localhost:5173`).

Команда:
```bash
py -3 scripts/start_local.py
```

На первом запуске дополнительно поставятся зависимости фронтенда (`npm install`). Остановить приложение — `Ctrl+C`.

---

## Docker Compose (альтернатива)

1. Верните в `.env` контейнерный путь `FAQ_PATH=/app/data/smart_support_vtb_belarus_faq_final.xlsx`.
2. Запустите:
   ```bash
   docker compose up --build
   ```

Контейнеры:
- backend — `http://localhost:8000`
- frontend — `http://localhost:8080`

---

## Полезные команды

| Команда | Назначение |
|---------|------------|
| `py -3 -m backend.app.build_index` | Пересобрать базу FAQ и эмбеддинги |
| `py -3 -m uvicorn backend.app.api:app --reload` | Запустить backend вручную |
| `cd frontend && npm run dev` | Запустить frontend отдельно |
| `py -3 -m pip install -r backend/requirements.txt` | Установить/обновить зависимости backend |
| `cd frontend && npm install` | Установить/обновить зависимости frontend |

---

## Что делает сервис

1. **Zero-shot классификация** по списку категорий и подкатегорий из SQLite.
2. **Семантический поиск**: запрос сравнивается с FAQ только выбранного сегмента; при confidence < 0.5 производится поиск по всему справочнику.
3. **Формирование ответа** строго по шаблону FAQ, с аккуратной подстановкой найденных сущностей.
4. **Фронтенд** отображает уверенности, сущности, топ-3 шаблонов и позволяет финально отредактировать ответ и отправить обратную связь.

---

## Где искать данные

- `backend/data/faq.db` — SQLite с исходными FAQ
- `backend/data/faq_embeddings.npy` — нормализованные эмбеддинги вопросов
- `backend/data/feedback.jsonl` — журнал обратной связи операторов

---

## Частые проблемы

- **`Failed to fetch` во фронтенде** — не запущен backend. Используйте `scripts/start_local.py` или запустите Uvicorn вручную.
- **`Connection error` при построении индекса** — проверьте `SCIBOX_API_KEY`/`SCIBOX_BASE_URL` и доступ к интернету.
- **Excel обновился** — удалите `backend/data/faq.db` и `faq_embeddings.npy`, затем снова выполните `py -3 scripts/start_local.py`.

Удачной работы! Если потребуется изменить инфраструктуру (добавить новые источники данных или модели), пересоберите индекс и перезапустите скрипт.

