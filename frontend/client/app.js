const API_BASE =
  window.API_BASE || `${window.location.protocol}//${window.location.hostname}:8000/api`;

const SESSION_STORAGE_KEY = "client-chat-session";
const FEEDBACK_STORAGE_KEY = "client-chat-feedback";

const sessionId = loadSessionId();
let feedbackState = loadFeedbackState();

const messagesContainer = document.getElementById("messages");
const form = document.getElementById("message-form");
const textarea = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const statusElement = document.getElementById("status");
let isSending = false;
let pollTimer = null;
let historyCache = [];

const SENDER_CLASS_MAP = {
  client: "user",
  user: "user",
  support: "bot",
  bot: "bot",
};

function loadSessionId() {
  try {
    const stored = localStorage.getItem(SESSION_STORAGE_KEY);
    if (stored) {
      return stored;
    }
  } catch (_) {
    /* ignore */
  }
  const fresh =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now().toString(16)}-${Math.random().toString(16).slice(2, 10)}`;
  try {
    localStorage.setItem(SESSION_STORAGE_KEY, fresh);
  } catch (_) {
    /* ignore */
  }
  return fresh;
}

function loadFeedbackState() {
  try {
    const stored = localStorage.getItem(FEEDBACK_STORAGE_KEY);
    if (!stored) {
      return new Set();
    }
    const parsed = JSON.parse(stored);
    if (Array.isArray(parsed)) {
      return new Set(parsed.map(String));
    }
  } catch (_) {
    /* ignore */
  }
  return new Set();
}

function saveFeedbackState() {
  try {
    const payload = JSON.stringify(Array.from(feedbackState));
    localStorage.setItem(FEEDBACK_STORAGE_KEY, payload);
  } catch (_) {
    /* ignore */
  }
}

function rememberFeedback(messageId) {
  feedbackState.add(String(messageId));
  saveFeedbackState();
}

function hasFeedback(messageId) {
  return feedbackState.has(String(messageId));
}

async function postChatMessage(payload) {
  const response = await fetch(`${API_BASE}/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, session_id: sessionId }),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Ошибка ${response.status}`);
  }
  return response.json();
}

async function postMessageFeedback(messageId, useful) {
  const response = await fetch(`${API_BASE}/messages/${messageId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      useful: Boolean(useful),
      session_id: sessionId,
    }),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Ошибка ${response.status}`);
  }
  return response.json();
}

function formatMeta(message) {
  if (!message.timestamp) return "";
  try {
    return new Date(message.timestamp).toLocaleString();
  } catch (_) {
    return message.timestamp;
  }
}

function renderMessages(messages) {
  messagesContainer.innerHTML = "";
  messages.forEach((message) => {
    const roleClass = SENDER_CLASS_MAP[message.sender] || "user";
    const bubble = document.createElement("div");
    bubble.className = `bubble ${roleClass}`;
    bubble.textContent = message.text || "";

    const timestamp = formatMeta(message);
    if (timestamp) {
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = timestamp;
      bubble.appendChild(meta);
    }

    const messageId = Number(message?.id);
    const allowFeedback =
      roleClass === "bot" &&
      Boolean(message?.template_unmodified) &&
      Number.isFinite(messageId);

    if (allowFeedback) {
      const actions = document.createElement("div");
      actions.className = "feedback-actions";

      if (hasFeedback(messageId)) {
        const note = document.createElement("div");
        note.className = "feedback-note";
        note.textContent = "Спасибо за обратную связь!";
        actions.appendChild(note);
      } else {
        const label = document.createElement("span");
        label.className = "feedback-label";
        label.textContent = "Ответ помог?";
        actions.appendChild(label);

        const positiveBtn = document.createElement("button");
        positiveBtn.type = "button";
        positiveBtn.className = "feedback-button primary";
        positiveBtn.textContent = "Ответ помог";

        const negativeBtn = document.createElement("button");
        negativeBtn.type = "button";
        negativeBtn.className = "feedback-button";
        negativeBtn.textContent = "Ответ не помог";

        const buttons = [positiveBtn, negativeBtn];
        const setDisabled = (value) => {
          buttons.forEach((btn) => {
            btn.disabled = value;
          });
        };

        const showThankYou = (useful) => {
          actions.innerHTML = "";
          const note = document.createElement("div");
          note.className = "feedback-note";
          note.textContent = useful
            ? "Рады, что ответ помог!"
            : "Спасибо, мы передадим ваш отзыв.";
          actions.appendChild(note);
        };

        const handleClick = async (useful) => {
          setDisabled(true);
          try {
            await postMessageFeedback(messageId, useful);
            rememberFeedback(messageId);
            showThankYou(useful);
            clearStatus();
          } catch (error) {
            console.error("feedback error", error);
            setStatus("Не удалось отправить отзыв. Попробуйте позже.");
            setDisabled(false);
          }
        };

        positiveBtn.addEventListener("click", () => handleClick(true));
        negativeBtn.addEventListener("click", () => handleClick(false));

        actions.appendChild(positiveBtn);
        actions.appendChild(negativeBtn);
      }

      bubble.appendChild(actions);
    }

    messagesContainer.appendChild(bubble);
  });
  scrollToBottom();
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  });
}

function setStatus(text) {
  statusElement.textContent = text || "";
}

function clearStatus() {
  setStatus("");
}

function setSendingState(state) {
  textarea.disabled = state;
  sendButton.disabled = state;
  if (state) {
    setStatus("Отправляем сообщение…");
  }
}

async function loadHistory({ silent = false, force = false } = {}) {
  if (!silent) {
    setStatus("Загружаем историю…");
  }
  try {
    const response = await fetch(`${API_BASE}/messages`, { cache: "no-cache" });
    if (!response.ok) {
      throw new Error(`Ошибка ${response.status}`);
    }
    const data = await response.json();
    const messages = Array.isArray(data.messages) ? data.messages : [];
    const serialized = JSON.stringify(messages);
    if (force || serialized !== JSON.stringify(historyCache)) {
      historyCache = messages;
      renderMessages(messages);
    }
    if (!silent) {
      clearStatus();
    }
  } catch (error) {
    console.error(error);
    setStatus("Не удалось загрузить историю. Попробуйте позже.");
  }
}

async function sendMessage(text) {
  if (isSending) return;
  isSending = true;
  setSendingState(true);

  try {
    await postChatMessage({ sender: "client", text });
    textarea.value = "";
    clearStatus();
    await loadHistory({ silent: true, force: true });
  } catch (error) {
    console.error("sendMessage error", error);
    setStatus("Не удалось отправить сообщение. Попробуйте ещё раз.");
  } finally {
    setSendingState(false);
    isSending = false;
  }
}

function startPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
  }
  pollTimer = setInterval(() => loadHistory({ silent: true }), 5000);
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const value = textarea.value.trim();
  if (!value) {
    setStatus("Введите сообщение.");
    return;
  }
  sendMessage(value);
});

loadHistory().finally(() => {
  startPolling();
});
