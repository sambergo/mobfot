import json
import os
import re
import urllib.parse
from logging import getLevelName, getLogger
from typing import Optional, Union

import requests
from cachecontrol import CacheControl

VERSION = "1.2.0"


class MobFot:
    BASE_URL = "https://www.fotmob.com/api"
    LOGGER = getLogger(__name__)

    def __init__(
        self, proxies: Optional[dict] = None, logging_level: Optional[str] = "WARNING"
    ) -> None:
        SESSION = requests.Session()
        if proxies:
            SESSION.proxies.update(proxies)
        CACHE_SESSION = CacheControl(SESSION)

        if logging_level:
            if logging_level.upper() in [
                "DEBUG",
                "INFO",
                "WARNING",
                "ERROR",
                "CRITICAL",
            ]:
                self.LOGGER.setLevel(getLevelName(logging_level.upper()))
            else:
                print(f"Logging level {logging_level} not recognized!")

        self.session = CACHE_SESSION
        self.matches_url = f"{self.BASE_URL}/matches?"
        self.leagues_url = f"{self.BASE_URL}/leagues?"
        self.teams_url = f"{self.BASE_URL}/teams?"
        self.player_url = f"{self.BASE_URL}/playerData?"
        self.match_details_url = f"{self.BASE_URL}/matchDetails?"
        self.search_url = f"{self.BASE_URL}/searchData?"
        self.tv_listing_url = f"{self.BASE_URL}/tvlisting?"
        self.tv_listings_url = f"{self.BASE_URL}/tvlistings?"
        self.DATA_PATH = self._get_data_path()
        self._create_data_folder_if_not_exists()

    def _get_data_path(self):
        if os.name == "nt":  # Windows
            app_data_folder = os.path.join(os.environ["APPDATA"], "mobfot\\")
            return app_data_folder
        elif os.name == "posix":  # Linux or macOS
            xdg_data = os.getenv("XDG_DATA_HOME")
            data_folder = "/mobfot/"
            if not xdg_data:
                raise Exception("XDG_DATA_HOME environment variable is not set.")
            return xdg_data + data_folder
        else:
            raise NotImplementedError("Unsupported operating system")

    def _create_data_folder_if_not_exists(self):
        try:
            if not os.path.exists(self.DATA_PATH):
                os.makedirs(self.DATA_PATH)
                print(f"Folder '{self.DATA_PATH}' created successfully!")
        except Exception as e:
            print(f"Error creating folder: {str(e)}")
            raise SystemExit

    def _match_is_finished(self, match) -> bool:
        return (
            match["header"]["status"]["finished"]
            and match["header"]["status"]["started"]
        )

    def _parse_filepath(self, match_id):
        return self.DATA_PATH + str(match_id) + ".json"

    def _load_if_file_exist(self, filepath: str):
        if os.path.isfile(filepath):
            with open(filepath) as file:
                return json.load(file)
        else:
            return None

    def _check_date(self, date: str) -> Union[re.Match, None]:
        """Makes sure dates are formatted correctly YYYY-MM-DD

        Args:
            date (str): The date (YYYY-MM-DD)

        Returns:
            Union[re.Match, None]:
        """
        pattern = re.compile(r"(20\d{2})(\d{2})(\d{2})")
        return pattern.match(date)

    def _execute_query(self, url: str) -> dict:
        """Executes a single query against the API

        Args:
            url (str): URL

        Returns:
            dict: The response from the API
        """
        response = self.session.get(url)
        response.raise_for_status()
        self.LOGGER.debug(response)
        return response.json()

    def get_matches_by_date(
        self, date: str, time_zone: str = "America/New_York"
    ) -> dict:
        """Gets all the matches for a given date

        Args:
            date (str): The date (YYYY-MM-DD)
            time_zone (str, optional): The time zone. Defaults to "America/New_York".

        Returns:
            dict: A dictionary of all the matches for a particular date
        """
        if self._check_date(date) is not None:
            url = f"{self.matches_url}date={date}&timezone={time_zone}"
            return self._execute_query(url)
        return {}

    def get_league(
        self,
        id: int,
        tab: str = "overview",
        type: str = "league",
        time_zone: str = "America/New_York",
    ) -> dict:
        """Gets information about a given league

        Args:
            id (int): The league ID
            tab (str, optional): What tab of information to get. Defaults to "overview".
            type (str, optional): Defaults to "league".
            time_zone (str, optional): The time zone. Defaults to "America/New_York".

        Returns:
            dict: The response from the API
        """
        url = f"{self.leagues_url}id={id}&tab={tab}&type={type}&timezone={time_zone}"
        return self._execute_query(url)

    def get_team(
        self,
        id: int,
        tab: str = "overview",
        type: str = "league",
        time_zone: str = "America/New_York",
    ) -> dict:
        """Gets information about a given team

        Args:
            id (int): The team ID
            tab (str, optional): What tab of information to get. Defaults to "overview".
            type (str, optional): Defaults to "league".
            time_zone (str, optional): The time zone. Defaults to "America/New_York".

        Returns:
            dict: The response from the API
        """
        url = f"{self.teams_url}id={id}&tab={tab}&type={type}&timezone={time_zone}"
        return self._execute_query(url)

    def get_player(self, id: int) -> dict:
        """Gets information about a given player

        Args:
            id (int): The player ID

        Returns:
            dict: The response from the API
        """
        url = f"{self.player_url}id={id}"
        return self._execute_query(url)

    def get_match_details(self, match_id: int, no_cache: bool = False) -> dict:
        """Gets information about a given match

        Args:
            match_id (int): The match ID

        Returns:
            dict: The response from the API
        """
        url = f"{self.match_details_url}matchId={match_id}"
        filepath = self._parse_filepath(match_id)
        match_from_cache = self._load_if_file_exist(filepath)
        if not no_cache and match_from_cache:
            return match_from_cache
        else:
            match_details = self._execute_query(url)
            if self._match_is_finished(match_details):
                try:
                    with open(filepath, "w") as file:
                        file.write(json.dumps(match_details))
                except Exception as e:
                    print(f"Error writing to file: {str(e)}")
            return match_details

    def get_match_tv_listing(self, match_id: int, country_code: str = "GB") -> dict:
        """Gets the TV listing for a given match

        Args:
            match_id (int): The match ID
            country_code (str, optional): The country code. Defaults to "GB".

        Returns:
            dict: The response from the API
        """
        url = f"{self.tv_listing_url}matchId={match_id}&countryCode={country_code}"
        return self._execute_query(url)

    def get_tv_listings_country(self, country_code: str = "GB") -> dict:
        """Get TV listing information by country

        Args:
            country_code (str, optional): The country code. Defaults to "GB".

        Returns:
            dict: The response from the API
        """
        url = f"{self.tv_listings_url}countryCode={country_code}"
        return self._execute_query(url)

    def search(self, term: str, user_language: str = "en-GB,en") -> dict:
        """Searches FotMob for a given term

        Args:
            term (str): The term to search fr
            user_language (str, optional): The language. Defaults to "en-GB,en".

        Returns:
            dict: The response from the API
        """
        search_term = urllib.parse.quote_plus(term)
        url = f"{self.search_url}term={search_term}&userLanguage={user_language}"
        return self._execute_query(url)
