from crewai.tools import tool
from backend.clients.weather_client import WeatherClient


@tool("current_weather")
def get_current_weather(city: str) -> str:
    """
    Get current weather information for a specific city.

    Args:
        city (str): The name of the city to get weather for

    Returns:
        str: Current weather information formatted as HTML
    """
    try:
        weather_client = WeatherClient()
        weather_data = weather_client.get_current_weather(city)

        if "error" in weather_data:
            return f"Error getting weather for {city}: {weather_data['error']}"

        # Format as HTML for better presentation
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ccc; border-radius: 8px;">
            <h2 style="color: #333;">Current Weather in {weather_data['location']}</h2>
            <p>
                Condition: {weather_data['condition']}<br>
                🌡️ Temperature: {weather_data['temp_c']}°C<br>
                🤔 Feels like: {weather_data['feelslike_c']}°C<br>
                💧 Humidity: {weather_data['humidity']}%
            </p>
        </div>
        """
        return f"```html-render\n{html}\n```"

    except Exception as e:
        return f"Error retrieving current weather for {city}: {str(e)}"


@tool("weather_forecast")
def get_weather_forecast(city: str, days: int = 7) -> str:
    """
    Get weather forecast for a specific city for multiple days.

    Args:
        city (str): The name of the city to get forecast for
        days (int): Number of days for forecast (1-14), defaults to 7

    Returns:
        str: Weather forecast information formatted as HTML
    """
    try:
        weather_client = WeatherClient()

        # Ensure days is within valid range
        days = max(1, min(days, 14))

        forecast_data = weather_client.get_forecast(city, days)

        if "error" in forecast_data:
            return f"Error getting forecast for {city}: {forecast_data['error']}"

        # Format as HTML for better presentation
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ccc; border-radius: 8px;">
            <h2 style="color: #333;">Weather Forecast for {city} - Next {days} Days</h2>
            <ul style="list-style: none; padding: 0;">
        """

        for day in forecast_data['forecast']['forecastday']:
            date = day['date']
            condition = day['day']['condition']['text'].strip()
            temp_max = day['day']['maxtemp_c']
            temp_min = day['day']['mintemp_c']
            html += f"""
                <li style="margin-bottom: 15px; padding: 10px; border: 1px solid #ccc; border-radius: 8px;">
                    <strong>{date}</strong><br>
                    Condition: {condition}<br>
                    🌡️ Max: {temp_max}°C, Min: {temp_min}°C
                </li>
            """

        html += """
            </ul>
        </div>
        """
        return f"```html-render\n{html}\n```"

    except Exception as e:
        return f"Error retrieving forecast for {city}: {str(e)}"