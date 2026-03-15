import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, Set
from pipelines.base.task import Task

class DetermineHistoricalTournamentsTask(Task):
    """
    Scrapes the ESPN schedule for a given year and identifies new tournaments.

    This task fetches the schedule for a specific season and compares the 
    found tournament IDs against those already stored in the Parquet dataset.

    Attributes:
        year (int): The PGA season year to scrape (e.g., 2024).
    """

    def __init__(self, name: str, year: int):
        """
        Initializes the DetermineHistoricalTournamentsTask.

        Args:
            name (str): The name of the task.
            year (int): The season year to scrape.
        """
        super().__init__(name)
        self.year = year
        self.tournaments_path = "data/pga/raw/tournaments/data.parquet"

    def _get_existing_tournament_ids(self) -> Set[int]:
        """
        Retrieves the set of tournament IDs already present in the Parquet storage.

        Returns:
            Set[int]: A set of integer tournament IDs. Returns an empty set if 
                the file does not exist.
        """
        if not os.path.exists(self.tournaments_path):
            return set()
        
        try:
            df = pd.read_parquet(self.tournaments_path)
            if "id" in df.columns:
                return set(df["id"].tolist())
            return set()
        except Exception as e:
            print(f"Error reading existing tournaments: {e}")
            return set()

    def execute(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Executes the scraping of historical tournament IDs.

        Args:
            context (Dict[str, Any]): The shared pipeline context.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing 'tournament_ids' 
                found for the year that are not already in storage.
        """
        url = f"https://www.espn.com/golf/schedule/_/season/{self.year}"
        print(f"Fetching schedule from: {url}")
        
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch schedule for {self.year}")
            return {"tournament_ids": []}

        soup = BeautifulSoup(response.text, "html.parser")
        existing_ids = self._get_existing_tournament_ids()
        new_ids = []

        # Find "Completed Tournaments" section
        completed_header = soup.find(lambda tag: tag.name == "h2" and "Completed Tournaments" in tag.text)
        if not completed_header:
            print("Could not find 'Completed Tournaments' section.")
            return {"tournament_ids": []}

        table = completed_header.find_next("table")
        if not table:
            return {"tournament_ids": []}

        rows = table.find_all("tr")[1:] # Skip header
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 2:
                continue
            
            link = cols[1].find("a")
            if link and "tournamentId=" in link["href"]:
                t_id = int(link["href"].split("tournamentId=")[1])
                if t_id not in existing_ids:
                    new_ids.append(t_id)

        print(f"Found {len(new_ids)} new tournament IDs for {self.year}")
        return {"tournament_ids": new_ids}
