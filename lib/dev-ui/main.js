const chatLog = document.getElementById('chatLog');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');

sendButton.addEventListener('click', () => {
    if (messageInput.value.trim()) {
        const userMessage = {
            user: 'User',
            content: messageInput.value
        };

        // This function will handle appending messages to the chat log
        appendMessage(userMessage);
        messageInput.value = '';

        // Send message via IPC to parent process
        sendMessage(userMessage);
    }
});

function appendMessage(data) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('border', 'p-2', 'mt-3');
    messageElement.innerHTML = `
        <h6>${data.user}</h6>
        <pre class="message-text">${data.content}</pre>
    `;
    chatLog.appendChild(messageElement);
    chatLog.scrollTop = chatLog.scrollHeight;
}

async function sendMessage(data) {
    await fetch('/api/ipc/write', {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data),
    });
}

read_inflight = false;

async function readMessages() {
    if (read_inflight) return;
    read_inflight = true;
    const response = await fetch('/api/ipc/read');
    if (response.status === 200) {
        const message = await response.json()
        appendMessage(message);
    }
    read_inflight = false;
    return
}

// Poll for new messages every second
setInterval(readMessages, 1000);
