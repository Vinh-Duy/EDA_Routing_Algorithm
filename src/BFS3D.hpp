#ifndef BFS_3D_HPP
#define BFS_3D_HPP

#include "IRouter3D.hpp"
#include <queue>

class BFS3D : public IRouter3D {
public:
    bool route(std::vector<std::vector<std::vector<std::string>>>& grid, Point3D src, Point3D dst, std::string symbol, std::vector<Point3D>& path) override {
        int layers = grid.size();
        int rows = grid[0].size();
        int cols = grid[0][0].size();
        
        std::vector<std::vector<std::vector<bool>>> visited(layers, std::vector<std::vector<bool>>(rows, std::vector<bool>(cols, false)));
        std::vector<std::vector<std::vector<Point3D>>> parent(layers, std::vector<std::vector<Point3D>>(rows, std::vector<Point3D>(cols, {-1, -1, -1})));
        
        std::queue<Point3D> q;
        q.push(src);
        visited[src.z][src.x][src.y] = true;

        int dz[] = {0, 0, 0, 0, -1, 1};
        int dx[] = {-1, 1, 0, 0, 0, 0};
        int dy[] = {0, 0, -1, 1, 0, 0};
        
        bool found = false;

        while (!q.empty()) {
            Point3D curr = q.front(); q.pop();

            if (curr.z == dst.z && curr.x == dst.x && curr.y == dst.y) {
                found = true; break;
            }

            for (int i = 0; i < 6; i++) {
                int nz = curr.z + dz[i];
                int nx = curr.x + dx[i];
                int ny = curr.y + dy[i];
                
                if (nz >= 0 && nz < layers && nx >= 0 && nx < rows && ny >= 0 && ny < cols && !visited[nz][nx][ny]) {
                    if (grid[nz][nx][ny] == "." || (nz == dst.z && nx == dst.x && ny == dst.y)) {
                        visited[nz][nx][ny] = true;
                        parent[nz][nx][ny] = curr;
                        q.push({nz, nx, ny});
                    }
                }
            }
        }

        path.push_back(dst); // Lưu điểm đích

        Point3D cp = parent[dst.z][dst.x][dst.y];
        while (!(cp.z == src.z && cp.x == src.x && cp.y == src.y)) {
            path.push_back(cp); // Lưu các điểm trên đường đi
            // Nếu phát hiện nhảy layer (xuyên tầng), đánh dấu là VIA (V)
            if (cp.z != parent[cp.z][cp.x][cp.y].z) {
                grid[cp.z][cp.x][cp.y] = "V"; 
            } else {
                grid[cp.z][cp.x][cp.y] = symbol;
            }
            cp = parent[cp.z][cp.x][cp.y];
        }
        
        path.push_back(src); // 3. Lưu điểm xuất phát
        
        return true;
    }
};

#endif