from datetime import datetime

from pydantic import BaseModel


class Snapshot(BaseModel):
    seq: int
    table_state: dict
    timestamp: datetime
