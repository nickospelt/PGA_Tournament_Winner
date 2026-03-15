import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, Any, Optional
from pipelines.base.task import Task

class DetermineCurrentTournamentsTask(Task):
    """
    Identifies active or upcoming tournaments for the current year.

    This task checks the ESPN schedule for the current date and extracts 
    IDs for tournaments currently in progress or the next scheduled event.
    """

    def __init__(self, name: str):
        """
        Initializes the DetermineCurrentTournamentsTask.

        Args:
            name (str): The name of the task.
        """
        super().__init__(name)

    def execute(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Executes the detection of current tournament IDs.

        Args:
            context (Dict[str, Any]): The shared pipeline context.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing 'tournament_ids' 
                for current or upcoming events.
        """
        current_year = datetime.now().year
        url = f"https://www.espn.com/golf/schedule/_/season/{current_year}"
        
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        current_ids = []

        # Look for "Current Tournaments"
        current_header = soup.find(lambda tag: tag.name == "h2" and "Current Tournaments" in tag.text)
        if current_header:
            table = current_header.find_next("table")
            if table:
                rows = table.find_all("tr")[1:]
                for row in rows:
                    link = row.find("a", href=True)
                    if link and "tournamentId=" in link["href"]:
                        current_ids.append(int(link["href"].split("tournamentId=")[1]))
        
        # If no current, get the next scheduled one
        if not current_ids:
            scheduled_header = soup.find(lambda tag: tag.name == "h2" and "Scheduled Tournaments" in tag.text)
            if scheduled_header:
                table = scheduled_header.find_next("table")
                if table:
                    first_row = table.find("tr", class_=lambda x: x != "header")
                    if first_row:
                        link = first_row.find("a", href=True)
                        if link and "tournamentId=" in link["href"]:
                            current_ids.append(int(link["href"].split("tournamentId=")[1]))

        print(f"Current/Upcoming tournament IDs: {current_ids}")
        return {"tournament_ids": current_ids}
