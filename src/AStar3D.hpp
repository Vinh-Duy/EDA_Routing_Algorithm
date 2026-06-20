#ifndef ASTAR_3D_HPP
#define ASTAR_3D_HPP

#include "IRouter3D.hpp"
#include <vector>
#include <queue>
#include <cmath>
#include <string>

struct Node3D {
    Point3D p;
    int g, f;
    bool operator>(const Node3D& other) const { return f > other.f; }
};

class AStar3D : public IRouter3D {
private:
    const int VIA_COST = 5; // Chi phí đục lỗ xuyên tầng (thường cao hơn đi ngang)

    int getHeuristic(Point3D a, Point3D b) {
        return std::abs(a.x - b.x) + std::abs(a.y - b.y) + (std::abs(a.z - b.z) * VIA_COST);
    }

public:
    bool route(std::vector<std::vector<std::vector<std::string>>>& grid, Point3D src, Point3D dst, std::string symbol, std::vector<Point3D>& path) override {
        int layers = grid.size();
        int rows = grid[0].size();
        int cols = grid[0][0].size();

        std::priority_queue<Node3D, std::vector<Node3D>, std::greater<Node3D>> pq;
        std::vector<std::vector<std::vector<int>>> gScore(layers, std::vector<std::vector<int>>(rows, std::vector<int>(cols, 1e9)));
        std::vector<std::vector<std::vector<Point3D>>> parent(layers, std::vector<std::vector<Point3D>>(rows, std::vector<Point3D>(cols, {-1, -1, -1})));

        gScore[src.z][src.x][src.y] = 0;
        pq.push({src, 0, getHeuristic(src, dst)});

        int dz[] = {0, 0, 0, 0, -1, 1};
        int dx[] = {-1, 1, 0, 0, 0, 0};
        int dy[] = {0, 0, -1, 1, 0, 0};

        while (!pq.empty()) {
            Node3D curr = pq.top(); pq.pop();

            if (curr.p.z == dst.z && curr.p.x == dst.x && curr.p.y == dst.y) {
                Point3D cp = parent[dst.z][dst.x][dst.y];
                path.push_back(dst); // Lưu điểm đích
                while (!(cp.z == src.z && cp.x == src.x && cp.y == src.y)) {
                    path.push_back(cp); // Lưu các điểm trên đường đi

                    if (cp.z != parent[cp.z][cp.x][cp.y].z) {
                        grid[cp.z][cp.x][cp.y] = "V"; 
                    } else {
                        grid[cp.z][cp.x][cp.y] = symbol;
                    }
                    cp = parent[cp.z][cp.x][cp.y];
                }
                path.push_back(src); // Lưu điểm xuất phát
                return true;
            }

            for (int i = 0; i < 6; i++) {
                int nz = curr.p.z + dz[i];
                int nx = curr.p.x + dx[i];
                int ny = curr.p.y + dy[i];

                if (nz >= 0 && nz < layers && nx >= 0 && nx < rows && ny >= 0 && ny < cols) {
                    if (grid[nz][nx][ny] == "." || (nz == dst.z && nx == dst.x && ny == dst.y)) {

                        // Tính cost: Nếu thay đổi Z (i >= 4) thì cộng VIA_COST, ngược lại cộng 1
                        int moveCost = (i >= 4) ? VIA_COST : 1; 
                        int nextG = curr.g + moveCost;

                        if (nextG < gScore[nz][nx][ny]) {
                            gScore[nz][nx][ny] = nextG;
                            parent[nz][nx][ny] = curr.p;
                            pq.push({{nz, nx, ny}, nextG, nextG + getHeuristic({nz, nx, ny}, dst)});
                        }
                    }
                }
            }
        }
        return false;
    }
};

#endif