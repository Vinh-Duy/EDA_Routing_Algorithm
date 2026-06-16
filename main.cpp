#include <iostream>
#include <vector>
#include <queue>
#include <fstream>
#include <chrono>

using namespace std;

enum CellState { EMPTY = 0, OBSTACLE = 1, START = 2, TARGET = 3, PATH = 4 };

struct Point { int x, y; };

int dx[] = {-1, 1, 0, 0};
int dy[] = {0, 0, -1, 1};

void printGrid(const vector<vector<int>>& grid) {
    for (const auto& row : grid) {
        for (int cell : row) {
            if (cell == EMPTY) cout << ". ";
            else if (cell == OBSTACLE) cout << "# "; 
            else if (cell == START) cout << "S ";    
            else if (cell == TARGET) cout << "T ";   
            else if (cell == PATH) cout << "o ";
        }
        cout << endl;
    }
}

bool findPath(vector<vector<int>>& grid, Point src, Point dst) {
    int rows = grid.size();
    int cols = grid[0].size();
    
    // Bảng ghi nhớ vết chân để truy vết ngược lại đường đi
    vector<vector<Point>> parent(rows, vector<Point>(cols, {-1, -1}));
    // Bảng đánh dấu những ô đã đi qua để không đi lùi
    vector<vector<bool>> visited(rows, vector<bool>(cols, false));
    
    queue<Point> q; // Hàng đợi để vết dầu loang ra xung quanh

    q.push(src);
    visited[src.x][src.y] = true;
    bool found = false;

    // Quá trình spreading
    while (!q.empty()) {
        Point curr = q.front();
        q.pop();

        // Nếu chạm T thì stop
        if (curr.x == dst.x && curr.y == dst.y) {
            found = true;
            break;
        }

        //Spread ra 4 hướng xung quanh
        for (int i = 0; i < 4; i++) {
            int nx = curr.x + dx[i];
            int ny = curr.y + dy[i];

            // Nếu ô tiếp theo nằm trong chip, không đâm vào tường, và chưa đi qua
            if (nx >= 0 && nx < rows && ny >= 0 && ny < cols && 
                grid[nx][ny] != OBSTACLE && !visited[nx][ny]) {
                
                visited[nx][ny] = true;
                parent[nx][ny] = curr; // Lưu lại ô trước 
                q.push({nx, ny});
            }
        }
    }

    // Nếu tìm thấy đường, bắt đầu vẽ ngược từ T về S
    if (found) {
        Point curr = parent[dst.x][dst.y];
        while (curr.x != src.x || curr.y != src.y) {
            grid[curr.x][curr.y] = PATH; // Đánh dấu sợi dây
            curr = parent[curr.x][curr.y];
        }
        return true;
    }
    return false;
}

int main() {
    ifstream inputFile("chip_layout.txt");
    if (!inputFile.is_open()) {
        cout << "[ERROR] Can't open file, check the location of the file" << endl;
        return 1;
    }

    int rows, cols;
    inputFile >> rows >> cols;
    vector<vector<int>> chipGrid(rows, vector<int>(cols, EMPTY));
    Point src, dst;

    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            char ch;
            inputFile >> ch;
            if (ch == '#') {
                chipGrid[i][j] = OBSTACLE;
            } else if (ch == 'S') {
                chipGrid[i][j] = START;
                src = {i, j}; // Tự động lấy tọa độ xuất phát
            } else if (ch == 'T') {
                chipGrid[i][j] = TARGET;
                dst = {i, j}; // Tự động lấy tọa độ đích
            }
        }
    }

    inputFile.close();

    cout << "\n" << endl;
    printGrid(chipGrid);

    auto startTime = chrono::high_resolution_clock::now();
    
    bool result = findPath(chipGrid, src, dst);
    
    auto stopTime = chrono::high_resolution_clock::now();
    auto duration = chrono::duration_cast<chrono::microseconds>(stopTime - startTime);

    cout << "\n" << endl;
    if (result) {
        printGrid(chipGrid);
        cout << "\n[Success]" << endl;
    } else {
        cout << "\n[Failed]" << endl;
    }

    cout << "Runtime: " << duration.count() << " microseconds." << endl;

    return 0;
}