from pydantic import BaseModel, Field

class PlayerTournamentStats(BaseModel):
    player_name: str
    tournament_id: int
    season: int
    drive_dist: float = Field(description="Driving distance average")
    drive_acc: float = Field(description="Driving accuracy percentage")
    gir_acc: float = Field(description="Greens in Regulation percentage")
    putts_per_gir: float = Field(description="Putts per GIR")
    eagles: int
    birdies: int
    pars: int
    bogeys: int
    double_bogeys: int
    earnings: int
    fedex_pts: int
    total_score: int
