from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ValidationError
)
from enum import Enum
from typing import ClassVar


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
                             f" connects a zone to itself")
        return self


class MapConfig(BaseModel):
    drone_amount: int = Field(gt=0)
    zones: dict[str, ZoneConfig]
    connections: list[ConnectionConfig]
    start_hub: str
    end_hub: str


class MapParser:
    _ZONE_KEYS: ClassVar[frozenset[str]] = frozenset({
        "zone",
        "color",
        "max_drones"
    })
    _ZONE_SORTS: ClassVar[frozenset[str]] = frozenset({
        "hub",
        "start_hub",
        "end_hub"
    })
    _CONNECTION_KEYS: ClassVar[frozenset[str]] = frozenset({
        "max_link_capacity"
    })

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
        self._pairs: set[frozenset[str]] = set()

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
                raise ParseError(f'Line {line_number} missing'
                                 f' ":" in "{line}"') from None
            key = key.strip()
            value = value.strip()
            if self._drone_amount is None and key != "nb_drones":
                raise ParseError(f"Line {line_number}: expected 'nb_drones:"
                                 f" <number>' as first line, got '{line}'")
            if key == "nb_drones":
                self._parse_nb_drones(line_number, value)
            elif key in self._ZONE_SORTS:
                zone_config_dict = self._parse_zone(line_number, value)
                if zone_config_dict.name in self._zones:
                    raise ParseError(f"Line {line_number}: duplicate zone"
                                     f" name '{zone_config_dict.name}'")
                self._zones[zone_config_dict.name] = zone_config_dict
                if key == "start_hub":
                    if self._start_hub is not None:
                        raise ParseError(f"Line {line_number}: duplicate"
                                         f"'start_hub', already defined "
                                         f"as {self._start_hub}")
                    self._start_hub = zone_config_dict.name
                if key == "end_hub":
                    if self._end_hub is not None:
                        raise ParseError(f"Line {line_number}: duplicate "
                                         f"'end_hub', already defined as"
                                         f" {self._end_hub}")
                    self._end_hub = zone_config_dict.name
            elif key == "connection":
                connection = self._parse_connection(line_number, value)
                if (
                    connection.zone_a not in self._zones
                    or connection.zone_b not in self._zones
                ):
                    raise ParseError(f"Line {line_number}: Unknown zone in "
                                     f"'{connection.zone_a}-"
                                     f"{connection.zone_b}'")
                pair: frozenset[str] = frozenset({
                    connection.zone_a,
                    connection.zone_b
                    })
                if pair in self._pairs:
                    raise ParseError(f"Line {line_number}: duplicate"
                                     f"connection '{connection.zone_a}"
                                     f"-{connection.zone_b}'")
                self._pairs.add(pair)
                self._connections.append(connection)
            else:
                raise ParseError(f"Line {line_number}: Unknown line'"
                                 f"type '{key}'")
        if self._start_hub is None:
            raise ParseError(f"{self._path}: missing 'start_hub' definition")
        if self._end_hub is None:
            raise ParseError(f"{self._path}: missing 'end_hub' definition")
        if self._drone_amount is None:
            raise ParseError(f"{self._path}: missing 'drone_amount'"
                             f" definition")
        map_result = MapConfig(
            drone_amount=self._drone_amount,
            zones=self._zones,
            connections=self._connections,
            start_hub=self._start_hub,
            end_hub=self._end_hub
        )
        return map_result

    def _parse_nb_drones(self, line_number: int, value: str) -> None:
        if self._drone_amount is not None:
            raise ParseError(f"Line {line_number}: duplicate 'nb_drones':"
                             f" definition (already set to"
                             f" {self._drone_amount})")
        try:
            amount = int(value)
        except ValueError:
            raise ParseError(f"Line {line_number}: Invalid drone amount"
                             f" '{value}', expected a positive integer"
                             ) from None
        if amount < 1:
            raise ParseError(f"Line {line_number}: Drone amount cannot"
                             f" be 0 or negative")
        self._drone_amount = amount

    def _parse_zone(self, line_number: int, line: str) -> ZoneConfig:
        base, bracket, rest = line.partition("[")
        if "]" in base:
            raise ParseError(f"Line {line_number}: unexpected ']'"
                             f" before metadata")
        if not bracket:
            metadata = ""
        else:
            metadata = ""
            if not rest.endswith("]"):
                raise ParseError(f"Line {line_number}: expected closing ']'")
            metadata = rest[:-1]
            if "[" in metadata or "]" in metadata:
                raise ParseError(f"Line {line_number}: Unexpected"
                                 f" bracket in {metadata}")
        parts = base.split()
        if len(parts) != 3:
            raise ParseError(f"Line {line_number}: expected"
                             f" '<name> <x> <y>', got '{base}'")
        name, x_text, y_text = parts
        try:
            x = int(x_text)
            y = int(y_text)
        except ValueError:
            raise ParseError(f"Line {line_number}: Invalid coordinates"
                             f" '{x_text}' and '{y_text}' for zone"
                             f" '{name}', expected integers") from None
        metadata_dict = self._parse_metadata(line_number, metadata)
        for key in metadata_dict:
            if key not in self._ZONE_KEYS:
                raise ParseError(f"Line {line_number}: Unknown metadata key"
                                 f" '{key}' for zone, allowed:"
                                 f" {','.join(self._ZONE_KEYS)}")
        zone_dict: dict[str, str | int] = {"name": name, "x": x, "y": y}
        for key, value in metadata_dict.items():
            if key == "zone":
                zone_dict["zone_type"] = value
            else:
                zone_dict[key] = value
        try:
            return ZoneConfig.model_validate(zone_dict)
        except ValidationError as e:
            message = e.errors()[0]["msg"]
            raise ParseError(f"Line {line_number}: Invalid zone {name}:"
                             f" {message}") from None

    def _parse_connection(
        self,
        line_number: int,
        line: str
    ) -> ConnectionConfig:
        base, bracket, rest = line.partition("[")
        if "]" in base:
            raise ParseError(f"Line {line_number}: unexpected"
                             f" ']' before metadata")
        if not bracket:
            metadata = ""
        else:
            metadata = ""
            if not rest.endswith("]"):
                raise ParseError(f"Line {line_number}: expected closing ']'")
            metadata = rest[:-1]
            if "[" in metadata or "]" in metadata:
                raise ParseError(f"Line {line_number}:"
                                 f" Unexpected bracket in {metadata}")
        parts = base.split("-")
        if len(parts) != 2:
            raise ParseError(f"Line {line_number}: expected '<name1>-"
                             f"<name2>', got '{base}'")
        name1, name2 = parts
        name1 = name1.strip()
        name2 = name2.strip()
        if name1 == "" or name2 == "":
            raise ParseError(f"Line {line_number}: expected '<name1>"
                             f"-<name2>', got '{base}'")
        if " " in name1 or " " in name2:
            raise ParseError(f"Line {line_number}: invalid zone name"
                             f" in connection {name1}-{name2}.")
        metadata_dict = self._parse_metadata(line_number, metadata)
        for key in metadata_dict:
            if key not in self._CONNECTION_KEYS:
                raise ParseError(f"Line {line_number}: Unknown metadata key"
                                 f" '{key}' for connection, allowed:"
                                 f" {','.join(self._CONNECTION_KEYS)}")
        connection_dict: dict[str, str] = {"zone_a": name1, "zone_b": name2}
        for key, value in metadata_dict.items():
            connection_dict[key] = value
        try:
            return ConnectionConfig.model_validate(connection_dict)
        except ValidationError as e:
            message = e.errors()[0]["msg"]
            raise ParseError(f"Line {line_number}: Invalid connection"
                             f" {name1}-{name2}: {message}") from None

    @staticmethod
    def _parse_metadata(
        line_number: int,
        metadata_text: str
    ) -> dict[str, str]:
        metadata = metadata_text.split()
        result: dict[str, str] = {}
        for pair in metadata:
            key, sign, value = pair.partition("=")
            if sign != "=" or not key or not value or "=" in value:
                raise ParseError(f"Line {line_number}: invalid metadata"
                                 f" '{pair}', expected 'key=value'")
            if key in result:
                raise ParseError(f"Line {line_number}: duplicate"
                                 f" metadata key '{key}'")
            result[key] = value
        return result
