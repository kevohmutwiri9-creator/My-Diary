document.addEventListener('DOMContentLoaded', () => {
  const toggleBtn = document.getElementById('assistant-toggle');
  const closeBtn = document.getElementById('assistant-close');
  const card = document.querySelector('.assistant-card');
  const chat = document.querySelector('.assistant-chat');
  const input = document.getElementById('assistant-input');
  const sendBtn = document.getElementById('assistant-send');
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

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

  // Add message to chat
  const addMessage = (text, isUser = false) => {
    const msg = document.createElement('div');
    msg.className = `mb-2 p-2 rounded ${isUser ? 'bg-primary text-white' : 'bg-light'}`;
    msg.style.maxWidth = '80%';
    msg.style.marginLeft = isUser ? 'auto' : '0';
    msg.style.wordBreak = 'break-word';
    msg.textContent = text;
    chat.appendChild(msg);
    chat.scrollTop = chat.scrollHeight;
  };

  // Handle sending messages
  sendBtn.addEventListener('click', sendQuestion);
  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendQuestion();
  });

  async function sendQuestion() {
    const question = input.value.trim();
    if (!question) return;
    
    addMessage(question, true);
    input.value = '';
    input.disabled = true;
    sendBtn.disabled = true;
    
    if (!csrfToken) {
      addMessage('Unable to send message because CSRF token is missing.', false);
      input.disabled = false;
      sendBtn.disabled = false;
      return;
    }

    try {
      const response = await fetch('/assistant/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ question })
      });
      
      if (!response.ok) throw new Error('Network error');
      
      const data = await response.json();
      if (data.error) throw new Error(data.error);
      
      addMessage(data.answer);
    } catch (error) {
      addMessage(`Error: ${error.message}`);
    } finally {
      input.disabled = false;
      sendBtn.disabled = false;
      input.focus();
    }
  }

  // Initial welcome message
  addMessage("Hi! I'm your diary assistant. Ask me about your entries or writing habits.");
});
