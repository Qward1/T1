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
  root.innerHTML = "";

  if (!list.length) {
    return;
  }

  const ordered = [...list].reverse();
  ordered.forEach((entry) => {
    const timestamp = formatDateTime(entry.timestamp);
    const classification = [entry.category, entry.subcategory]
      .filter(Boolean)
      .join(" / ");
    const baseMeta = [timestamp, classification].filter(Boolean).join(" • ");

    const clientHeader = ["Клиент", baseMeta].filter(Boolean).join(" • ");
    const clientMessage = document.createElement("div");
    clientMessage.className = "chat-message client";
    clientMessage.innerHTML = `
      <div class="message-header">${escapeHTML(clientHeader)}</div>
      <div class="message-text">${formatSnippet(entry.query || "")}</div>
    `;
    root.appendChild(clientMessage);

    if (entry.template_text) {
      const statusParts = [];
      if (entry.main_vote !== null && entry.main_vote !== undefined) {
        statusParts.push(
          `Категория: ${entry.main_vote ? "верно" : "ошибка"}`
        );
      }
      if (entry.sub_vote !== null && entry.sub_vote !== undefined) {
        statusParts.push(
          `Подкатегория: ${entry.sub_vote ? "верно" : "ошибка"}`
        );
      }
      if (
        entry.template_positive !== null &&
        entry.template_positive !== undefined
      ) {
        statusParts.push(
          entry.template_positive ? "Шаблон одобрен" : "Шаблон отклонен"
        );
      }
      const operatorHeader = ["Оператор", baseMeta, statusParts.join(" • ")]
        .filter(Boolean)
        .join(" • ");
      const operatorMessage = document.createElement("div");
      operatorMessage.className = "chat-message operator";
      operatorMessage.innerHTML = `
        <div class="message-header">${escapeHTML(operatorHeader)}</div>
        <div class="message-text">${formatSnippet(
          entry.template_text || ""
        )}</div>
      `;
      root.appendChild(operatorMessage);
    }
  });

  root.scrollTop = root.scrollHeight;
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
    const thresholdText = SCORE_THRESHOLD.toFixed(1);
    empty.innerHTML = `<div class="question-title">Подходящего ответа нет (score &lt; ${thresholdText}).</div>`;
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
  const { search, classify, feedback, history } = summary;

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
      const responseText = template?.value ?? "";
      if (!responseText.trim()) {
        showBanner("Нет ответа для отправки.");
        return;
      }

      const selected = getSelectedResult();
      if (state.lastQuery) {
        try {
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
          await refreshStats();
        } catch (err) {
          console.warn("Не удалось сохранить историю ответа:", err);
        }
      }

      let copySuccess = false;

      if (navigator.clipboard?.writeText) {
        try {
          await navigator.clipboard.writeText(responseText);
          copySuccess = true;
        } catch (err) {
          console.warn("Clipboard API недоступен:", err);
        }
      }

      if (!copySuccess && template?.select) {
        template.focus();
        template.select();
        try {
          copySuccess = document.execCommand("copy");
        } catch (err) {
          console.warn("document.execCommand('copy') не сработал:", err);
          copySuccess = false;
        }
        window.getSelection()?.removeAllRanges?.();
      }

      if (copySuccess) {
        showBanner("Ответ скопирован в буфер обмена.", "success");
      } else {
        showBanner("Скопируйте ответ вручную (Ctrl+C).", "warning");
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
  setInterval(refreshStats, 60_000);
});
