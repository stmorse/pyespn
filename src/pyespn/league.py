# league.py
from typing import Any, Dict, List, Optional, Type

from .api_gateway import APIGateway
from .models import Team, Player, Matchup

class League:
    def __init__(self, season: int, league_id: int):
        self.season = season
        self.league_id = league_id

        # interface to the API via schema.yaml
        self.gw = APIGateway()

    def get_teams(self) -> List[Team]:
        return self.gw.request(
            "league_teams",
            path_args={"season": self.season, "league_id": self.league_id}
        )
    
    def get_players(self) -> List[Player]:
        return self.gw.request(
            "players_short",
            path_args={"season": self.season}
        )
    
    def get_matchups(self) -> List[Matchup]:
        # returns boxscore-level detail on all matchups for the season
        return self.gw.request(
            "matchups",
            path_args={"season": self.season, "league_id": self.league_id}
        )