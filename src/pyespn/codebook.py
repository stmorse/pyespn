from __future__ import annotations
from dataclasses import asdict, dataclass
from importlib import resources
from typing import Optional, Dict, Any

import yaml


@dataclass(frozen=True)
class Position:
    id: int
    abbr: str
    name: str

@dataclass(frozen=True)
class ProTeam:  
    id: int
    abbr: str
    name: str


class Codebook:
    def __init__(
        self,
        positions_by_id: Dict[int, Position],
        pro_teams_by_id: Dict[int, ProTeam],
    ) -> None:
        self._positions_by_id = positions_by_id
        self._pro_teams_by_id = pro_teams_by_id
        self.pos_unk = Position(id=-1, abbr="Unk", name="Unknown")
        self.team_unk = ProTeam(id=-1, abbr="Unk", name="Unknown")

    @classmethod
    def load(cls) -> "Codebook":
        """Loads codebook.yaml and returns a Codebook instance with the info"""

        with resources.files("pyespn").joinpath("codebook.yaml").open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # build positions
        positions: Dict[int, Position] = {}
        for id, meta in (data.get("positions") or {}).items():
            id = int(id)
            positions[id] = Position(
                id=id, 
                abbr=str(meta["abbr"]), 
                name=str(meta["name"])
            )

        # build teams
        teams: Dict[int, ProTeam] = {}
        for id, meta in (data.get("pro_teams") or {}).items():
            id = int(id)
            teams[id] = ProTeam(
                id=id, 
                abbr=str(meta["abbr"]), 
                name=str(meta["name"])
            )

        return cls(positions_by_id=positions, pro_teams_by_id=teams)

    # ---- simple lookups ----
    def position(self, id_: int) -> Position:
        return self._positions_by_id.get(int(id_), self.pos_unk)

    def pro_team(self, id_: int) -> ProTeam:
        return self._pro_teams_by_id.get(int(id_), self.team_unk)


# Lazy load a single instance with `codebook()` call
_CB: Optional[Codebook] = None
def codebook() -> Codebook:
    global _CB
    if _CB is None:
        _CB = Codebook.load()
    return _CB