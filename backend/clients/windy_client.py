import os
import requests
import time
import math
from typing import Dict, Any


def get_current_weather(lat: float, lon: float) -> Dict[str, Any]:
    api_key = os.getenv('WINDY_API_KEY')
    if not api_key:
        raise ValueError('WINDY_API_KEY not found in variables')

    url = 'https://api.windy.com/api/point-forecast/v2'

    payload = {
        'lat': float(lat),
        'lon': float(lon),
        'model': 'gfs',
        'parameters': [
            'wind', 'windGust', 'temp', 'dewpoint',
            'rh', 'pressure', 'precip'
        ],
        'levels': ['surface'],
        'key': api_key
    }

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Python Weather Client'
    }
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.ok:
                break

            if response.status_code == 503:
                if attempt < max_retries - 1:
                    print(
                        f"The server is not available, attempted "
                        f"{attempt + 1}/{max_retries}, waiting..."
                    )
                    time.sleep(2 ** attempt)
                    continue

            raise requests.HTTPError(f'HTTP {response.status_code}: {response.text}')

        except requests.ConnectionError as e:
            if attempt < max_retries - 1:
                print(
                    f"Connection error, attempt "
                    f"{attempt + 1}/{max_retries}, waiting..."
                )
                time.sleep(2 ** attempt)
                continue
            raise requests.ConnectionError(
                f"Failed to connect to API after {max_retries} attempts: {e}")

        except requests.Timeout as e:
            if attempt < max_retries - 1:
                print(
                    f"Таймаут запиту, спроба {attempt + 1}/{max_retries}, очікування...")
                time.sleep(2 ** attempt)
                continue
            raise requests.Timeout(f"Таймаут запиту після {max_retries} спроб: {e}")

    data = response.json()
    wind_speed = None
    if 'wind_u-surface' in data and 'wind_v-surface' in data:
        wind_u = data['wind_u-surface'][0]
        wind_v = data['wind_v-surface'][0]
        wind_speed = round(math.sqrt(wind_u**2 + wind_v**2), 1)

    current_weather = {
        'temperature': f"{round(data['temp-surface'][0] - 273.15)}°C"
        if data.get('temp-surface') else None,
        'wind_speed': f"{wind_speed} м/с"
        if wind_speed is not None else None,
        'wind_gust': f"{round(data['gust-surface'][0])} м/с"
        if data.get('gust-surface') else None,
        'humidity': f"{round(data['rh-surface'][0])}%"
        if data.get('rh-surface') else None,
        'pressure': f"{round(data['pressure-surface'][0] / 100)} гПа"
        if data.get('pressure-surface') else None,
        'precipitation': f"{data['past3hprecip-surface'][0]:.1f} мм"
        if data.get('past3hprecip-surface') else None,
        'dewpoint': f"{round(data['dewpoint-surface'][0] - 273.15)}°C"
        if data.get('dewpoint-surface') else None
    }

    return current_weather
