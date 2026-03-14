from typing import Optional
from pipelines.base.pipeline import Pipeline
from pipelines.tasks.determine_historical_tournaments import DetermineHistoricalTournamentsTask
from pipelines.tasks.determine_current_tournaments import DetermineCurrentTournamentsTask
from pipelines.tasks.fetch_tournament_data import FetchTournamentDataTask
from pipelines.tasks.fetch_weather_data import FetchWeatherDataTask

def create_espn_pipeline(mode: str, year: Optional[int] = None, db_path: str = "Data/PGA_SQL_DB/PGA.db") -> Pipeline:
    """
    Factory function to create an ESPN PGA Ingestion Pipeline.

    This function orchestrates the sequence of tasks required to scrape 
    tournament and weather data from ESPN and other sources.

    Args:
        mode (str): Execution mode, either 'historical' or 'current'.
        year (Optional[int]): The year to scrape for historical mode. 
            Required if mode is 'historical'.
        db_path (str): The path to the SQLite database. Defaults to 
            'Data/PGA_SQL_DB/PGA.db'.

    Returns:
        Pipeline: A configured Pipeline instance with the appropriate tasks.

    Raises:
        ValueError: If mode is 'historical' but no year is provided.
    """
    pipeline = Pipeline(f"ESPN PGA {mode.capitalize()} Ingestion")
    
    if mode == "historical":
        if not year:
            raise ValueError("Year must be provided for historical mode")
        surveyor = DetermineHistoricalTournamentsTask("Determine Historical Tournaments", year, db_path)
    else:
        surveyor = DetermineCurrentTournamentsTask("Determine Current Tournaments", db_path)
        
    fetcher = FetchTournamentDataTask("Fetch Tournament Data", db_path, depends_on=[surveyor])
    weather = FetchWeatherDataTask("Fetch Weather Data", db_path, depends_on=[fetcher])
    
    pipeline.add_task(surveyor)
    pipeline.add_task(fetcher)
    pipeline.add_task(weather)
    
    return pipeline

if __name__ == "__main__":
    pass
