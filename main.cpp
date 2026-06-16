#include <iostream>
#include <vector>
#include <queue>

using namespace std;

enum CellState { EMPTY = 0, OBSTACLE = 1, START = 2, TARGET = 3, PATH = 4 };

struct Point { int x, y; };

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

int main() {
    int rows = 10, cols = 10;
    vector<vector<int>> chipGrid(rows, vector<int>(cols, EMPTY));

    // Đặt tường chắn và điểm S, T
    chipGrid[3][4] = OBSTACLE; chipGrid[4][4] = OBSTACLE; chipGrid[5][4] = OBSTACLE;
    chipGrid[6][4] = OBSTACLE; chipGrid[6][5] = OBSTACLE; 

    Point src = {4, 2}; Point dst = {4, 7};
    chipGrid[src.x][src.y] = START; chipGrid[dst.x][dst.y] = TARGET;

    printGrid(chipGrid);
    return 0;
}