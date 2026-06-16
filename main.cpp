#include <iostream>
#include <vector>
#include <queue>
#include <fstream>
#include <chrono>
#include <string>
#include <map>

using namespace std;

enum CellState { EMPTY = 0, OBSTACLE = 1, START = 2, TARGET = 3, PATH = 4 };

struct Point { int x, y; };

struct Net {
    string name;
    string srcLabel;   // Kí hiệu nguồn (S1, S2)
    string dstLabel;   // Kí hiệu đích (T1, T2)
    Point src;         // Tọa độ nguồn
    Point dst;         // Tọa độ đích
};

void printGrid(const vector<vector<string>>& grid) {
    for (const auto& row : grid) {
        for (const string& cell : row) {
            cout << cell;
            for (int k = 0; k < 4 - cell.length(); k++) cout << " ";
        }
        cout << endl;
    }
}

bool routeNetBFS(vector<vector<string>>& grid, Net net, string pathSymbol) {
    int rows = grid.size();
    int cols = grid[0].size();
    
    vector<vector<bool>> visited(rows, vector<bool>(cols, false));
    vector<vector<Point>> parent(rows, vector<Point>(cols, {-1, -1}));
    
    queue<Point> q;
    q.push(net.src);
    visited[net.src.x][net.src.y] = true;

    int dx[] = {-1, 1, 0, 0};
    int dy[] = {0, 0, -1, 1};
    
    bool found = false;
    while (!q.empty()) {
        Point curr = q.front();
        q.pop();
        
        if (curr.x == net.dst.x && curr.y == net.dst.y) {
            found = true;
            break;
        }
        
        for (int i = 0; i < 4; i++) {
            int nx = curr.x + dx[i];
            int ny = curr.y + dy[i];
            
            if (nx >= 0 && nx < rows && ny >= 0 && ny < cols && !visited[nx][ny]) {
                // Chỉ được đi vào ô trống "." HOẶC chính là điểm Đích của mình.
                // Các ký hiệu như "o1", "o2" của dây trước đó sẽ tự động bị coi là Ostacle.
                if (grid[nx][ny] == "." || grid[nx][ny] == net.dstLabel) {
                    visited[nx][ny] = true;
                    parent[nx][ny] = curr;
                    q.push({nx, ny});
                }
            }
        }
    }

    if (!found) return false;
    
    // Đi ngược từ Đích về Nguồn để vẽ lại đường đi bằng ký tự o1, o2...
    Point cp = parent[net.dst.x][net.dst.y];
    while (!(cp.x == net.src.x && cp.y == net.src.y)) {
        grid[cp.x][cp.y] = pathSymbol;
        cp = parent[cp.x][cp.y];
    }
    return true;
}

int main() {
    ifstream inputFile("chip_layout.txt");
    if (!inputFile.is_open()) {
        cout << "[ERROR] There are no such file or the file is in the wrong location" << endl;
        return 1;
    }

    int rows, cols;
    inputFile >> rows >> cols;

    vector<vector<string>> chipGrid(rows, vector<string>(cols, "."));
    map<string, Point> pinMap;

    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            inputFile >> chipGrid[i][j];
            if (chipGrid[i][j] != "." && chipGrid[i][j] != "#") {
                pinMap[chipGrid[i][j]] = {i, j};
            }
        }
    }
    inputFile.close();

    vector<Net> netList;
    int netIdx = 1;
    while (true) {
        string sLabel = "S" + to_string(netIdx);
        string tLabel = "T" + to_string(netIdx);
        if (pinMap.count(sLabel) && pinMap.count(tLabel)) {
            netList.push_back({"Net" + to_string(netIdx), sLabel, tLabel, pinMap[sLabel], pinMap[tLabel]});
            netIdx++;
        } else {
            break;
        }
    }

    cout << "" << endl;
    printGrid(chipGrid);
    cout << "" << endl;

    auto startTime = chrono::high_resolution_clock::now();
    
    int netCount = 1;
    bool allSucceeded = true;
    
    for (const auto& net : netList) {
        string pathSymbol = "o" + to_string(netCount);
        cout << "\n>> BFS is finding way for " << net.name << " (" << net.srcLabel << " -> " << net.dstLabel << ")..." << endl;
        
        bool success = routeNetBFS(chipGrid, net, pathSymbol);
        
        if (success) {
            cout << "[Success] " << net.name << endl;
        } else {
            cout << "[Failed] " << net.name << endl;
            allSucceeded = false;
        }
        netCount++;
    }

    auto stopTime = chrono::high_resolution_clock::now();
    auto duration = chrono::duration_cast<chrono::microseconds>(stopTime - startTime);

    cout << "\n" << endl;
    printGrid(chipGrid);
    cout << "" << endl;
    
    if (allSucceeded) {
        cout << "[Success all]" << endl;
    } else {
        cout << "[Warning]" << endl;
    }
    cout << "Runtime: " << duration.count() << " microseconds." << endl;

    return 0;
}