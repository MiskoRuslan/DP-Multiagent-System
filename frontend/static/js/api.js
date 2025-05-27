let currentAgent = null;
let currentUserId = 'dbf62431-144b-48f3-9a46-25edb1da85ae'; // TODO: отримувати з автентифікації

// Завантажити тестові дані (для відлагодження)
function loadTestAgents() {
    const agentsList = document.getElementById('agentsList');
    const loadingStatus = document.getElementById('agentsLoadingStatus');

    loadingStatus.style.display = 'none';

    const testAgents = [
        { id: 'test_1', name: 'Тестовий Агент 1' },
        { id: 'test_2', name: 'Тестовий Агент 2' },
        { id: 'generic', name: 'GenericAgent' }
    ];

    agentsList.innerHTML = '';

    testAgents.forEach(agent => {
        const listItem = document.createElement('li');
        listItem.className = 'p-2 bg-gray-100 rounded cursor-pointer hover:bg-gray-200 transition-colors';
        listItem.textContent = agent.name;
        listItem.onclick = () => loadAgent(agent.id, agent.name);
        agentsList.appendChild(listItem);
    });

    console.log('Тестові агенти завантажені');
}

// Завантажити всіх агентів при старті сторінки
async function loadAgents() {
    const agentsList = document.getElementById('agentsList');
    const loadingStatus = document.getElementById('agentsLoadingStatus');

    console.log('Спроба завантаження агентів...');

    try {
        const response = await fetch('/api/v1/all_agents');
        console.log('Відповідь сервера:', response.status, response.statusText);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Помилка відповіді сервера:', errorText);
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }

        const agents = await response.json();
        console.log('Завантажені агенти:', agents);

        // Сховати статус завантаження
        loadingStatus.style.display = 'none';

        agentsList.innerHTML = '';

        if (!agents || agents.length === 0) {
            agentsList.innerHTML = '<li class="p-2 text-gray-500">Немає доступних агентів</li>';
            return;
        }

        agents.forEach(agent => {
            const listItem = document.createElement('li');
            listItem.className = 'p-2 bg-gray-100 rounded cursor-pointer hover:bg-gray-200 transition-colors';
            listItem.textContent = agent.name || agent.id || 'Невідомий агент';
            listItem.onclick = () => loadAgent(agent.id, agent.name || agent.id);
            agentsList.appendChild(listItem);
        });

        console.log('Агенти успішно завантажені');
    } catch (error) {
        console.error('Помилка завантаження агентів:', error);
        loadingStatus.style.display = 'none';

        // Детальна інформація про помилку
        let errorMessage = 'Помилка завантаження агентів';
        if (error.message.includes('Failed to fetch')) {
            errorMessage = 'Неможливо підключитися до сервера. Перевірте чи запущений backend.';
        } else if (error.message.includes('404')) {
            errorMessage = 'Ендпоінт /api/v1/all_agents не знайдено';
        } else if (error.message.includes('500')) {
            errorMessage = 'Внутрішня помилка сервера';
        }

        agentsList.innerHTML = `
            <li class="p-2 text-red-500 text-sm">
                ${errorMessage}
                <br><small>Деталі: ${error.message}</small>
            </li>
            <li class="p-2 mt-2">
                <button onclick="loadAgents()" class="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600">
                    Спробувати знову
                </button>
            </li>
            <li class="p-2 mt-2">
                <button onclick="loadTestAgents()" class="px-3 py-1 bg-green-500 text-white rounded text-sm hover:bg-green-600">
                    Завантажити тестові дані
                </button>
            </li>
        `;
    }
}

// Завантажити чат з конкретним агентом
async function loadAgent(agentId, agentName) {
    currentAgent = {
        id: agentId,
        name: agentName
    };

    // Оновити UI - показати який агент активний
    const agentItems = document.querySelectorAll('#agentsList li');
    agentItems.forEach(item => {
        item.classList.remove('bg-blue-200', 'bg-blue-500', 'text-white');
        item.classList.add('bg-gray-100');
        if (item.textContent === agentName) {
            item.classList.remove('bg-gray-100');
            item.classList.add('bg-blue-500', 'text-white');
        }
    });

    // Оновити статус обраного агента
    const selectedAgentText = document.getElementById('selectedAgentText');
    selectedAgentText.textContent = `Активний чат з: ${agentName}`;

    // Завантажити історію чату
    await loadChatHistory();
}

// Завантажити історію чату між користувачем та агентом
async function loadChatHistory() {
    if (!currentAgent) return;

    try {
        const response = await fetch(`/api/v1/get_chat?user_id=${currentUserId}&agent_id=${currentAgent.id}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const chatHistory = await response.json();

        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = '';

        chatHistory.forEach(message => {
            displayMessage(message);
        });

        scrollChatToBottom();
    } catch (error) {
        console.error('Помилка завантаження історії чату:', error);
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = '<div class="text-red-500">Помилка завантаження історії чату</div>';
    }
}

// Відобразити повідомлення в чаті
// Відобразити повідомлення в чаті
function displayMessage(message) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'mb-3 p-3 rounded-lg';

    // ВИПРАВЛЕНА ЛОГІКА: спочатку перевіряємо поле sender з бази даних
    let sender = '';
    let isFromUser = false;
    let isFromAgent = false;

    // Перевіряємо sender з бази даних (це найнадійніший спосіб)
    if (message.sender === 'USER') {
        isFromUser = true;
        sender = 'Ви';
    } else if (message.sender === 'AGENT') {
        isFromAgent = true;
        sender = currentAgent ? currentAgent.name : 'Агент';
    }
    // Резервна логіка для випадків коли sender відсутній (тільки для нових повідомлень)
    else if (message.user_id === currentUserId) {
        isFromUser = true;
        sender = 'Ви';
    } else if (message.user_id === 'agent_response') {
        isFromAgent = true;
        sender = currentAgent ? currentAgent.name : 'Агент';
    } else {
        // Для випадків коли не можемо точно визначити відправника
        messageDiv.classList.add('bg-yellow-50', 'border-l-4', 'border-yellow-400');
        sender = 'Невідомо';
        console.warn('Не вдалося визначити відправника повідомлення:', message);
    }

    // Застосовуємо стилі на основі відправника
    if (isFromUser) {
        messageDiv.classList.add('bg-blue-100', 'ml-8', 'border-l-4', 'border-blue-500');
    } else if (isFromAgent) {
        messageDiv.classList.add('bg-gray-100', 'mr-8', 'border-l-4', 'border-gray-500');
    }

    let content = '';

    // Спочатку перевіряємо message_text (з бази даних)
    if (message.message_text) {
        content = message.message_text;
    }
    // Потім перевіряємо text (з API)
    else if (message.text) {
        content = message.text;
    }
    // Для зображень
    else if (message.message_type === 'IMAGE' && (message.message_image || message.image)) {
        const imageData = message.message_image || message.image;
        content = `<img src="data:image/jpeg;base64,${imageData}" alt="Зображення" class="max-w-xs rounded shadow-md">`;
    }
    // Якщо це AI відповідь
    else if (message.ai_response) {
        content = message.ai_response;
    }
    else {
        content = '<em class="text-gray-500">Порожнє повідомлення</em>';
    }

    // Форматування часу
    let timestamp = '';
    if (message.was_sent) {
        timestamp = new Date(message.was_sent).toLocaleString('uk-UA', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    messageDiv.innerHTML = `
        <div class="flex justify-between items-center mb-2">
            <div class="font-semibold text-sm ${isFromUser ? 'text-blue-700' : isFromAgent ? 'text-gray-700' : 'text-yellow-700'}">${sender}</div>
            <div class="text-xs text-gray-400">${timestamp}</div>
        </div>
        <div class="text-gray-800 leading-relaxed">${content}</div>
    `;

    chatMessages.appendChild(messageDiv);
}

// Відправити повідомлення
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();

    if (!message) return;

    if (!currentAgent) {
        alert('Спочатку оберіть агента зі списку');
        return;
    }

    // Створити об'єкт повідомлення
    const chatMessage = {
        message_type: 'TEXT',
        text: message,
        image: null,
        was_sent: new Date().toISOString(),
        agent_id: currentAgent.id,
        user_id: currentUserId
    };

    // Показати повідомлення користувача одразу
    const userMessage = { ...chatMessage, sender: 'USER' };
    displayMessage(userMessage);
    input.value = '';
    scrollChatToBottom();

    // Показати індикатор набору для агента
    const typingDiv = document.createElement('div');
    typingDiv.className = 'mb-3 p-3 rounded-lg bg-gray-50 mr-8 border-l-4 border-gray-300';
    typingDiv.id = 'typing-indicator';
    typingDiv.innerHTML = `
        <div class="flex items-center space-x-2">
            <div class="font-semibold text-sm text-gray-600">${currentAgent.name}</div>
            <div class="flex space-x-1">
                <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.1s;"></div>
                <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s;"></div>
            </div>
        </div>
        <div class="text-gray-500 text-sm mt-1">Набирає відповідь...</div>
    `;
    document.getElementById('chatMessages').appendChild(typingDiv);
    scrollChatToBottom();

    try {
        // Відправити повідомлення на сервер
        const response = await fetch('/api/v1/send', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(chatMessage)
        });

        // Видалити індикатор набору
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const responseData = await response.json();
        console.log('Відповідь сервера:', responseData);

        // Відобразити відповідь агента
        if (responseData && responseData.ai_response) {
            const agentResponse = {
                message_type: 'TEXT',
                text: responseData.ai_response,
                was_sent: new Date().toISOString(),
                agent_id: currentAgent.id,
                user_id: 'agent_response',
                sender: 'AGENT'
            };
            displayMessage(agentResponse);
        } else {
            console.warn('Немає AI відповіді в responseData:', responseData);
        }

        scrollChatToBottom();
    } catch (error) {
        console.error('Помилка відправки повідомлення:', error);

        // Видалити індикатор набору в разі помилки
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }

        // Показати повідомлення про помилку
        const errorMessage = {
            message_type: 'TEXT',
            text: `❌ Помилка відправки повідомлення: ${error.message}`,
            was_sent: new Date().toISOString(),
            agent_id: 'system',
            user_id: 'system',
            sender: 'SYSTEM'
        };
        displayMessage(errorMessage);
        scrollChatToBottom();
    }
}

// Прокрутити чат вниз
function scrollChatToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Обробка завантаження сторінки
window.addEventListener('DOMContentLoaded', () => {
    // Завантажити агентів
    loadAgents();

    // Обробники подій для відправки повідомлень
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendMessage();
            }
        });

        // Фокус на поле введення
        chatInput.focus();
    }

    const sendButton = document.getElementById('sendButton');
    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    }
});
