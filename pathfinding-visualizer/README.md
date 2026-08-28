# Pathfinding Visualizer

Five graph-search algorithms animated on an interactive grid.

**Live demo:** [pathfinding.spbdatascience.org](https://pathfinding.spbdatascience.org)

## Features

- A* (Manhattan heuristic), Dijkstra, Greedy Best-First, BFS, and DFS
- Draw walls and weighted terrain (cost 5); drag the start and target nodes, with instant re-search after a run
- Maze generation by recursive division
- Per-run stats: nodes visited, path length, path cost, and compute time
- Each algorithm is labeled with whether it guarantees the shortest path, and the visualization makes the difference obvious

## Implementation notes

All algorithms run client-side in vanilla JavaScript. The weighted searches share one priority-queue implementation (a binary min-heap) and differ only in their priority function: `g` for Dijkstra, `h` for Greedy, `g + h` for A*, which makes it clear that these three are the same algorithm with different priority functions. Flask only serves the page, keeping deployment identical to the club's other projects.

## Stack

JavaScript (no dependencies), Flask

## Local development

```bash
pip install flask
python app.py
```
