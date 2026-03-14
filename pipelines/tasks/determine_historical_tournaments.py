import os
import sqlite3
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, Set
from pipelines.base.task import Task

class DetermineHistoricalTournamentsTask(Task):
    """
    Scrapes the ESPN schedule for a given year and identifies new tournaments.

    This task fetches the schedule for a specific season and compares the 
    found tournament IDs against those already stored in the database.

    Attributes:
        year (int): The PGA season year to scrape (e.g., 2024).
        db_path (str): Path to the SQLite database file.
    """

    def __init__(self, name: str, year: int, db_path: str):
        """
        Initializes the DetermineHistoricalTournamentsTask.

        Args:
            name (str): The name of the task.
            year (int): The season year to scrape.
            db_path (str): The path to the SQLite database.
        """
        super().__init__(name)
        self.year = year
        self.db_path = db_path

    def _get_existing_tournament_ids(self) -> Set[int]:
        """
        Retrieves the set of tournament IDs already present in the database.

        Returns:
            Set[int]: A set of integer tournament IDs. Returns an empty set if 
                the database or table does not exist.
        """
        if not os.path.exists(self.db_path):
            return set()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM tournaments")
            ids = {row[0] for row in cursor.fetchall()}
            return ids
        except sqlite3.OperationalError:
            # Table might not exist yet
            return set()
        finally:
            conn.close()

    def execute(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Executes the scraping of historical tournament IDs.

        Args:
            context (Dict[str, Any]): The shared pipeline context.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing 'tournament_ids' 
                found for the year that are not already in the database.
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
