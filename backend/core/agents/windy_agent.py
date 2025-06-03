from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from backend.clients.windy_client import get_current_weather
from crewai.tools import tool
from datetime import datetime
import asyncio


@tool("get_windy_weather")
def get_windy_weather_tool(lat: float, lon: float) -> str:
    """
    Get current weather data from Windy API by coordinates.

    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate

    Returns:
        Formatted HTML string with weather information
    """
    try:
        # Отримуємо дані з вашого windy_client
        weather_data = get_current_weather(lat, lon)

        # Форматуємо у HTML
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 20px auto; padding: 20px; 
                    border: 2px solid #4CAF50; border-radius: 15px; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);">

            <h2 style="text-align: center; color: #1976d2; margin-bottom: 20px; font-size: 24px;">
                🌤️ Погода від Windy
            </h2>

            <div style="background: rgba(255,255,255,0.8); padding: 15px; border-radius: 10px; margin-bottom: 15px;">
                <h3 style="color: #424242; margin-top: 0;">📍 Координати</h3>
                <p style="margin: 5px 0; color: #666;">
                    <strong>Широта:</strong> {lat:.4f}° | 
                    <strong>Довгота:</strong> {lon:.4f}°
                </p>
                <p style="margin: 5px 0; color: #666; font-size: 12px;">
                    <em>Оновлено: {timestamp}</em>
                </p>
            </div>

            <div style="background: rgba(255,255,255,0.9); padding: 15px; border-radius: 10px;">
                <h3 style="color: #424242; margin-top: 0;">🌡️ Поточні умови</h3>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px;">
                    {_create_weather_item("🌡️", "Температура", weather_data.get('temperature', 'N/A'))}
                    {_create_weather_item("💨", "Швидкість вітру", weather_data.get('wind_speed', 'N/A'))}
                    {_create_weather_item("💨💨", "Пориви вітру", weather_data.get('wind_gust', 'N/A'))}
                    {_create_weather_item("💧", "Вологість", weather_data.get('humidity', 'N/A'))}
                    {_create_weather_item("📊", "Тиск", weather_data.get('pressure', 'N/A'))}
                    {_create_weather_item("🌧️", "Опади (3год)", weather_data.get('precipitation', 'N/A'))}
                </div>

                {_create_weather_item("🌫️", "Точка роси", weather_data.get('dewpoint', 'N/A'), full_width=True)}
            </div>
        </div>
        """

        return html

    except Exception as e:
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 20px auto; padding: 20px; 
                    border: 2px solid #f44336; border-radius: 15px; background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);">

            <h2 style="text-align: center; color: #d32f2f; margin-bottom: 20px;">
                ❌ Помилка отримання даних
            </h2>

            <div style="background: rgba(255,255,255,0.8); padding: 15px; border-radius: 10px;">
                <p style="color: #666; margin: 10px 0;">
                    <strong>Координати:</strong> {lat:.4f}°, {lon:.4f}°
                </p>
                <p style="color: #d32f2f; margin: 10px 0;">
                    <strong>Помилка:</strong> {str(e)}
                </p>
            </div>
        </div>
        """


def _create_weather_item(icon: str, label: str, value: str,
                         full_width: bool = False) -> str:
    """Створює HTML елемент для погодного параметра"""
    width_style = "grid-column: 1 / -1;" if full_width else ""

    return f"""
    <div style="{width_style} background: rgba(255,255,255,0.6); padding: 10px; border-radius: 8px; 
                border-left: 4px solid #4CAF50;">
        <div style="font-size: 14px; color: #666; margin-bottom: 2px;">
            {icon} {label}
        </div>
        <div style="font-size: 16px; font-weight: bold; color: #333;">
            {value}
        </div>
    </div>
    """


class WindyWeatherAgent:

    def __init__(self, agent_id: str, name: str, system_prompt: str = None):
        self.agent_id = agent_id
        self.name = name
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

        backstory = system_prompt if system_prompt else """
        You are a smart weather assistant that provides accurate weather information based on coordinates.
        You have access to tools to retrieve current weather from the Windy API.
        
        When users ask about weather, you should:
        1. Use the get_windy_weather tool to generate current conditions based on coordinates
        2. Extract coordinates (latitude and longitude) using the user's message
        3. Provide useful and informative responses in HTML format
        4. If coordinates are not provided, ask the user to provide them
        
        Always be friendly and helpful in your responses.
        Reply in Ukrainian.
        """

        # Створюємо агента з інструментами
        self.agent = Agent(
            role='Smart Windy weather assistant',
            goal='Provide accurate coordinate weather information using Windy API',
            backstory=backstory,
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[get_windy_weather_tool]
        )

    async def process_message(self, message: str) -> str:
        try:
            task = Task(
                description=f"""
                Analyze the user's message and give appropriate answer using the available weather tools.

                Повідомлення користувача: "{message}"
                ID агента: {self.agent_id}

                Інструкції:
                - Якщо користувач надає координати (широту та довготу), 
                використай інструмент get_windy_weather
                - Якщо координати не вказані, 
                попроси користувача надати широту та довготу
                - Витягуй координати з повідомлення користувача уважно
                - Координати можуть бути у різних форматах: 
                50.4501, 30.5234 або 50.4501°N, 30.5234°E тощо
                - Завжди надавай корисні та інформативні відповіді
                - Відповідай українською мовою
                - Використовуй HTML-форматування для красивого відображення погоди 
                (Помісти відповідь у наступну структуру: 
                ```html-render <відповідь у вигляді html>```
                Надай повну відповідь, яка безпосередньо відповідає на 
                запит користувача про погоду.
                """,
                expected_output="Корисна відповідь про "
                                "погоду використовуючи відповідні "
                                "інструменти на основі запиту користувача",
                agent=self.agent
            )

            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                process=Process.sequential,
                verbose=True
            )

            # Запускаємо crew асинхронно
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, crew.kickoff)

            return str(result)

        except Exception as e:
            print(f"Помилка обробки повідомлення з WindyWeatherAgent: {str(e)}")
            return (f"Вибачте, я зіткнувся з помилкою під час "
                    f"обробки вашого запиту про погоду: {str(e)}")
