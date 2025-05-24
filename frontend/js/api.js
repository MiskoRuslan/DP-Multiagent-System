async function sendText() {
    const text = document.getElementById('textInput').value;
    const responseElement = document.getElementById('response');
    responseElement.textContent = '...';
    responseElement.className = 'mt-6 text-center text-gray-600';
    try {
        const response = await fetch('/api/text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });
        const data = await response.json();
        responseElement.textContent = data.message;
        responseElement.className = 'mt-6 text-center text-green-600';
    } catch (error) {
        responseElement.textContent = 'Error: ' + error.message;
        responseElement.className = 'mt-6 text-center text-red-600';
    }
}
