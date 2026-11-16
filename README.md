*This project has been created as part of the 42 curriculum by lekoelma*

# Description

Fly-in routes a fleet of drones from a start zone to an end zone through a network of connected zones, in as few simulation turns as possible. The map is read from a text file and describes the zones (with coordinates, a type, a color and a capacity) and the connections between them (each with its own capacity).

Rules;

* a zone can hold only max_drones at once (the start and end zones are umlimited);
* a connection can carry only max_link_capacity drones per turn;
* entering a restricted zone takes 2 turns, and a drone may never stop halfway;
* blocked zones can never be entered;
* priority zones cost 1 turn but are preferred over equally fast alternatives.

The program parses the map, plans a conflict-free route for every drone and prints one line per turn listing every movement, for example D1-roof1 D2-corridorA.

# Instructions
Requirements: Python 3.10 or newer.

```bash
make install							Install dependencies(pydantic, flake8, mypy)
make run								run on the default map
make run MAP=path/to/map.txt			run on anothe map
make debug MAP=path/to/map.txt  		run under pdb
make lint								flake8 + mypy with the required flags
make lint-strict						flake8 + mypy --strict
make clean								remove casches
```
Invalid map files ar rejected with a message naming the line and the cause, for example "line 12: duplicate zone name 'roof1'".

# Project structure
| File 		    | Contents																    |	
|---------------|---------------------------------------------------------------------------|
| read_map.py   | MapParser and the pydancit models ZoneConfig, ConnectionConfig, MapConfig |
| graph.py      | Graph (adjacency list, zone and connection lookups) and Edge              |
| solve_path.py | Pathfinder, ReservationTable and Planner                                  |
| output.py     | OutputFormatter and ColorPalette                                          |

# Algorithm

## Parsing

The map is parsed in two layers. MapParser splits each line into its parts (type, name, coordinats, metadata between brackets) and checks everything that needs the whole file: nb_drones comes first, zone names are unique, ther is exactly one start and one end, connections only refer to known zones and are not duplicated (a-b and b-a count as the same). The pydantic models then validate each value: integer coordinates, a valid zone type, positive capacities, no dash or space in a name. Pydantic errors are turned into a ParseError with the line number.

## Graph

Graph build an adjacency list: for each zone, the edges to its neighbours. Each connection becomes two directed edges that share the same connection object, so its capacity is looked up in one place. The graph also answers the questions the planners needs: the cost of entering a zone, wheter a zone is blocked or priority, and which connection links two zones.

## Planning: prioritized planning over space and time

Drones are planned one after another. A ReservationTable records, for every turn, how many drones are in each zone and on each connection. For each drone, Pathfinder.find_timed_path runs Dijkstra over positions(zone, turn) instead of zones alone. From a position a drone can:
1. wait in its zone, if the zone has room in the next turn;
2. move to a normal or priority neighbour, if that zone and the connection have room in the next turn;
3. move to a restricted neighbour, if the connection has room in both of the next two turns and the zone has room on arrival. This is checked before departing, so a drone never gets stuk on a connection.

Because a position includes the turn, the cost is simply the arrival turn, and the firest time the end is taken from the priority queue is the earliest possible arrival. Ties are broken by the number of priority zones on the route. The chosen plan is then reserverd , and the next drone plans around it. 

The key difference from planning a fixed route and letting drones queue behind each other: each drone chooses its route knowing when the earlier drones will be where. If a zone or connection is busy at the moment a drone would nded it, it can take another route instead of waiting. On The Impossible Dream this makes consecutive drones alternate between two restricted branches, keeping one drone per turn moving through the single-file entrance.

The search bounded by max_turn = (drones + 1) x zones x 2. This is always enough: even if every drone waited in the start until the previous one had arrived, all would finish within it. Before planning an ordinary Dijkstra on the empty map checks that the end is reachable at all.

Limitation: drones planned earliers never give way to later ones, so the result is not guaranteed ooptimal on every map. On the provided maps this did not cost any turns.

# Visual Representation

The output uses ANSI colors in the terminal. Each zone name is printed in the color given in the map, so a reader can follow drones through the network at a glance and recognise zones (for example the gold priority zones or the dark_red restricted ones) without looking them up. A drone on its way to a restricted zone is shown on the connection, with both zone names in ther own color. If a color name is not supported or a zone does not have a color, the zone is printed uncolored, so an unknown color never crashes the program

# Recourses
* dijkstra: https://www.geeksforgeeks.org/dsa/dijkstras-shortest-path-algorithm-greedy-algo-7/
* heapq: https://www.w3schools.com/python/ref_module_heapq.asp
* dictionary get() method: https://www.w3schools.com/python/ref_module_heapq.asp
* string partition method: https://www.w3schools.com/python/ref_string_partition.asp
* dictionary setdefault() method: https://www.w3schools.com/python/ref_dictionary_setdefault.asp
* classvar: https://typing.python.org/en/latest/spec/class-compat.html
* text coloring: - https://stackoverflow.com/questions/287871/how-do-i-print-colored-text-to-the-terminal
* ANSI color codes: https://jakob-bagterp.github.io/colorist-for-python/ansi-escape-codes/introduction/

# Use of AI

I used Claude (Antrophic) as a tutor for some parts of the project. Al code was written by my. AI was used to:
- Explain concepts: heapq, dijkstra, get() method, output_coloring
- Review the code: it pointed out bugs and gave hitns, which I fixed myself 