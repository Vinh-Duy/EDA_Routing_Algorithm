#ifndef ASTAR_2D_HPP
#define ASTAR_2D_HPP

#include "IRouter2D.hpp" 
#include <vector>
#include <queue>
#include <cmath>
#include <string>

struct Node {
    Point p;
    int g, f;
    bool operator>(const Node& other) const { return f > other.f; }
};

class AStar2D : public IRouter2D {
private:
    int getManhattan(Point a, Point b) {
        return std::abs(a.x - b.x) + std::abs(a.y - b.y);
    }

public:
    bool route(std::vector<std::vector<std::string>>& grid, Point src, Point dst, std::string symbol) override {
        if (grid.empty() || grid[0].empty()) return false;
        int rows = static_cast<int>(grid.size()), cols = static_cast<int>(grid[0].size());
        for (const auto& row : grid) if (static_cast<int>(row.size()) != cols) return false;
        auto legal = [&](Point p) { return p.x >= 0 && p.x < rows && p.y >= 0 && p.y < cols; };
        if (!legal(src) || !legal(dst) || grid[src.x][src.y] == "#" || grid[dst.x][dst.y] == "#") return false;
        if (src.x == dst.x && src.y == dst.y) return true;
        std::priority_queue<Node, std::vector<Node>, std::greater<Node>> pq;
        std::vector<std::vector<int>> gScore(rows, std::vector<int>(cols, 1e9));
        std::vector<std::vector<Point>> parent(rows, std::vector<Point>(cols, {-1, -1}));

        gScore[src.x][src.y] = 0;
        pq.push({src, 0, getManhattan(src, dst)});

        int dx[] = {-1, 1, 0, 0};
        int dy[] = {0, 0, -1, 1};

        while (!pq.empty()) {
            Node curr = pq.top(); pq.pop();
            if (curr.g != gScore[curr.p.x][curr.p.y]) continue;

            if (curr.p.x == dst.x && curr.p.y == dst.y) {
                Point cp = parent[dst.x][dst.y];
                while (!(cp.x == src.x && cp.y == src.y)) {
                    grid[cp.x][cp.y] = symbol;
                    cp = parent[cp.x][cp.y];
                }
                return true;
            }

            for (int i = 0; i < 4; i++) {
                int nx = curr.p.x + dx[i], ny = curr.p.y + dy[i];
                if (nx >= 0 && nx < rows && ny >= 0 && ny < cols && (grid[nx][ny] == "." || (nx == dst.x && ny == dst.y))) {
                    int nextG = curr.g + 1;
                    if (nextG < gScore[nx][ny]) {
                        gScore[nx][ny] = nextG;
                        parent[nx][ny] = curr.p;
                        pq.push({{nx, ny}, nextG, nextG + getManhattan({nx, ny}, dst)});
                    }
                }
            }
        }
        return false;
    }
};

#endif
