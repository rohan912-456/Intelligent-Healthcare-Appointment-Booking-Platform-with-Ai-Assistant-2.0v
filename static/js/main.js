/* ── Clinical Couture Main JS ─────────────────────────── */

// ── Chat Sidebar ──────────────────────────────────────
const sidebar    = document.getElementById('chatSidebar');
const chatBody   = document.getElementById('chatBody');
const userInput  = document.getElementById('userInput');
const sendBtn    = document.getElementById('sendBtn');
const closeBtn   = document.getElementById('closeChat');
const resetBtn   = document.getElementById('resetChat');
const chatToggle = document.getElementById('chatToggle');

if (chatToggle) {
  chatToggle.addEventListener('click', () => {
    sidebar.classList.add('sidebar-open');
  });
}
if (closeBtn) {
  closeBtn.addEventListener('click', () => {
    sidebar.classList.remove('sidebar-open');
  });
}

// ── Escape text to prevent XSS ──────────────────────
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;          // textContent escapes automatically
  return div.innerHTML;
}

// ── Format current time ──────────────────────────────
function nowTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ── Append message bubble ────────────────────────────
function appendMsg(text, role) {
  const wrap = document.createElement('div');
  wrap.className = `msg ${role}`;

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = escapeHtml(text).replace(/\n/g, '<br>');  // safe: already escaped

  const time = document.createElement('div');
  time.className = 'msg-time';
  time.textContent = nowTime();

  wrap.appendChild(bubble);
  wrap.appendChild(time);
  chatBody.appendChild(wrap);
  chatBody.scrollTop = chatBody.scrollHeight;
}

// ── Typing indicator ─────────────────────────────────
function showTyping() {
  const wrap = document.createElement('div');
  wrap.className = 'msg bot';
  wrap.id = 'typingIndicator';
  wrap.innerHTML = `
    <div class="typing-bubble">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>`;
  chatBody.appendChild(wrap);
  chatBody.scrollTop = chatBody.scrollHeight;
}

function removeTyping() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

// ── Send message ─────────────────────────────────────
async function sendMessage() {
  if (!userInput) return;
  const text = userInput.value.trim();
  if (!text) return;

  appendMsg(text, 'user');
  userInput.value = '';
  sendBtn.disabled = true;
  showTyping();

  try {
    const res = await fetch('/chat/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    removeTyping();
    appendMsg(data.reply || 'Sorry, something went wrong.', 'bot');
  } catch {
    removeTyping();
    appendMsg('Connection error. Please try again.', 'bot');
  } finally {
    sendBtn.disabled = false;
    userInput.focus();
  }
}

if (sendBtn) sendBtn.addEventListener('click', sendMessage);
if (userInput) {
  userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
}

// ── Reset chat history ────────────────────────────────
if (resetBtn) {
  resetBtn.addEventListener('click', async () => {
    await fetch('/chat/reset', { method: 'POST' });
    chatBody.innerHTML = `
      <div class="msg bot">
        <div class="msg-bubble">👋 Chat cleared! How can I help you?</div>
      </div>`;
  });
}

// ── Auto-dismiss alerts (Vanilla JS) ──────────────────
document.querySelectorAll('.flash-animation').forEach(alert => {
  setTimeout(() => {
    alert.style.opacity = '0';
    alert.style.transition = 'opacity 0.5s ease-out';
    setTimeout(() => alert.remove(), 500);
  }, 5000);
});

// ── Navbar active state ───────────────────────────────
const currentPath = window.location.pathname;
document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
  if (link.getAttribute('href') === currentPath) {
    link.classList.add('active');
    link.style.color = '#fff';
    link.style.background = 'rgba(255,255,255,.15)';
  }
});
