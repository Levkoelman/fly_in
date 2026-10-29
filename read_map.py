from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class ParseError(Exception):
    """Raised when the map file cannot be read or contains invalid data."""


class ZoneType(Enum):
    NORMAL = "normal"
    RESTRICTED = "restricted"
    PRIORITY = "priority"
    BLOCKED = "blocked"


class ZoneConfig(BaseModel):
    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = Field(gt=0, default=1)
    
    @field_validator("name")
    @classmethod
    def check_zone_name(cls, name: str) -> str:
        if " " in name or "-" in name:
            raise ValueError(f"Zone name '{name}' contains invalid character")
        return name


class ConnectionConfig(BaseModel):
    zone_a: str
    zone_b: str
    max_link_capacity: int = Field(gt=0, default=1)
    
    @model_validator(mode='after')
    def check_zones(self) -> 'ConnectionConfig':
        if self.zone_a == self.zone_b:
            raise ValueError(f"Connection '{self.zone_a}-{self.zone_b}'"
                             f"connects a zone to itself")
        return self


class MapConfig(BaseModel):
    drone_amount: int = Field(gt=0)
    zones: dict[str, ZoneConfig]
    connections: list[ConnectionConfig]
    start_hub: str
    end_hub: str
    

class MapParser:
    def __init__(
        self,
        file_path: str,
    ) -> None:
        self._path = file_path
        self._drone_amount: int | None = None
        self._zones: dict[str, ZoneConfig] = {}
        self._connections: list[ConnectionConfig] = []
        self._start_hub: str | None = None
        self._end_hub: str | None = None
        
    def read_lines(self) -> list[str]:
        try:
            with open(self._path) as f:
                data = f.read()
        except (OSError, UnicodeDecodeError) as e:
            raise ParseError(f"Can't open file: {self._path}") from e
        lines = data.splitlines()
        return lines
    
    def check_map(self) -> 'MapConfig':
        lines = self.read_lines()
        for line_number, line in enumerate(lines, start=1):
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            try:
                key, value = line.split(":", 1)
            except ValueError:
                raise ParseError(f'Line {line_number} missing ":" in "{line}"') from None
            key = key.strip()
            value = value.strip()
            if self._drone_amount is None and key != "nb_drones":
                raise ParseError(f"Line {line_number}: expected 'nb_drones:"
                                 f" <number>' as first line, got '{line}'")
            if key == "nb_drones":
                self.parse_nb_drones(line_number, value)
                
                
    def parse_nb_drones(self, line_number: int, value: str) -> None:
        if self._drone_amount is not None:
            raise ParseError(f"Line {line_number}: duplicate 'nb_drones':"
                             f" definition (already set to {self._drone_amount})")
        try:
            amount = int(value)
        except ValueError:
            raise ParseError(f"Line {line_number}; Invalid drone amount"
                             f" '{value}', expected a positive integer")
        if amount < 1:
            raise ParseError(f"Line {line_number}: Drone amount cannot be 0 or negative")
        self._drone_amount = amount