from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

class Team(BaseModel):
    name: str
    current_projected_rank: Optional[int] = None

    model_config = {
        "populate_by_name": True,  # allow using both field and alias names
        "extra": "ignore",         # ignore fields the API adds later
    }