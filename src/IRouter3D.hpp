#ifndef IROUTER3D_HPP
#define IROUTER3D_HPP

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

struct Point3D { int z, x, y; };
inline bool operator==(Point3D a, Point3D b) { return a.z == b.z && a.x == b.x && a.y == b.y; }
inline bool operator!=(Point3D a, Point3D b) { return !(a == b); }
struct Net3D {
    std::string name;
    Point3D src, dst;
    // Canonical order is source, target, then extra terminals in input order.
    std::vector<Point3D> terminals;
};
inline bool pointLess(Point3D a, Point3D b) {
    return std::tie(a.z,a.x,a.y) < std::tie(b.z,b.x,b.y);
}
struct TreeEdge3D { Point3D a, b; };
inline bool operator==(TreeEdge3D x, TreeEdge3D y) { return x.a==y.a && x.b==y.b; }
struct RouteTree3D { std::vector<TreeEdge3D> edges; };
inline bool operator==(const RouteTree3D& a,const RouteTree3D& b) { return a.edges==b.edges; }
using Cost = std::int64_t;
using Path = std::vector<Point3D>;
constexpr Cost VIA_STEP_COST = 6; // One graph edge plus five units of VIA penalty.
constexpr Cost OCCUPANCY_PENALTY = 100;
constexpr Cost HISTORY_INCREMENT = 50;

// Immutable physical layout; occupancy and display never replace pin/obstacle data.
struct Layout {
    int layers = 0, rows = 0, cols = 0;
    std::vector<std::string> cells;
    std::vector<Net3D> nets;
    void validateShape() const {
        if (layers <= 0 || rows <= 0 || cols <= 0 ||
            layers > 1000000 / rows || layers * rows > 1000000 / cols ||
            static_cast<std::int64_t>(layers)*rows*cols != static_cast<std::int64_t>(cells.size()))
            throw std::invalid_argument("Invalid layout dimensions or cell storage");
    }
    bool contains(Point3D p) const {
        return p.z >= 0 && p.z < layers && p.x >= 0 && p.x < rows && p.y >= 0 && p.y < cols;
    }
    int index(Point3D p) const { return (p.z * rows + p.x) * cols + p.y; }
    Point3D point(int i) const { return {i / (rows * cols), (i / cols) % rows, i % cols}; }
    bool legal(Point3D p, const Net3D& net) const {
        if (!contains(p)) return false;
        const auto& cell = cells.at(index(p));
        if (cell=="#") return false;
        if (cell==".") return true;
        if (!net.terminals.empty())
            return std::find(net.terminals.begin(),net.terminals.end(),p)!=net.terminals.end();
        return p == net.src || p == net.dst;
    }
};
inline int distance(Point3D a, Point3D b) {
    return std::abs(a.z-b.z) + std::abs(a.x-b.x) + std::abs(a.y-b.y);
}
inline std::array<Point3D, 6> neighbors(Point3D p) {
    return {{{p.z,p.x-1,p.y}, {p.z,p.x+1,p.y}, {p.z,p.x,p.y-1},
             {p.z,p.x,p.y+1}, {p.z-1,p.x,p.y}, {p.z+1,p.x,p.y}}};
}
struct SearchResult {
    Path path;
    std::uint64_t expanded = 0;
    Cost search_cost = 0; // Weighted cost at search time, also evaluated for BFS.
};
class IRouter3D {
public:
    // False only when fixed-layout, fixed-order reruns cannot change the paths.
    // Default conservatively to true for other routing strategies.
    virtual bool respondsToCongestion() const { return true; }
    virtual SearchResult route(const Layout& layout, const Net3D& net,
                               const std::vector<int>& occupancy,
                               const std::vector<Cost>& history) const = 0;
    // Extend a connected tree from any of its cells to one remaining terminal.
    virtual SearchResult routeToTree(const Layout& layout, const Net3D& net,
                                     const std::vector<int>& treeSources, int target,
                                     const std::vector<int>& occupancy,
                                     const std::vector<Cost>& history,
                                     const std::vector<bool>& ownTree) const = 0;
    virtual ~IRouter3D() = default;
};
#endif
