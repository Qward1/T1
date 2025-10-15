Ты — опытный full-stack разработчик. В этом репозитории уже есть рабочая Python-логика (бэкенд), и есть заготовка фронта index_clean.html. Нужно:

аккуратно оформить и «раскрыть» функциональность бэкенда через чистые HTTP-эндпоинты,

подключить фронт так, чтобы весь функционал доступен из браузера без перезагрузки страницы,

не ломать существующую структуру и артефакты (*.db, *.npy, *.jsonl), а только использовать их.

0) Карта репозитория (важно для ориентирования)
backend/
  __init__.py
  api.py
  build_index.py
  classifiers.py
  recommenders.py
  repository.py
  scibox_client.py
  settings.py
  storage.py
  faq_embeddings.npy
  faq.db
  stats.db
  feedback.jsonl
frontend/
  index_clean.html


Если каталогов backend/ и frontend/ нет, создай их и перемести файлы логически (или настрой импорты без перемещения). Пути в коде должны соответствовать фактической структуре проекта.

1) Проанализируй .py-модули и сформируй слой «сервиса»

Прочитай recommenders.py, classifiers.py, repository.py, storage.py, build_index.py, scibox_client.py и определи публичные функции (например: построение/загрузка индекса, поиск/рекоммендации по faq.db и faq_embeddings.npy, классификация запроса, чтение/запись статистики в stats.db, сохранение фидбэка в feedback.jsonl и т.п.).

Оберни эти функции в service-слой (services/logic.py), чтобы эндпоинты были тонкими: никакой бизнес-логики в контроллерах.

Учти конфигурацию из settings.py (пути к БД/артефактам, флаги и т.п.). Ничего не хардкодить.

2) HTTP-API (FastAPI предпочтительно)

Если api.py уже использует FastAPI/Flask — доработай. Если нет — сделай на FastAPI:

Установи структуру:

backend/
  api.py           # точка входа FastAPI
  routers/
    search.py      # поиск/рекомендации
    classify.py    # классификация
    feedback.py    # сбор обратной связи
    stats.py       # статистика/метрики
  services/logic.py
  models.py        # Pydantic-схемы запросов/ответов


Реализуй эндпоинты (названия/параметры подстрой под реальную логику):

POST /api/search

Вход: { query: str, top_k?: int }

Выход: { results: Array<{id, title, snippet, score, source?}> }

Использует: индекс (faq_embeddings.npy, faq.db) и/или recommenders.py.

POST /api/classify

Вход: { text: str }

Выход: { label: str, confidence: float }

Использует: classifiers.py.

POST /api/feedback

Вход: { query: str, item_id?: str, useful: bool, comment?: str }

Выход: { ok: true }

Аппенд в feedback.jsonl строкой JSON; создай файл, если нет. Записывай timestamp, session_id (из куки/генерации), user_agent.

GET /api/stats/summary

Выход: агрегаты из stats.db (кол-во запросов, CTR, средний score, распределение меток и т.п.). Если в проекте ещё нет сохранения статистики — добавь в service-слое запись события на каждый поиск/классификацию.

POST /api/index/rebuild (опционально, если в build_index.py есть сборка)

Защити простым токеном из settings.py в заголовке X-Admin-Token.

Схемы в models.py (Pydantic): SearchRequest, SearchResult, ClassifyRequest, ClassifyResponse, FeedbackRequest, StatsSummary и т.п.

Обработка ошибок: единый хэндлер, ответы формата {error: {code, message}}, статус-коды 400/404/500.

CORS: включи CORS для index_clean.html при локальной разработке.

Запуск: uvicorn backend.api:app --reload --port 8000

3) Подключи index_clean.html к API

Не переписывай разметку радикально. Добавь минимальный JS-модуль frontend/app.js и подключи его в index_clean.html (в самом низу перед </body>):

<script type="module" src="./app.js"></script>


В app.js:

Возьми ссылки на существующие DOM-элементы (поле запроса, кнопка «Найти», контейнер результатов, блок для классификации, форма фидбэка).

Реализуй функции:

search(query, topK=5) → POST /api/search

classify(text) → POST /api/classify

sendFeedback(payload) → POST /api/feedback

loadStats() → GET /api/stats/summary

Добавь обработчики:

По Enter в поле поиска — search(), отрисовка карточек результатов (заголовок, сниппет, score, кнопка «Полезно/Не полезно» → отправка фидбэка).

Отдельная кнопка «Определить тип запроса» → classify() и вывод метки.

В футере/сайдбаре — панель «Статистика» (простые числа + мини-таблица).

UI-детали:

Показать лоадеры (disabled на кнопках, «Идёт поиск…»).

Показ ошибок (красный блок, текст из {error.message}).

Никаких сторонних сборок — чистый ES-модуль, fetch, без зависимостей.

Примерные фрагменты, которые нужно сгенерировать:

// app.js (фрагменты)
const API = (path) => `${location.origin.replace(/:\d+$/, ':8000')}${path}`; // если фронт на другом порту

export async function search(query, topK = 5) {
  const res = await fetch(API('/api/search'), {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ query, top_k: topK })
  });
  return await handleResponse(res);
}

export async function classify(text) {
  const res = await fetch(API('/api/classify'), {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ text })
  });
  return await handleResponse(res);
}

export async function sendFeedback(payload) {
  const res = await fetch(API('/api/feedback'), {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  });
  return await handleResponse(res);
}

async function handleResponse(res) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.error?.message || `HTTP ${res.status}`);
  return data;
}


И шаблон отрисовки карточек результата:

function renderResults(list) {
  const root = document.querySelector('#results');
  root.innerHTML = '';
  list.forEach(item => {
    const el = document.createElement('article');
    el.className = 'result';
    el.innerHTML = `
      <h3>${escapeHTML(item.title || 'Без названия')}</h3>
      <p>${escapeHTML(item.snippet || '')}</p>
      <div class="meta">
        <span>score: ${Number(item.score ?? 0).toFixed(3)}</span>
        <button class="btn-like">Полезно</button>
        <button class="btn-dislike">Не полезно</button>
      </div>
    `;
    el.querySelector('.btn-like').onclick = () =>
      sendFeedback({ query: lastQuery, item_id: item.id, useful: true });
    el.querySelector('.btn-dislike').onclick = () =>
      sendFeedback({ query: lastQuery, item_id: item.id, useful: false });
    root.appendChild(el);
  });
}

4) Работа с файлами и БД

faq.db: подключайся в repository.py через контекстный менеджер, пул не нужен. Чтение — только SELECT-ы, запись — не требуется (если требуется, используй транзакции).

faq_embeddings.npy: загружай лениво при первом запросе в сервисе поиска. Кэшируй в памяти приложения.

stats.db: создай (если нет) таблицы events(search|classify|feedback) со стандартными полями (id, ts, session_id, payload JSON, extra).

feedback.jsonl: одна строка — один JSON-объект; файл открыт в a+, запись через json.dumps(obj, ensure_ascii=False) + \n, flush().

5) Безопасность и производительность

Включи лимит тела запроса (например, 100KB).

Валидируй входные данные через Pydantic (минимальная длина query, допустимый диапазон top_k).

Добавь простую rate-limit заглушку в памяти по IP/session_id (например, не более 10 запросов в 10 секунд).

Ленивая загрузка тяжёлых артефактов; прогрев кэша при старте по флагу settings.WARMUP.

6) Тесты/скрипты и dev-сценарий

Добавь Makefile (или npm-скрипты для фронта, но можно без них):

make dev — запускает uvicorn и открывает frontend/index_clean.html в браузере.

make fmt — форматирование ruff + black.

make test — быстрые smoke-тесты эндпоинтов (pytest с httpx).

Добавь файл README.md с инструкцией запуска:

python -m venv .venv && source .venv/bin/activate

pip install -r requirements.txt (сгенерируй)

uvicorn backend.api:app --reload --port 8000

Открыть frontend/index_clean.html локально.

7) Качество кода и стиль

Python: ruff, black, импорт-группы, тайпинги, докстринги.

JS: модульный код, функции до 50 строк, без jQuery/фреймворков.

HTML/CSS: не ломай структуру index_clean.html; добавь только минимальные классы и контейнеры #results, #classify, #stats, #errors.

Всё, что не очевидно в логике, — документируй в коде.

8) Критерии готовности (Definition of Done)

 POST /api/search возвращает релевантные результаты за <300 мс при прогретом кэше.

 Классификация работает и отображается во фронте.

 Фидбэк пишется в feedback.jsonl.

 События пишутся в stats.db; /api/stats/summary отдаёт агрегаты.

 В index_clean.html всё взаимодействие без перезагрузки, с понятной обработкой ошибок и лоадерами.

 Репозиторий собирается и запускается с нуля по README.

9) Что именно нужно сгенерировать

Полный код FastAPI-приложения (api.py, routers/*.py, services/logic.py, models.py) с реальными импортами из наших модулей.

JS-модуль frontend/app.js и точечные правки frontend/index_clean.html (только подключение и минимальные контейнеры).

Инициализацию/миграции для stats.db (если нет — создай таблицы при старте).

Обработку feedback.jsonl.

requirements.txt, README.md, необязательный Makefile.

Небольшие smoke-тесты tests/test_api.py.

Если где-то в .py логика уже реализует часть этого — переиспользуй, а не дублируй.

Соблюдай идемпотентность изменений: генерация должна быть аккуратной, без разрушения существующих модулей и с сохранением совместимости импортов.