from pydantic import BaseModel

class PlayerRoundScore(BaseModel):
    player_name: str
    tournament_id: int
    season: int
    round: int
    score: int
