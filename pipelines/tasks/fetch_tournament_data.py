from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import time
import re

from pipelines.base.task import Task
from data.pga.models.player_tournament_stats import PlayerTournamentStats
from data.pga.models.player_round_score import PlayerRoundScore
from data.pga.models.tournament import Tournament
from data.pga.storage import save_to_parquet

def convert_espn_dates(raw_date: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Converts ESPN's date format (e.g., 'April 11 - 14, 2024' or 'March 15, 2026') 
    to a tuple of start and end datetime objects.
    
    If the input contains a date range, it parses both dates. If it contains 
    a single date, both start and end will be set to that date.
    
    Args:
        raw_date (str): The raw date string from ESPN.
        
    Returns:
        Tuple[Optional[datetime], Optional[datetime]]: (start_date, end_date) 
            as datetime objects.
    """
    try:
        # Handle Date Range: "April 11 - 14, 2024"
        if " - " in raw_date:
            raw_date_parts = raw_date.split(" - ")
            first_part = raw_date_parts[0].split(" ")
            second_part = raw_date_parts[1].split(",")
            
            year = second_part[-1].strip()
            start_month = first_part[0]
            start_day = first_part[1]
            
            # Handle cases where tournament spans across months: "March 28 - April 1, 2024"
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
            
            return start_dt, end_dt
        
        # Handle Single Date: "March 15, 2026"
        else:
            month = raw_date.split(" ")[0]
            fmt = "%B %d, %Y" if len(month) > 3 else "%b %d, %Y"
            dt = datetime.strptime(raw_date, fmt)
            return dt, dt

    except Exception as e:
        print(f"Error converting dates '{raw_date}': {e}")
        return None, None

class FetchTournamentDataTask(Task):
    """
    Scrapes detailed player and course data for a list of tournament IDs.

    Uses Selenium to navigate the multi-tabbed ESPN leaderboard interface
    to extract metadata, performance statistics, and round scores.
    Validated data is stored in Parquet format.
    """

    def __init__(self, name: str, depends_on: Optional[List[Task]] = None):
        """
        Initializes the FetchTournamentDataTask.

        Args:
            name (str): The name of the task.
            depends_on (Optional[List[Task]]): Tasks that must provide 
                'tournament_ids' in the context. Defaults to None.
        """
        super().__init__(name, depends_on=depends_on)

    def _setup_browser(self) -> webdriver.Chrome:
        """
        Initializes a headless Selenium Chrome browser.

        Returns:
            webdriver.Chrome: A configured Selenium webdriver instance.
        """
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
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
        
        try:
            for t_id in tournament_ids:
                meta = self._process_tournament(t_id, browser)
                if meta:
                    processed_tournaments.append(meta)
        finally:
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
        time.sleep(3) # Allow JS to load
        soup = BeautifulSoup(browser.page_source, "html.parser")
        
        try:
            # Metadata extraction
            headline = soup.find('h1', class_="headline")
            name = headline.text if headline else "Unknown Tournament"
            
            date_span = soup.find('span', class_="Leaderboard__Event__Date")
            date_str = date_span.text if date_span else ""
            
            location_div = soup.find('div', class_="Leaderboard__Course__Location")
            location = location_div.text.split(' - ')[1] if location_div else "Unknown Location"
            
            start_dt, end_dt = convert_espn_dates(date_str)
            season = start_dt.year if start_dt else datetime.now().year

            # Scrape Purse
            purse = 0
            purse_info = soup.find(lambda tag: tag.name == "div" and "Purse:" in tag.text)
            if purse_info:
                purse_text = purse_info.text.replace("Purse:", "").strip()
                purse_val = re.sub(r'[^\d]', '', purse_text)
                if purse_val:
                    purse = int(purse_val)

            print(f"Scraped: {name} at {location} ({start_dt} to {end_dt}) - Purse: ${purse}")
            
            # Create Tournament Object and Save
            tournament = Tournament(
                id=t_id,
                name=name,
                location=location,
                start_date=start_dt if start_dt else datetime.now(),
                end_date=end_dt if end_dt else datetime.now(),
                purse=purse,
                prev_winner=""
            )
            save_to_parquet([tournament], "tournaments")

            # Parse Leaderboard for Stats and Scores
            stats, scores = self._parse_leaderboard(soup, t_id, season)
            
            if stats:
                save_to_parquet(stats, "player_tournament_stats", partition_cols=["season", "tournament_id"])
            if scores:
                save_to_parquet(scores, "player_round_scores", partition_cols=["season", "tournament_id"])
            
            return {
                "tournament_id": t_id,
                "location": location,
                "start_date": start_dt.strftime("%Y-%m-%d") if start_dt else "",
                "end_date": end_dt.strftime("%Y-%m-%d") if end_dt else ""
            }
        except Exception as e:
            print(f"Error scraping metadata for {t_id}: {e}")
            return None

    def _parse_leaderboard(self, soup: BeautifulSoup, t_id: int, season: int) -> Tuple[List[PlayerTournamentStats], List[PlayerRoundScore]]:
        """
        Parses the main leaderboard table to extract player stats and round scores.

        Args:
            soup (BeautifulSoup): Parsed HTML of the leaderboard page.
            t_id (int): Tournament ID.
            season (int): Season year.

        Returns:
            Tuple[List[PlayerTournamentStats], List[PlayerRoundScore]]: Validated records.
        """
        stats_list = []
        scores_list = []
        
        # Locate the leaderboard table
        tables = soup.find_all("table")
        target_table = None
        for table in tables:
            headers = [th.text.strip().upper() for th in table.find_all("th")]
            if "PLAYER" in headers and ("TOT" in headers or "SCORE" in headers):
                target_table = table
                break
        
        if not target_table:
            print("Could not find leaderboard table.")
            return stats_list, scores_list
            
        headers = [th.text.strip().upper() for th in target_table.find_all("th")]
        col_map = {name: i for i, name in enumerate(headers)}
        
        rows = target_table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if not cols or len(cols) < len(headers):
                continue
            
            try:
                # Player Name
                p_idx = col_map.get("PLAYER")
                if p_idx is None: continue
                player_link = cols[p_idx].find("a", class_="AnchorLink")
                if not player_link: continue
                player_name = player_link.text.strip()
                
                # Round Scores
                rounds = []
                for r in ["R1", "R2", "R3", "R4"]:
                    if r in col_map:
                        val = cols[col_map[r]].text.strip()
                        if val and val != "-" and val.isdigit():
                            rounds.append((int(r[1]), int(val)))
                
                total_strokes = sum(s for _, s in rounds)
                
                # Earnings and FedEx Points
                earnings = 0
                if "EARNINGS" in col_map:
                    val = cols[col_map["EARNINGS"]].text.strip().replace("$", "").replace(",", "")
                    if val.isdigit():
                        earnings = int(val)
                        
                fedex = 0
                if "FEDEX PTS" in col_map:
                    val = cols[col_map["FEDEX PTS"]].text.strip().replace(",", "")
                    if val.isdigit():
                        fedex = int(val)
                
                # Create and add validated records
                stats = PlayerTournamentStats(
                    player_name=player_name,
                    tournament_id=t_id,
                    season=season,
                    earnings=earnings,
                    fedex_pts=fedex,
                    total_score=total_strokes,
                    drive_dist=0.0, drive_acc=0.0, gir_acc=0.0, putts_per_gir=0.0,
                    eagles=0, birdies=0, pars=0, bogeys=0, double_bogeys=0
                )
                stats_list.append(stats)
                
                for r_num, score in rounds:
                    scores_list.append(PlayerRoundScore(
                        player_name=player_name,
                        tournament_id=t_id,
                        season=season,
                        round=r_num,
                        score=score
                    ))
            except Exception:
                continue
                
        return stats_list, scores_list
