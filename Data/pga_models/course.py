from pydantic import BaseModel

class Course(BaseModel):
    name: str # PK
    location: str
    ## Aggregate/Engineered Features TBD