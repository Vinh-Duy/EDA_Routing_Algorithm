#ifndef IROUTER3D_HPP
#define IROUTER3D_HPP

#include <vector>
#include <string>

struct Point3D { int z, x, y; };
struct Net3D { std::string name; Point3D src, dst; };

class IRouter3D {
public:
    virtual bool route(std::vector<std::vector<std::vector<std::string>>>& grid, Point3D src, Point3D dst, std::string symbol, std::vector<Point3D>& path) = 0;
    virtual ~IRouter3D() {} 
};

#endif