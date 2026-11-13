from graph import Graph
import heapq
Cost = tuple[int, int]
Position = tuple[str, int]


class PlanningError(Exception):
    """Raised when an Error occurs during planning"""


class ReservationTable:
    """Tracks which zones and connections are claimen in which turn"""

    def __init__(self, graph: Graph) -> None:
        """Create an empty table for the given graph.

        Args:
            graph: The graph uses to look up capacities.
        """
        self._graph: Graph = graph
        self._zone_usage: dict[tuple[str, int], int] = {}
        self._link_usage: dict[tuple[frozenset[str], int], int] = {}

    def zone_has_room(self, zone: str, turn: int) -> bool:
        """Return wheter a zone can tacke on more drone in a turn.

        The start and end zones always have room.

        Args:
            zone: Name of the zone.
            turn: The turn to check.
        """
        if zone == self._graph.start or zone == self._graph.end:
            return True
        reserved_drones = self._zone_usage.get((zone, turn), 0)
        max_drones = self._graph.zone(zone).max_drones
        return (reserved_drones < max_drones)

    def link_has_room(self, zone_a: str, zone_b: str, turn: int) -> bool:
        """Return wheter a connection can take one more drone in a turn.

        Args:
            zone_a: Name of one end of the connection.
            zone_b: Name of the other end.
            turn: The turn to check.
        """
        link = frozenset({zone_a, zone_b})
        reserved_drones = self._link_usage.get((link, turn), 0)
        max_drones = self._graph.connection(zone_a, zone_b).max_link_capacity
        return (reserved_drones < max_drones)

    def reserve_zone(self, zone: str, turn: int) -> None:
        """Claim one place in a zone for a turn.

        Args:
            zone: The name of the zone.
            turn: The turn to claim
        """
        reserved_drones = self._zone_usage.get((zone, turn), 0) + 1
        self._zone_usage[(zone, turn)] = reserved_drones

    def reserve_link(self, zone_a: str, zone_b: str, turn: int) -> None:
        """Claim one place on a connection for a turn.

        Args:
            zone_a: Name of one end of the connection.
            zone_b: Name of the other end.
            turn: The turn to claim.
        """
        link = frozenset({zone_a, zone_b})
        reserved_drones = self._link_usage.get((link, turn), 0) + 1
        self._link_usage[(link, turn)] = reserved_drones

    def reserve_plan(self, plan: list[Position]) -> None:
        """Claim every zone and connection a drone's plan uses.

        Waiting claims the zone; a noral move claims the zone and the
        connection on arrival; a restricted move clais the connetion for
        both turns and the zone on arrival.

        Args:
            plan: The drone's (zone, turn) positions from start tot end
        """
        pairs = zip(plan, plan[1:])
        for pair in pairs:
            previous, current = pair
            prev_zone, prev_turn = previous
            cur_zone, cur_turn = current
            if prev_zone == cur_zone:
                self.reserve_zone(cur_zone, cur_turn)
            elif (cur_turn - prev_turn) == 1:
                self.reserve_zone(cur_zone, cur_turn)
                self.reserve_link(prev_zone, cur_zone, cur_turn)
            elif (cur_turn - prev_turn) == 2:
                self.reserve_zone(cur_zone, cur_turn)
                self.reserve_link(prev_zone, cur_zone, prev_turn + 1)
                self.reserve_link(prev_zone, cur_zone, cur_turn)


class Planner:
    """Plans a route for every drone, one after another."""
    def __init__(self, graph: Graph) -> None:
        """Set up a planner with an empty reservation table.

        Args:
            graph: The graph to plan routes on.
        """
        self._graph = graph
        self._reservation_table: ReservationTable = ReservationTable(graph)
        self._pathfinder: Pathfinder = Pathfinder(graph)

    def plan_all(self) -> list[list[Position]]:
        """Plan every drone from start to end without capicity conflicts.

        Each drone gest the earliest plan that respects reservations of
        the drones planned before it, and its plan is then reserved.
        max_turn is a safe upper bound: even if every drone waited for the
        previous one to arrive, all would finish within it.

        Returns:
            One plan per drone, in drone order

        Raises:
            PlanningError: If the end cannot be reached from the start.
        """
        max_turn = (
            (self._graph.drone_amount + 1) * (self._graph.zone_amount) * 2
        )
        plans: list[list[Position]] = []
        if self._pathfinder.find_shortest_path(
            self._graph.start,
            self._graph.end
        ) is None:
            raise PlanningError(
                f"No route possible from {self._graph.start}"
                f" to {self._graph.end}")
        for i in range(self._graph.drone_amount):
            plan = self._pathfinder.find_timed_path(
                self._graph.start,
                self._graph.end,
                self._reservation_table,
                max_turn)
            if plan is None:
                raise PlanningError(
                    f"No route found for drone {i + 1} from"
                    f" '{self._graph.start}' to '{self._graph.end}'")
            plans.append(plan)
            self._reservation_table.reserve_plan(plan)
        return plans


class Pathfinder:
    """Finds routes for drones through the zone graph."""
    def __init__(self, graph: Graph) -> None:
        """Create ap athfinder for a graph.

        Args:
            graph: The graph to search in.
        """
        self._graph: Graph = graph

    def find_shortest_path(self, start: str, end: str) -> list[str] | None:
        """Find the fastest route on an empty map, ignoring other drones.

        Uses Dijkstra with (turns, -priority zones) as cost, so among
        equally fast routes the one throuth more priority zones wins.
        Blocked zones are skipped.

        Args:
            start: Name of the start zone.
            end: Name of the end zone.

        Returns:
            The zone names from start to end, or None if end is unreachable
        """
        best_cost: dict[str, Cost] = {start: (0, 0)}
        came_from: dict[str, str] = {}
        queue: list[tuple[Cost, str]] = []
        heapq.heappush(queue, (best_cost[start], start))
        while queue:
            cost, name = heapq.heappop(queue)
            if name == end:
                break
            if cost > best_cost[name]:
                continue
            for edge in self._graph.neighbours(name):
                if self._graph.is_blocked(edge.target):
                    continue
                turns, priority = cost
                new_turns = turns + self._graph.move_cost(edge.target)
                if self._graph.is_priority(edge.target):
                    priority -= 1
                new_cost = (new_turns, priority)
                if (edge.target not in best_cost
                        or new_cost < best_cost[edge.target]):
                    best_cost[edge.target] = new_cost
                    came_from[edge.target] = name
                    heapq.heappush(
                        queue,
                        (best_cost[edge.target], edge.target))
        if end not in best_cost:
            return None
        path: list[str] = [end]
        current = end
        while current != start:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    def find_timed_path(
        self,
        start: str,
        end: str,
        reservation_table: ReservationTable,
        max_turn: int
    ) -> list[Position] | None:
        """Find the earliest-arriving plan for one drone.

        Runs Dijkstra over (zone, turn) positions. From each position a
        drone can waint, move to a normal or priority neigbour (arrives next
        turn), or move to a restricted neighbour (one turn on the connection,
        arrives two turns later). An option is only taken if the reservation
        table has room for it. Ties in an arrival turn go to the plan trough
        more priority zones.

        Args:
            start: Name fot the start zone.
            end: Name of the end zone.
            reservation_table: Places already claimed by earlier drones.
            max_turn: Turn after which the search gives up.

        Returns:
            The (zone, turn) positions from start to end, or None if end is
            not reached within a max_turn. A missing turn between two
            positions means the drone was on a connection that turn.
        """
        visited: set[Position] = set()
        came_from: dict[Position, Position] = {}
        queue: list[tuple[int, int, str, Position | None]] = []
        heapq.heappush(queue, (0, 0, start, None))
        while queue:
            turn, priority, zone, last_position = heapq.heappop(queue)
            if (zone, turn) in visited:
                continue
            visited.add((zone, turn))
            if last_position is not None:
                came_from[(zone, turn)] = last_position
            if zone == end:
                path: list[Position] = [(end, turn)]
                current = (end, turn)
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return path
            if turn >= max_turn:
                continue
            if reservation_table.zone_has_room(zone, turn + 1):
                heapq.heappush(queue, (turn + 1, priority, zone, (zone, turn)))
            for edge in self._graph.neighbours(zone):
                target = edge.target
                if self._graph.is_blocked(target):
                    continue
                if self._graph.move_cost(target) == 1:
                    if (reservation_table.zone_has_room(target, turn + 1)
                            and reservation_table.link_has_room(
                                zone, target, turn + 1)):
                        new_priority = priority
                        if self._graph.is_priority(target):
                            new_priority -= 1
                        heapq.heappush(
                            queue,
                            (turn + 1, new_priority, target, (zone, turn)))
                elif self._graph.move_cost(edge.target) == 2:
                    if (reservation_table.link_has_room(zone, target, turn + 1)
                        and reservation_table.link_has_room(
                            zone, target, turn + 2)
                        and reservation_table.zone_has_room(
                            target, turn + 2)):
                        heapq.heappush(
                            queue, (turn + 2, priority, target, (zone, turn))
                            )
        return None
