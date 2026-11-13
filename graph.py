from dataclasses import dataclass
from read_map import ConnectionConfig, MapConfig, ZoneConfig, ZoneType


@dataclass(frozen=True)
class Edge:
    """A directed link from one zone to a
    neighbouring zone through a connection."""
    target: str
    connection: ConnectionConfig


class Graph:
    """Adjacency representation of the zone network used for pathfinding.

    Built once from a parsed map. Gives read-only access to zones,
    neighbours, movement costs and the start and end of the map.
    """

    def __init__(self, map_config: MapConfig) -> None:
        """Build the graph from a parsed map.

        Args:
            map_config: The validated map produced by the parser.
        """
        self._zones: dict[str, ZoneConfig] = map_config.zones
        self._start: str = map_config.start_hub
        self._end: str = map_config.end_hub
        self._amount: int = map_config.drone_amount
        self._neighbours: dict[str, list[Edge]] = {}
        self._connections: dict[frozenset[str], ConnectionConfig] = {}
        self._build_neighbours(map_config.connections)

    def _build_neighbours(self, connections: list[ConnectionConfig]) -> None:
        """Fill the adjacency list with one edge per direction per connection.

        Both edges of a connection share the same ConnectionConfig object,
        so link usage can later be tracked in one place.

        Args:
            connections: All connections of the map.
        """
        for zone in self._zones:
            self._neighbours[zone] = []
        for connection in connections:
            edge_ab = Edge(target=connection.zone_b, connection=connection)
            edge_ba = Edge(target=connection.zone_a, connection=connection)
            self._neighbours[connection.zone_a].append(edge_ab)
            self._neighbours[connection.zone_b].append(edge_ba)
            key = frozenset({connection.zone_a, connection.zone_b})
            self._connections[key] = connection

    def neighbours(self, name: str) -> list[Edge]:
        """Return the outgoing edges of a zone.

        Args:
            name: Name of the zone.

        Returns:
            A copy of the list of edges leaving this zone.
        """
        return list(self._neighbours[name])

    def zone(self, name: str) -> ZoneConfig:
        """Return the configuration of a zone.

        Args:
            name: Name of the zone.

        Returns:
            The zone's configuration (type, capacity, color, coordinates).
        """
        return self._zones[name]

    @property
    def start(self) -> str:
        """Name of the start zone."""
        return self._start

    @property
    def end(self) -> str:
        """Name of the end zone."""
        return self._end

    @property
    def drone_amount(self) -> int:
        """Number of drones that must be routed from start to end."""
        return self._amount

    @property
    def zone_amount(self) -> int:
        """Number of zones"""
        return len(self._zones)

    def connection(self, zone_a: str, zone_b: str) -> ConnectionConfig:
        """Return the connection between two zones.

        The order the zones does not matter (zone_a, zone_b) and
        (zone_b, zone_a) return the same connection.

        Args:
            zone_a: Name of one zone.
            zone_b: Name of the other zone.

        Returns:
            The connection linking the two zones.
        """
        key = frozenset({zone_a, zone_b})
        return self._connections[key]

    def move_cost(self, name: str) -> int:
        """Return the number of turns needed to enter a zone.

        Args:
            name: Name of the destination zone.

        Return:
            1 for normal and priority zones, 2 for restricted zones.

        Raises:
            ValueError: If the zone is blockec and cannot be entered.
        """
        zonetype = self._zones[name].zone_type
        if zonetype in (ZoneType.NORMAL, ZoneType.PRIORITY):
            return 1
        elif zonetype == ZoneType.RESTRICTED:
            return 2
        else:
            raise ValueError(f"Zone '{name}' is blocked"
                             f" and cannot be entered.")

    def is_blocked(self, name: str) -> bool:
        """Return whether a zone is blocked and may not be entered."""
        return self._zones[name].zone_type == ZoneType.BLOCKED

    def is_priority(self, name: str) -> bool:
        """Return whether a zone is a priority zone."""
        return self._zones[name].zone_type == ZoneType.PRIORITY
