#!/usr/bin/env python3

from read_map import MapParser, ParseError
from graph import Graph
from solve_path import Planner, PlanningError


def main() -> None:
    parser = MapParser("02_circular_loop.txt")
    try:
        map_config = parser.check_map()
        graph = Graph(map_config)
        planner = Planner(graph)
        plans = planner.plan_all()
        for i, plan in enumerate(plans):
            print(f"Drone {i + 1}: {plan}")
    except (ParseError, PlanningError) as e:
        print(e)


if __name__ == "__main__":
    main()
