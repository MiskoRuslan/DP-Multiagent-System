import os
import requests
from datetime import datetime, timedelta


class WeatherClient:
    def __init__(self, api_key=None, base_url="http://api.weatherapi.com/v1"):
        self.api_key = api_key or os.getenv("WEATHER_API_KEY", "df1f1f02e8c14a8d9e4214813231012")
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def _make_request(self, endpoint, params):
        params["key"] = self.api_key
        try:
            response = self.session.get(f"{self.base_url}/{endpoint}", params=params)
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = response.json().get("error", {}).get("message", "Unknown error")
                return {"error": f"API Error: {response.status_code}, {error_msg}"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Connection Error: {e}"}

    def get_current_weather(self, city, lang="en", aqi="no"):
        params = {"q": city, "lang": lang, "aqi": aqi}
        data = self._make_request("current.json", params)
        if "error" not in data:
            return {
                "location": data["location"]["name"],
                "region": data["location"]["region"],
                "country": data["location"]["country"],
                "temp_c": data["current"]["temp_c"],
                "temp_f": data["current"]["temp_f"],
                "condition": data["current"]["condition"]["text"],
                "humidity": data["current"]["humidity"],
                "wind_kph": data["current"]["wind_kph"],
                "feelslike_c": data["current"]["feelslike_c"],
                "aqi": data["current"].get("air_quality", {}) if aqi == "yes" else None
            }
        return data

    def get_forecast(self, city, days=1, lang="en", aqi="no", alerts="no"):
        params = {"q": city, "days": max(1, min(days, 14)), "lang": lang, "aqi": aqi, "alerts": alerts}
        data = self._make_request("forecast.json", params)
        if "error" not in data:
            forecast = []
            for day in data["forecast"]["forecastday"]:
                forecast.append({
                    "date": day["date"],
                    "max_temp_c": day["day"]["maxtemp_c"],
                    "min_temp_c": day["day"]["mintemp_c"],
                    "condition": day["day"]["condition"]["text"],
                    "precip_mm": day["day"]["totalprecip_mm"],
                    "sunrise": day["astro"]["sunrise"],
                    "sunset": day["astro"]["sunset"]
                })
            return {
                "location": data["location"]["name"],
                "forecast": forecast,
                "alerts": data.get("alerts", {}).get("alert", []) if alerts == "yes" else []
            }
        return data

    def get_historical_weather(self, city, date, lang="en"):
        params = {"q": city, "dt": date, "lang": lang}
        data = self._make_request("history.json", params)
        if "error" not in data:
            day = data["forecast"]["forecastday"][0]
            return {
                "location": data["location"]["name"],
                "date": day["date"],
                "max_temp_c": day["day"]["maxtemp_c"],
                "min_temp_c": day["day"]["mintemp_c"],
                "condition": day["day"]["condition"]["text"],
                "precip_mm": day["day"]["totalprecip_mm"]
            }
        return data

    def get_astronomy(self, city, date=None, lang="en"):
        params = {"q": city, "lang": lang}
        if date:
            params["dt"] = date
        data = self._make_request("astronomy.json", params)
        if "error" not in data:
            astro = data["astronomy"]["astro"]
            return {
                "location": data["location"]["name"],
                "date": data["location"]["localtime"].split()[0],
                "sunrise": astro["sunrise"],
                "sunset": astro["sunset"],
                "moonrise": astro["moonrise"],
                "moonset": astro["moonset"],
                "moon_phase": astro["moon_phase"]
            }
        return data
