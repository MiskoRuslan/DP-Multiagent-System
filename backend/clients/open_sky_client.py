import os
from dataclasses import dataclass

import requests
from typing import Optional, List, Union, Dict, Any
from datetime import datetime, timezone
import time
from pydantic import BaseModel

AIRPORT_DB_TOKEN = os.getenv("AIRPORT_DB_TOKEN")

class StateVector(BaseModel):
    """Aircraft state vector data"""
    icao24: str
    callsign: Optional[str]
    origin_country: str
    time_position: Optional[int]
    last_contact: int
    longitude: Optional[float]
    latitude: Optional[float]
    baro_altitude: Optional[float]
    on_ground: bool
    velocity: Optional[float]
    true_track: Optional[float]
    vertical_rate: Optional[float]
    sensors: Optional[List[int]]
    geo_altitude: Optional[float]
    squawk: Optional[str]
    spi: bool
    position_source: int


@dataclass
class AircraftState:
    """Структура даних для поточного стану літака"""
    icao24: str  # Hex код літака
    callsign: Optional[str]  # Позивний
    origin_country: str  # Країна реєстрації
    time_position: Optional[int]  # Unix timestamp останнього оновлення позиції
    last_contact: int  # Unix timestamp останнього контакту
    longitude: Optional[float]  # Довгота (градуси)
    latitude: Optional[float]  # Широта (градуси)
    baro_altitude: Optional[float]  # Барометрична висота (метри)
    on_ground: bool  # Чи на землі
    velocity: Optional[float]  # Швидкість (м/с)
    true_track: Optional[float]  # Справжній курс (градуси)
    vertical_rate: Optional[float]  # Вертикальна швидкість (м/с)
    sensors: Optional[list]  # Список сенсорів
    geo_altitude: Optional[float]  # Геометрична висота (метри)
    squawk: Optional[str]  # Squawk код
    spi: bool  # Спеціальна ідентифікація
    position_source: Optional[int]  # Джерело позиції (0=ADS-B, 1=ASTERIX, 2=MLAT)
    category: Optional[int]  # Категорія літака

    # Додаткові обчислювані поля
    status: str = "Unknown"  # Статус активності
    speed_kmh: Optional[float] = None  # Швидкість в км/год
    altitude_ft: Optional[float] = None  # Висота в футах
    age_seconds: Optional[int] = None  # Вік даних в секундах


class Flight(BaseModel):
    """Flight information"""
    icao24: str
    first_seen: int
    est_departure_airport: Optional[str]
    last_seen: int
    est_arrival_airport: Optional[str]
    callsign: Optional[str]
    est_departure_airport_horiz_distance: Optional[int]
    est_departure_airport_vert_distance: Optional[int]
    est_arrival_airport_horiz_distance: Optional[int]
    est_arrival_airport_vert_distance: Optional[int]
    departure_airport_candidates_count: int
    arrival_airport_candidates_count: int


class TrackPoint(BaseModel):
    """Single point of aircraft track"""
    time: int
    latitude: Optional[float]
    longitude: Optional[float]
    baro_altitude: Optional[float]
    true_track: Optional[float]
    on_ground: bool


class OpenSkyClient:
    """Client for OpenSky Network REST API"""

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.base_url = "https://opensky-network.org/api"
        self.session = requests.Session()
        if username and password:
            self.session.auth = (username, password)

    def get_current_aircraft_state(self, icao24: str) -> Optional[AircraftState]:
        """
        Отримує поточний стан конкретного літака за його hex кодом

        Args:
            icao24 (str): Hex код літака

        Returns:
            Optional[AircraftState]: Поточний стан літака або None якщо не знайдено
        """
        try:
            # Параметри запиту для конкретного літака
            params = {
                'icao24': icao24.lower()  # OpenSky вимагає lowercase
            }

            response = self.session.get(f"{self.base_url}/states/all", params=params)
            response.raise_for_status()

            data = response.json()

            # Перевіряємо чи є дані про літаки
            if not data.get('states') or len(data['states']) == 0:
                return None

            # Беремо перший (та єдиний) результат
            state_data = data['states'][0]

            # Розпаковуємо дані згідно з документацією OpenSky API
            aircraft_state = AircraftState(
                icao24=state_data[0],  # icao24
                callsign=state_data[1].strip() if state_data[1] else None,  # callsign
                origin_country=state_data[2],  # origin_country
                time_position=state_data[3],  # time_position
                last_contact=state_data[4],  # last_contact
                longitude=state_data[5],  # longitude
                latitude=state_data[6],  # latitude
                baro_altitude=state_data[7],  # baro_altitude
                on_ground=state_data[8],  # on_ground
                velocity=state_data[9],  # velocity
                true_track=state_data[10],  # true_track
                vertical_rate=state_data[11],  # vertical_rate
                sensors=state_data[12],  # sensors
                geo_altitude=state_data[13],  # geo_altitude
                squawk=state_data[14],  # squawk
                spi=state_data[15],  # spi
                position_source=state_data[16],  # position_source
                category=state_data[17] if len(state_data) > 17 else None  # category
            )

            # Обчислюємо додаткові поля
            current_time = int(time.time())

            # Визначаємо статус активності
            if aircraft_state.last_contact:
                age = current_time - aircraft_state.last_contact
                aircraft_state.age_seconds = age

                if age < 60:
                    aircraft_state.status = "Active (Live)"
                elif age < 300:
                    aircraft_state.status = "Recent (< 5 min)"
                elif age < 1800:
                    aircraft_state.status = "Delayed (< 30 min)"
                else:
                    aircraft_state.status = "Inactive (> 30 min)"

            # Конвертуємо швидкість в км/год
            if aircraft_state.velocity:
                aircraft_state.speed_kmh = aircraft_state.velocity * 3.6

            # Конвертуємо висоту в фути
            if aircraft_state.baro_altitude:
                aircraft_state.altitude_ft = aircraft_state.baro_altitude * 3.28084

            return aircraft_state

        except Exception as e:
            return None

    def get_detailed_aircraft_info(self, icao24: str) -> Dict[str, Any]:
        """
        Отримує повну детальну інформацію про літак: поточний стан + історію польотів

        Args:
            icao24 (str): Hex код літака

        Returns:
            Dict[str, Any]: Повна інформація про літак
        """
        result = {
            'hex_code': icao24.upper(),
            'current_state': None,
            'recent_flights': None,
            'aircraft_image': None,
            'summary': {}
        }

        # 1. Поточний стан
        current_state = self.get_current_aircraft_state(icao24)
        result['current_state'] = current_state

        # 2. Історія польотів за останні 7 dnй
        try:
            recent_flights = self.get_flights_by_aircraft(
                icao24=icao24,
                begin=int(time.time()) - 86400 * 7,
                end=int(time.time())
            )
            result['recent_flights'] = recent_flights
        except Exception as e:
            result['recent_flights'] = []

        # 3. Зображення літака
        try:
            aircraft_image = self.get_image_of_aircraft(icao24)
            result['aircraft_image'] = aircraft_image
        except Exception as e:
            result['aircraft_image'] = None

        # 4. Формування підсумку
        summary = {}

        if current_state:
            summary.update({
                'is_active': current_state.status in ["Active (Live)",
                                                      "Recent (< 5 min)"],
                'location': {
                    'latitude': current_state.latitude,
                    'longitude': current_state.longitude,
                    'altitude_m': current_state.baro_altitude,
                    'altitude_ft': current_state.altitude_ft
                } if current_state.latitude and current_state.longitude else None,
                'flight_info': {
                    'callsign': current_state.callsign,
                    'country': current_state.origin_country,
                    'speed_kmh': current_state.speed_kmh,
                    'heading': current_state.true_track,
                    'on_ground': current_state.on_ground
                },
                'status': current_state.status,
                'last_seen_ago_seconds': current_state.age_seconds
            })

        if result['recent_flights']:
            summary['total_flights_week'] = len(result['recent_flights'])
            summary['most_recent_flight'] = {
                'callsign': result['recent_flights'][0].callsign,
                'departure': result['recent_flights'][0].est_departure_airport,
                'arrival': result['recent_flights'][0].est_arrival_airport
            }

        result['summary'] = summary

        return result

    def get_states(self,
                   time: Optional[int] = None,
                   icao24: Optional[Union[str, List[str]]] = None,
                   bbox: Optional[tuple] = None) -> List[StateVector]:
        """Returns current aircraft state vectors"""
        print("I'm INSIDE get_states() function")
        print(f"Original bbox: {bbox}")

        params = {}

        if time:
            params['time'] = time

        if icao24:
            if isinstance(icao24, str):
                params['icao24'] = icao24
            else:
                params['icao24'] = ','.join(icao24)

        if bbox:
            # Припускаємо що bbox це (lat_min, lat_max, lon_min, lon_max)
            # або (south, north, west, east)
            lat_min, lat_max, lon_min, lon_max = bbox

            # Переконуємось що координати правильні
            params['lamin'] = min(lat_min, lat_max)  # мінімальна широта
            params['lamax'] = max(lat_min, lat_max)  # максимальна широта
            params['lomin'] = min(lon_min, lon_max)  # мінімальна довгота
            params['lomax'] = max(lon_min, lon_max)  # максимальна довгота

            print(f"API params: lamin={params['lamin']}, lamax={params['lamax']}, "
                  f"lomin={params['lomin']}, lomax={params['lomax']}")

        print(f"Request params: {params}")

        response = self.session.get(f"{self.base_url}/states/all", params=params)
        response.raise_for_status()

        data = response.json()
        print(f"API Response: {data}")

        if not data.get('states'):
            print("No states returned from API")
            return []

        states = []
        for state in data['states']:
            states.append(StateVector(
                icao24=state[0],
                callsign=state[1].strip() if state[1] else None,
                origin_country=state[2],
                time_position=state[3],
                last_contact=state[4],
                longitude=state[5],
                latitude=state[6],
                baro_altitude=state[7],
                on_ground=state[8],
                velocity=state[9],
                true_track=state[10],
                vertical_rate=state[11],
                sensors=state[12],
                geo_altitude=state[13],
                squawk=state[14],
                spi=state[15],
                position_source=state[16]
            ))
        print("Result Data = ==================================================")
        print(data)
        return states

    def get_image_of_aircraft(self, hex_code: str):
        url = f"https://api.planespotters.net/pub/photos/hex/{hex_code}"
        response = self.session.get(url)
        return response.json()

    def get_airport_info(self, code: str):
        url = f"https://airportdb.io/api/v1/airport/{code}?apiToken={AIRPORT_DB_TOKEN}"
        response = self.session.get(url)
        return response.json()

    def get_flights_by_aircraft(
            self,
            icao24: str,
            begin: int,
            end: int
    ) -> List[Flight]:
        """Returns flights for a particular aircraft within time interval"""
        params = {
            'icao24': icao24,
            'begin': begin,
            'end': end
        }

        response = self.session.get(f"{self.base_url}/flights/aircraft", params=params)
        response.raise_for_status()

        flights = []
        for flight_data in response.json():
            flights.append(Flight(
                icao24=flight_data['icao24'],
                first_seen=flight_data['firstSeen'],
                est_departure_airport=flight_data.get('estDepartureAirport'),
                last_seen=flight_data['lastSeen'],
                est_arrival_airport=flight_data.get('estArrivalAirport'),
                callsign=flight_data.get('callsign', '').strip() if flight_data.get(
                    'callsign') else None,
                est_departure_airport_horiz_distance=flight_data.get(
                    'estDepartureAirportHorizDistance'),
                est_departure_airport_vert_distance=flight_data.get(
                    'estDepartureAirportVertDistance'),
                est_arrival_airport_horiz_distance=flight_data.get(
                    'estArrivalAirportHorizDistance'),
                est_arrival_airport_vert_distance=flight_data.get(
                    'estArrivalAirportVertDistance'),
                departure_airport_candidates_count=flight_data[
                    'departureAirportCandidatesCount'],
                arrival_airport_candidates_count=flight_data[
                    'arrivalAirportCandidatesCount']
            ))

        return flights

    def get_flights_by_interval(self, begin: int, end: int) -> List[Flight]:
        """Returns flights for a certain time interval (requires authentication)"""
        params = {
            'begin': begin,
            'end': end
        }

        response = self.session.get(f"{self.base_url}/flights/all", params=params)
        response.raise_for_status()

        return [Flight(**flight) for flight in response.json()]

    def get_arrivals_by_airport(self, airport: str, begin: int, end: int) -> List[
        Flight]:
        """Returns flights arriving at given airport within time interval"""
        params = {
            'airport': airport,
            'begin': begin,
            'end': end
        }

        response = self.session.get(f"{self.base_url}/flights/arrival", params=params)
        response.raise_for_status()

        flights = []
        for flight_data in response.json():
            flights.append(Flight(
                icao24=flight_data['icao24'],
                first_seen=flight_data['firstSeen'],
                est_departure_airport=flight_data.get('estDepartureAirport'),
                last_seen=flight_data['lastSeen'],
                est_arrival_airport=flight_data.get('estArrivalAirport'),
                callsign=flight_data.get('callsign', '').strip() if flight_data.get(
                    'callsign') else None,
                est_departure_airport_horiz_distance=flight_data.get(
                    'estDepartureAirportHorizDistance'),
                est_departure_airport_vert_distance=flight_data.get(
                    'estDepartureAirportVertDistance'),
                est_arrival_airport_horiz_distance=flight_data.get(
                    'estArrivalAirportHorizDistance'),
                est_arrival_airport_vert_distance=flight_data.get(
                    'estArrivalAirportVertDistance'),
                departure_airport_candidates_count=flight_data[
                    'departureAirportCandidatesCount'],
                arrival_airport_candidates_count=flight_data[
                    'arrivalAirportCandidatesCount']
            ))

        return flights

    def get_departures_by_airport(
            self,
            airport: str,
            begin: int,
            end: int
    ) -> List[Flight]:
        """Returns flights departing from given airport within time interval"""
        params = {
            'airport': airport,
            'begin': begin,
            'end': end
        }

        response = self.session.get(f"{self.base_url}/flights/departure", params=params)
        response.raise_for_status()

        flights = []
        for flight_data in response.json():
            flights.append(Flight(
                icao24=flight_data['icao24'],
                first_seen=flight_data['firstSeen'],
                est_departure_airport=flight_data.get('estDepartureAirport'),
                last_seen=flight_data['lastSeen'],
                est_arrival_airport=flight_data.get('estArrivalAirport'),
                callsign=flight_data.get('callsign', '').strip() if flight_data.get(
                    'callsign') else None,
                est_departure_airport_horiz_distance=flight_data.get(
                    'estDepartureAirportHorizDistance'),
                est_departure_airport_vert_distance=flight_data.get(
                    'estDepartureAirportVertDistance'),
                est_arrival_airport_horiz_distance=flight_data.get(
                    'estArrivalAirportHorizDistance'),
                est_arrival_airport_vert_distance=flight_data.get(
                    'estArrivalAirportVertDistance'),
                departure_airport_candidates_count=flight_data[
                    'departureAirportCandidatesCount'],
                arrival_airport_candidates_count=flight_data[
                    'arrivalAirportCandidatesCount']
            ))

        return flights

    def get_track_by_aircraft(self, icao24: str, time: int) -> List[TrackPoint]:
        """Returns flight track for aircraft at given time"""
        params = {
            'icao24': icao24,
            'time': time
        }

        response = self.session.get(f"{self.base_url}/tracks/all", params=params)
        response.raise_for_status()

        data = response.json()
        if not data.get('path'):
            return []

        tracks = []
        for point in data['path']:
            tracks.append(TrackPoint(
                time=point[0],
                latitude=point[1],
                longitude=point[2],
                baro_altitude=point[3],
                true_track=point[4],
                on_ground=point[5]
            ))

        return tracks

    def get_states_raw(
            self,
            lamin: float,
            lomin: float,
            lamax: float,
            lomax: float
    ) -> Dict[str, Any]:
        """Returns raw JSON response from states/all endpoint with bounding box"""
        params = {
            'lamin': lamin,
            'lomin': lomin,
            'lamax': lamax,
            'lomax': lomax
        }

        response = self.session.get(f"{self.base_url}/states/all", params=params)
        response.raise_for_status()

        return response.json()

    @staticmethod
    def timestamp_to_datetime(timestamp: int) -> datetime:
        """Converts Unix timestamp to datetime object"""
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    @staticmethod
    def datetime_to_timestamp(dt: datetime) -> int:
        """Converts datetime object to Unix timestamp"""
        return int(dt.timestamp())

    @staticmethod
    def get_current_timestamp() -> int:
        """Returns current Unix timestamp"""
        return int(time.time())


if __name__ == "__main__":
    # Ініціалізація клієнта (замініть None на ваші облікові дані, якщо є)
    client = OpenSkyClient(username=None, password=None)  # Додайте username і password для автентифікованих методів

    # Параметри для тестів
    icao24 = "4b1807"  # Перевірений код літака, який мав активність (24 рейси)
    airport = "EDDF"   # Франкфурт, великий аеропорт із великою кількістю рейсів
    current_time = client.get_current_timestamp()  # Поточний час (31 травня 2025, 22:17 EEST)
    seven_days_ago = current_time - 7 * 24 * 3600  # 7 днів тому
    bbox = (45.0, 5.0, 55.0, 25.0)  # Розширена зона (Європа), але використовується лише з автентифікацією

    # Тест 1: get_states
    print("Тестування get_states...")
    try:
        # Якщо автентифікація є, використовуємо bbox, інакше без нього
        params = {'time': current_time - 300}  # 5 хвилин тому
        if client.session.auth:
            params.update({'lamin': 45.0, 'lomin': 5.0, 'lamax': 55.0, 'lomax': 25.0})
        states = client.get_states(**params)
        print(f"Отримано {len(states)} векторів стану")
        for state in states[:2]:  # Виводимо перші 2 для стислості
            print(f"ICAO24: {state.icao24}, Позивний: {state.callsign}, Позиція: ({state.latitude}, {state.longitude})")
        if not states:
            print("Попередження: не отримано станів, можливо, потрібна автентифікація або активні літаки відсутні")
    except Exception as e:
        print(f"Помилка в get_states: {e}")

    # Тест 2: get_flights_by_aircraft
    print("\nТестування get_flights_by_aircraft...")
    try:
        flights = client.get_flights_by_aircraft(icao24=icao24, begin=seven_days_ago, end=current_time)
        print(f"Отримано {len(flights)} рейсів для літака {icao24}")
        for flight in flights[:2]:
            print(f"Рейс: {flight.callsign}, З: {flight.est_departure_airport}, До: {flight.est_arrival_airport}")
        if not flights:
            print("Попередження: не отримано рейсів, перевірте icao24 або розширте часовий діапазон")
    except Exception as e:
        print(f"Помилка в get_flights_by_aircraft: {e}")

    # Тест 3: get_flights_by_interval
    print("\nТестування get_flights_by_interval...")
    if client.session.auth:  # Перевірка наявності автентифікації
        try:
            flights = client.get_flights_by_interval(begin=seven_days_ago, end=current_time)
            print(f"Отримано {len(flights)} рейсів у часовому діапазоні")
            for flight in flights[:2]:
                print(f"Рейс: {flight.callsign}, ICAO24: {flight.icao24}")
            if not flights:
                print("Попередження: не отримано рейсів, перевірте часовий діапазон")
        except Exception as e:
            print(f"Помилка в get_flights_by_interval: {e}")
    else:
        print("Тест пропущено: для get_flights_by_interval потрібна автентифікація (додайте username і password)")

    # Тест 4: get_arrivals_by_airport
    print("\nТестування get_arrivals_by_airport...")
    try:
        arrivals = client.get_arrivals_by_airport(airport=airport, begin=seven_days_ago, end=current_time)
        print(f"Отримано {len(arrivals)} прильотів до {airport}")
        for flight in arrivals[:2]:
            print(f"Приліт: {flight.callsign}, З: {flight.est_departure_airport}")
        if not arrivals:
            print("Попередження: не отримано прильотів, перевірте код аеропорту або часовий діапазон")
    except Exception as e:
        print(f"Помилка в get_arrivals_by_airport: {e}")

    # Тест 5: get_departures_by_airport
    print("\nТестування get_departures_by_airport...")
    try:
        departures = client.get_departures_by_airport(airport=airport, begin=seven_days_ago, end=current_time)
        print(f"Отримано {len(departures)} вильотів з {airport}")
        for flight in departures[:2]:
            print(f"Виліт: {flight.callsign}, До: {flight.est_arrival_airport}")
        if not departures:
            print("Попередження: не отримано вильотів, перевірте код аеропорту або часовий діапазон")
    except Exception as e:
        print(f"Помилка в get_departures_by_airport: {e}")

    # Тест 6: get_track_by_aircraft
    print("\nТестування get_track_by_aircraft...")
    try:
        # Використаємо час із рейсу, отриманого в get_flights_by_aircraft
        flights = client.get_flights_by_aircraft(icao24=icao24, begin=seven_days_ago, end=current_time)
        track_time = flights[0].last_seen if flights else current_time - 3600  # Останній час рейсу або 1 годину тому
        tracks = client.get_track_by_aircraft(icao24=icao24, time=track_time)
        print(f"Отримано {len(tracks)} точок треку для літака {icao24}")
        for track in tracks[:2]:
            print(f"Точка треку: Час: {track.time}, Позиція: ({track.latitude}, {track.longitude})")
        if not tracks:
            print("Попередження: не отримано точок треку, перевірте icao24 або час")
    except Exception as e:
        print(f"Помилка в get_track_by_aircraft: {e}")

    # Тест 7: get_states_raw
    print("\nТестування get_states_raw...")
    try:
        # Якщо автентифікація є, використовуємо bbox, інакше без нього
        if client.session.auth:
            raw_data = client.get_states_raw(lamin=45.0, lomin=5.0, lamax=55.0, lomax=25.0)
        else:
            raw_data = client.get_states_raw()  # Без bbox для неавтентифікованих
        print(f"Отримано сирі дані: {len(raw_data.get('states', []))} станів")
        print(f"Зразок ключів: {list(raw_data.keys())[:5]}")
        if not raw_data.get('states'):
            print("Попередження: не отримано станів, можливо, потрібна автентифікація")
    except Exception as e:
        print(f"Помилка в get_states_raw: {e}")

    # Тест 8: timestamp_to_datetime
    print("\nТестування timestamp_to_datetime...")
    try:
        dt = client.timestamp_to_datetime(current_time)
        print(f"Конвертовано timestamp {current_time} у datetime: {dt}")
    except Exception as e:
        print(f"Помилка в timestamp_to_datetime: {e}")

    # Тест 9: datetime_to_timestamp
    print("\nТестування datetime_to_timestamp...")
    try:
        dt = datetime.now(timezone.utc)
        timestamp = client.datetime_to_timestamp(dt)
        print(f"Конвертовано datetime {dt} у timestamp: {timestamp}")
    except Exception as e:
        print(f"Помилка в datetime_to_timestamp: {e}")

    # Тест 10: get_current_timestamp
    print("\nТестування get_current_timestamp...")
    try:
        timestamp = client.get_current_timestamp()
        print(f"Поточний timestamp: {timestamp}")
    except Exception as e:
        print(f"Помилка в get_current_timestamp: {e}")