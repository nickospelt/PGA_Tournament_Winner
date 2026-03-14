from pydantic import BaseModel
from datetime import datetime

class Tournament(BaseModel):
    id: int
    name: str
    start_date: datetime
    end_date: datetime
    purse: int
    prev_winner: str