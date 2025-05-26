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
function displayMessage(message) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'mb-3 p-2 rounded';

    const isFromUser = message.user_id === currentUserId;
    const sender = isFromUser ? 'Ви' : (currentAgent ? currentAgent.name : 'Агент');

    if (isFromUser) {
        messageDiv.classList.add('bg-blue-100', 'ml-8');
    } else {
        messageDiv.classList.add('bg-gray-100', 'mr-8');
    }

    let content = '';
    if (message.message_type === 'TEXT' && message.message_text) {
        content = message.message_text;
    } else if (message.message_type === 'IMAGE' && message.message_image) {
        content = `<img src="data:image/jpeg;base64,${message.message_image}" alt="Зображення" class="max-w-xs rounded">`; // Змінено з message.image на message.message_image
    }

    const timestamp = new Date(message.was_sent).toLocaleString('uk-UA');

    messageDiv.innerHTML = `
        <div class="font-semibold text-sm ${isFromUser ? 'text-blue-700' : 'text-gray-700'}">${sender}</div>
        <div class="mt-1">${content}</div>
        <div class="text-xs text-gray-500 mt-1">${timestamp}</div>
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
    displayMessage(chatMessage);
    input.value = '';
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

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const responseData = await response.json();

        // Відобразити відповідь агента
        if (responseData && typeof responseData === 'string') {
            // Якщо сервер повертає просто рядок
            const agentResponse = {
                message_type: 'TEXT',
                text: responseData,
                image: null,
                was_sent: new Date().toISOString(),
                agent_id: currentAgent.id,
                user_id: 'agent_response'
            };
            displayMessage(agentResponse);
        } else if (responseData && responseData.text) {
            // Якщо сервер повертає об'єкт ChatMessageResponse
            const agentResponse = {
                ...responseData,
                user_id: 'agent_response'
            };
            displayMessage(agentResponse);
        }

        scrollChatToBottom();
    } catch (error) {
        console.error('Помилка відправки повідомлення:', error);

        // Показати повідомлення про помилку
        const errorDiv = document.createElement('div');
        errorDiv.className = 'text-red-500 text-center p-2';
        errorDiv.textContent = 'Помилка відправки повідомлення. Спробуйте ще раз.';
        document.getElementById('chatMessages').appendChild(errorDiv);
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
    document.getElementById('chatInput').addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendMessage();
        }
    });

    document.getElementById('sendButton')?.addEventListener('click', sendMessage);

    // Фокус на поле введення
    document.getElementById('chatInput').focus();
});
