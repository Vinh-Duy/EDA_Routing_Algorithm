#include <iostream>
#include <vector>
#include <queue>
#include <fstream>
#include <chrono>
#include <string>
#include <map>
#include <cmath>
#include <functional>

using namespace std;

struct Point { int x, y; };

struct AStarNode {
    Point p;
    int g; // Chi phí thực tế đi từ điểm bắt đầu đến ô hiện tại
    int f; // Tổng chi phí dự đoán: F = G + H
    // Thao tác toán tử để priority_queue ưu tiên thằng có F nhỏ nhất
    bool operator>(const AStarNode& other) const {
        return f > other.f;
    }
};

struct Net {
    string name;
    string srcLabel;   // Kí hiệu nguồn (S1, S2)
    string dstLabel;   // Kí hiệu đích (T1, T2)
    Point src;         // Tọa độ nguồn
    Point dst;         // Tọa độ đích
};

int getManhattanDistance(Point a, Point b) {
    return abs(a.x - b.x) + abs(a.y - b.y);
}

void printGrid(const vector<vector<string>>& grid) {
    for (const auto& row : grid) {
        for (const string& cell : row) {
            cout << cell;
            for (int k = 0; k < 4 - cell.length(); k++) cout << " ";
        }
        cout << endl;
    }
}

bool routeSingleNet(vector<vector<string>>& grid, Net net, string pathSymbol) {
    int rows = grid.size();
    int cols = grid[0].size();
    // Hàng đợi ưu tiên: Luôn lôi thằng có tổng chi phí F nhỏ nhất ra xử lý trước
    priority_queue<AStarNode, vector<AStarNode>, greater<AStarNode>> pq;
    // Mảng lưu chi phí G nhỏ nhất tới từng ô
    vector<vector<int>> gScore(rows, vector<int>(cols, 1000000000));
    vector<vector<Point>> parent(rows, vector<Point>(cols, {-1, -1}));
    // Điểm xuất phát
    gScore[net.src.x][net.src.y] = 0;
    int hStart = getManhattanDistance(net.src, net.dst);
    pq.push({net.src, 0, hStart});
    
    int dx[] = {-1, 1, 0, 0};
    int dy[] = {0, 0, -1, 1};
    
    bool found = false;
    while (!pq.empty()) {
        AStarNode curr = pq.top();
        pq.pop();
        if (curr.p.x == net.dst.x && curr.p.y == net.dst.y) {
            found = true;
            break;
        }

        if (curr.g > gScore[curr.p.x][curr.p.y]) continue;
        
        for (int i = 0; i < 4; i++) {
            int nx = curr.p.x + dx[i];
            int ny = curr.p.y + dy[i];
            
            if (nx >= 0 && nx < rows && ny >= 0 && ny < cols) {
                
                // Ô đó phải TRỐNG vả lại KHÔNG ĐƯỢC là dây của net khác. 
                // Ngoại lệ: Cho phép bước lên chính điểm ĐÍCH của mình.
                if (grid[nx][ny] == "." || grid[nx][ny] == net.dstLabel) {
                    
                    int nextG = curr.g + 1; // Chi phí bước thêm 1 ô là +1
                    
                    if (nextG < gScore[nx][ny]) {
                        gScore[nx][ny] = nextG;
                        parent[nx][ny] = curr.p;
                        int nextH = getManhattanDistance({nx, ny}, net.dst);
                        pq.push({{nx, ny}, nextG, nextG + nextH});
                    }
                }
            }
        }
    }
    
    if (!found) return false;

    Point currPoint = parent[net.dst.x][net.dst.y];
    while (!(currPoint.x == net.src.x && currPoint.y == net.src.y)) {
        grid[currPoint.x][currPoint.y] = pathSymbol;
        currPoint = parent[currPoint.x][currPoint.y];
    }
    return true;
}

int main() {
    ifstream inputFile("chip_layout.txt");
    if (!inputFile.is_open()) {
        cout << "[ERROR] Can't open file 'chip_layout.txt'" << endl;
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
    if (pinMap.count("S1") && pinMap.count("T1")) netList.push_back({"Net1", "S1", "T1", pinMap["S1"], pinMap["T1"]});
    if (pinMap.count("S2") && pinMap.count("T2")) netList.push_back({"Net2", "S2", "T2", pinMap["S2"], pinMap["T2"]});

    cout << "" << endl;
    printGrid(chipGrid);
    cout << "" << endl;

    //chạy thuật toán astar cho từng net và đo thời gian thực thi
    auto startTime = chrono::high_resolution_clock::now();
    
    int netCount = 1;
    bool allSucceeded = true;
    for (const auto& net : netList) {
        string pathSymbol = "o" + to_string(netCount); // Sợi dây 1 vẽ bằng o1, dây 2 bằng o2
        cout << "\n>> Dang dinh tuyen cho " << net.name << " (" << net.srcLabel << " -> " << net.dstLabel << ")..." << endl;
        
        bool success = routeSingleNet(chipGrid, net, pathSymbol);
        
        if (success) {
            cout << "[OK] " << net.name << " dinh tuyen thanh cong!" << endl;
        } else {
            cout << "[FAILED] " << net.name << " BI TAC NGHEN! Khong tim duoc duong đi." << endl;
            allSucceeded = false;
        }
        netCount++;
    }

    auto stopTime = chrono::high_resolution_clock::now();
    auto duration = chrono::duration_cast<chrono::microseconds>(stopTime - startTime);

    // 3. IN KẾT QUẢ CUỐI CÙNG
    cout << "\n" << endl;
    printGrid(chipGrid);
    cout << "-" << endl;
    
    if (allSucceeded) {
        cout << "[Success]" << endl;
    } else {
        cout << "[Warning]" << endl;
    }
    cout << "Runtime: " << duration.count() << " microseconds." << endl;

    return 0;
}