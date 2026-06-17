#ifndef IROUTER_HPP
#define IROUTER_HPP

#include <vector>
#include <string>

struct Point { int x, y; };
struct Net { std::string name; Point src, dst; };

class IRouter {
public:
    virtual bool route(std::vector<std::vector<std::string>>& grid, Point src, Point dst, std::string symbol) = 0;
    virtual ~IRouter() {} 
};

#endif