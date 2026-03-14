from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pipelines.base.task import Task

def convert_espn_dates(raw_date: str) -> Tuple[str, str]:
    """
    Converts ESPN's date format (e.g., 'April 11 - 14, 2024') to YYYY-MM-DD.
    
    Args:
        raw_date (str): The raw date string from ESPN.
        
    Returns:
        Tuple[str, str]: (start_date, end_date) in YYYY-MM-DD format.
    """
    try:
        raw_date_parts = raw_date.split(" - ")
        first_part = raw_date_parts[0].split(" ")
        second_part = raw_date_parts[1].split(",")
        
        year = second_part[1].strip()
        start_month = first_part[0]
        start_day = first_part[1]
        
        # Handle cases where tournament spans across months
        if len(second_part[0].strip().split(" ")) > 1:
            end_month_part = second_part[0].strip().split(" ")
            end_month = end_month_part[0]
            end_day = end_month_part[1]
        else:
            end_month = start_month
            end_day = second_part[0].strip()

        start_str = f"{start_month} {start_day}, {year}"
        end_str = f"{end_month} {end_day}, {year}"
        
        # Determine if month is abbreviated or full
        fmt = "%B %d, %Y" if len(start_month) > 3 else "%b %d, %Y"
        
        start_dt = datetime.strptime(start_str, fmt)
        end_dt = datetime.strptime(end_str, fmt)
        
        return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Error converting dates '{raw_date}': {e}")
        return "", ""

class FetchTournamentDataTask(Task):
    """
    Scrapes detailed player and course data for a list of tournament IDs.

    Uses Selenium to navigate the multi-tabbed ESPN leaderboard interface
    to extract metadata, performance statistics, and hole-by-hole data.

    Attributes:
        db_path (str): Path to the SQLite database file.
    """

    def __init__(self, name: str, db_path: str, depends_on: Optional[List[Task]] = None):
        """
        Initializes the FetchTournamentDataTask.

        Args:
            name (str): The name of the task.
            db_path (str): The path to the SQLite database.
            depends_on (Optional[List[Task]]): Tasks that must provide 
                'tournament_ids' in the context. Defaults to None.
        """
        super().__init__(name, depends_on=depends_on)
        self.db_path = db_path

    def _setup_browser(self) -> webdriver.Chrome:
        """
        Initializes a headless Selenium Chrome browser.

        Returns:
            webdriver.Chrome: A configured Selenium webdriver instance.
        """
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        return webdriver.Chrome(options=chrome_options)

    def execute(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Iterates through tournament IDs and scrapes detailed data for each.

        Args:
            context (Dict[str, Any]): The shared pipeline context containing 
                'tournament_ids'.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing 'processed_tournaments' 
                list with metadata for weather tasks.
        """
        tournament_ids = context.get("tournament_ids", [])
        if not tournament_ids:
            print("No tournament IDs to fetch.")
            return None

        browser = self._setup_browser()
        processed_tournaments = []
        
        for t_id in tournament_ids:
            meta = self._process_tournament(t_id, browser)
            if meta:
                processed_tournaments.append(meta)
            
        browser.quit()
        return {"processed_tournaments": processed_tournaments}

    def _process_tournament(self, t_id: int, browser: webdriver.Chrome) -> Optional[Dict[str, Any]]:
        """
        Orchestrates the scraping of a single tournament's sub-pages.

        Args:
            t_id (int): The ESPN tournament ID.
            browser (webdriver.Chrome): The active Selenium browser instance.

        Returns:
            Optional[Dict[str, Any]]: Metadata about the tournament (id, location, dates).
        """
        print(f"Processing Tournament ID: {t_id}")
        
        # 1. Leaderboard & Metadata
        url = f"https://www.espn.com/golf/leaderboard?tournamentId={t_id}"
        browser.get(url)
        soup = BeautifulSoup(browser.page_source, "html.parser")
        
        try:
            name = soup.find('h1', class_="headline").text
            date_str = soup.find('span', class_="Leaderboard__Event__Date").text
            
            # Extract Location
            location_info = soup.find('div', class_="Leaderboard__Course__Location").text.split(' - ')
            location = location_info[1]
            
            start_date, end_date = convert_espn_dates(date_str)
            
            print(f"Scraped: {name} at {location} ({start_date} to {end_date})")
            
            # TODO: Implement full data extraction and persistence
            
            return {
                "tournament_id": t_id,
                "location": location,
                "start_date": start_date,
                "end_date": end_date
            }
        except Exception as e:
            print(f"Error scraping metadata for {t_id}: {e}")
            return None
