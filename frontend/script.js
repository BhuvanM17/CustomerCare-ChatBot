const API_URL = window.location.hostname === 'localhost' ? 'http://localhost:5000/chat' : '/api/chat';

const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const chatForm = document.getElementById('chatForm');

// Focus input on load
userInput.focus();

// Quick Message Handler
function sendQuickMessage(text) {
    userInput.value = text;
    handleChatSubmit({ preventDefault: () => {} });
}

// Clear Chat
function clearChat() {
    chatMessages.innerHTML = `
        <div class="message bot-message">
            <div class="message-content">
                Hello! 👋 I'm your AI-powered e-commerce invoice assistant.<br><br>
                I can generate invoices, validate missing fields, and suggest what to add before checkout.
            </div>
            <span class="timestamp">Just now</span>
        </div>
    `;
}

// Handle Submit
async function handleChatSubmit(e) {
    e.preventDefault();
    
    const message = userInput.value.trim();
    if (!message) return;

    // 1. Add User Message
    addMessage(message, 'user');
    userInput.value = '';
    
    // 2. Show Typing Indicator
    const typingId = showTypingIndicator();

    try {
        // 3. Call API
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message }),
        });

        const data = await response.json();
        
        // Remove typing indicator
        removeTypingIndicator(typingId);

        if (data.error) {
            addMessage('⚠️ Sorry, I encountered an error. Please try again.', 'bot');
        } else {
            addMessage(data.response, 'bot');
        }

    } catch (error) {
        removeTypingIndicator(typingId);
        addMessage('⚠️ Server connection failed. Is the backend running? Please check simple server instructions.', 'bot');
        console.error('Error:', error);
    }
}

// Add Message to UI
function addMessage(text, sender) {
    const div = document.createElement('div');
    div.classList.add('message', `${sender}-message`);
    
    // Parse Markdown if bot
    let content = text;
    if (sender === 'bot') {
        if (typeof marked !== 'undefined') {
            // Configure marked to break on single newlines
            marked.setOptions({ breaks: true });
            content = marked.parse(text);
        } else {
            // Fallback basic parsing
            content = text.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
                          .replace(/\n/g, '<br>');
        }
    }

    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    div.innerHTML = `
        <div class="message-content">${content}</div>
        <span class="timestamp">${time}</span>
    `;

    chatMessages.appendChild(div);
    scrollToBottom();
}

// Typing Indicator
function showTypingIndicator() {
    const id = 'typing-' + Date.now();
    const div = document.createElement('div');
    div.id = id;
    div.classList.add('message', 'bot-message');
    div.innerHTML = `
        <div class="typing-indicator">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        </div>
    `;
    chatMessages.appendChild(div);
    scrollToBottom();
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}
