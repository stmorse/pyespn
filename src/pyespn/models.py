from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel
from .codebook import codebook, Position, ProTeam


# --------------------------------------------------
# TEAM
# --------------------------------------------------

class RecordLine(BaseModel):
    wins: int
    losses: int
    ties: int = 0
    pointsFor: Optional[float] = 0.0
    pointsAgainst: Optional[float] = 0.0

    model_config = {"extra": "ignore"}

class TeamRecord(BaseModel):
    overall: Optional[RecordLine] = None
    home: Optional[RecordLine] = None
    away: Optional[RecordLine] = None
    
    model_config = {"populate_by_name": True, "extra": "ignore"}

class Team(BaseModel):
    id: int
    abbrev: str
    name: str
    currentProjectedRank: Optional[int] = None
    draftDayProjectedRank: Optional[int] = None
    rankCalculatedFinal: Optional[int] = None
    rankFinal: Optional[int] = None
    playoffSeed: Optional[int] = None
    points: Optional[float] = None
    pointsAdjusted: Optional[float] = None
    waiverRank: Optional[int] = None
    record: Optional[TeamRecord] = None

    model_config = {
        "populate_by_name": True,  # allow using both field and alias names
        "extra": "ignore",         # ignore fields the API adds later
    }

# --------------------------------------------------
# PLAYER
# --------------------------------------------------

class Player(BaseModel):
    id: int
    firstName: str
    lastName: str
    defaultPositionId: int
    eligibleSlots: List[int]
    proTeamId: int

    model_config = {"extra": "ignore"}

    def position(self) -> Position:
        """Return Position object for default_position_id"""
        return codebook().position(self.defaultPositionId)

    def pro_team(self) -> ProTeam:
        """Return a ProTeam object for pro_team_id"""
        return codebook().pro_team(self.proTeamId)