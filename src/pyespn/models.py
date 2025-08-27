from typing import Any, Dict, List, Literal, Optional, Type
from pydantic import BaseModel, Field, conint
from .codebook import codebook, Position, ProTeam


# --------------------------------------------------
# TEAM
# --------------------------------------------------

class RecordLine(BaseModel):
    wins: int
    losses: int
    ties: int
    pointsFor: float
    pointsAgainst: float

    model_config = {"extra": "ignore"}

class TeamRecord(BaseModel):
    overall: RecordLine
    home: RecordLine
    away: RecordLine
    
    model_config = {"populate_by_name": True, "extra": "ignore"}

class Team(BaseModel):
    id: int
    abbrev: str
    name: str
    currentProjectedRank: int = None
    draftDayProjectedRank: int = None
    rankCalculatedFinal: int = None
    rankFinal: int = None
    playoffSeed: int = None
    points: float = None
    pointsAdjusted: float = None
    waiverRank: int = None
    record: TeamRecord = None

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

    def default_position(self) -> Position:
        """Return Position object for default_position_id"""
        return codebook().position(self.defaultPositionId)
    
    def eligible_positions(self) -> List[Position]:
        return [codebook().position(p) for p in self.eligibleSlots]

    def pro_team(self) -> ProTeam:
        """Return a ProTeam object for pro_team_id"""
        return codebook().pro_team(self.proTeamId)
    

# --------------------------------------------------
# MATCHUP
# --------------------------------------------------

# class RosterEntry(BaseModel):
#     lineupSlotId: int
#     playerId: int

#     model_config = {"extra": "ignore"}

# class TeamRoster(BaseModel):
#     appliedStatTotal: float
#     entries: List[RosterEntry]

#     model_config = {"extra": "ignore"}

class TeamMatchupHistorical(BaseModel):
    teamId: int
    totalPoints: float
    # TODO: 

    model_config = {"extra": "ignore"}

class MatchupHistorical(BaseModel):
    id: int
    away: TeamMatchupHistorical
    home: TeamMatchupHistorical
    matchupPeriodId: int

    model_config = {"extra": "ignore"}


# --------------------------------------------------
# ROSTER MOVE
# --------------------------------------------------

class RosterMove(BaseModel):
    playerId: int
    type: Literal["LINEUP"] = "LINEUP"
    fromLineupSlotId: int
    toLineupSlotId: int

    model_config = {"extra": "ignore"}

class ExecuteRosterMove(BaseModel):
    isLeagueManager: bool = False
    teamId: int
    type: Literal["ROSTER"] = "ROSTER"
    scoringPeriodId: int
    executionType: Literal["EXECUTE", "VALIDATE"] = "EXECUTE"
    items: List[RosterMove] = Field(min_length=1)

    model_config = {
        "extra": "ignore",          # tolerate extra keys from user code
        "populate_by_name": True,   # if you later add aliases
    }

class RosterMoveResponse(BaseModel):
    pass
