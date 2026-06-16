#include <iostream>
#include <vector>
#include <queue>

using namespace std;

enum CellState { EMPTY = 0, OBSTACLE = 1, START = 2, TARGET = 3, PATH = 4 };

struct Point { int x, y; };

int main() {
    int rows = 10, cols = 10;
    vector<vector<int>> chipGrid(rows, vector<int>(cols, EMPTY));
    return 0;
}