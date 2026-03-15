from pydantic import BaseModel
from datetime import datetime

class WeatherRecord(BaseModel):
    date: datetime # PK
    location: str # PK
    elevation: float
    temperature: float
    precipitation: float
    wind_speed: float
    wind_direction: float