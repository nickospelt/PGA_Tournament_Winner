from pydantic import BaseModel

class Player(BaseModel):
    name: str # PK
    ## Aggregate/Engineered Features TBD