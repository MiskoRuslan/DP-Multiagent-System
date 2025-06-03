from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from crewai.tools import tool
from datetime import datetime, timezone, timedelta
import asyncio
import json
from typing import List, Optional, Dict, Any
import re

from backend.clients.open_sky_client import OpenSkyClient


# Імпортуємо наш OpenSky клієнт
# from backend.clients.opensky_client import OpenSkyClient  # Розкоментуйте та вкажіть правильний шлях


@tool("get_current_aircraft_states")
def get_current_aircraft_states_tool(bbox: Optional[str] = None,
                                     icao24: Optional[str] = None) -> str:
    """
    Get current aircraft state vectors in the specified area or for specific aircraft.

    Args:
        bbox: Bounding box as string "lat_min,lon_min,lat_max,lon_max" (e.g., "49.0,29.0,51.0,31.0" for Ukraine area)
        icao24: Specific aircraft ICAO24 code (e.g., "4b1807")

    Returns:
        Formatted HTML string with aircraft information
    """
    try:
        client = OpenSkyClient()

        # Парсимо bbox якщо надано
        bbox_params = None
        if bbox:
            coords = [float(x.strip()) for x in bbox.split(',')]
            if len(coords) == 4:
                bbox_params = tuple(coords)

        # Отримуємо стани літаків
        states = client.get_states(bbox=bbox_params, icao24=icao24)

        if not states:
            return _create_empty_result_html(
                "Наразі не знайдено активних літаків у вказаній зоні")

        # Створюємо HTML
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 20px auto; padding: 20px; 
                    border: 2px solid #2196F3; border-radius: 15px; background: linear-gradient(135deg, #e1f5fe 0%, #b3e5fc 100%);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);">

            <h2 style="text-align: center; color: #0277bd; margin-bottom: 20px; font-size: 24px;">
                ✈️ Поточні авіарейси
            </h2>

            <div style="background: rgba(255,255,255,0.8); padding: 15px; border-radius: 10px; margin-bottom: 15px;">
                <p style="margin: 5px 0; color: #666;">
                    <strong>Знайдено літаків:</strong> {len(states)} | 
                    <strong>Оновлено:</strong> {timestamp}
                </p>
                {f'<p style="margin: 5px 0; color: #666;"><strong>Зона:</strong> {bbox}</p>' if bbox else ''}
                {f'<p style="margin: 5px 0; color: #666;"><strong>ICAO24:</strong> {icao24}</p>' if icao24 else ''}
            </div>

            <div style="display: grid; gap: 15px;">
                {"".join([_create_aircraft_card(state) for state in states[:10]])}
            </div>

            {f'<p style="text-align: center; color: #666; margin-top: 15px; font-style: italic;">Показано перші 10 з {len(states)} літаків</p>' if len(states) > 10 else ''}
        </div>
        """

        return html

    except Exception as e:
        return _create_error_html("Помилка отримання даних про літаки", str(e))


@tool("get_aircraft_flights")
def get_aircraft_flights_tool(icao24: str, days_back: int = 7) -> str:
    """
    Get flight history for specific aircraft.

    Args:
        icao24: Aircraft ICAO24 code (e.g., "4b1807")
        days_back: Number of days to look back (default: 7)

    Returns:
        Formatted HTML string with flight history
    """
    try:
        client = OpenSkyClient()
        current_time = client.get_current_timestamp()
        begin_time = current_time - days_back * 24 * 3600

        flights = client.get_flights_by_aircraft(icao24, begin_time, current_time)

        if not flights:
            return _create_empty_result_html(
                f"Не знайдено рейсів для літака {icao24} за останні {days_back} днів")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 20px auto; padding: 20px; 
                    border: 2px solid #FF9800; border-radius: 15px; background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);">

            <h2 style="text-align: center; color: #ef6c00; margin-bottom: 20px; font-size: 24px;">
                🛫 Історія рейсів літака
            </h2>

            <div style="background: rgba(255,255,255,0.8); padding: 15px; border-radius: 10px; margin-bottom: 15px;">
                <p style="margin: 5px 0; color: #666;">
                    <strong>ICAO24:</strong> {icao24} | 
                    <strong>Знайдено рейсів:</strong> {len(flights)} | 
                    <strong>Період:</strong> {days_back} днів
                </p>
                <p style="margin: 5px 0; color: #666; font-size: 12px;">
                    <em>Оновлено: {timestamp}</em>
                </p>
            </div>

            <div style="display: grid; gap: 10px;">
                {"".join([_create_flight_card(flight) for flight in flights])}
            </div>
        </div>
        """

        return html

    except Exception as e:
        return _create_error_html("Помилка отримання історії рейсів", str(e))


@tool("get_airport_flights")
def get_airport_flights_tool(airport_code: str, flight_type: str = "both",
                             days_back: int = 1) -> str:
    """
    Get flights for specific airport (arrivals, departures or both).

    Args:
        airport_code: ICAO airport code (e.g., "UKBB" for Kyiv Boryspil, "EDDF" for Frankfurt)
        flight_type: Type of flights - "arrivals", "departures", or "both" (default: "both")
        days_back: Number of days to look back (default: 1)

    Returns:
        Formatted HTML string with airport flights information
    """
    try:
        client = OpenSkyClient()
        current_time = client.get_current_timestamp()
        begin_time = current_time - days_back * 24 * 3600

        arrivals = []
        departures = []

        if flight_type in ["arrivals", "both"]:
            arrivals = client.get_arrivals_by_airport(airport_code, begin_time,
                                                      current_time)

        if flight_type in ["departures", "both"]:
            departures = client.get_departures_by_airport(airport_code, begin_time,
                                                          current_time)

        if not arrivals and not departures:
            return _create_empty_result_html(
                f"Не знайдено рейсів для аеропорту {airport_code}")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 900px; margin: 20px auto; padding: 20px; 
                    border: 2px solid #4CAF50; border-radius: 15px; background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);">

            <h2 style="text-align: center; color: #2e7d32; margin-bottom: 20px; font-size: 24px;">
                🏢 Рейси аеропорту {airport_code}
            </h2>

            <div style="background: rgba(255,255,255,0.8); padding: 15px; border-radius: 10px; margin-bottom: 15px;">
                <p style="margin: 5px 0; color: #666;">
                    <strong>Аеропорт:</strong> {airport_code} | 
                    <strong>Прильотів:</strong> {len(arrivals)} | 
                    <strong>Вильотів:</strong> {len(departures)} | 
                    <strong>Період:</strong> {days_back} д.
                </p>
                <p style="margin: 5px 0; color: #666; font-size: 12px;">
                    <em>Оновлено: {timestamp}</em>
                </p>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                {_create_airport_section("Прильоти ✈️⬇️", arrivals, "#4CAF50") if arrivals else ""}
                {_create_airport_section("Вильоти ✈️⬆️", departures, "#FF9800") if departures else ""}
            </div>
        </div>
        """

        return html

    except Exception as e:
        return _create_error_html("Помилка отримання даних аеропорту", str(e))


@tool("get_aircraft_track")
def get_aircraft_track_tool(icao24: str, hours_back: int = 1) -> str:
    """
    Get flight track for aircraft.

    Args:
        icao24: Aircraft ICAO24 code
        hours_back: Hours back from current time to get track (default: 1)

    Returns:
        Formatted HTML string with track information
    """
    try:
        client = OpenSkyClient()
        track_time = client.get_current_timestamp() - hours_back * 3600

        tracks = client.get_track_by_aircraft(icao24, track_time)

        if not tracks:
            return _create_empty_result_html(f"Не знайдено треку для літака {icao24}")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 20px auto; padding: 20px; 
                    border: 2px solid #9C27B0; border-radius: 15px; background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);">

            <h2 style="text-align: center; color: #7b1fa2; margin-bottom: 20px; font-size: 24px;">
                🛤️ Трек польоту літака
            </h2>

            <div style="background: rgba(255,255,255,0.8); padding: 15px; border-radius: 10px; margin-bottom: 15px;">
                <p style="margin: 5px 0; color: #666;">
                    <strong>ICAO24:</strong> {icao24} | 
                    <strong>Точок треку:</strong> {len(tracks)} | 
                    <strong>Період:</strong> {hours_back} год назад
                </p>
                <p style="margin: 5px 0; color: #666; font-size: 12px;">
                    <em>Оновлено: {timestamp}</em>
                </p>
            </div>

            <div style="background: rgba(255,255,255,0.9); padding: 15px; border-radius: 10px;">
                <h3 style="color: #424242; margin-top: 0;">📍 Точки маршруту</h3>
                <div style="max-height: 400px; overflow-y: auto;">
                    {"".join([_create_track_point(track, i) for i, track in enumerate(tracks)])}
                </div>
            </div>
        </div>
        """

        return html

    except Exception as e:
        return _create_error_html("Помилка отримання треку", str(e))


# Допоміжні функції для створення HTML елементів
def _create_aircraft_card(state) -> str:
    """Створює картку літака"""
    status = "🟢 У повітрі" if not state.on_ground else "🔴 На землі"

    return f"""
    <div style="background: rgba(255,255,255,0.9); padding: 15px; border-radius: 10px; 
                border-left: 4px solid {'#4CAF50' if not state.on_ground else '#f44336'};">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div>
                <strong style="color: #1976d2;">✈️ {state.callsign or 'N/A'}</strong>
                <br><small>ICAO24: {state.icao24}</small>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 12px; padding: 4px 8px; border-radius: 12px; 
                           background: {'rgba(76, 175, 80, 0.2)' if not state.on_ground else 'rgba(244, 67, 54, 0.2)'};">
                    {status}
                </span>
            </div>
        </div>

        <div style="margin-top: 10px; display: grid; grid-template-columns: 1fr 1fr; gap: 5px; font-size: 13px;">
            <div><strong>🌍 Країна:</strong> {state.origin_country}</div>
            <div><strong>📍 Позиція:</strong> {f'{state.latitude:.3f}, {state.longitude:.3f}' if state.latitude and state.longitude else 'N/A'}</div>
            <div><strong>📏 Висота:</strong> {f'{state.baro_altitude:.0f} м' if state.baro_altitude else 'N/A'}</div>
            <div><strong>🏃 Швидкість:</strong> {f'{state.velocity:.0f} м/с' if state.velocity else 'N/A'}</div>
        </div>
    </div>
    """


def _create_flight_card(flight) -> str:
    """Створює картку рейсу"""
    dep_time = datetime.fromtimestamp(flight.first_seen, tz=timezone.utc).strftime(
        "%d.%m %H:%M") if flight.first_seen else "N/A"
    arr_time = datetime.fromtimestamp(flight.last_seen, tz=timezone.utc).strftime(
        "%d.%m %H:%M") if flight.last_seen else "N/A"

    return f"""
    <div style="background: rgba(255,255,255,0.9); padding: 12px; border-radius: 8px; 
                border-left: 4px solid #FF9800;">
        <div style="display: grid; grid-template-columns: 1fr auto 1fr; gap: 15px; align-items: center;">
            <div style="text-align: left;">
                <strong style="color: #ef6c00;">🛫 {flight.est_departure_airport or 'N/A'}</strong>
                <br><small>{dep_time}</small>
            </div>

            <div style="text-align: center;">
                <strong style="color: #1976d2;">✈️ {flight.callsign or 'N/A'}</strong>
                <br><small style="color: #666;">━━━━━━━━━━━▶</small>
            </div>

            <div style="text-align: right;">
                <strong style="color: #ef6c00;">🛬 {flight.est_arrival_airport or 'N/A'}</strong>
                <br><small>{arr_time}</small>
            </div>
        </div>
    </div>
    """


def _create_airport_section(title: str, flights: List, color: str) -> str:
    """Створює секцію для рейsів аеропорту"""
    if not flights:
        return ""

    return f"""
    <div style="background: rgba(255,255,255,0.9); padding: 15px; border-radius: 10px;">
        <h3 style="color: {color}; margin-top: 0; text-align: center;">{title}</h3>
        <div style="max-height: 300px; overflow-y: auto;">
            {"".join([_create_simple_flight_card(flight) for flight in flights[:15]])}
        </div>
        {f'<p style="text-align: center; color: #666; font-size: 12px; margin-top: 10px;">Показано 15 з {len(flights)}</p>' if len(flights) > 15 else ''}
    </div>
    """


def _create_simple_flight_card(flight) -> str:
    """Створює просту картку рейсу для аеропорту"""
    return f"""
    <div style="background: rgba(255,255,255,0.7); padding: 8px; margin: 5px 0; border-radius: 6px;">
        <strong>{flight.callsign or 'N/A'}</strong> 
        <span style="color: #666;">
            {flight.est_departure_airport or 'N/A'} → {flight.est_arrival_airport or 'N/A'}
        </span>
    </div>
    """


def _create_track_point(track, index: int) -> str:
    """Створює точку треку"""
    track_time = datetime.fromtimestamp(track.time, tz=timezone.utc).strftime(
        "%H:%M:%S") if track.time else "N/A"

    return f"""
    <div style="background: rgba(255,255,255,0.7); padding: 10px; margin: 5px 0; border-radius: 6px; 
                border-left: 3px solid #9C27B0;">
        <div style="display: grid; grid-template-columns: auto 1fr 1fr 1fr; gap: 10px; align-items: center; font-size: 13px;">
            <strong style="color: #7b1fa2;">#{index + 1}</strong>
            <div><strong>⏰</strong> {track_time}</div>
            <div><strong>📍</strong> {f'{track.latitude:.4f}, {track.longitude:.4f}' if track.latitude and track.longitude else 'N/A'}</div>
            <div><strong>📏</strong> {f'{track.baro_altitude:.0f} м' if track.baro_altitude else 'N/A'}</div>
        </div>
    </div>
    """


def _create_error_html(title: str, error: str) -> str:
    """Створює HTML для помилки"""
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 20px auto; padding: 20px; 
                border: 2px solid #f44336; border-radius: 15px; background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
        <h2 style="text-align: center; color: #d32f2f; margin-bottom: 20px;">❌ {title}</h2>
        <div style="background: rgba(255,255,255,0.8); padding: 15px; border-radius: 10px;">
            <p style="color: #d32f2f; margin: 10px 0;"><strong>Помилка:</strong> {error}</p>
        </div>
    </div>
    """


def _create_empty_result_html(message: str) -> str:
    """Створює HTML для пустого результату"""
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 20px auto; padding: 20px; 
                border: 2px solid #FF9800; border-radius: 15px; background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
        <h2 style="text-align: center; color: #ef6c00; margin-bottom: 20px;">ℹ️ Інформація</h2>
        <div style="background: rgba(255,255,255,0.8); padding: 15px; border-radius: 10px;">
            <p style="color: #666; margin: 10px 0; text-align: center;">{message}</p>
        </div>
    </div>
    """


class OpenSkyAviationAgent:
    """Агент для роботи з авіаційними даними OpenSky Network"""

    def __init__(self, agent_id: str, name: str, system_prompt: str = None):
        self.agent_id = agent_id
        self.name = name
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

        backstory = system_prompt if system_prompt else """
        Ви експертний авіаційний аналітик, який має доступ до даних OpenSky Network.
        Ви можете надавати інформацію про:

        1. Поточні позиції літаків в реальному часі
        2. Історію рейсів конкретних літаків
        3. Рейси аеропортів (прильоти та вильоти)
        4. Треки польотів літаків

        Коли користувачі запитують про авіацію, ви повинні:
        - Використовувати відповідні інструменти для отримання актуальних даних
        - Інтерпретувати ICAO коди літаків та аеропортів
        - Надавати детальну та корисну інформацію
        - Пояснювати авіаційні терміни простою мовою

        Завжди відповідайте українською мовою та будьте дружелюбними і корисними.
        """

        # Створюємо агента з усіма інструментами
        self.agent = Agent(
            role='Expert Aviation Data Analyst',
            goal='Provide comprehensive aviation information using OpenSky Network data',
            backstory=backstory,
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[
                get_current_aircraft_states_tool,
                get_aircraft_flights_tool,
                get_airport_flights_tool,
                get_aircraft_track_tool
            ]
        )

    async def process_message(self, message: str) -> str:
        """Обробляє повідомлення користувача"""
        try:
            task = Task(
                description=f"""
                Проаналізуйте запит користувача та надайте відповідь використовуючи доступні авіаційні інструменти.

                Повідомлення користувача: "{message}"
                ID агента: {self.agent_id}

                Інструкції:
                - Визначте, який тип авіаційної інформації потрібен користувачу
                - Використайте відповідні інструменти для отримання даних:
                  * get_current_aircraft_states - для поточних позицій літаків
                  * get_aircraft_flights - для історії рейсів конкретного літака
                  * get_airport_flights - для рейсів аеропорту
                  * get_aircraft_track - для треку польоту літака

                - Розпізнавайте:
                  * ICAO коди літаків (наприклад, "4b1807")
                  * ICAO коди аеропортів (наприклад, "UKBB", "EDDF")
                  * Координати для області пошуку
                  * Часові періоди

                - У відповіді використовуйте структуру:
                ```html-render
                <ваша HTML відповідь>
                ```

                - Завжди надавайте корисну, детальну відповідь українською мовою
                - Якщо потрібні додаткові параметри, попросіть користувача їх надати
                """,
                expected_output="Детальна авіаційна інформація у форматі HTML на основі запиту користувача",
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
            print(f"Помилка обробки повідомлення в OpenSkyAviationAgent: {str(e)}")
            return (f"Вибачте, я зіткнувся з помилкою під час обробки вашого "
                    f"авіаційного запиту: {str(e)}")


# Приклад використання
if __name__ == "__main__":
    async def test_agent():
        agent = OpenSkyAviationAgent("aviation_001", "AviationExpert")

        # Тестові запити
        test_messages = [
            "Покажи поточні літаки в зоні України (координати 49.0,29.0,51.0,31.0)",
            "Розкажи про рейси літака з кодом 4b1807 за останні 3 дні",
            "Які рейси були в аеропорту EDDF за вчора?",
            "Покажи трек польоту літака 4b1807 за останню годину"
        ]

        for msg in test_messages:
            print(f"\n--- Тест: {msg} ---")
            response = await agent.process_message(msg)
            print(response)
            print("\n" + "=" * 80)

    # Запускаємо тест
    # asyncio.run(test_agent())
