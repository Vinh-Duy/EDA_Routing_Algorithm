#include <iostream>
#include <vector>
#include <map>
#include <fstream>
#include "AStar2D.hpp"
#include "IRouter2D.hpp"
#include "BFS2D.hpp"

void printGrid(const std::vector<std::vector<std::string>>& grid) {
    for (const auto& row : grid) {
        for (const std::string& cell : row) {
            std::cout << cell;
            for (size_t k = 0; k < 4 - cell.length(); k++) std::cout << " ";
        }
        std::cout << std::endl;
    }
}

int main() {
    std::ifstream inputFile("data/chip_layout_complex.txt");
    if (!inputFile.is_open()) {
        std::cout << "[ERROR] Can not find chip_layout.txt" << std::endl;
        return 1;
    }

    int rows, cols;
    inputFile >> rows >> cols;
    
    std::vector<std::vector<std::string>> grid(rows, std::vector<std::string>(cols));
    std::map<std::string, Point> pinMap;
    
    for (int i = 0; i < rows; ++i) {
        for (int j = 0; j < cols; ++j) {
            inputFile >> grid[i][j];
            if (grid[i][j] != "." && grid[i][j] != "#") {
                pinMap[grid[i][j]] = {i, j};
            }
        }
    }
    inputFile.close();

    std::vector<Net> netList;
    int idx = 1;
    while (pinMap.count("S" + std::to_string(idx)) && pinMap.count("T" + std::to_string(idx))) {
        netList.push_back({"Net" + std::to_string(idx), pinMap["S" + std::to_string(idx)], pinMap["T" + std::to_string(idx)]});
        idx++;
    }

    std::cout << "" << std::endl;
    printGrid(grid);
    std::cout << "\n" << std::endl;

    IRouter2D* router = new BFS2D();

    auto start_time = std::chrono::high_resolution_clock::now();

    for (const auto& net : netList) {
        std::string symbol = "o" + net.name.substr(3); 
        
        if (router->route(grid, net.src, net.dst, symbol)) {
            std::cout << "[SUCCESS] " << net.name << " routed successfully" << std::endl;
        } else {
            std::cout << "[FAIL] " << net.name << " is blocked" << std::endl;
        }
    }

    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);

    delete router;

    std::cout << "\n" << std::endl;
    printGrid(grid);
    std::cout << "" << std::endl;

    std::cout << "\n[PERFORMANCE] Runtime: " << duration.count() << " microseconds" << std::endl;

    return 0;
}