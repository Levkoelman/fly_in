#!/usr/bin/env python3

from read_map import MapParser, ParseError
from graph import Graph
from solve_path import Planner, PlanningError
from output import OutputFormatter, ColorPalette
import sys


def main() -> None:
    parser = MapParser(sys.argv[1])
    try:
        map_config = parser.check_map()
        graph = Graph(map_config)
        planner = Planner(graph)
        plans = planner.plan_all()
        colors = ColorPalette()
        output = OutputFormatter(graph, plans, colors)
        output.write_output()
    except (ParseError, PlanningError) as e:
        print(e)


if __name__ == "__main__":
    main()
