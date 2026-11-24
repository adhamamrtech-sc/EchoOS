import heapq, sys

def solve(path):
    maze = [list(l.rstrip("\n")) for l in open(path)]
    w = max(len(r) for r in maze)
    maze = [r + [" "] * (w - len(r)) for r in maze]
    A = B = None
    for i, r in enumerate(maze):
        for j, c in enumerate(r):
            if c == "A": A = (i, j)
            if c == "B": B = (i, j)
    h = lambda p: abs(p[0]-B[0]) + abs(p[1]-B[1])
    pq, seen, parent = [(h(A), A)], {A}, {}
    while pq:
        _, (x, y) = heapq.heappop(pq)
        if (x, y) == B:
            break
        for dx, dy in ((-1,0),(1,0),(0,-1),(0,1)):
            n = (x+dx, y+dy)
            if n in seen: continue
            if not (0 <= n[0] < len(maze) and 0 <= n[1] < w): continue
            if maze[n[0]][n[1]] == "#": continue
            seen.add(n); parent[n] = (x, y)
            heapq.heappush(pq, (h(n), n))
    p = B
    while p != A:
        maze[p[0]][p[1]] = "*"
        p = parent[p]
    maze[B[0]][B[1]] = "B"
    print("".join("".join(r)+"\n" for r in maze))

for f in (sys.argv[1:] or ["maze1.txt", "maze2.txt", "maze3.txt"]):
    solve(f)
