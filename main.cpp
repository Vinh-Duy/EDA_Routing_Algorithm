#include <iostream>
#include <vector>
#include <queue>

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

    // Quá trình lan tỏa
    while (!q.empty()) {
        Point curr = q.front();
        q.pop();

        // Nếu chạm đích T thì dừng lại
        if (curr.x == dst.x && curr.y == dst.y) {
            found = true;
            break;
        }

        // Thử loang ra 4 hướng xung quanh
        for (int i = 0; i < 4; i++) {
            int nx = curr.x + dx[i];
            int ny = curr.y + dy[i];

            // Nếu ô tiếp theo nằm trong chip, không đâm vào tường, và chưa đi qua
            if (nx >= 0 && nx < rows && ny >= 0 && ny < cols && 
                grid[nx][ny] != OBSTACLE && !visited[nx][ny]) {
                
                visited[nx][ny] = true;
                parent[nx][ny] = curr; // Lưu lại ô trước đó
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
    int rows = 10, cols = 10;
    vector<vector<int>> chipGrid(rows, vector<int>(cols, EMPTY));

    // Đặt tường chắn và điểm S, T
    chipGrid[3][4] = OBSTACLE; chipGrid[4][4] = OBSTACLE; chipGrid[5][4] = OBSTACLE; chipGrid[3][5] = OBSTACLE;
    chipGrid[6][4] = OBSTACLE; chipGrid[6][5] = OBSTACLE; chipGrid[6][6] = OBSTACLE; chipGrid[6][7] = OBSTACLE;

    Point src = {4, 2}; Point dst = {4, 7};
    chipGrid[src.x][src.y] = START; chipGrid[dst.x][dst.y] = TARGET;

    printGrid(chipGrid);

    if (findPath(chipGrid, src, dst)) {
        cout << "" << endl;
        printGrid(chipGrid);
    } else {
        cout << "Routing Failed" << endl;
    }

    return 0;
}