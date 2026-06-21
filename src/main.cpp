#include <iostream>
#include <vector>
#include <map>
#include <fstream>
#include <sstream>
#include <chrono>
#include "IRouter3D.hpp" 
#include "AStar3D.hpp"
#include "BFS3D.hpp"

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

    // Khởi tạo lưới lưu trữ chi phí phạt
    std::vector<std::vector<std::vector<int>>> penaltyGrid(layers, std::vector<std::vector<int>>(rows, std::vector<int>(cols, 0)));
    
    int maxIterations = 10;
    bool hasConflicts = true;
    std::vector<std::vector<Point3D>> finalPaths(netList.size()); // Lưu toạ độ xuất ra JSON

    for (int iter = 1; iter <= maxIterations && hasConflicts; ++iter) {
        std::cout << "\n--- RIP-UP & REROUTE ITERATION " << iter << " ---" << std::endl;
        hasConflicts = false;
        
        // Rip-up toàn bộ dây hiện tại, chỉ giữ lại chân Pin và Vật cản
        for (int z = 0; z < layers; ++z) {
            for (int x = 0; x < rows; ++x) {
                for (int y = 0; y < cols; ++y) {
                    if (grid[z][x][y].find("o") == 0 || grid[z][x][y] == "V" || grid[z][x][y] == "X") {
                        grid[z][x][y] = ".";
                    }
                }
            }
        }

        // Bắt đầu Reroute từng Net
        for (size_t i = 0; i < netList.size(); ++i) {
            std::string symbol = "o" + netList[i].name.substr(3); 
            std::vector<Point3D> currentPath;
            
            router->route(grid, netList[i].src, netList[i].dst, symbol, currentPath, penaltyGrid);
            finalPaths[i] = currentPath;
        }

        // Kiểm tra xung đột (Dấu X) và tăng Penalty
        for (int z = 0; z < layers; ++z) {
            for (int x = 0; x < rows; ++x) {
                for (int y = 0; y < cols; ++y) {
                    if (grid[z][x][y] == "X") {
                        hasConflicts = true;
                        penaltyGrid[z][x][y] += 50; // Tăng điểm phạt để vòng sau chúng nó né ô này ra
                    }
                }
            }
        }

        if (!hasConflicts) {
            std::cout << "[SUCCESS] 100% Routed without conflicts after " << iter << " iterations." << std::endl;
        } else {
            std::cout << "[WARNING] Conflicts detected! Adjusting penalties and re-routing..." << std::endl;
        }
    }

    std::ofstream jsonFile("output.json");
    jsonFile << "{\n  \"nets\": [\n";
    for (size_t i = 0; i < netList.size(); ++i) {
        if (i > 0) jsonFile << ",\n";
        jsonFile << "    {\n      \"name\": \"" << netList[i].name << "\",\n      \"path\": [";
        for (size_t j = 0; j < finalPaths[i].size(); ++j) {
            jsonFile << "{\"z\":" << finalPaths[i][j].z << ", \"x\":" << finalPaths[i][j].x << ", \"y\":" << finalPaths[i][j].y << "}";
            if (j < finalPaths[i].size() - 1) jsonFile << ", ";
        }
        jsonFile << "]\n    }";
        
        if (!finalPaths[i].empty()) {
            std::cout << "[SUCCESS] " << netList[i].name << " routed successfully." << std::endl;
        } else {
            std::cout << "[FAIL] " << netList[i].name << " is blocked completely!" << std::endl;
        }
    }
    jsonFile << "\n  ]\n}\n";
    jsonFile.close();

    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);

    delete router;

    std::cout << "\n" << std::endl;
    printGrid(grid);

    std::cout << "\n[PERFORMANCE] Runtime: " << duration.count() << " microseconds" << std::endl;

    return 0;
}