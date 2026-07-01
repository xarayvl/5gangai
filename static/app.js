// ============================================================
// 5AI Web - Frontend logic
// Mirrors the behavior of ChatWindow / FiveAIApp in the original
// PySide6 ui.py, but talks to server.py over fetch()/SSE instead
// of Qt signals.
// ============================================================

const I18N = window.I18N || {};
function tr(key) {
  return I18N[key] || key;
}

const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const chatListEl = document.getElementById('chat-list');
const newChatBtn = document.getElementById('new-chat-btn');
const logoutBtn = document.getElementById('logout-btn');
const sidebarEl = document.getElementById('sidebar');
const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
const sidebarOpenBtn = document.getElementById('sidebar-open-btn');
const sidebarBackdrop = document.getElementById('sidebar-backdrop');
const settingsTrigger = document.getElementById('settings-trigger');
const settingsOverlay = document.getElementById('settings-overlay');
const settingsClose = document.getElementById('settings-close');
const settingsDoneBtn = document.getElementById('settings-done-btn');
const langButtons = document.querySelectorAll('.lang-btn');
const clearChatBtn = document.getElementById('clear-chat-btn');
const modelPicker = document.getElementById('model-picker');
const modelPickerBtn = document.getElementById('model-picker-btn');
const modelPickerMenu = document.getElementById('model-picker-menu');
const modelPickerName = document.getElementById('model-picker-name');

let currentChatId = window.CURRENT_CHAT_ID;
let isStreaming = false;

// ------------------------------------------------------------
// Collapsible sidebar
// ------------------------------------------------------------
function isMobileViewport() {
  return window.matchMedia('(max-width: 760px)').matches;
}

function setSidebarCollapsed(collapsed) {
  sidebarEl.classList.toggle('collapsed', collapsed);
  sidebarOpenBtn.classList.toggle('visible', collapsed);
  if (sidebarBackdrop) {
    sidebarBackdrop.classList.toggle('visible', isMobileViewport() && !collapsed);
  }
}

// On mobile the sidebar should start closed (it overlays the chat
// instead of sitting beside it); on desktop it starts open.
setSidebarCollapsed(isMobileViewport());

// Only auto-close on mobile — desktop keeps the sidebar open after
// picking/creating a chat, same as before.
function closeSidebarOnMobile() {
  if (isMobileViewport()) setSidebarCollapsed(true);
}

if (sidebarToggleBtn) {
  sidebarToggleBtn.addEventListener('click', () => setSidebarCollapsed(true));
}
if (sidebarOpenBtn) {
  sidebarOpenBtn.addEventListener('click', () => setSidebarCollapsed(false));
}
if (sidebarBackdrop) {
  sidebarBackdrop.addEventListener('click', () => setSidebarCollapsed(true));
}

// ------------------------------------------------------------
// Settings modal (account / model / language / actions)
// ------------------------------------------------------------
function openSettings() {
  settingsOverlay.classList.add('open');
}

function closeSettings() {
  settingsOverlay.classList.remove('open');
}

if (settingsTrigger) settingsTrigger.addEventListener('click', openSettings);
if (settingsClose) settingsClose.addEventListener('click', closeSettings);
if (settingsDoneBtn) settingsDoneBtn.addEventListener('click', closeSettings);
if (settingsOverlay) {
  settingsOverlay.addEventListener('click', (e) => {
    if (e.target === settingsOverlay) closeSettings();
  });
}
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && settingsOverlay && settingsOverlay.classList.contains('open')) {
    closeSettings();
  }
  if (e.key === 'Escape' && modelPicker && modelPicker.classList.contains('open')) {
    closeModelPicker();
  }
});

// ------------------------------------------------------------
// Model picker — top-left of the chat area (ChatGPT-style),
// replaces the old settings-modal <select>.
// ------------------------------------------------------------
function openModelPicker() {
  modelPicker.classList.add('open');
  modelPickerBtn.setAttribute('aria-expanded', 'true');
}

function closeModelPicker() {
  modelPicker.classList.remove('open');
  modelPickerBtn.setAttribute('aria-expanded', 'false');
}

if (modelPickerBtn) {
  modelPickerBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    if (modelPicker.classList.contains('open')) {
      closeModelPicker();
    } else {
      openModelPicker();
    }
  });
}

if (modelPickerMenu) {
  modelPickerMenu.querySelectorAll('.model-picker-item').forEach((item) => {
    item.addEventListener('click', async () => {
      const modelId = item.dataset.modelId;
      const modelName = item.dataset.modelName;

      modelPickerMenu.querySelectorAll('.model-picker-item').forEach((el) => {
        el.classList.toggle('selected', el === item);
      });
      modelPickerName.textContent = modelName;
      closeModelPicker();

      try {
        await fetch('/api/model', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ model_id: modelId }),
        });
      } catch {
        // silent fail
      }
    });
  });
}

document.addEventListener('click', (e) => {
  if (modelPicker && modelPicker.classList.contains('open') && !modelPicker.contains(e.target)) {
    closeModelPicker();
  }
});

// Reopen settings automatically after a language-switch reload, so the
// toggle doesn't feel like it "lost your place".
if (sessionStorage.getItem('reopenSettings') === '1') {
  sessionStorage.removeItem('reopenSettings');
  openSettings();
}

// ------------------------------------------------------------
// Language toggle — persists server-side (Database.save_language),
// then reloads so every template string re-renders via i18n.py's t().
// ------------------------------------------------------------
langButtons.forEach((btn) => {
  btn.addEventListener('click', async () => {
    const lang = btn.dataset.lang;
    if (btn.classList.contains('active') || lang === window.CURRENT_LANGUAGE) return;
    langButtons.forEach((b) => b.classList.toggle('active', b === btn));
    try {
      await fetch('/api/language', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lang }),
      });
    } catch {
      // silent fail
    } finally {
      sessionStorage.setItem('reopenSettings', '1');
      window.location.reload();
    }
  });
});

if (clearChatBtn) {
  clearChatBtn.addEventListener('click', async () => {
    if (isStreaming) return;
    if (!confirm(tr('clear_conversation_confirm'))) return;
    try {
      await fetch(`/api/chats/${currentChatId}/clear`, { method: 'POST' });
      messagesEl.innerHTML = '';
      renderEmptyState();
      updateChatTitleInSidebar(currentChatId, tr('new_chat_default_title'));
      closeSettings();
    } catch {
      // silent fail
    }
  });
}

// ------------------------------------------------------------
// Auto-growing textarea (mirrors GrowingTextEdit)
// ------------------------------------------------------------
const MIN_HEIGHT = 24;
const MAX_HEIGHT = 180;

function autoGrow() {
  inputEl.style.height = MIN_HEIGHT + 'px';
  const newHeight = Math.min(Math.max(inputEl.scrollHeight, MIN_HEIGHT), MAX_HEIGHT);
  inputEl.style.height = newHeight + 'px';
}

function updateSendBtnState() {
  sendBtn.disabled = isStreaming || inputEl.value.trim().length === 0;
}

inputEl.addEventListener('input', () => {
  autoGrow();
  updateSendBtnState();
});

inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn.addEventListener('click', sendMessage);

// ------------------------------------------------------------
// Markdown-lite rendering (bold/italic/headers/lists/code blocks)
// ------------------------------------------------------------
function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function inlineFormat(str) {
  let s = escapeHtml(str);
  // inline code
  s = s.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
  // bold+italic / bold / italic (order matters)
  s = s.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>');
  s = s.replace(/__(.+?)__/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^_])_([^_\n]+)_(?!_)/g, '$1<em>$2</em>');
  return s;
}

function buildCodeBlockHtml(block) {
  const lang = (block.lang || '').trim();
  const escaped = escapeHtml(block.code);
  const langLabel = lang || 'text';
  return (
    '<div class="code-block">' +
      '<div class="code-block-header">' +
        `<span class="code-lang">${escapeHtml(langLabel)}</span>` +
        `<button class="copy-code-btn" type="button">${tr('copy_code')}</button>` +
      '</div>' +
      `<pre><code class="code-block-content">${escaped}</code></pre>` +
    '</div>'
  );
}

// Converts a chunk of assistant markdown-ish text into safe HTML:
// fenced ```code``` blocks, # ## ### headers, **bold**/*italic*,
// `inline code`, -/* bullet lists, 1. numbered lists, and literal
// "<br>" text the model sometimes emits instead of a real newline.
function renderMarkdown(raw) {
  if (!raw) return '';

  let text = raw.replace(/<br\s*\/?>/gi, '\n');

  // Pull out fenced code blocks first so nothing else touches them.
  const codeBlocks = [];
  text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, code) => {
    codeBlocks.push({ lang, code: code.replace(/\n$/, '') });
    return `\u0000CB${codeBlocks.length - 1}\u0000`;
  });

  const lines = text.split('\n');
  let html = '';
  let listBuffer = [];
  let listType = null;
  let paraBuffer = [];

  function flushList() {
    if (listBuffer.length) {
      const tag = listType === 'ol' ? 'ol' : 'ul';
      html += `<${tag}>` + listBuffer.map((li) => `<li>${inlineFormat(li)}</li>`).join('') + `</${tag}>`;
      listBuffer = [];
      listType = null;
    }
  }

  function flushPara() {
    if (paraBuffer.length) {
      html += `<p>${paraBuffer.map(inlineFormat).join('<br>')}</p>`;
      paraBuffer = [];
    }
  }

  for (const line of lines) {
    const codeMatch = line.match(/^\u0000CB(\d+)\u0000$/);
    if (codeMatch) {
      flushList();
      flushPara();
      html += buildCodeBlockHtml(codeBlocks[Number(codeMatch[1])]);
      continue;
    }

    const h3 = line.match(/^### (.*)/);
    const h2 = line.match(/^## (.*)/);
    const h1 = line.match(/^# (.*)/);
    if (h3 || h2 || h1) {
      flushList();
      flushPara();
      const content = (h3 || h2 || h1)[1];
      const tag = h3 ? 'h3' : h2 ? 'h2' : 'h1';
      html += `<${tag}>${inlineFormat(content)}</${tag}>`;
      continue;
    }

    const ulMatch = line.match(/^\s*[-*]\s+(.*)/);
    const olMatch = line.match(/^\s*\d+[.)]\s+(.*)/);
    if (ulMatch) {
      flushPara();
      if (listType !== 'ul') { flushList(); listType = 'ul'; }
      listBuffer.push(ulMatch[1]);
      continue;
    }
    if (olMatch) {
      flushPara();
      if (listType !== 'ol') { flushList(); listType = 'ol'; }
      listBuffer.push(olMatch[1]);
      continue;
    }

    if (line.trim() === '') {
      flushList();
      flushPara();
      continue;
    }

    flushList();
    paraBuffer.push(line);
  }
  flushList();
  flushPara();

  return html;
}

// Copy-to-clipboard for code blocks (event delegation, works for
// both server-rendered and streamed-in blocks).
messagesEl.addEventListener('click', (e) => {
  const btn = e.target.closest('.copy-code-btn');
  if (!btn) return;
  const codeEl = btn.closest('.code-block').querySelector('.code-block-content');
  if (!codeEl) return;
  const text = codeEl.textContent;
  const restoreLabel = tr('copy_code');
  const doneLabel = tr('copied');
  const finish = () => {
    btn.textContent = doneLabel;
    btn.classList.add('copied');
    setTimeout(() => {
      btn.textContent = restoreLabel;
      btn.classList.remove('copied');
    }, 1500);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(finish).catch(finish);
  } else {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch {}
    document.body.removeChild(ta);
    finish();
  }
});

// ------------------------------------------------------------
// Rendering helpers
// ------------------------------------------------------------
function removeEmptyState() {
  const empty = document.getElementById('empty-state');
  if (empty) empty.remove();
}

function appendMessage(role, text, { animate = false } = {}) {
  removeEmptyState();
  const row = document.createElement('div');
  row.className = `msg-row ${role}` + (animate ? ' msg-enter' : '');
  const bubble = document.createElement('div');
  bubble.className = 'bubble' + (role === 'user' ? ' plain' : '');
  if (role === 'assistant') {
    bubble.innerHTML = renderMarkdown(text);
  } else {
    bubble.textContent = text;
  }
  row.appendChild(bubble);
  messagesEl.appendChild(row);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return bubble;
}

function showTypingIndicator(bubble) {
  bubble.classList.add('typing');
  bubble.innerHTML = '<span></span><span></span><span></span>';
}

function hideTypingIndicator(bubble) {
  bubble.classList.remove('typing');
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// Re-render the server-rendered assistant bubbles (initial page load)
// through the same markdown-lite formatter used for live messages.
document.querySelectorAll('.msg-row.assistant .bubble').forEach((bubble) => {
  const raw = bubble.textContent;
  bubble.innerHTML = renderMarkdown(raw);
});

// ------------------------------------------------------------
// Sending a message + SSE streaming
// ------------------------------------------------------------
async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text || isStreaming) return;

  appendMessage('user', text, { animate: true });
  inputEl.value = '';
  autoGrow();

  isStreaming = true;
  updateSendBtnState();

  const assistantBubble = appendMessage('assistant', '', { animate: true });
  showTypingIndicator(assistantBubble);

  try {
    const res = await fetch(`/api/chats/${currentChatId}/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });

    if (!res.ok || !res.body) {
      hideTypingIndicator(assistantBubble);
      assistantBubble.textContent = `[${tr('error_reach_server')}]`;
      isStreaming = false;
      updateSendBtnState();
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullText = '';
    let firstChunkSeen = false;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop(); // keep incomplete chunk in buffer

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith('data:')) continue;
        const jsonStr = line.slice(5).trim();
        if (!jsonStr) continue;

        let payload;
        try {
          payload = JSON.parse(jsonStr);
        } catch {
          continue;
        }

        if (payload.type === 'chunk') {
          if (!firstChunkSeen) {
            hideTypingIndicator(assistantBubble);
            firstChunkSeen = true;
          }
          fullText += payload.text;
          assistantBubble.innerHTML = renderMarkdown(fullText);
          scrollToBottom();
        } else if (payload.type === 'meta') {
          if (payload.is_first) {
            updateChatTitleInSidebar(currentChatId, text.slice(0, 32) || tr('new_chat_default_title'));
          }
        } else if (payload.type === 'done') {
          if (payload.title) {
            updateChatTitleInSidebar(currentChatId, payload.title);
          }
          refreshChatList();
        }
      }
    }
  } catch (err) {
    hideTypingIndicator(assistantBubble);
    assistantBubble.textContent = `[${tr('error_connection_lost')}]`;
  } finally {
    isStreaming = false;
    updateSendBtnState();
  }
}

// ------------------------------------------------------------
// Sidebar: chat list
// ------------------------------------------------------------
function updateChatTitleInSidebar(chatId, title) {
  const item = chatListEl.querySelector(`.chat-item[data-chat-id="${chatId}"] .chat-title`);
  if (item) item.textContent = title;
}

function selectChatItem(chatId) {
  document.querySelectorAll('.chat-item').forEach((el) => {
    el.classList.toggle('selected', el.dataset.chatId === chatId);
  });
}

async function refreshChatList() {
  try {
    const res = await fetch('/api/chats');
    const data = await res.json();
    if (!data.ok) return;

    chatListEl.innerHTML = '';
    data.chats.forEach((c) => {
      chatListEl.appendChild(buildChatItem(c.id, c.title));
    });
    selectChatItem(currentChatId);
  } catch {
    // silent fail - non critical
  }
}

function buildChatItem(chatId, title) {
  const item = document.createElement('div');
  item.className = 'chat-item';
  item.dataset.chatId = chatId;

  const titleSpan = document.createElement('span');
  titleSpan.className = 'chat-title';
  titleSpan.textContent = title;

  const delBtn = document.createElement('button');
  delBtn.className = 'delete-btn';
  delBtn.dataset.chatId = chatId;
  delBtn.title = tr('delete_tooltip');
  delBtn.textContent = '✕';

  item.appendChild(titleSpan);
  item.appendChild(delBtn);

  item.addEventListener('click', (e) => {
    if (e.target === delBtn) return;
    loadChat(chatId);
    closeSidebarOnMobile();
  });

  delBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    deleteChat(chatId);
  });

  return item;
}

function renderEmptyState() {
  const empty = document.createElement('div');
  empty.className = 'empty-state';
  empty.id = 'empty-state';
  const h1 = document.createElement('h1');
  h1.textContent = tr('what_can_i_help');
  const mark = document.createElement('div');
  mark.className = 'empty-mark';
  empty.appendChild(mark);
  empty.appendChild(h1);
  messagesEl.appendChild(empty);
}

async function loadChat(chatId) {
  if (chatId === currentChatId || isStreaming) return;

  try {
    const res = await fetch(`/api/chats/${chatId}`);
    const data = await res.json();
    if (!data.ok) return;

    currentChatId = chatId;
    selectChatItem(chatId);
    closeSidebarOnMobile();

    messagesEl.innerHTML = '';
    if (data.messages.length === 0) {
      renderEmptyState();
    } else {
      data.messages.forEach((m) => appendMessage(m.role, m.content));
    }
  } catch {
    // silent fail
  }
}

async function deleteChat(chatId) {
  try {
    await fetch(`/api/chats/${chatId}`, { method: 'DELETE' });
    const item = chatListEl.querySelector(`.chat-item[data-chat-id="${chatId}"]`);
    if (item) item.remove();

    if (chatId === currentChatId) {
      const remaining = chatListEl.querySelector('.chat-item');
      if (remaining) {
        loadChat(remaining.dataset.chatId);
      } else {
        startNewChat();
      }
    }
  } catch {
    // silent fail
  }
}

// ------------------------------------------------------------
// New chat — guarded so users can't spam-create empty chats:
//  1) if the currently open chat is still empty/untyped, reuse it
//     instead of creating another blank one.
//  2) the server also enforces a hard per-user cap (MAX_CHATS_PER_USER
//     in backend.py); if hit, surface the translated error.
// ------------------------------------------------------------
async function startNewChat() {
  if (isStreaming) return;

  const isCurrentEmpty = document.getElementById('empty-state') !== null;
  if (isCurrentEmpty) {
    inputEl.focus();
    return;
  }

  try {
    const res = await fetch('/api/chats/new', { method: 'POST' });
    const data = await res.json();

    if (!data.ok) {
      if (data.limit_reached) {
        alert(data.error || tr('chat_limit_reached'));
      }
      return;
    }

    currentChatId = data.chat_id;

    const item = buildChatItem(currentChatId, tr('new_chat_default_title'));
    chatListEl.insertBefore(item, chatListEl.firstChild);
    selectChatItem(currentChatId);
    closeSidebarOnMobile();

    messagesEl.innerHTML = '';
    renderEmptyState();
  } catch {
    // silent fail
  }
}

newChatBtn.addEventListener('click', startNewChat);

// ------------------------------------------------------------
// Existing chat items (rendered server-side on load)
// ------------------------------------------------------------
document.querySelectorAll('.chat-item').forEach((item) => {
  const chatId = item.dataset.chatId;
  item.addEventListener('click', (e) => {
    if (e.target.classList.contains('delete-btn')) return;
    loadChat(chatId);
    closeSidebarOnMobile();
  });
  const delBtn = item.querySelector('.delete-btn');
  if (delBtn) {
    delBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      deleteChat(chatId);
    });
  }
});

// ------------------------------------------------------------
// Logout
// ------------------------------------------------------------
logoutBtn.addEventListener('click', async () => {
  try {
    await fetch('/api/logout', { method: 'POST' });
  } finally {
    window.location.href = '/login';
  }
});

// Initial state
autoGrow();
updateSendBtnState();
