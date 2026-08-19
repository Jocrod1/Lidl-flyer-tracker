"""Domain model for a persisted Lidl flyer."""

from __future__ import annotations

import dataclasses
import datetime as dt
import enum
from typing import Optional


class FlyerStatus(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    DOWNLOADED = "DOWNLOADED"
    STORED = "STORED"
    FAILED = "FAILED"


@dataclasses.dataclass
class FlyerRecord:
    """Represents one flyer row in the database."""

    source_url: str
    storage_key: str
    category: str
    name: str
    content_hash: str
    status: FlyerStatus

    id: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    downloaded_at: Optional[dt.datetime] = None
    created_at: Optional[dt.datetime] = None
