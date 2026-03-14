from pydantic import BaseModel
from datetime import datetime

class WeatherRecord(BaseModel):
    tournament_id: int # PK [Tournament.id FK]
    date: datetime # PK
    location: str
    elevation: float
    temperature: float
    precipitation: float
    wind_speed: float
    wind_direction: float