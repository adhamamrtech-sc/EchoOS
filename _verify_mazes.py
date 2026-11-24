"""Independent check of greedy_bfs.py and astar.py on given + similar mazes."""
import heapq
import importlib.util
import os
import tempfile
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
MOVES = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = [l.rstrip("\n").rstrip("\r") for l in f]
    while lines and lines[-1] == "":
        lines.pop()
    w = max(len(r) for r in lines)
    maze = [list(r.ljust(w, " ")) for r in lines]
    A = B = None
    for i, row in enumerate(maze):
        for j, c in enumerate(row):
            if c == "A":
                A = (i, j)
            if c == "B":
                B = (i, j)
    return maze, A, B, w


def walkable(maze, w, p):
    x, y = p
    return 0 <= x < len(maze) and 0 <= y < w and maze[x][y] != "#"


def bfs_shortest(maze, A, B, w):
    q = deque([A])
    parent = {A: None}
    while q:
        cur = q.popleft()
        if cur == B:
            break
        x, y = cur
        for dx, dy in MOVES:
            n = (x + dx, y + dy)
            if n in parent or not walkable(maze, w, n):
                continue
            parent[n] = cur
            q.append(n)
    if B not in parent:
        return None
    path = []
    p = B
    while p is not None:
        path.append(p)
        p = parent[p]
    path.reverse()
    return path


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def capture_solve(mod, maze_path):
    maze, A, B, w = load(maze_path)
    # Re-run internal logic by parsing printed output is fragile.
    # Instead call the same search by monkeypatching print and reconstructing
    # from the printed * cells plus A/B.
    import io, sys
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        mod.solve(maze_path)
    finally:
        sys.stdout = old
    out = buf.getvalue().rstrip("\n")
    grid = [list(row) for row in out.splitlines()]
    stars = []
    a = b = None
    for i, row in enumerate(grid):
        for j, c in enumerate(row):
            if c == "*":
                stars.append((i, j))
            if c == "A":
                a = (i, j)
            if c == "B":
                b = (i, j)
    # Reconstruct path order using 4-neighbor chain A -> * -> B
    path = [a]
    used = set()
    cur = a
    cells = set(stars) | {b}
    while cur != b:
        x, y = cur
        nxts = []
        for dx, dy in MOVES:
            n = (x + dx, y + dy)
            if n in cells and n not in used:
                nxts.append(n)
        if len(nxts) != 1:
            # path might branch visually if * is only path; allow 1 unused neighbor
            if not nxts:
                raise AssertionError("broken printed path")
            # pick neighbor closest to B manhattan
            nxts.sort(key=lambda p: abs(p[0] - b[0]) + abs(p[1] - b[1]))
        nxt = nxts[0]
        used.add(nxt)
        path.append(nxt)
        cur = nxt
        if len(path) > 10000:
            raise AssertionError("loop in printed path")
    return path, out, A, B, maze, w


def check_path(maze, w, A, B, path, name):
    assert path[0] == A, f"{name}: path must start at A"
    assert path[-1] == B, f"{name}: path must end at B"
    for p in path:
        assert walkable(maze, w, p), f"{name}: went through wall/out at {p}"
        ch = maze[p[0]][p[1]]
        assert ch != "#", f"{name}: wall"
    for p1, p2 in zip(path, path[1:]):
        assert abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) == 1, f"{name}: not 4-adj {p1}->{p2}"


def write_maze(text):
    fd, path = tempfile.mkstemp(suffix=".txt", text=True)
    os.close(fd)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


greedy = load_module("greedy_bfs", os.path.join(HERE, "greedy_bfs.py"))
astar = load_module("astar", os.path.join(HERE, "astar.py"))

cases = {
    "maze1": os.path.join(HERE, "maze1.txt"),
    "maze2": os.path.join(HERE, "maze2.txt"),
    "maze3": os.path.join(HERE, "maze3.txt"),
    "dl_maze1": r"C:\Users\dell\Downloads\maze1.txt",
    "dl_maze2": r"C:\Users\dell\Downloads\maze2.txt",
    "dl_maze3": r"C:\Users\dell\Downloads\maze3.txt",
}

# Similar mazes
cases["open"] = write_maze("A   B\n")
cases["crlf"] = write_maze("A #\r\n  #\r\n  B\r\n")
cases["uneven"] = write_maze("A\n  #\n B\n")
cases["deadend"] = write_maze(
    "A     #\n##### #\n      B\n"
)
cases["wide"] = write_maze(
    "A                B\n# ################\n#                 \n##################\n"
)
cases["detour"] = write_maze("A########B\n          \n##########\n")

ok = 0
fail = 0
for name, path in cases.items():
    maze, A, B, w = load(path)
    shortest = bfs_shortest(maze, A, B, w)
    assert A and B, f"{name}: missing A/B"
    assert shortest is not None, f"{name}: maze has no path (test data bug)"
    opt = len(shortest) - 1
    for algo, mod in (("Greedy", greedy), ("A*", astar)):
        try:
            path_cells, out, A2, B2, maze2, w2 = capture_solve(mod, path)
            check_path(maze, w, A, B, path_cells, f"{name}/{algo}")
            steps = len(path_cells) - 1
            extra = ""
            if algo == "A*":
                assert steps == opt, f"{name}/A*: {steps} != optimal {opt}"
                extra = f" optimal={opt}"
            else:
                extra = f" (opt={opt})"
            print(f"OK  {name:10} {algo:6} steps={steps}{extra}")
            ok += 1
        except Exception as e:
            print(f"FAIL {name:10} {algo:6} {e}")
            fail += 1

print(f"\n{ok} passed, {fail} failed")
raise SystemExit(1 if fail else 0)
