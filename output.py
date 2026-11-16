from solve_path import Position
from graph import Graph
from typing import ClassVar


class ColorPalette:
    """Colors zone names with the colors from the map."""
    COLORS: ClassVar[dict[str, str]] = {
        "black": "\033[90m",
        "blue": "\033[34m",
        "brown": "\033[38;5;130m",
        "crimson": "\033[38;5;160m",
        "cyan": "\033[36m",
        "darkred": "\033[38;5;124m",
        "gold": "\033[38;5;220m",
        "green": "\033[32m",
        "lime": "\033[38;5;118m",
        "magenta": "\033[35m",
        "maroon": "\033[38;5;88m",
        "orange": "\033[38;5;208m",
        "purple": "\033[38;5;93m",
        "rainbow": "\033[95m",
        "red": "\033[31m",
        "violet": "\033[38;5;177m",
        "yellow": "\033[33m",
    }

    RESET: ClassVar[str] = "\033[0m"

    def colorize(self, zone: str, color: str | None) -> str:
        """Colors the zone_name to the color specified in the map.

        Unknown colors and zones without a color are left uncolored.

        Args:
            zone: The zone name to color.
            color: A color name from the map, or None.

        Returns:
            The text string, either with a new color or unchanged.
        """
        if color is None:
            return zone
        code = self.COLORS.get(color, "")
        if not code:
            return zone
        return f"{code}{zone}{self.RESET}"

    def color_connection(
        self,
        zone_a: str,
        color_a: str | None,
        zone_b: str,
        color_b: str | None
    ) -> str:
        """Colors two zones in a connection by calling colorize
        twice for both zones.

        Args:
            zone_a: The first zone of which to change the color.
            color_a: The color string to apply to zone_a.
            zone_b: The second zone of which to change the color.
            color_b: The color string to apply to zone_b.

        Returns:
            The connection as '<zone_a>-<zone_b>', each name colored.
        """
        colored_a = self.colorize(zone_a, color_a)
        colored_b = self.colorize(zone_b, color_b)
        return f"{colored_a}-{colored_b}"


class OutputFormatter:
    """Turns the drone plans into one line of movement per turn."""
    def __init__(
        self,
        graph: Graph,
        plans: list[list[Position]],
        color_palette: ColorPalette
    ) -> None:
        """Create a formatter for a set of plans.

        Args:
            graph: The graph used for zone colors and connection names.
            plans: One plan per drone, in drone order.
            color_palette: The palette used to color zone names.
        """
        self._graph = graph
        self._plans = plans
        self._color_palette = color_palette

    def collect_output(self) -> dict[int, list[str]]:
        """Collect every drone movement, grouped by turn.

        Waiting drones are left out. A drone moving to a restricted zone
        appears on the connection in the turn in between, and in the zone
        when it arrives.

        Returns:
            A dict from turn number to the movements in that turn, such
            as 'D1-roof1' or 'D2-roof1-tunnel'.
        """
        turns: dict[int, list[str]] = {}
        for i, plan in enumerate(self._plans, start=1):
            pairs = zip(plan, plan[1:])
            for pair in pairs:
                previous, current = pair
                prev_zone, prev_turn = previous
                cur_zone, cur_turn = current
                if prev_zone == cur_zone:
                    continue
                elif (cur_turn - prev_turn) == 1:
                    z_color = self._graph.zone(cur_zone).color
                    colored_z = self._color_palette.colorize(cur_zone, z_color)
                    turns.setdefault(cur_turn, []).append(f"D{i}-{colored_z}")
                elif (cur_turn - prev_turn == 2):
                    z_color = self._graph.zone(cur_zone).color
                    colored_z = self._color_palette.colorize(cur_zone, z_color)
                    connection = self._graph.connection(prev_zone, cur_zone)
                    color_a = self._graph.zone(connection.zone_a).color
                    color_b = self._graph.zone(connection.zone_b).color
                    colored_con = self._color_palette.color_connection(
                        connection.zone_a,
                        color_a,
                        connection.zone_b,
                        color_b)
                    turns.setdefault(
                        prev_turn + 1, []).append(f"D{i}-{colored_con}")
                    turns.setdefault(cur_turn, []).append(f"D{i}-{colored_z}")
        return turns

    def write_output(self) -> None:
        """Print one line of movements per turn, from turn 1 to the end.

        A turn in which no drone moves is printed as an empty line.
        """
        turns = self.collect_output()
        for turn in range(1, max(turns) + 1):
            print(" ".join(turns.get(turn, [])))
