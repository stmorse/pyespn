# league.py
from typing import Any, Dict, List, Optional, Type
import datetime

from .api_gateway import APIGateway
from .models import (
    Team, Player, MatchupHistorical, 
    RosterMove, RosterMoveResponse, ExecuteRosterMove
)


class League:
    def __init__(self, season: int, league_id: int):
        self.season = season
        self.league_id = league_id

        # Check if season is the current year
        current_year = datetime.datetime.now().year
        self.historical = self.season < current_year

        # interface to the API via schema.yaml
        self.gw = APIGateway()

    def get_teams(self) -> List[Team]:
        path_args = {"season": self.season, "league_id": self.league_id}

        if self.historical:
            # TODO: we have API leaking in here with "seasonId"
            response = self.gw.request(
                "league_teams_historical", 
                path_args=path_args,
                query_args={"seasonId": self.season} 
            )

            # response is a list of Season's
            # should be only one since we specified ?seasonId=
            # but we'll loop through anyway
            for season in response:
                if season.seasonId == self.season:
                    return season.teams
        else:
            # otherwise, just pull this season normally
            return self.gw.request("league_teams", path_args=path_args)
    
    def get_players(self) -> List[Player]:
        return self.gw.request(
            "players_short",
            path_args={"season": self.season}
        )
    
    # TODO: fix typing for non-historial also
    def get_matchups(self) -> List[MatchupHistorical]:
        # returns boxscore-level detail on all matchups for the season
        return self.gw.request(
            "matchups_historical" if self.historical else "matchups",
            path_args={"season": self.season, "league_id": self.league_id}
        )
    
    def execute_roster_move(
            self,
            team_id: int,
            moves: List[RosterMove]
    ) -> RosterMoveResponse:
        # build payload (will be a ExecuteRosterMove object)
        payload = {
            "teamId": team_id,
            "scoringPeriodId": 1,
            "items": moves
        }

        # send post request and return response
        return self.gw.request(
            "roster_move",
            path_args={"season": self.season, "league_id": self.league_id},
            payload=ExecuteRosterMove.model_validate(payload)
        )