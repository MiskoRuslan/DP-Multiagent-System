from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_openai import ChatOpenAI
import asyncio
import time
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple
import json

from backend.clients.open_sky_client import OpenSkyClient
from backend.clients.windy_client import get_current_weather

# Словник координат країн (bbox: [min_lat, max_lat, min_lon, max_lon])
COUNTRY_COORDINATES = {
    'poland': [49.0, 54.8, 14.1, 24.2],
    'ukraine': [44.3, 52.4, 22.1, 40.2],
    'germany': [47.3, 55.1, 5.9, 15.0],
    'france': [41.4, 51.1, -5.1, 9.6],
    'spain': [27.6, 43.8, -18.2, 4.3],
    'italy': [35.5, 47.1, 6.6, 18.5],
    'united kingdom': [49.9, 60.8, -8.6, 1.8],
    'netherlands': [50.8, 53.6, 3.4, 7.2],
    'belgium': [49.5, 51.5, 2.5, 6.4],
    'czech republic': [48.6, 51.1, 12.1, 18.9],
    'austria': [46.4, 49.0, 9.5, 17.2],
    'switzerland': [45.8, 47.8, 5.9, 10.5],
    'slovakia': [47.7, 49.6, 16.8, 22.6],
    'hungary': [45.7, 48.6, 16.1, 22.9],
    'romania': [43.6, 48.3, 20.3, 29.7],
    'bulgaria': [41.2, 44.2, 22.4, 28.6],
    'greece': [34.8, 41.7, 19.4, 29.6],
    'turkey': [35.8, 42.1, 25.7, 44.8],
    'norway': [57.9, 71.2, 4.6, 31.3],
    'sweden': [55.3, 69.1, 11.1, 24.2],
    'finland': [59.8, 70.1, 20.5, 31.6],
    'denmark': [54.6, 57.8, 8.1, 15.2],
    'portugal': [32.4, 42.2, -31.3, -6.2],
    'ireland': [51.4, 55.4, -10.5, -6.0],
    'croatia': [42.4, 46.5, 13.5, 19.4],
    'serbia': [42.2, 46.2, 18.8, 23.0],
    'bosnia and herzegovina': [42.6, 45.3, 15.7, 19.6],
    'slovenia': [45.4, 46.9, 13.4, 16.6],
    'montenegro': [41.9, 43.5, 18.4, 20.4],
    'north macedonia': [40.9, 42.4, 20.5, 23.0],
    'albania': [39.6, 42.7, 19.3, 21.1],
    'latvia': [55.7, 58.1, 21.0, 28.2],
    'lithuania': [53.9, 56.4, 21.0, 26.8],
    'estonia': [57.5, 59.7, 21.8, 28.2],
    'moldova': [45.5, 48.5, 26.6, 30.1],
    'belarus': [51.3, 56.2, 23.2, 32.8],
    'usa': [24.4, 71.4, -179.1, -66.9],
    'canada': [41.7, 83.1, -141.0, -52.6],
    'japan': [24.0, 45.6, 122.9, 153.9],
    'south korea': [33.1, 38.6, 124.6, 131.9],
    'china': [18.2, 53.6, 73.5, 134.8],
    'australia': [-43.6, -10.7, 113.3, 153.6],
}


def get_country_bounds(country_name: str) -> Optional[
    Tuple[float, float, float, float]]:
    """Отримати координати країни за назвою"""
    country_key = country_name.lower().strip()

    # Спробуємо знайти точну відповідність
    if country_key in COUNTRY_COORDINATES:
        bounds = COUNTRY_COORDINATES[country_key]
        return bounds[0], bounds[1], bounds[2], bounds[
            3]  # min_lat, max_lat, min_lon, max_lon

    # Спробуємо знайти часткову відповідність
    for key in COUNTRY_COORDINATES:
        if country_key in key or key in country_key:
            bounds = COUNTRY_COORDINATES[key]
            return bounds[0], bounds[1], bounds[2], bounds[3]

    return None


def analyze_aircraft_distribution(aircraft_states: List) -> Dict:
    """Аналіз розподілу літаків"""
    analysis = {
        'total_aircraft': len(aircraft_states),
        'active_flights': 0,
        'ground_aircraft': 0,
        'countries': Counter(),
        'altitudes': {'low': 0, 'medium': 0, 'high': 0, 'unknown': 0},
        'speeds': {'slow': 0, 'medium': 0, 'fast': 0, 'unknown': 0},
        'aircraft_types': Counter(),
        'major_airlines': Counter(),
    }

    for state in aircraft_states:
        # Статус польоту
        if state.on_ground:
            analysis['ground_aircraft'] += 1
        else:
            analysis['active_flights'] += 1

        # Країни
        if state.origin_country:
            analysis['countries'][state.origin_country] += 1

        # Висота
        if state.baro_altitude:
            if state.baro_altitude < 3000:  # < 3km
                analysis['altitudes']['low'] += 1
            elif state.baro_altitude < 10000:  # 3-10km
                analysis['altitudes']['medium'] += 1
            else:  # > 10km
                analysis['altitudes']['high'] += 1
        else:
            analysis['altitudes']['unknown'] += 1

        # Швидкість
        if state.velocity:
            speed_kmh = state.velocity * 3.6
            if speed_kmh < 200:
                analysis['speeds']['slow'] += 1
            elif speed_kmh < 800:
                analysis['speeds']['medium'] += 1
            else:
                analysis['speeds']['fast'] += 1
        else:
            analysis['speeds']['unknown'] += 1

        # Авіакомпанії (з позивного)
        if state.callsign and len(state.callsign.strip()) >= 3:
            airline_code = state.callsign.strip()[:3]
            analysis['major_airlines'][airline_code] += 1

    return analysis


def get_traffic_density_analysis(aircraft_states: List, bounds: Tuple) -> Dict:
    """Аналіз щільності трафіку"""
    min_lat, max_lat, min_lon, max_lon = bounds

    # Розділяємо простір на сітку 10x10
    grid_size = 10
    lat_step = (max_lat - min_lat) / grid_size
    lon_step = (max_lon - min_lon) / grid_size

    grid_density = defaultdict(int)

    for state in aircraft_states:
        if state.latitude and state.longitude:
            # Знаходимо позицію в сітці
            lat_idx = min(int((state.latitude - min_lat) / lat_step), grid_size - 1)
            lon_idx = min(int((state.longitude - min_lon) / lon_step), grid_size - 1)
            grid_density[(lat_idx, lon_idx)] += 1

    # Знаходимо найщільніші зони
    sorted_density = sorted(grid_density.items(), key=lambda x: x[1], reverse=True)

    return {
        'total_zones': len(grid_density),
        'max_density': sorted_density[0][1] if sorted_density else 0,
        'top_zones': sorted_density[:5],
        'average_density': sum(grid_density.values()) / len(
            grid_density) if grid_density else 0
    }


@tool("analyze_country_airspace")
def analyze_country_airspace(country_name: str) -> str:
    """
    Проводить детальний аналіз ситуації в авіапросторі вказаної країни

    Args:
        country_name (str): Назва країни для аналізу (наприклад: "Poland", "Ukraine", "Germany")
    Returns:
        str: Детальний HTML-аналіз ситуації в авіапросторі
    """

    result_parts = []

    try:
        # Ініціалізація клієнта
        open_sky_client = OpenSkyClient()
        result_parts.append(f"🌍 Аналіз авіапростору країни: {country_name.upper()}")

        # Отримання координат країни
        bounds = get_country_bounds(country_name)
        if not bounds:
            return f"❌ Не вдалося знайти координати для країни: {country_name}. Доступні країни: {', '.join(list(COUNTRY_COORDINATES.keys())[:10])}..."

        min_lat, max_lat, min_lon, max_lon = bounds
        result_parts.append(f"📍 Координати області аналізу:")
        result_parts.append(f"  Широта: {min_lat}° - {max_lat}°")
        result_parts.append(f"  Довгота: {min_lon}° - {max_lon}°")

    except Exception as e:
        return f"❌ ПОМИЛКА при ініціалізації: {e}"

    # Отримання поточних станів літаків в регіоні
    try:
        current_time = int(time.time())

        # Використовуємо метод get_states з bbox
        bbox = (min_lat, max_lat, min_lon, max_lon)
        aircraft_states = open_sky_client.get_states(bbox=bbox)

        if not aircraft_states:
            result_parts.append("\n⚠️ Не знайдено активних літаків у вказаному регіоні")
            aircraft_states = []
        else:
            result_parts.append(f"\n✈️ ЗАГАЛЬНА СТАТИСТИКА:")
            result_parts.append(f"Всього літаків у регіоні: {len(aircraft_states)}")

    except Exception as e:
        result_parts.append(f"\n❌ Помилка отримання станів літаків: {e}")
        aircraft_states = []

    # Детальний аналіз розподілу літаків
    if aircraft_states:
        try:
            distribution = analyze_aircraft_distribution(aircraft_states)

            result_parts.append(f"\n📊 РОЗПОДІЛ ЛІТАКІВ:")
            result_parts.append(f"  Активні польоти: {distribution['active_flights']}")
            result_parts.append(f"  На землі: {distribution['ground_aircraft']}")

            # Топ-5 країн за кількістю літаків
            result_parts.append(f"\n🌐 ТОП-5 КРАЇН ЗА КІЛЬКІСТЮ ЛІТАКІВ:")
            for country, count in distribution['countries'].most_common(5):
                result_parts.append(f"  {country}: {count} літаків")

            # Розподіл за висотою
            result_parts.append(f"\n📏 РОЗПОДІЛ ЗА ВИСОТОЮ:")
            result_parts.append(f"  Низька (<3км): {distribution['altitudes']['low']}")
            result_parts.append(
                f"  Середня (3-10км): {distribution['altitudes']['medium']}")
            result_parts.append(
                f"  Висока (>10км): {distribution['altitudes']['high']}")
            result_parts.append(f"  Невідома: {distribution['altitudes']['unknown']}")

            # Розподіл за швидкістю
            result_parts.append(f"\n🚀 РОЗПОДІЛ ЗА ШВИДКІСТЮ:")
            result_parts.append(
                f"  Повільні (<200км/г): {distribution['speeds']['slow']}")
            result_parts.append(
                f"  Середні (200-800км/г): {distribution['speeds']['medium']}")
            result_parts.append(
                f"  Швидкі (>800км/г): {distribution['speeds']['fast']}")
            result_parts.append(f"  Невідома: {distribution['speeds']['unknown']}")

            # Топ авіакомпанії
            if distribution['major_airlines']:
                result_parts.append(f"\n🏢 ТОП-5 АВІАКОМПАНІЙ ЗА ПОЗИВНИМИ:")
                for airline, count in distribution['major_airlines'].most_common(5):
                    result_parts.append(f"  {airline}: {count} літаків")

        except Exception as e:
            result_parts.append(f"\n❌ Помилка аналізу розподілу: {e}")

    # Аналіз щільності трафіку
    if aircraft_states:
        try:
            density_analysis = get_traffic_density_analysis(aircraft_states, bounds)

            result_parts.append(f"\n🗺️ АНАЛІЗ ЩІЛЬНОСТІ ТРАФІКУ:")
            result_parts.append(
                f"  Максимальна щільність в зоні: {density_analysis['max_density']} літаків")
            result_parts.append(
                f"  Середня щільність: {density_analysis['average_density']:.1f} літаків на зону")
            result_parts.append(f"  Активних зон: {density_analysis['total_zones']}")

        except Exception as e:
            result_parts.append(f"\n❌ Помилка аналізу щільності: {e}")

    # Аналіз найактивніших літаків
    if aircraft_states:
        try:
            result_parts.append(f"\n🔍 ДЕТАЛІ НАЙАКТИВНІШИХ ЛІТАКІВ:")

            # Сортуємо за швидкістю та висотою
            active_aircraft = [state for state in aircraft_states if
                               not state.on_ground and state.velocity]
            active_aircraft.sort(key=lambda x: x.velocity or 0, reverse=True)

            for i, state in enumerate(active_aircraft[:5]):  # Топ-5
                result_parts.append(f"  Літак {i + 1}:")
                result_parts.append(f"    ICAO24: {state.icao24}")
                result_parts.append(f"    Позивний: {state.callsign or 'Невідомий'}")
                result_parts.append(f"    Країна: {state.origin_country}")
                if state.velocity:
                    result_parts.append(
                        f"    Швидкість: {state.velocity * 3.6:.0f} км/год")
                if state.baro_altitude:
                    result_parts.append(f"    Висота: {state.baro_altitude:.0f} м")
                if state.latitude and state.longitude:
                    result_parts.append(
                        f"    Координати: {state.latitude:.4f}, {state.longitude:.4f}")

        except Exception as e:
            result_parts.append(f"\n❌ Помилка аналізу активних літаків: {e}")

    # Погодні умови в різних частинах країни
    try:
        result_parts.append(f"\n🌤️ ПОГОДНІ УМОВИ В РЕГІОНІ:")

        # Беремо 4 точки: центр та кути
        weather_points = [
            ("Центр", (min_lat + max_lat) / 2, (min_lon + max_lon) / 2),
            ("Півн.-Зах.", max_lat - (max_lat - min_lat) * 0.2,
             min_lon + (max_lon - min_lon) * 0.2),
            ("Півд.-Сх.", min_lat + (max_lat - min_lat) * 0.2,
             max_lon - (max_lon - min_lon) * 0.2),
        ]

        for location, lat, lon in weather_points:
            try:
                weather = get_current_weather(lat=lat, lon=lon)
                result_parts.append(f"  {location} ({lat:.2f}, {lon:.2f}):")
                for key, value in weather.items():
                    if value and key in ['temperature', 'wind_speed', 'wind_direction',
                                         'visibility']:
                        result_parts.append(
                            f"    {key.replace('_', ' ').title()}: {value}")
            except:
                result_parts.append(f"  {location}: Погода недоступна")

    except Exception as e:
        result_parts.append(f"\n❌ Помилка отримання погоди: {e}")

    # Аналіз трендів та рекомендації
    if aircraft_states:
        result_parts.append(f"\n📈 АНАЛІЗ ТА РЕКОМЕНДАЦІЇ:")

        active_ratio = (distribution['active_flights'] / len(
            aircraft_states)) * 100 if aircraft_states else 0
        high_altitude_ratio = (distribution['altitudes']['high'] / len(
            aircraft_states)) * 100 if aircraft_states else 0

        if active_ratio > 80:
            result_parts.append("  🟢 Високий рівень активності повітряного руху")
        elif active_ratio > 50:
            result_parts.append("  🟡 Середній рівень активності повітряного руху")
        else:
            result_parts.append("  🔴 Низький рівень активності повітряного руху")

        if high_altitude_ratio > 60:
            result_parts.append("  ✈️ Переважають висотні польоти (комерційна авіація)")
        else:
            result_parts.append("  🚁 Змішаний трафік різних висот")

        # Рекомендації для авіації
        result_parts.append("  💡 Рекомендації:")
        if density_analysis.get('max_density', 0) > 10:
            result_parts.append("    • Підвищена увага в зонах високої щільності")
        if distribution['altitudes']['unknown'] > len(aircraft_states) * 0.3:
            result_parts.append("    • Рекомендується покращення моніторингу висот")

    result_parts.append(f"\n✅ Аналіз авіапростору {country_name} завершено")
    result_text = '\n'.join(result_parts)

    # Обробка через LLM для створення HTML
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

        analysis_prompt = f"""Ось повний аналіз авіапростору країни:
                        {result_text}

                        Створи сучасний, інтерактивний HTML-код для відображення цього аналізу.
                        Використай:
                        - Сучасний дизайн з картками та іконками
                        - Кольорове кодування для різних типів інформації
                        - Графіки та діаграми (використай Chart.js або подібні)
                        - Responsive дизайн
                        - Анімації та hover-ефекти
                        - Темну або світлу тему на вибір

                        ОБОВ'ЯЗКОВО! ПОВЕРТАЙ ВИКЛЮЧНО HTML КОД, БЕЗ ФОРМАТУВАННЯ ТА
                        ТЕГІВ, У ЧИСТОМУ ВИГЛЯДІ, НЕ ЗАКРИВАЙ ЙОГО У ```html 
                        ЧИ ЩОСЬ ПОДІБНЕ. ВИКЛЮЧНО ЧИСТИЙ КОД!

                        Додай підсумковий висновок про стан авіапростору та можливі ризики чи особливості.
                        """

        response = llm.invoke(analysis_prompt)
        return response.content

    except Exception as e:
        result_parts.append(f"\n❌ Помилка обробки LLM: {e}")
        return '\n'.join(result_parts)


@tool("analysis_info_about_aircraft")
def analysis_info_about_aircraft(hex_code: str) -> str:
    """
    Prepares a detailed analysis of the aircraft based on its hex code

    Args:
        hex_code (str): Hex code of the aircraft.
    Returns:
        str: Detailed analysis of all available information about the aircraft
    """

    result_parts = []

    try:
        # Ініціалізація OpenSky клієнта
        open_sky_client = OpenSkyClient()
        result_parts.append(f"🔍 Аналіз літака з HEX кодом: {hex_code.upper()}")

    except Exception as e:
        return f"❌ ПОМИЛКА при ініціалізації OpenSky клієнта: {e}"

    # Отримання інформації про польоти літака за останні 7 днів
    aircraft_info = None
    try:
        begin_time = int(time.time()) - 86400 * 7
        end_time = int(time.time())
        aircraft_info = open_sky_client.get_flights_by_aircraft(
            icao24=hex_code,
            begin=begin_time,
            end=end_time,
        )

        if aircraft_info:
            result_parts.append(f"\n✈️ ІНФОРМАЦІЯ ПРО ПОЛЬОТИ (останні 7 днів):")
            result_parts.append(f"Загальна кількість польотів: {len(aircraft_info)}")

            for i, flight in enumerate(aircraft_info[:3]):  # Показуємо перші 3 польоти
                result_parts.append(f"  Рейс {i + 1}:")
                result_parts.append(f"    Позивний: {flight.callsign or 'Невідомий'}")
                result_parts.append(
                    f"    Відправлення: {flight.est_departure_airport or 'Невідомий'}")
                result_parts.append(
                    f"    Прибуття: {flight.est_arrival_airport or 'Невідомий'}")
                result_parts.append(
                    f"    Початок: {time.strftime('%Y-%m-%d %H:%M', time.gmtime(flight.first_seen))}")
                result_parts.append(
                    f"    Завершення: {time.strftime('%Y-%m-%d %H:%M', time.gmtime(flight.last_seen))}")
        else:
            result_parts.append("\n⚠️ Польоти за останні 7 днів не знайдені")

    except Exception as e:
        print(f"❌ ПОМИЛКА при отриманні інформації про польоти: {e}")
        result_parts.append(f"\n❌ Помилка отримання польотів: {e}")

    # Отримання зображення літака
    image_url = None
    try:
        aircraft_image_dict = open_sky_client.get_image_of_aircraft(hex_code)

        if aircraft_image_dict and aircraft_image_dict.get("photos") and len(
                aircraft_image_dict["photos"]) > 0:
            image_url = aircraft_image_dict["photos"][0]["thumbnail"]["src"]
            result_parts.append(f"\n📸 ФОТО ЛІТАКА: {image_url}")
        else:
            result_parts.append("\n📸 Фото літака не знайдено")

    except Exception as e:
        print(f"❌ ПОМИЛКА при отриманні зображення літака: {e}")
        result_parts.append(f"\n❌ Помилка отримання зображення: {e}")

    # Отримання поточного стану літака
    current_state = None
    try:
        current_state = open_sky_client.get_current_aircraft_state(hex_code)

        if current_state:
            result_parts.append(f"\n🛩️ ПОТОЧНИЙ СТАН ЛІТАКА:")
            result_parts.append(f"  Позивний: {current_state.callsign or 'Невідомий'}")
            result_parts.append(f"  Країна реєстрації: {current_state.origin_country}")
            result_parts.append(f"  Статус: {current_state.status}")
            result_parts.append(
                f"  На землі: {'Так' if current_state.on_ground else 'Ні'}")

            if current_state.latitude and current_state.longitude:
                result_parts.append(
                    f"  Координати: {current_state.latitude:.4f}, {current_state.longitude:.4f}")
                result_parts.append(
                    f"  Висота: {current_state.altitude_ft:.0f} футів ({current_state.baro_altitude:.0f} м)" if current_state.altitude_ft else "  Висота: Невідома")
                result_parts.append(
                    f"  Швидкість: {current_state.speed_kmh:.0f} км/год" if current_state.speed_kmh else "  Швидкість: Невідома")
                result_parts.append(
                    f"  Курс: {current_state.true_track:.0f}°" if current_state.true_track else "  Курс: Невідомий")
        else:
            result_parts.append("\n⚠️ Поточний стан літака не знайдений")

    except Exception as e:
        print(f"❌ ПОМИЛКА при отриманні поточного стану: {e}")
        result_parts.append(f"\n❌ Помилка отримання поточного стану: {e}")

    # Аналіз активного польоту
    is_active_flight = current_state and current_state.status in ["Active (Live)",
                                                                  "Recent (< 5 min)"] and not current_state.on_ground

    if is_active_flight and aircraft_info:
        result_parts.append(f"\n🚁 АКТИВНИЙ ПОЛІТ ВИЯВЛЕНО!")

        # Останній рейс
        last_flight = aircraft_info[0] if aircraft_info else None

        if last_flight:
            # Інформація про маршрут
            result_parts.append(f"\n🛫 МАРШРУТ ПОЛЬОТУ:")
            result_parts.append(
                f"  Звідки: {last_flight.est_departure_airport or 'Невідомий'}")
            result_parts.append(
                f"  Куди: {last_flight.est_arrival_airport or 'Невідомий'}")

            # Інформація про аеропорт відправлення
            if last_flight.est_departure_airport:
                try:
                    start_airport = open_sky_client.get_airport_info(
                        last_flight.est_departure_airport)
                    if start_airport:
                        result_parts.append(
                            f"\n🛫 АЕРОПОРТ ВІДПРАВЛЕННЯ ({last_flight.est_departure_airport}):")
                        result_parts.append(
                            f"  Назва: {start_airport.get('name', 'Невідома')}")
                        result_parts.append(
                            f"  Місто: {start_airport.get('municipality', 'Невідоме')}")
                        result_parts.append(
                            f"  Країна: {start_airport.get('iso_country', 'Невідома')}")
                        result_parts.append(
                            f"  Координати: {start_airport.get('latitude_deg', 'N/A')}, {start_airport.get('longitude_deg', 'N/A')}")
                except Exception as e:
                    print(
                        f"❌ ПОМИЛКА при отриманні погоди в місцезнаходженні літака: {e}")
                    result_parts.append(
                        f"\n❌ Помилка отримання погоди в поточному місцезнаходженні")

            # Інформація про аеропорт прибуття
            if last_flight.est_arrival_airport:
                try:
                    end_airport = open_sky_client.get_airport_info(
                        last_flight.est_arrival_airport)
                    if end_airport:
                        result_parts.append(
                            f"\n🛬 АЕРОПОРТ ПРИБУТТЯ ({last_flight.est_arrival_airport}):")
                        result_parts.append(
                            f"  Назва: {end_airport.get('name', 'Невідома')}")
                        result_parts.append(
                            f"  Місто: {end_airport.get('municipality', 'Невідоме')}")
                        result_parts.append(
                            f"  Країна: {end_airport.get('iso_country', 'Невідома')}")
                        result_parts.append(
                            f"  Координати: {end_airport.get('latitude_deg', 'N/A')}, {end_airport.get('longitude_deg', 'N/A')}")

                        # Погода в аеропорті прибуття
                        if end_airport.get('latitude_deg') and end_airport.get(
                                'longitude_deg'):
                            try:
                                airport_weather = get_current_weather(
                                    lat=end_airport['latitude_deg'],
                                    lon=end_airport['longitude_deg']
                                )
                                result_parts.append(
                                    f"\n🌦️ ПОГОДА В АЕРОПОРТІ ПРИБУТТЯ:")
                                for key, value in airport_weather.items():
                                    if value:
                                        result_parts.append(
                                            f"  {key.replace('_', ' ').title()}: {value}")
                            except Exception as e:
                                print(
                                    f"❌ ПОМИЛКА при отриманні погоди в аеропорті прибуття: {e}")
                                result_parts.append(
                                    f"\n❌ Помилка отримання погоди в аеропорті прибуття")

                except Exception as e:
                    print(
                        f"❌ ПОМИЛКА при отриманні інформації про аеропорт прибуття: {e}")
                    result_parts.append(
                        f"\n❌ Помилка отримання інформації про аеропорт прибуття")

    elif current_state and current_state.on_ground:
        result_parts.append(f"\n🛬 Літак знаходиться на землі")
    elif current_state:
        result_parts.append(
            f"\n⏸️ Літак не в активному польоті (статус: {current_state.status})")
    else:
        result_parts.append(f"\n❓ Не вдалося визначити поточний стан літака")

    result_parts.append(f"\n✅ Аналіз завершено")
    result_text = '\n'.join(result_parts)

    # Обробка результату через LLM
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

    analysis_prompt = f"""Ось усі доступні дані по повітряному судну:
                    {result_text}
                    Проведи глибокий аналіз усіх параметрів.
                    Поверни тільки html код для відображення усіх даних та 
                    підсумковим описом як на твою думку ті чи інші показники 
                    можуть повпливати на судно, переліт чи на момент посадки.
                    ОБОВ'ЯЗКОВО! ПОВЕРТАЙ ВИКЛЮЧНО КОД, БЕЗ ФОРМАТУВАННЯ ТА
                    ТЕГІВ, У ЧИСТОМУ ВИГЛЯДІ, НЕ ЗАКРИВАЙ ЙОГО У ```html '''
                    ЧИ ЩОСЬ ПОДІБНЕ. ВИКЛЮЧНО ЧИСТИЙ КОД!
                    """

    # Отримуємо відповідь від LLM
    response = llm.invoke(analysis_prompt)

    return response.content


class AviationAnalysisAgent:
    def __init__(self, agent_id: str, name: str, system_prompt: str = None):
        self.agent_id = agent_id
        self.name = name
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

        # Set up default backstory if none provided
        backstory = system_prompt if system_prompt else """
        You are a versatile aviation analysis assistant designed to help users with 
        comprehensive aircraft and airspace analysis.
        You have access to specialized tools to perform detailed aviation-related tasks.

        When processing requests, you should:
        1. Analyze the user's message to understand their aviation-related intent
        2. Use appropriate tools to fulfill the request
        3. Provide clear, detailed, and accurate aviation analysis
        4. Adapt to the context of the user's aviation query

        Available Tools:
        1) For analyzing a specific aircraft: use "analysis_info_about_aircraft" 
           - Requires hexadecimal aircraft code (e.g., 4891B9)
           - Provides comprehensive aircraft analysis including current state, flight
            history, weather conditions, and photos

        2) For analyzing country airspace: use "analyze_country_airspace"
           - Requires country name (e.g., "Poland", "Ukraine", "Germany")  
           - Provides comprehensive airspace analysis including:
             * Current aircraft distribution and statistics
             * Traffic density analysis
             * Country-specific aviation patterns
             * Weather conditions across the region
             * Active flights analysis
             * Safety recommendations

        Key Features:
        - Real-time aircraft tracking and analysis
        - Comprehensive airspace monitoring
        - Weather integration for aviation safety
        - Historical flight data analysis
        - Interactive HTML visualizations
        - Multi-language support (Ukrainian interface)

        Always be professional, accurate, and provide actionable aviation insights.
        """

        # Create the agent with both tools
        self.agent = Agent(
            role='Aviation Analysis Specialist',
            goal='Provide comprehensive aviation analysis for aircraft and airspace using real-time data and advanced analytical tools',
            backstory=backstory,
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[analysis_info_about_aircraft, analyze_country_airspace]
        )

    async def process_message(self, message: str) -> str:
        """Process user message and return appropriate aviation analysis using CrewAI agents and tools."""
        try:
            task = Task(
                description=f"""
                Analyze the user's aviation-related message and respond appropriately using available specialized tools.

                User Message: "{message}"
                Agent ID: {self.agent_id}

                Instructions:
                - Determine if the user wants aircraft analysis or airspace analysis
                - For aircraft analysis: extract hex code and use analysis_info_about_aircraft tool
                - For airspace/country analysis: extract country name and use analyze_country_airspace tool
                - If the request is ambiguous, ask for clarification
                - Provide comprehensive aviation analysis with safety insights
                - Extract relevant parameters (hex codes, country names) carefully
                - Handle both Ukrainian and English inputs

                Examples of requests:
                - "Analyze aircraft 4891B9" → use analysis_info_about_aircraft
                - "Проаналізуй ситуацію в авіапросторі Польщі" → use analyze_country_airspace
                - "Show me airspace situation in Germany" → use analyze_country_airspace
                - "What's happening with flight ABC123?" → may need hex code clarification

                Provide a complete, professional aviation analysis that directly addresses the user's request.
                """,
                expected_output="A comprehensive aviation analysis using appropriate tools, formatted as HTML for optimal visualization",
                agent=self.agent
            )

            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                process=Process.sequential,
                verbose=True
            )

            # Run the crew asynchronously
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, crew.kickoff)

            return f"```html-render \n{str(result)} \n```"

        except Exception as e:
            print(f"Error processing message with AviationAnalysisAgent: {str(e)}")
            return f"Sorry, I encountered an error while processing your aviation analysis request: {str(e)}"


# Додаткові корисні функції для розширення функціоналу OpenSkyClient
class EnhancedOpenSkyClient(OpenSkyClient):
    """Розширений клієнт з додатковими методами для аналізу авіапростору"""

    def get_country_aircraft_stats(self, country_name: str) -> Dict:
        """Отримати статистику літаків для конкретної країни"""
        print(f"Country name: {country_name} =====================================")
        bounds = get_country_bounds(country_name)
        print(bounds)
        if not bounds:
            return {"error": f"Country {country_name} not found"}

        bbox = (bounds[0], bounds[1], bounds[2], bounds[3])
        aircraft_states = self.get_states(bbox=bbox)

        if not aircraft_states:
            return {"total": 0, "active": 0, "grounded": 0}

        stats = analyze_aircraft_distribution(aircraft_states)
        return {
            "total": stats['total_aircraft'],
            "active": stats['active_flights'],
            "grounded": stats['ground_aircraft'],
            "countries": dict(stats['countries'].most_common(10)),
            "altitudes": stats['altitudes'],
            "speeds": stats['speeds']
        }

    def get_busiest_airports_in_region(self, country_name: str, days_back: int = 7) -> \
    List[Dict]:
        """Знайти найзавантаженіші аеропорти в регіоні"""
        # Цей метод потребує розширеної реалізації з базою даних аеропортів
        # Тут базова структура для майбутнього розширення
        return []

    def get_flight_trends(self, country_name: str, hours_back: int = 24) -> Dict:
        """Аналіз трендів польотів за останні години"""
        # Для реалізації потрібно зберігати історичні дані
        # Тут базова структура
        return {
            "trend": "stable",  # "increasing", "decreasing", "stable"
            "peak_hours": [],
            "average_flights_per_hour": 0
        }
