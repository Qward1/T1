const API = (path) => `${location.origin.replace(/:\d+$/, ":8000")}${path}`;

const sessionKey = "smart-support-session";
const themeKey = "smart-support-theme";

const state = {
  lastQuery: "",
  lastResults: [],
  lastClassification: null,
  classificationVotes: { main: null, sub: null },
  templateVote: null,
  lastTopItemId: null,
  isLoading: false,
};

const sessionId = loadSessionId();

function loadSessionId() {
  try {
    const stored = localStorage.getItem(sessionKey);
    if (stored) return stored;
  } catch (_) {
    /* ignore */
  }
  const fresh =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `${Date.now().toString(16)}-${Math.random().toString(16).slice(2, 10)}`;
  try {
    localStorage.setItem(sessionKey, fresh);
  } catch (_) {
    /* ignore */
  }
  return fresh;
}

async function handleResponse(res) {
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch (_) {
    data = {};
  }
  if (!res.ok) {
    const message =
      data?.error?.message || data?.detail || `HTTP ${res.status}`;
    throw new Error(message);
  }
  return data;
}

export async function search(query, topK = 5) {
  const res = await fetch(API("/api/search"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: topK, session_id: sessionId }),
  });
  return handleResponse(res);
}

export async function classify(text) {
  const res = await fetch(API("/api/classify"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, session_id: sessionId }),
  });
  return handleResponse(res);
}

export async function sendFeedback(payload) {
  const res = await fetch(API("/api/feedback"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, session_id: sessionId }),
  });
  return handleResponse(res);
}

export async function loadStats() {
  const res = await fetch(API("/api/stats/summary"));
  return handleResponse(res);
}

async function postClassificationVote(body) {
  const res = await fetch(API("/api/quality/classification"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, session_id: sessionId }),
  });
  return handleResponse(res);
}

async function postTemplateVote(body) {
  const res = await fetch(API("/api/quality/template"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, session_id: sessionId }),
  });
  return handleResponse(res);
}

async function postResponseLog(body) {
  const res = await fetch(API("/api/history"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, session_id: sessionId }),
  });
  return handleResponse(res);
}

function escapeHTML(value) {
  return (value ?? "")
    .toString()
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatSnippet(value) {
  return escapeHTML(value).replace(/\n/g, "<br>");
}

function showBanner(message, variant = "error") {
  const box = document.querySelector("#errors");
  if (!box) return;
  if (!message) {
    box.style.display = "none";
    box.textContent = "";
    delete box.dataset.variant;
    return;
  }
  box.dataset.variant = variant;
  box.textContent = message;
  box.style.display = "block";
}

function toggleLoading(isLoading) {
  const button = document.querySelector("#processRequest");
  if (!button) return;
  if (!button.dataset.defaultLabel) {
    button.dataset.defaultLabel = button.textContent.trim();
  }
  button.disabled = isLoading;
  button.textContent = isLoading
    ? "Загрузка…"
    : button.dataset.defaultLabel || "Обработать запрос";
}

function renderResults(items) {
  const root = document.querySelector("#results");
  if (!root) return;
  root.innerHTML = "";

  if (!items.length) {
    const empty = document.createElement("li");
    empty.className = "similar-question";
    empty.innerHTML = `<div class="question-title">Ничего не найдено</div>`;
    root.appendChild(empty);
    return;
  }

  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = "similar-question";
    li.innerHTML = `
      <div class="question-title">${escapeHTML(item.title || "Без названия")}</div>
      <div class="question-category">${escapeHTML(item.category || "")} — ${escapeHTML(item.subcategory || "")}</div>
      <p class="question-snippet">${formatSnippet(item.snippet || "")}</p>
      <div class="question-meta" style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
        <span>score: ${Number(item.score ?? 0).toFixed(3)}</span>
        <button class="choice-btn" data-action="like">Полезно</button>
        <button class="choice-btn" data-action="dislike">Не полезно</button>
      </div>
    `;

    li
      .querySelector('[data-action="like"]')
      ?.addEventListener("click", () => {
        submitFeedback(
          state.lastQuery,
          item.id,
          true,
          "Спасибо за оценку!"
        );
      });

    li
      .querySelector('[data-action="dislike"]')
      ?.addEventListener("click", () => {
        submitFeedback(
          state.lastQuery,
          item.id,
          false,
          "Спасибо, мы учтем ваш отзыв."
        );
      });

    root.appendChild(li);
  });
}

function updateTemplate(firstResult) {
  const template = document.querySelector("#responseTemplate");
  if (!template) return;
  template.value = firstResult?.snippet || "";
}

function setVoteButtonState(button, enabled, isActive) {
  if (!button) return;
  button.disabled = !enabled;
  if (!enabled) {
    button.classList.remove("active");
    button.setAttribute("aria-pressed", "false");
    return;
  }
  button.classList.toggle("active", isActive);
  button.setAttribute("aria-pressed", isActive ? "true" : "false");
}

function updateClassificationControls() {
  const classification = state.lastClassification;
  const hasMain = Boolean(classification?.category);
  const hasSub = Boolean(classification?.subcategory);

  setVoteButtonState(
    document.querySelector("#mainCategoryYes"),
    hasMain,
    state.classificationVotes.main === true
  );
  setVoteButtonState(
    document.querySelector("#mainCategoryNo"),
    hasMain,
    state.classificationVotes.main === false
  );
  setVoteButtonState(
    document.querySelector("#subCategoryYes"),
    hasSub,
    state.classificationVotes.sub === true
  );
  setVoteButtonState(
    document.querySelector("#subCategoryNo"),
    hasSub,
    state.classificationVotes.sub === false
  );

  const mainDisplay = document.querySelector("#mainCategory");
  if (mainDisplay) {
    mainDisplay.classList.toggle("determined", hasMain);
  }
  const subDisplay = document.querySelector("#subCategory");
  if (subDisplay) {
    subDisplay.classList.toggle("determined", hasSub);
  }
}

async function handleClassificationVote(target, correct) {
  const classification = state.lastClassification;
  if (!classification) {
    showBanner("Classification is not available yet.");
    return;
  }
  if (target === "main" && !classification.category) {
    showBanner("Main category is missing.");
    return;
  }
  if (target === "sub" && !classification.subcategory) {
    showBanner("Subcategory is missing.");
    return;
  }

  const previous = state.classificationVotes[target];
  state.classificationVotes[target] = correct;
  updateClassificationControls();

  try {
    await postClassificationVote({
      category: classification.category,
      subcategory: classification.subcategory,
      target,
      correct,
    });
    refreshStats();
  } catch (err) {
    state.classificationVotes[target] = previous ?? null;
    updateClassificationControls();
    showBanner(err?.message || "Could not submit classification feedback.");
  }
}

function bindClassificationButtons() {
  [
    { selector: "#mainCategoryYes", target: "main", correct: true },
    { selector: "#mainCategoryNo", target: "main", correct: false },
    { selector: "#subCategoryYes", target: "sub", correct: true },
    { selector: "#subCategoryNo", target: "sub", correct: false },
  ].forEach(({ selector, target, correct }) => {
    const button = document.querySelector(selector);
    if (!button || button.dataset.bound === "1") return;
    button.dataset.bound = "1";
    button.addEventListener("click", () =>
      handleClassificationVote(target, correct)
    );
  });

  updateClassificationControls();
}

function submitFeedback(query, itemId, useful, successMessage) {
  if (!query || !itemId) {
    showBanner("Отсутствуют данные для отправки отзыва.");
    return Promise.resolve(false);
  }
  return sendFeedback({ query, item_id: itemId, useful })
    .then(() => {
      if (successMessage) {
        showBanner(successMessage, "success");
      }
      refreshStats();
      return true;
    })
    .catch((err) => {
      showBanner(err.message);
      return false;
    });
}

function updateClassification(raw) {
  state.lastClassification = raw
    ? {
        category: raw?.category || null,
        subcategory: raw?.subcategory || null,
      }
    : null;
  state.classificationVotes = { main: null, sub: null };
  updateClassificationControls();

  const mainNode = document.querySelector("#mainCategory");
  const subNode = document.querySelector("#subCategory");

  if (mainNode) {
    if (raw?.category) {
      const percent = raw.category_confidence
        ? `${Math.round(raw.category_confidence * 100)}%`
        : "";
      mainNode.textContent = percent
        ? `${raw.category} (${percent})`
        : raw.category;
    } else {
      mainNode.textContent = "Не определено";
    }
  }

  if (subNode) {
    if (raw?.subcategory) {
      const percent = raw.subcategory_confidence
        ? `${Math.round(raw.subcategory_confidence * 100)}%`
        : "";
      subNode.textContent = percent
        ? `${raw.subcategory} (${percent})`
        : raw.subcategory;
    } else {
      subNode.textContent = "Не определено";
    }
  }
}

function applyStats(summary) {
  if (!summary) return;
  const { search, classify, feedback } = summary;

  const totalRequests = document.querySelector("#totalRequests");
  if (totalRequests) totalRequests.textContent = `${search.total}`;

  const todayRequests = document.querySelector("#todayRequests");
  if (todayRequests) todayRequests.textContent = `${classify.total}`;

  const autoResolved = document.querySelector("#autoResolved");
  if (autoResolved) autoResolved.textContent = `${search.success}`;

  const answerAccuracy = document.querySelector("#answerAccuracy");
  if (answerAccuracy) {
    answerAccuracy.textContent = `${(search.success_rate * 100).toFixed(1)}%`;
  }

  const clientRating = document.querySelector("#clientRating");
  if (clientRating) {
    clientRating.textContent = `${(feedback.positive_rate * 100).toFixed(1)}%`;
  }

  const mainCategoryAccuracy = document.querySelector("#mainCategoryAccuracy");
  if (mainCategoryAccuracy) {
    mainCategoryAccuracy.textContent = `${(
      classify.success_rate * 100
    ).toFixed(1)}%`;
  }

  const subCategoryAccuracy = document.querySelector("#subCategoryAccuracy");
  if (subCategoryAccuracy) {
    subCategoryAccuracy.textContent = `${(
      classify.avg_score * 100
    ).toFixed(1)}%`;
  }
}

async function refreshStats() {
  try {
    const summary = await loadStats();
    applyStats(summary);
  } catch (err) {
    console.warn("Не удалось получить статистику:", err);
  }
}

async function runWorkflow() {
  if (state.isLoading) return;

  const textarea = document.querySelector("#clientRequest");
  const query = textarea?.value?.trim() ?? "";
  if (!query) {
    showBanner("Введите текст запроса.");
    return;
  }

  state.isLoading = true;
  toggleLoading(true);
  showBanner("");

  try {
    state.lastQuery = query;
    const [searchResult, classifyResult] = await Promise.all([
      search(query),
      classify(query),
    ]);

    state.lastResults = searchResult.results ?? [];
    renderResults(state.lastResults);
    updateTemplate(state.lastResults[0]);
    updateClassification(classifyResult.raw);

    refreshStats();
  } catch (err) {
    showBanner(err.message || "Произошла ошибка при обращении к API.");
  } finally {
    state.isLoading = false;
    toggleLoading(false);
  }
}

function bindTemplateButtons() {
  const positive = document.querySelector("#templateYes");
  const negative = document.querySelector("#templateNo");

  if (positive) {
    positive.addEventListener("click", () => {
      const top = state.lastResults[0];
      if (!state.lastQuery || !top) {
        showBanner("Нет результата для оценки.");
        return;
      }
      submitFeedback(
        state.lastQuery,
        top.id,
        true,
        "Благодарим за подтверждение!"
      );
    });
  }

  if (negative) {
    negative.addEventListener("click", () => {
      const top = state.lastResults[0];
      if (!state.lastQuery || !top) {
        showBanner("Нет результата для оценки.");
        return;
      }
      submitFeedback(
        state.lastQuery,
        top.id,
        false,
        "Спасибо, мы улучшим ответ."
      );
    });
  }
}

function bindThemeToggle() {
  const toggle = document.querySelector("#themeToggle");
  if (!toggle) return;

  const apply = (theme) => {
    if (theme === "dark") {
      document.body.dataset.theme = "dark";
      toggle.querySelector(".sun-icon").style.display = "none";
      toggle.querySelector(".moon-icon").style.display = "block";
    } else {
      delete document.body.dataset.theme;
      toggle.querySelector(".sun-icon").style.display = "block";
      toggle.querySelector(".moon-icon").style.display = "none";
    }
    try {
      localStorage.setItem(themeKey, theme || "");
    } catch (_) {
      /* ignore */
    }
  };

  let stored = "";
  try {
    stored = localStorage.getItem(themeKey) || "";
  } catch (_) {
    stored = "";
  }
  if (stored) apply(stored);

  toggle.addEventListener("click", () => {
    const next = document.body.dataset.theme === "dark" ? "" : "dark";
    apply(next);
  });
}

function bindEvents() {
  const button = document.querySelector("#processRequest");
  if (button) {
    button.addEventListener("click", runWorkflow);
  }

  const textarea = document.querySelector("#clientRequest");
  if (textarea) {
    textarea.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        runWorkflow();
      }
    });
  }

  const sendButton = document.querySelector("#sendResponse");
  if (sendButton) {
    sendButton.addEventListener("click", () => {
      const template = document.querySelector("#responseTemplate");
      if (!template?.value) {
        showBanner("Нет ответа для отправки.");
        return;
      }
      if (navigator.clipboard?.writeText) {
        navigator.clipboard
          .writeText(template.value)
          .then(() =>
            showBanner("Ответ скопирован в буфер обмена.", "success")
          )
          .catch(() => showBanner("Не удалось скопировать ответ."));
      } else {
        showBanner("В браузере недоступен буфер обмена.");
      }
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  bindClassificationButtons();
  bindTemplateButtons();
  bindThemeToggle();
  refreshStats();
  setInterval(refreshStats, 60_000);
});
