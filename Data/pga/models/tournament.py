from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Tournament(BaseModel):
    id: int # [PK] (from ESPN)
    name: str
    location: str # [WeatherRecord.location FK]
    start_date: datetime
    end_date: datetime
    r1_date: Optional[datetime] = None
    r2_date: Optional[datetime] = None
    r3_date: Optional[datetime] = None
    r4_date: Optional[datetime] = None
    purse: int
    prev_winner: str