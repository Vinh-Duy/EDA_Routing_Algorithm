#ifndef BFS_2D_HPP
#define BFS_2D_HPP

#include "IRouter.hpp"
#include <queue>

class BFS2D : public IRouter {
public:
    bool route(std::vector<std::vector<std::string>>& grid, Point src, Point dst, std::string symbol) override {
        int rows = grid.size(), cols = grid[0].size();
        std::vector<std::vector<bool>> visited(rows, std::vector<bool>(cols, false));
        std::vector<std::vector<Point>> parent(rows, std::vector<Point>(cols, {-1, -1}));
        
        std::queue<Point> q;
        q.push(src);
        visited[src.x][src.y] = true;

        int dx[] = {-1, 1, 0, 0};
        int dy[] = {0, 0, -1, 1};
        bool found = false;

        while (!q.empty()) {
            Point curr = q.front(); q.pop();

            if (curr.x == dst.x && curr.y == dst.y) {
                found = true; break;
            }

            for (int i = 0; i < 4; i++) {
                int nx = curr.x + dx[i], ny = curr.y + dy[i];
                if (nx >= 0 && nx < rows && ny >= 0 && ny < cols && !visited[nx][ny]) {
                    if (grid[nx][ny] == "." || (nx == dst.x && ny == dst.y)) {
                        visited[nx][ny] = true;
                        parent[nx][ny] = curr;
                        q.push({nx, ny});
                    }
                }
            }
        }

        if (!found) return false;

        Point cp = parent[dst.x][dst.y];
        while (!(cp.x == src.x && cp.y == src.y)) {
            grid[cp.x][cp.y] = symbol;
            cp = parent[cp.x][cp.y];
        }
        return true;
    }
};

#endif