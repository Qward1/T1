const API = (path) => `${location.origin.replace(/:\d+$/, ":8000")}${path}`;

const sessionKey = "smart-support-session";
const themeKey = "smart-support-theme";

const SCORE_THRESHOLD = 0.5;

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
  activeChatLocked: false,
  chatNodes: new Map(),
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

export async function spellCheckTemplate(text) {
  const res = await fetch(API("/api/spellcheck"), {
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

  if (!list.length) {

    state.chatNodes = new Map();

    root.innerHTML = "";

    const empty = document.createElement("div");

    empty.className = "chat-empty";

    empty.textContent = "История пуста. Ожидаем сообщения клиента.";

    root.appendChild(empty);

    return;

  }

  if (!(state.chatNodes instanceof Map)) {

    state.chatNodes = new Map();

  }

  const existingNodes = state.chatNodes;

  const nextNodes = new Map();

  const fragment = document.createDocumentFragment();

  list.forEach((entry) => {

    const isClient = entry.sender === "client" || entry.sender === "user";

    let message = existingNodes.get(entry.id);

    if (!message) {

      message = document.createElement("div");

      message.className = "chat-message";

      message.dataset.messageId = String(entry.id);

      const headerNode = document.createElement("div");

      headerNode.className = "message-header";

      message.appendChild(headerNode);

      const bodyNode = document.createElement("div");

      bodyNode.className = "message-text";

      message.appendChild(bodyNode);

      const metaNode = document.createElement("div");

      metaNode.className = "message-meta";

      message.appendChild(metaNode);

      message._header = headerNode;

      message._body = bodyNode;

      message._meta = metaNode;

    }

    if (isClient && message.dataset.clickBound !== "1") {

      message.dataset.clickBound = "1";

      message.addEventListener("click", () =>

        setActiveChatMessage(entry.id, { manual: true })

      );

    }

    let header = message._header || message.querySelector(".message-header");

    let body = message._body || message.querySelector(".message-text");

    let meta = message._meta || message.querySelector(".message-meta");

    if (!message._header && header) {

      message._header = header;

    }

    if (!message._body && body) {

      message._body = body;

    }

    if (!meta) {

      meta = document.createElement("div");

      meta.className = "message-meta";

      message.appendChild(meta);

    }

    if (!message._meta && meta) {

      message._meta = meta;

    }

    message.className = "chat-message";

    message.classList.toggle("client", isClient);

    message.classList.toggle("operator", !isClient);

    message.classList.toggle("clickable", isClient);

    message.dataset.messageId = String(entry.id);

    message.classList.toggle("active", entry.id === state.activeChatMessageId);

    const author = isClient ? "Клиент" : "Поддержка";

    const metaParts = [author, formatDateTime(entry.timestamp)].filter(Boolean);

    if (header) {

      header.textContent = metaParts.join(" • " );

    }

    if (body) {

      body.innerHTML = formatSnippet(entry.text || "");

    }

    const timestampText = formatDateTime(entry.timestamp);

    if (meta) {

      if (timestampText) {

        meta.textContent = timestampText;

        meta.style.display = "";

      } else {

        meta.textContent = "";

        meta.style.display = "none";

      }

    }

    fragment.appendChild(message);

    nextNodes.set(entry.id, message);

  });

  root.replaceChildren(fragment);

  state.chatNodes = nextNodes;

  if (state.activeChatLocked) {

    const activeNode = root.querySelector(`[data-message-id="${state.activeChatMessageId}"]`);

    if (activeNode) {

      activeNode.scrollIntoView({ block: "center" });

    }

  } else {

    root.scrollTop = root.scrollHeight;

  }

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

function setActiveChatMessage(messageId, { autoProcess = false, manual = false } = {}) {

  const target = state.chatHistory.find((entry) =>

    entry.id === messageId && (entry.sender === "client" || entry.sender === "user")

  );

  if (!target) {

    return;

  }

  state.activeChatMessageId = target.id;

  state.activeChatLocked = Boolean(manual);

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

  if (autoProcess && !manual && target.text) {

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

      const activeExists =

        state.activeChatMessageId &&
        messages.some(

          (entry) =>

            entry.id === state.activeChatMessageId &&
            (entry.sender === "client" || entry.sender === "user")

        );

      if (!activeExists) {

        state.activeChatLocked = false;

        setActiveChatMessage(latestClient.id, { autoProcess: changed, manual: false });

      } else if (!state.activeChatLocked && changed && latestClient.id !== state.activeChatMessageId) {

        setActiveChatMessage(latestClient.id, { autoProcess: true, manual: false });

      } else {

        highlightActiveChatMessage();

      }

    } else {

      state.activeChatMessageId = null;

      state.activeChatLocked = false;

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

  const visibleItems = items.slice(0, 3);

  if (!visibleItems.length) {
    const empty = document.createElement("li");
    empty.className = "similar-question";
    const thresholdText = SCORE_THRESHOLD.toFixed(1);
    empty.innerHTML = `<div class="question-title">Подходящего ответа нет (score &lt; ${thresholdText}).</div>`;
    root.appendChild(empty);
    return;
  }

  visibleItems.forEach((item) => {
    const li = document.createElement("li");
    const isSelected = Number(item.id) === Number(state.selectedResultId);
    li.className = "similar-question";
    if (isSelected) {
      li.classList.add("selected");
    }
    li.innerHTML = `
      <div class="question-title">${escapeHTML(item.title || "Без названия")}</div>
      <p class="question-snippet">${formatSnippet(item.snippet || "")}</p>
    `;

    li.addEventListener("click", () => {
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
  const normalized = raw ? { ...raw } : null;
  if (normalized?.below_threshold) {
    normalized.category = null;
    normalized.subcategory = null;
  }

  state.lastClassification = normalized
    ? {
        category: normalized?.category || null,
        subcategory: normalized?.subcategory || null,
        belowThreshold: Boolean(normalized?.below_threshold),
      }
    : null;
  state.classificationVotes = { main: null, sub: null };
  updateClassificationControls();

  const mainNode = document.querySelector("#mainCategory");
  const subNode = document.querySelector("#subCategory");

  const belowThreshold = Boolean(normalized?.below_threshold);

  if (mainNode) {
    if (normalized?.category && !belowThreshold) {
      const percent = normalized.category_confidence
        ? `${Math.round(normalized.category_confidence * 100)}%`
        : "";
      mainNode.textContent = percent
        ? `${normalized.category} (${percent})`
        : normalized.category;
      mainNode.classList.add("determined");
    } else {
      mainNode.textContent = "Неизвестно";
      mainNode.classList.remove("determined");
    }
  }

  if (subNode) {
    if (normalized?.subcategory && !belowThreshold) {
      const percent = normalized.subcategory_confidence
        ? `${Math.round(normalized.subcategory_confidence * 100)}%`
        : "";
      subNode.textContent = percent
        ? `${normalized.subcategory} (${percent})`
        : normalized.subcategory;
      subNode.classList.add("determined");
    } else {
      subNode.textContent = "Неизвестно";
      subNode.classList.remove("determined");
    }
  }
}

function applyStats(summary) {
  if (!summary) return;
  const { search, classify, feedback, classification_accuracy: accuracy } =
    summary;

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

  if (accuracy) {
    const { templates, main, sub } = accuracy;

    const templateAccuracyNode = document.querySelector(
      "#templateClassificationAccuracy"
    );
    if (templateAccuracyNode) {
      templateAccuracyNode.textContent = `${(
        templates.accuracy * 100
      ).toFixed(1)}%`;
    }
    const templateTotalsNode = document.querySelector(
      "#templateClassificationTotals"
    );
    if (templateTotalsNode) {
      templateTotalsNode.textContent = `${templates.correct} / ${templates.total}`;
    }

    const mainAccuracyNode = document.querySelector("#mainCategoryAccuracy");
    if (mainAccuracyNode) {
      mainAccuracyNode.textContent = `${(main.accuracy * 100).toFixed(1)}%`;
    }
    const mainTotalsNode = document.querySelector("#mainCategoryTotals");
    if (mainTotalsNode) {
      mainTotalsNode.textContent = `${main.correct} / ${main.total}`;
    }

    const subAccuracyNode = document.querySelector("#subCategoryAccuracy");
    if (subAccuracyNode) {
      subAccuracyNode.textContent = `${(sub.accuracy * 100).toFixed(1)}%`;
    }
    const subTotalsNode = document.querySelector("#subCategoryTotals");
    if (subTotalsNode) {
      subTotalsNode.textContent = `${sub.correct} / ${sub.total}`;
    }
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
    if (!state.lastResults.length) {
      showBanner(
        `Подходящего ответа нет (score < ${SCORE_THRESHOLD.toFixed(1)}).`,
        "info"
      );
    }
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

  const textarea = document.querySelector("#clientRequest");
  if (textarea) {
    textarea.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        runWorkflow();
      }
    });
  }

  const spellButton = document.querySelector("#spellCheck");
  if (spellButton) {
    spellButton.addEventListener("click", async () => {
      const template = document.querySelector("#responseTemplate");
      const currentText = template?.value ?? "";
      if (!currentText.trim()) {
        showBanner("Шаблонный ответ пуст — нечего исправлять.", "warning");
        return;
      }

      spellButton.disabled = true;
      const originalLabel = spellButton.textContent;
      spellButton.textContent = "Исправление...";

      try {
        const response = await spellCheckTemplate(currentText);
        const corrected = typeof response.corrected === "string" ? response.corrected : currentText;
        if (template) {
          template.value = corrected || currentText;
        }
        if (state.templateVote !== null) {
          state.templateVote = null;
          updateTemplateControls();
        }
        showBanner("Орфография в шаблоне обновлена.", "success");
      } catch (err) {
        showBanner(err.message || "Не удалось исправить текст шаблона.");
      } finally {
        spellButton.disabled = false;
        if (typeof originalLabel === "string") {
          spellButton.textContent = originalLabel;
        }
      }
    });
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
