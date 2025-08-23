# league.py
from typing import Any, Dict, List, Optional, Type

from .api_gateway import APIGateway
from .models import Team

class League:
    def __init__(self, season: int, id: int):
        self.season = season
        self.id = id

        # interface to the API via schema.yaml
        self.gw = APIGateway()

    def get_teams(self) -> List[Team]:
        return self.gw.request(
            "league_teams",
            path_args={"season": self.season, "league_id": self.id}
        )