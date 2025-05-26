let currentAgent = 'GenericAgent';

function sendMessage() {
    const input = document.getElementById('chatInput');
    const chatMessages = document.getElementById('chatMessages');
    const message = input.value.trim();

    if (!message) return;

    // Показуємо повідомлення від користувача
    chatMessages.innerHTML += `<div class="mb-2"><strong>You:</strong> ${message}</div>`;

    // Тимчасово імітуємо відповідь агента
    setTimeout(() => {
        chatMessages.innerHTML += `<div class="mb-2 text-green-600"><strong>${currentAgent}:</strong> ${message} (echo)</div>`;
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 500);

    input.value = '';
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

window.addEventListener('DOMContentLoaded', () => {
    document.getElementById('chatInput').addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    document.getElementById('sendButton')?.addEventListener('click', sendMessage);
});
