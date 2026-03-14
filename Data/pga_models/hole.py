from pydantic import BaseModel

class Hole(BaseModel):
    num: int # PK
    tournament_id: int # PK [Tournament.id FK]
    course_name: str # PK [Course.name FK]
    par: int
    yards: int
    avg_score: int
    eagles: int
    birdies: int
    pars: int
    bogeys: int
    double_bogeys: int