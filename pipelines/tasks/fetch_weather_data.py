import os
import pandas as pd
import requests
from typing import Dict, Any, Optional, List, Tuple
from geopy.geocoders import Nominatim
from pipelines.base.task import Task
from data.pga.models.weather_record import WeatherRecord
from data.pga.storage import save_to_parquet

class FetchWeatherDataTask(Task):
    """
    Checks for existing weather data and fetches missing data.

    This task iterates over processed tournaments, checks if weather records
    already exist in the Parquet storage for those dates/locations, and fetches
    them using the Weather API if necessary.
    """

    def __init__(self, name: str, depends_on: Optional[List[Task]] = None):
        """
        Initializes the FetchWeatherDataTask.

        Args:
            name (str): The name of the task.
            depends_on (Optional[List[Task]]): Tasks that provide 'processed_tournaments'.
        """
        super().__init__(name, depends_on=depends_on)
        self.weather_path = "data/pga/raw/weather_records/data.parquet"

    def _get_weather_data(self, city: str, start_date: str, end_date: str) -> Optional[Tuple]:
        """
        Retrieves historical weather data for a given location and date range.

        Args:
            city (str): The city name for the weather search.
            start_date (str): Start date in YYYY-MM-DD format.
            end_date (str): End date in YYYY-MM-DD format.

        Returns:
            Optional[Tuple]: date, temperature, precipitation, wind_speed, 
                wind_direction, elevation. Returns None if location not found.
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
        
        if 'daily' not in weather_data:
            print(f"No weather data found for {city}")
            return None

        date = weather_data['daily']['time']
        temperature = weather_data['daily']['temperature_2m_mean']
        precipitation = weather_data['daily']['precipitation_sum']
        wind_speed = weather_data['daily']['wind_speed_10m_max']
        wind_direction = weather_data['daily']['wind_direction_10m_dominant']
        elevation = weather_data['elevation']

        return date, temperature, precipitation, wind_speed, wind_direction, elevation

    def _weather_exists(self, location: str, start_date: str) -> bool:
        """
        Checks if weather records exist for the given location and start date.

        Args:
            location (str): The course location.
            start_date (str): The start date of the tournament.

        Returns:
            bool: True if records exist, False otherwise.
        """
        if not os.path.exists(self.weather_path):
            return False
        
        try:
            df = pd.read_parquet(self.weather_path)
            # Check if there's any record matching location and date
            exists = not df[(df['location'] == location) & (df['date'] == start_date)].empty
            return exists
        except Exception:
            return False

    def execute(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Executes the weather data retrieval and storage.

        Args:
            context (Dict[str, Any]): The shared pipeline context containing
                'processed_tournaments'.

        Returns:
            Optional[Dict[str, Any]]: None.
        """
        tournaments = context.get("processed_tournaments", [])
        for t in tournaments:
            location = t["location"]
            start_date = t["start_date"]
            end_date = t["end_date"]
            
            if not self._weather_exists(location, start_date):
                print(f"Fetching weather for {location} ({start_date} to {end_date})")
                try:
                    weather_info = self._get_weather_data(location, start_date, end_date)
                    if weather_info:
                        dates, temps, precips, winds, dirs, elevation = weather_info
                        
                        records = []
                        for i in range(len(dates)):
                            records.append(WeatherRecord(
                                date=datetime.strptime(dates[i], "%Y-%m-%d"),
                                location=location,
                                elevation=elevation,
                                temperature=temps[i],
                                precipitation=precips[i],
                                wind_speed=winds[i],
                                wind_direction=dirs[i]
                            ))
                        
                        save_to_parquet(records, "weather_records", partition_cols=["location"])
                        print(f"Stored weather for {location}")
                except Exception as e:
                    print(f"Failed to fetch weather for {location}: {e}")
            else:
                print(f"Weather data already exists for {location} on {start_date}")
        return None
