from typing import Optional, List
from pipelines.base.pipeline import Pipeline
from pipelines.tasks.determine_historical_tournaments import DetermineHistoricalTournamentsTask
from pipelines.tasks.determine_current_tournaments import DetermineCurrentTournamentsTask
from pipelines.tasks.provide_specific_tournaments import ProvideSpecificTournamentsTask
from pipelines.tasks.fetch_tournament_data import FetchTournamentDataTask
from pipelines.tasks.fetch_weather_data import FetchWeatherDataTask

def create_espn_pipeline(mode: str, year: Optional[int] = None, tournament_ids: Optional[List[int]] = None) -> Pipeline:
    """
    Factory function to create an ESPN PGA Ingestion Pipeline.

    This function orchestrates the sequence of tasks required to scrape 
    tournament and weather data from ESPN and other sources, storing 
    them in Parquet format.

    Args:
        mode (str): Execution mode, 'historical', 'current', or 'specific'.
        year (Optional[int]): The year to scrape for historical mode. 
            Required if mode is 'historical'.
        tournament_ids (Optional[List[int]]): List of specific tournament IDs.
            Required if mode is 'specific'.

    Returns:
        Pipeline: A configured Pipeline instance with the appropriate tasks.

    Raises:
        ValueError: If arguments are missing for the selected mode.
    """
    pipeline = Pipeline(f"ESPN PGA {mode.capitalize()} Ingestion")
    
    if mode == "historical":
        if not year:
            raise ValueError("Year must be provided for historical mode")
        surveyor = DetermineHistoricalTournamentsTask("Determine Historical Tournaments", year)
    elif mode == "specific":
        if not tournament_ids:
            raise ValueError("tournament_ids must be provided for specific mode")
        surveyor = ProvideSpecificTournamentsTask("Provide Specific Tournaments", tournament_ids)
    else:
        surveyor = DetermineCurrentTournamentsTask("Determine Current Tournaments")
        
    fetcher = FetchTournamentDataTask("Fetch Tournament Data", depends_on=[surveyor])
    weather = FetchWeatherDataTask("Fetch Weather Data", depends_on=[fetcher])
    
    pipeline.add_task(surveyor)
    pipeline.add_task(fetcher)
    pipeline.add_task(weather)
    
    return pipeline

if __name__ == "__main__":
    # Example usage:
    # pipeline = create_espn_pipeline(mode="historical", year=2024)
    # pipeline.run()
    pass
