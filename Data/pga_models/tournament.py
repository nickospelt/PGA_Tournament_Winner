from pydantic import BaseModel
from datetime import datetime

class Tournament(BaseModel):
    id: int # [PK] (from ESPN)
    name: str
    location: str # [WeatherRecord.location FK]
    start_date: datetime
    end_date: datetime
    purse: int
    prev_winner: str