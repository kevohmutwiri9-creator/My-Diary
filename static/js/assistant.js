document.addEventListener('DOMContentLoaded', () => {
  const toggleBtn = document.getElementById('assistant-toggle');
  const closeBtn = document.getElementById('assistant-close');
  const card = document.querySelector('.assistant-card');
  const chat = document.querySelector('.assistant-chat');
  const input = document.getElementById('assistant-input');
  const sendBtn = document.getElementById('assistant-send');
  const quickActionsContainer = document.createElement('div');
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

  quickActionsContainer.className = 'assistant-quick-actions mt-2 p-2 border-top';
  quickActionsContainer.innerHTML = `
    <div class="d-flex flex-wrap gap-2">
      <button type="button" class="btn btn-sm btn-outline-primary" data-assistant-action="prompts">
        <i class="bi bi-lightbulb"></i> Prompt Ideas
      </button>
      <button type="button" class="btn btn-sm btn-outline-success" data-assistant-action="summary">
        <i class="bi bi-journal-text"></i> Summarize Latest Entry
      </button>
      <button type="button" class="btn btn-sm btn-outline-warning" data-assistant-action="mood">
        <i class="bi bi-emoji-smile"></i> Mood Insight
      </button>
      <button type="button" class="btn btn-sm btn-outline-secondary" data-assistant-action="tags">
        <i class="bi bi-tags"></i> Tag Suggestions
      </button>
    </div>
  `;
  card.querySelector('.card-body').appendChild(quickActionsContainer);

  // Toggle assistant visibility
  toggleBtn.addEventListener('click', () => {
    card.classList.toggle('d-none');
    if (!card.classList.contains('d-none')) {
      input.focus();
    }
  });

  closeBtn.addEventListener('click', () => {
    card.classList.add('d-none');
  });

  const addMessage = (content, { isUser = false, html = false } = {}) => {
    const wrapper = document.createElement('div');
    wrapper.className = `mb-2 p-2 rounded ${isUser ? 'bg-primary text-white' : 'bg-light'}`;
    wrapper.style.maxWidth = '85%';
    wrapper.style.marginLeft = isUser ? 'auto' : '0';
    wrapper.style.wordBreak = 'break-word';
    if (html) {
      wrapper.innerHTML = content;
    } else {
      wrapper.textContent = content;
    }
    chat.appendChild(wrapper);
    chat.scrollTop = chat.scrollHeight;
    return wrapper;
  };

  const formatList = (items) => {
    if (!Array.isArray(items) || !items.length) return '';
    return `<ul class="mb-0 ps-3">${items.map(item => `<li>${item}</li>`).join('')}</ul>`;
  };

  const formatBadge = (label) => `<span class="badge bg-light text-dark border">${label}</span>`;

  const withLoading = async (message, fn) => {
    const loader = addMessage(
      `<div class="d-flex align-items-center gap-2"><div class="spinner-border spinner-border-sm" role="status"></div><span>${message}</span></div>`,
      { html: true }
    );
    try {
      return await fn();
    } finally {
      loader.remove();
    }
  };

  const disableInput = (disabled) => {
    input.disabled = disabled;
    sendBtn.disabled = disabled;
  };

  // General API helper
  const postJSON = async (url, payload = {}) => {
    if (!csrfToken) {
      throw new Error('CSRF token missing. Refresh the page.');
    }
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok || data.error) {
      throw new Error(data.error || 'Assistant request failed');
    }
    return data;
  };

  // Primary question handler
  sendBtn.addEventListener('click', sendQuestion);
  input.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      sendQuestion();
    }
  });

  async function sendQuestion() {
    const question = input.value.trim();
    if (!question) return;

    addMessage(question, { isUser: true });
    input.value = '';
    disableInput(true);

    try {
      const data = await withLoading('Thinking...', () =>
        postJSON('/assistant/ask', { question })
      );
      addMessage(data.answer);
    } catch (error) {
      addMessage(`⚠️ ${error.message}`);
    } finally {
      disableInput(false);
      input.focus();
    }
  }

  // Quick actions
  quickActionsContainer.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-assistant-action]');
    if (!button) return;

    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    const action = button.dataset.assistantAction;

    try {
      switch (action) {
        case 'prompts': {
          const data = await withLoading('Gathering tailored prompts...', () =>
            postJSON('/assistant/prompts')
          );
          const promptsHtml = formatList(data.prompts);
          addMessage(`Here are a few ideas to spark your writing:${promptsHtml}`, { html: true });
          break;
        }
        case 'summary': {
          const latestEntry = await fetchLatestEntry();
          if (!latestEntry) {
            addMessage('No recent entries found to summarize yet.');
            break;
          }
          const data = await withLoading('Summarizing your latest entry...', () =>
            postJSON('/assistant/summarize', {
              content: latestEntry.content,
              title: latestEntry.title,
            })
          );
          const takeaways = formatList(data.takeaways);
          addMessage(
            `<strong>${latestEntry.title || 'Latest entry summary'}:</strong><p class="mb-2">${data.summary}</p>${takeaways}`,
            { html: true }
          );
          break;
        }
        case 'mood': {
          const latestEntry = await fetchLatestEntry();
          if (!latestEntry) {
            addMessage('No recent entry content to analyse mood.');
            break;
          }
          const data = await withLoading('Reading the tone of your latest entry...', () =>
            postJSON('/assistant/mood', { content: latestEntry.content })
          );
          addMessage(
            `<div><strong>Mood insight:</strong> ${formatBadge(data.mood_label)}</div><div class="small text-muted">Confidence: ${(data.confidence * 100).toFixed(0)}%</div><p class="mb-0">${data.reasoning}</p>`,
            { html: true }
          );
          break;
        }
        case 'tags': {
          const latestEntry = await fetchLatestEntry();
          if (!latestEntry) {
            addMessage('Need an entry to recommend tags. Try writing one!');
            break;
          }
          const data = await withLoading('Scanning for recurring themes...', () =>
            postJSON('/assistant/tags', { content: latestEntry.content })
          );
          const badges = data.tags
            .map(tag => `${formatBadge(tag.label)} <span class="small text-muted">${(tag.confidence * 100).toFixed(0)}%</span>`)
            .join(' ');
          addMessage(`<div><strong>Suggested tags:</strong></div><div class="d-flex flex-wrap gap-2 mt-1">${badges}</div>`, { html: true });
          break;
        }
        default:
          addMessage('That feature is coming soon ✨');
      }
    } catch (error) {
      addMessage(`⚠️ ${error.message}`);
    } finally {
      button.disabled = false;
      button.removeAttribute('aria-busy');
    }
  });

  async function fetchLatestEntry() {
    try {
      const response = await fetch('/assistant/latest');
      if (!response.ok) return null;
      const data = await response.json();
      if (!data || !data.content) {
        return null;
      }
      return data;
    } catch (error) {
      return null;
    }
  }

  // Initial welcome message
  addMessage("Hi! I'm your diary assistant. Ask me anything or try the quick actions below.");
});
