import os
import sqlite3
import requests
from typing import Dict, Any, Optional, List
from geopy.geocoders import Nominatim
from pipelines.base.task import Task

class FetchWeatherDataTask(Task):
    """
    Checks for existing weather data and fetches missing data.

    This task iterates over processed tournaments, checks if weather records
    already exist in the database for those dates/locations, and fetches
    them using the Weather API if necessary.

    Attributes:
        db_path (str): Path to the SQLite database file.
    """

    def __init__(self, name: str, db_path: str, depends_on: Optional[List[Task]] = None):
        """
        Initializes the FetchWeatherDataTask.

        Args:
            name (str): The name of the task.
            db_path (str): The path to the SQLite database.
            depends_on (Optional[List[Task]]): Tasks that provide 'processed_tournaments'.
        """
        super().__init__(name, depends_on=depends_on)
        self.db_path = db_path

    def _get_weather_data(self, city: str, start_date: str, end_date: str):
        """
        Retrieves historical weather data for a given location and date range.

        Args:
            city (str): The city name for the weather search.
            start_date (str): Start date in YYYY-MM-DD format.
            end_date (str): End date in YYYY-MM-DD format.

        Returns:
            Tuple: date, temperature, precipitation, wind_speed, wind_direction, elevation
        """
        # Get longitude and latitude information
        geolocator = Nominatim(user_agent="GOLFSCOREPREDICTOR")
        location = geolocator.geocode(f"{city}")
        if location:
            city_latitude = location.latitude
            city_longitude = location.longitude
            print(f"{city} - Latitude: {city_latitude}, Longitude {city_longitude}")
        else:
            print(f"ERROR: Can't find Latitude and Longitude for {city}")
            return None

        # Retrieve Weather data
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": city_latitude,
            "longitude": city_longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": ["temperature_2m_mean", "precipitation_sum", "wind_speed_10m_max", "wind_direction_10m_dominant"],
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
        }
        response = requests.get(url, params=params)
        weather_data = response.json()
        print(f"Weather API Results [{city}]:\n {weather_data}\n")

        date = weather_data['daily']['time']
        temperature = weather_data['daily']['temperature_2m_mean']
        precipitation = weather_data['daily']['precipitation_sum']
        wind_speed = weather_data['daily']['wind_speed_10m_max']
        wind_direction = weather_data['daily']['wind_direction_10m_dominant']
        elevation = weather_data['elevation']

        return date, temperature, precipitation, wind_speed, wind_direction, elevation

    def _weather_exists(self, tournament_id: int) -> bool:
        """
        Checks if weather records exist for the given tournament ID.

        Args:
            tournament_id (int): The ID of the tournament.

        Returns:
            bool: True if records exist, False otherwise.
        """
        if not os.path.exists(self.db_path):
            return False
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM weather_records WHERE tournament_id = ? LIMIT 1", (tournament_id,))
            return cursor.fetchone() is not None
        except sqlite3.OperationalError:
            return False
        finally:
            conn.close()

    def _store_weather(self, t_id: int, location: str, dates: list, temps: list, precips: list, winds: list, dirs: list, elevation: float):
        """
        Persists weather records to the database.

        Args:
            t_id (int): Tournament ID.
            location (str): Course location.
            dates (list): List of dates.
            temps (list): List of temperatures.
            precips (list): List of precipitation sums.
            winds (list): List of wind speeds.
            dirs (list): List of wind directions.
            elevation (float): Course elevation.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            for i in range(len(dates)):
                cursor.execute("""
                    INSERT OR REPLACE INTO weather_records 
                    (tournament_id, date, location, elevation, temperature, precipitation, wind_speed, wind_direction)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (t_id, dates[i], location, elevation, temps[i], precips[i], winds[i], dirs[i]))
            conn.commit()
        except Exception as e:
            print(f"Error storing weather for tournament {t_id}: {e}")
        finally:
            conn.close()

    def execute(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Executes the weather data retrieval and storage.

        Args:
            context (Dict[str, Any]): The shared pipeline context.

        Returns:
            Optional[Dict[str, Any]]: None.
        """
        tournaments = context.get("processed_tournaments", [])
        for t in tournaments:
            t_id = t["tournament_id"]
            if not self._weather_exists(t_id):
                print(f"Fetching weather for {t['location']} ({t['start_date']} to {t['end_date']})")
                try:
                    weather_info = self._get_weather_data(
                        t["location"], t["start_date"], t["end_date"]
                    )
                    if weather_info:
                        dates, temps, precips, winds, dirs, elevation = weather_info
                        self._store_weather(t_id, t["location"], dates, temps, precips, winds, dirs, elevation)
                        print(f"Stored weather for tournament {t_id}")
                except Exception as e:
                    print(f"Failed to fetch weather for tournament {t_id}: {e}")
            else:
                print(f"Weather data already exists for tournament {t_id}")
        return None
