const API = (path) => `${location.origin.replace(/:\d+$/, ":8000")}${path}`;

const sessionKey = "smart-support-session";
const themeKey = "smart-support-theme";

const state = {
  lastQuery: "",
  lastResults: [],
  selectedResultId: null,
  lastClassification: null,
  classificationVotes: { main: null, sub: null },
  templateVote: null,
  lastTopItemId: null,
  isLoading: false,
  chatHistory: [],
  activeChatMessageId: null,
  chatHistorySignature: "",
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

export async function postChatMessage(payload) {
  const res = await fetch(API("/api/message"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, session_id: sessionId }),
  });
  return handleResponse(res);
}

export async function fetchChatHistory() {
  const res = await fetch(API("/api/messages"));
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

function formatDateTime(value) {
  if (!value) return "";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function renderChatHistory(entries) {

  const root = document.querySelector("#chatHistory");

  if (!root) return;

  const list = Array.isArray(entries) ? entries : [];

  state.chatHistory = list;

  state.chatHistorySignature = JSON.stringify(list);

  root.innerHTML = "";

  if (!list.length) {

    const empty = document.createElement("div");

    empty.className = "chat-empty";

    empty.textContent = "История пуста. Ожидаем сообщения клиента.";

    root.appendChild(empty);

    return;

  }

  list.forEach((entry) => {

    const isClient = entry.sender === "client" || entry.sender === "user";

    const roleClass = isClient ? "client" : "operator";

    const message = document.createElement("div");

    message.className = `chat-message ${roleClass}`;

    message.dataset.messageId = String(entry.id);

    if (entry.id === state.activeChatMessageId) {

      message.classList.add("active");

    }

    if (isClient) {

      message.classList.add("clickable");

      message.addEventListener("click", () => setActiveChatMessage(entry.id));

    }

    const header = document.createElement("div");

    header.className = "message-header";

    const author = isClient ? "Клиент" : "Поддержка";

    const metaParts = [author, formatDateTime(entry.timestamp)].filter(Boolean);

    header.textContent = metaParts.join(" • " );

    message.appendChild(header);

    const body = document.createElement("div");

    body.className = "message-text";

    body.innerHTML = formatSnippet(entry.text || "");

    message.appendChild(body);

    const details = [entry.category, entry.subcategory]

      .filter(Boolean)

      .join(" / " );

    if (details) {

      const meta = document.createElement("div");

      meta.className = "message-meta";

      meta.textContent = details;

      message.appendChild(meta);

    }

    root.appendChild(message);

  });

  root.scrollTop = root.scrollHeight;

}

function findLatestClientMessage(messages = state.chatHistory) {

  for (let i = messages.length - 1; i >= 0; i -= 1) {

    const entry = messages[i];

    if (entry.sender === "client" || entry.sender === "user") {

      return entry;

    }

  }

  return null;

}

function highlightActiveChatMessage() {

  const nodes = document.querySelectorAll("#chatHistory .chat-message");

  nodes.forEach((node) => {

    const id = Number(node.dataset.messageId);

    node.classList.toggle("active", id === state.activeChatMessageId);

  });

}

function setActiveChatMessage(messageId, { autoProcess = false } = {}) {

  const target = state.chatHistory.find((entry) =>

    entry.id === messageId && (entry.sender === "client" || entry.sender === "user")

  );

  if (!target) {

    return;

  }

  state.activeChatMessageId = target.id;

  state.lastQuery = target.text || "";

  highlightActiveChatMessage();

  const template = document.querySelector("#responseTemplate");

  if (template && (autoProcess || !template.value)) {

    template.value = target.template_answer || "";

  }

  updateClassification({

    category: target.category || null,

    subcategory: target.subcategory || null,

    category_confidence: null,

    subcategory_confidence: null,

  });

  renderResults([]);

  if (autoProcess && target.text) {

    runWorkflow({ text: target.text, silent: true });

  }

}

function getActiveClientMessage() {

  if (!state.chatHistory.length) {

    return null;

  }

  if (state.activeChatMessageId) {

    const selected = state.chatHistory.find((entry) =>

      entry.id === state.activeChatMessageId &&

      (entry.sender === "client" || entry.sender === "user")

    );

    if (selected) {

      return selected;

    }

  }

  return findLatestClientMessage(state.chatHistory);

}

async function refreshChatHistory({ silent = false } = {}) {

  try {

    const data = await fetchChatHistory();

    const messages = Array.isArray(data.messages) ? data.messages : [];

    const serialized = JSON.stringify(messages);

    const changed = serialized !== state.chatHistorySignature;

    if (changed) {

      renderChatHistory(messages);

    } else {

      state.chatHistory = messages;

      highlightActiveChatMessage();

    }

    const latestClient = findLatestClientMessage(messages);

    if (latestClient) {

      if (!state.activeChatMessageId || changed) {

        setActiveChatMessage(latestClient.id, { autoProcess: changed });

      }

    } else {

      state.activeChatMessageId = null;

      highlightActiveChatMessage();

    }

  } catch (err) {

    if (!silent) {

      console.warn("Не удалось получить чат:", err);

    }

  }

}

function setChoiceButtonState(
  button,
  { active = false, disabled = false } = {}
) {
  if (!button) return;
  button.classList.toggle("active", Boolean(active));
  button.disabled = Boolean(disabled);
  button.setAttribute("aria-pressed", active ? "true" : "false");
}

function getSelectedResult() {
  if (!state.lastResults.length || !state.selectedResultId) {
    return null;
  }
  return (
    state.lastResults.find(
      (item) => Number(item.id) === Number(state.selectedResultId)
    ) || null
  );
}

function updateTemplateControls() {
  const hasSelection = Boolean(getSelectedResult());
  const positiveBtn = document.querySelector("#templateYes");
  const negativeBtn = document.querySelector("#templateNo");

  setChoiceButtonState(positiveBtn, {
    active: state.templateVote === true,
    disabled: !hasSelection,
  });
  setChoiceButtonState(negativeBtn, {
    active: state.templateVote === false,
    disabled: !hasSelection,
  });
}

function setSelectedResult(resultId, { rerender = true } = {}) {
  state.selectedResultId = resultId ?? null;
  const selected = getSelectedResult();
  state.lastTopItemId = selected?.id ?? null;
  updateTemplate(selected);
  state.templateVote = null;
  updateTemplateControls();
  if (rerender) {
    renderResults(state.lastResults);
  }
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
    const isSelected = Number(item.id) === Number(state.selectedResultId);
    li.className = "similar-question";
    if (isSelected) {
      li.classList.add("selected");
    }
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
      ?.addEventListener("click", (event) => {
        event.stopPropagation();
        submitFeedback(
          state.lastQuery,
          item.id,
          true,
          "Спасибо за оценку!"
        );
      });

    li
      .querySelector('[data-action="dislike"]')
      ?.addEventListener("click", (event) => {
        event.stopPropagation();
        submitFeedback(
          state.lastQuery,
          item.id,
          false,
          "Спасибо, мы учтем ваш отзыв."
        );
      });

    li.addEventListener("click", (event) => {
      if (event.target.closest("[data-action]")) {
        return;
      }
      if (Number(state.selectedResultId) === Number(item.id)) {
        return;
      }
      setSelectedResult(item.id);
    });

    root.appendChild(li);
  });
}

function updateTemplate(firstResult) {
  const template = document.querySelector("#responseTemplate");
  if (!template) return;
  template.value = firstResult?.snippet || "";
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

function updateClassificationControls() {
  const classification = state.lastClassification;
  const hasMain = Boolean(classification?.category);
  const hasSub = Boolean(classification?.subcategory);

  setChoiceButtonState(document.querySelector("#mainCategoryYes"), {
    active: state.classificationVotes.main === true,
    disabled: !hasMain,
  });
  setChoiceButtonState(document.querySelector("#mainCategoryNo"), {
    active: state.classificationVotes.main === false,
    disabled: !hasMain,
  });

  setChoiceButtonState(document.querySelector("#subCategoryYes"), {
    active: state.classificationVotes.sub === true,
    disabled: !hasSub,
  });
  setChoiceButtonState(document.querySelector("#subCategoryNo"), {
    active: state.classificationVotes.sub === false,
    disabled: !hasSub,
  });
}

function setClassificationVoteInProgress(target, inProgress) {
  const selectors =
    target === "main"
      ? ["#mainCategoryYes", "#mainCategoryNo"]
      : ["#subCategoryYes", "#subCategoryNo"];
  selectors.forEach((selector) => {
    const button = document.querySelector(selector);
    if (!button) return;
    if (inProgress) {
      button.disabled = true;
      button.dataset.loading = "1";
    } else {
      delete button.dataset.loading;
    }
  });
}

async function handleClassificationVote(target, correct) {
  const classification = state.lastClassification;
  if (!classification) {
    showBanner("Нет данных классификации для оценки.");
    return;
  }

  if (target === "main" && !classification.category) {
    showBanner("Основная категория не определена.");
    return;
  }

  if (target === "sub" && !classification.subcategory) {
    showBanner("Подкатегория не определена.");
    return;
  }

  if (state.classificationVotes[target] === correct) {
    return;
  }

  setClassificationVoteInProgress(target, true);
  try {
    await postClassificationVote({
      target,
      correct,
      category: classification.category,
      subcategory: classification.subcategory,
    });
    state.classificationVotes[target] = correct;
    refreshStats();
  } catch (err) {
    showBanner(
      err?.message || "Не удалось сохранить оценку классификации."
    );
  } finally {
    setClassificationVoteInProgress(target, false);
    updateClassificationControls();
  }
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
      mainNode.classList.add("determined");
    } else {
      mainNode.textContent = "Не определено";
      mainNode.classList.remove("determined");
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
      subNode.classList.add("determined");
    } else {
      subNode.textContent = "Не определено";
      subNode.classList.remove("determined");
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

  renderChatHistory(history || []);
}

async function refreshStats() {
  try {
    const summary = await loadStats();
    applyStats(summary);
  } catch (err) {
    console.warn("Не удалось получить статистику:", err);
  }
}

async function runWorkflow({ text, silent = false } = {}) {

  if (state.isLoading) return;

  const source = text ?? state.lastQuery ?? "";

  const query = source.trim();

  if (!query) {

    if (!silent) {

      showBanner("Нет сообщения клиента.");

    }

    return;

  }

  state.lastQuery = query;

  state.isLoading = true;

  if (!silent) {

    toggleLoading(true);

    showBanner("");

  }

  try {

    const [searchResult, classifyResult] = await Promise.all([

      search(query),

      classify(query),

    ]);

    state.lastResults = searchResult.results ?? [];

    const primaryId = state.lastResults[0]?.id ?? null;

    setSelectedResult(primaryId, { rerender: false });

    renderResults(state.lastResults);

    updateClassification(classifyResult.raw);

    if (!silent) {

      refreshStats();

    }

  } catch (err) {

    if (!silent) {

      showBanner(err.message || "Произошла ошибка при обращении к API.");

    } else {

      console.warn('Автообработка не удалась:', err);

    }

  } finally {

    state.isLoading = false;

    if (!silent) {

      toggleLoading(false);

    }

  }

}

function bindTemplateButtons() {
  const positive = document.querySelector("#templateYes");
  const negative = document.querySelector("#templateNo");

  const handleTemplateFeedback = (isPositive) => {
    const selected = getSelectedResult();
    if (!state.lastQuery || !selected) {
      showBanner("Нет выбранного ответа для оценки.");
      return;
    }
    submitFeedback(
      state.lastQuery,
      selected.id,
      isPositive,
      isPositive
        ? "Благодарим за подтверждение!"
        : "Спасибо, мы улучшим ответ."
    ).then((ok) => {
      if (ok) {
        state.templateVote = isPositive;
        updateTemplateControls();
      }
    });
  };

  positive?.addEventListener("click", () => handleTemplateFeedback(true));
  negative?.addEventListener("click", () => handleTemplateFeedback(false));
}

function bindClassificationButtons() {
  const mainYes = document.querySelector("#mainCategoryYes");
  const mainNo = document.querySelector("#mainCategoryNo");
  const subYes = document.querySelector("#subCategoryYes");
  const subNo = document.querySelector("#subCategoryNo");

  mainYes?.addEventListener("click", () => handleClassificationVote("main", true));
  mainNo?.addEventListener("click", () => handleClassificationVote("main", false));
  subYes?.addEventListener("click", () => handleClassificationVote("sub", true));
  subNo?.addEventListener("click", () => handleClassificationVote("sub", false));
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

  const processButton = document.querySelector("#processRequest");

  if (processButton) {

    processButton.addEventListener("click", () => {

      const target = getActiveClientMessage();

      runWorkflow({ text: target?.text ?? "" });

    });

  }

  const refreshButton = document.querySelector("#chatRefresh");

  if (refreshButton) {

    refreshButton.addEventListener("click", () => refreshChatHistory());

  }

  const sendButton = document.querySelector("#sendResponse");

  if (sendButton) {

    sendButton.addEventListener("click", async () => {

      const template = document.querySelector("#responseTemplate");

      const responseText = template?.value?.trim() ?? "";

      if (!responseText) {

        showBanner("Нет текста ответа.");

        return;

      }

      const target = getActiveClientMessage();

      if (!target) {

        showBanner("Нет сообщения клиента для ответа.");

        return;

      }

      try {

        const selected = getSelectedResult();

        await postChatMessage({

          sender: "support",

          text: responseText,

          category: state.lastClassification?.category ?? target.category ?? null,

          subcategory: state.lastClassification?.subcategory ?? target.subcategory ?? null,

          template_id: selected ? selected.id : null,

          template_answer: responseText,

        });

        if (state.lastQuery) {

          await postResponseLog({

            query: state.lastQuery,

            category: state.lastClassification?.category ?? null,

            subcategory: state.lastClassification?.subcategory ?? null,

            main_vote: state.classificationVotes.main,

            sub_vote: state.classificationVotes.sub,

            template_text: responseText,

            template_positive: state.templateVote,

            top_item_id: selected ? selected.id : null,

          });

        }

        await refreshChatHistory({ silent: true });

        refreshStats();

        showBanner("Ответ отправлен клиенту.", "success");

      } catch (err) {

        console.error("Не удалось отправить ответ:", err);

        showBanner("Не удалось отправить ответ.");

      }

    });

  }

}

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  bindTemplateButtons();
  bindClassificationButtons();
  bindThemeToggle();
  updateTemplateControls();
  updateClassificationControls();
  refreshStats();
  refreshChatHistory();
  setInterval(refreshStats, 60_000);
  setInterval(() => refreshChatHistory({ silent: true }), 5_000);
});
