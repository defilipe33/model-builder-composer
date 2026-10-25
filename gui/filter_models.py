from dataclasses import dataclass
from typing import Any


@dataclass
class FilterDefinition:
    field: str
    operator: str
    value: Any
