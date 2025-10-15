const API_BASE =
  window.API_BASE || `${window.location.protocol}//${window.location.hostname}:8000/api`;

const messagesContainer = document.getElementById("messages");
const form = document.getElementById("message-form");
const textarea = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const statusElement = document.getElementById("status");
const templateAccuracyValue = document.getElementById("templateAccuracyValue");
const templateAccuracyMeta = document.getElementById("templateAccuracyMeta");
const mainAccuracyValue = document.getElementById("mainAccuracyValue");
const mainAccuracyMeta = document.getElementById("mainAccuracyMeta");
const subAccuracyValue = document.getElementById("subAccuracyValue");
const subAccuracyMeta = document.getElementById("subAccuracyMeta");

let isSending = false;
let pollTimer = null;
let historyCache = [];
let statsTimer = null;

const SENDER_CLASS_MAP = {
  client: "user",
  user: "user",
  support: "bot",
  bot: "bot",
};

async function postChatMessage(payload) {
  const response = await fetch(`${API_BASE}/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
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

function renderAccuracyCard(valueNode, metaNode, stats) {
  if (!valueNode || !metaNode) {
    return;
  }

  const total = Number(stats?.total ?? 0);
  const correct = Number(stats?.correct ?? 0);
  const accuracy = Number(stats?.accuracy ?? 0);

  if (total > 0 && Number.isFinite(accuracy)) {
    const safeAccuracy = Math.max(accuracy, 0);
    valueNode.textContent = `${(safeAccuracy * 100).toFixed(1)}%`;
  } else {
    valueNode.textContent = "–";
  }

  metaNode.textContent = `${correct} / ${total}`;
}

function renderAnalytics(summary) {
  if (!summary?.classification_accuracy) {
    return;
  }
  const { classification_accuracy: accuracy } = summary;
  renderAccuracyCard(
    templateAccuracyValue,
    templateAccuracyMeta,
    accuracy.templates
  );
  renderAccuracyCard(mainAccuracyValue, mainAccuracyMeta, accuracy.main);
  renderAccuracyCard(subAccuracyValue, subAccuracyMeta, accuracy.sub);
}

async function loadAnalytics({ silent = true } = {}) {
  try {
    const response = await fetch(`${API_BASE}/stats/summary`, {
      cache: "no-cache",
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    renderAnalytics(data);
  } catch (error) {
    if (!silent) {
      console.error("analytics fetch error", error);
    }
  }
}

function startAnalyticsPolling() {
  if (statsTimer) {
    clearInterval(statsTimer);
  }
  statsTimer = setInterval(() => loadAnalytics({ silent: true }), 60_000);
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

Promise.all([loadHistory(), loadAnalytics()]).finally(() => {
  startPolling();
  startAnalyticsPolling();
});
