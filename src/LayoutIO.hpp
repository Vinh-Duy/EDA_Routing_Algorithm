#ifndef LAYOUT_IO_HPP
#define LAYOUT_IO_HPP
#include "IRouter3D.hpp"
#include <fstream>
#include <map>
#include <sstream>

inline int positiveInteger(const std::string& text) {
    if (text.empty() || text[0] < '1' || text[0] > '9' ||
        text.find_first_not_of("0123456789") != std::string::npos)
        throw std::invalid_argument("Expected a positive integer: " + text);
    std::size_t used=0;
    int value=std::stoi(text,&used);
    if (used != text.size()) throw std::invalid_argument("Invalid integer: " + text);
    return value;
}
inline Layout readLayout(std::istream& input) {
    Layout l;
    std::string line, token;
    if (!std::getline(input,line)) throw std::runtime_error("Missing layout header");
    std::istringstream header(line);
    std::vector<int> dims;
    while (header >> token) dims.push_back(positiveInteger(token));
    if (dims.size()==2) { l.layers=1; l.rows=dims[0]; l.cols=dims[1]; }
    else if (dims.size()==3) { l.layers=dims[0]; l.rows=dims[1]; l.cols=dims[2]; }
    else throw std::runtime_error("Header must contain rows cols or layers rows cols");
    // Explicit educational-tool resource limit, checked without multiplication overflow.
    constexpr int maxCells=1000000;
    if (l.layers>maxCells/l.rows || l.layers*l.rows>maxCells/l.cols)
        throw std::runtime_error("Layout exceeds 1,000,000 cells");
    std::map<int,Point3D> sources,targets;
    int row=0, lineNumber=1;
    while (std::getline(input,line)) {
        ++lineNumber;
        std::istringstream values(line);
        std::vector<std::string> cells;
        while (values >> token) cells.push_back(token);
        if (cells.empty()) continue;
        if (row >= l.layers*l.rows || static_cast<int>(cells.size()) != l.cols)
            throw std::runtime_error("Wrong cell count at line " + std::to_string(lineNumber));
        for (int y=0;y<l.cols;++y) {
            const auto& cell=cells[y];
            if (cell != "." && cell != "#") {
                if (cell.size()<2 || (cell[0]!='S' && cell[0]!='T'))
                    throw std::runtime_error("Unknown cell token: " + cell);
                int id=positiveInteger(cell.substr(1));
                auto& pins=cell[0]=='S' ? sources : targets;
                if (!pins.emplace(id,Point3D{row/l.rows,row%l.rows,y}).second)
                    throw std::runtime_error("Duplicate pin: " + cell);
            }
            l.cells.push_back(cell);
        }
        ++row;
    }
    if (row != l.layers*l.rows) throw std::runtime_error("Incomplete layout: missing rows");
    if (sources.empty() || sources.size()!=targets.size())
        throw std::runtime_error("Layout needs at least one complete source/target pair");
    for (const auto& [id,src]: sources) {
        if (!targets.count(id)) throw std::runtime_error("Missing target for S" + std::to_string(id));
        l.nets.push_back({"Net"+std::to_string(id),src,targets.at(id)});
    }
    return l;
}
inline Layout readLayoutFile(const std::string& filename) {
    std::ifstream input(filename);
    if (!input) throw std::runtime_error("Cannot open input: " + filename);
    return readLayout(input);
}
#endif
