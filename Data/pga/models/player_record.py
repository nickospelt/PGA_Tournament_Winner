from pydantic import BaseModel
from datetime import datetime

class PlayerRecord(BaseModel):
    player_name: str # PK [Player.name FK]
    tournament_id: int # PK [Tournament.id FK]
    drive_dist: float
    drive_acc: float
    gir_acc: float
    putts_per_gir: float
    eagles: int
    birdies: int
    pars: int
    bogeys: int
    double_bogeys: int
    r1_score: int
    r2_score: int
    r3_score: int
    r4_score: int
    total_score: int
    earnings: int
    fedex_pts: int
