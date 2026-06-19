#include <iostream>
#include <vector>
#include <map>
#include <fstream>
#include <sstream>
#include <chrono>
#include "IRouter3D.hpp" 
#include "AStar3D.hpp"

void printGrid(const std::vector<std::vector<std::vector<std::string>>>& grid) {
    for (size_t z = 0; z < grid.size(); ++z) {
        std::cout << "=== Layer " << z << " ===" << std::endl;
        for (size_t x = 0; x < grid[z].size(); ++x) {
            for (size_t y = 0; y < grid[z][x].size(); ++y) {
                std::string cell = grid[z][x][y];
                std::cout << cell;
                for (size_t k = 0; k < 4 - cell.length(); k++) std::cout << " ";
            }
            std::cout << std::endl;
        }
        std::cout << std::endl;
    }
}

int main() {
    std::ifstream inputFile("data/chip_layout_complex.txt");
    if (!inputFile.is_open()) {
        std::cout << "[ERROR] Can not find layout file" << std::endl;
        return 1;
    }

    std::string firstLine;
    std::getline(inputFile, firstLine);
    std::stringstream ss(firstLine);
    
    int layers = 1, rows = 0, cols = 0;
    std::vector<int> dims;
    int temp;
    while (ss >> temp) dims.push_back(temp);
    
    if (dims.size() == 3) {
        layers = dims[0]; rows = dims[1]; cols = dims[2];
    } else if (dims.size() == 2) {
        rows = dims[0]; cols = dims[1];
    } else {
        std::cout << "[ERROR] Invalid layout header format." << std::endl;
        return 1;
    }

    std::vector<std::vector<std::vector<std::string>>> grid(layers, std::vector<std::vector<std::string>>(rows, std::vector<std::string>(cols)));
    std::map<std::string, Point3D> pinMap;
    
    for (int z = 0; z < layers; ++z) {
        for (int i = 0; i < rows; ++i) {
            for (int j = 0; j < cols; ++j) {
                inputFile >> grid[z][i][j];
                if (grid[z][i][j] != "." && grid[z][i][j] != "#") {
                    pinMap[grid[z][i][j]] = {z, i, j};
                }
            }
        }
    }
    inputFile.close();

    std::vector<Net3D> netList;
    int idx = 1;
    while (pinMap.count("S" + std::to_string(idx)) && pinMap.count("T" + std::to_string(idx))) {
        netList.push_back({"Net" + std::to_string(idx), pinMap["S" + std::to_string(idx)], pinMap["T" + std::to_string(idx)]});
        idx++;
    }

    std::cout << "" << std::endl;
    printGrid(grid);
    IRouter3D* router = new AStar3D(); 

    auto start_time = std::chrono::high_resolution_clock::now();

    for (const auto& net : netList) {
        std::string symbol = "o" + net.name.substr(3); 
        
        if (router->route(grid, net.src, net.dst, symbol)) {
            std::cout << "[SUCCESS] " << net.name << " routed successfully." << std::endl;
        } else {
            std::cout << "[FAIL] " << net.name << " is blocked!" << std::endl;
        }
    }

    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);

    delete router;

    std::cout << "\n" << std::endl;
    printGrid(grid);

    std::cout << "\n[PERFORMANCE] Runtime: " << duration.count() << " microseconds" << std::endl;

    return 0;
}