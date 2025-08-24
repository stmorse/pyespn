from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

class RecordLine(BaseModel):
    wins: int
    losses: int
    ties: int = 0
    points_for: Optional[float] = 0.0
    points_against: Optional[float] = 0.0

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
    current_projected_rank: Optional[int] = None
    draft_day_projected_rank: Optional[int] = None
    rank_calculated_final: Optional[int] = None
    rank_final: Optional[int] = None
    playoff_seed: Optional[int] = None
    points: Optional[float] = None
    points_adjusted: Optional[float] = None
    waiver_rank: Optional[int] = None
    record: Optional[TeamRecord] = None

    model_config = {
        "populate_by_name": True,  # allow using both field and alias names
        "extra": "ignore",         # ignore fields the API adds later
    }

class Player(BaseModel):
    id: int
    first_name: str
    last_name: str
    default_position_id: int
    eligible_positions: List[int]
    pro_team_id: int