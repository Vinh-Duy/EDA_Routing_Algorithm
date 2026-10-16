#ifndef SEARCH3D_HPP
#define SEARCH3D_HPP
#include "IRouter3D.hpp"
#include <functional>
#include <limits>
#include <queue>
#include <tuple>

inline void checkSearchInputs(const Layout& l, const std::vector<int>& occupancy,
                              const std::vector<Cost>& history) {
    if (l.layers <= 0 || l.rows <= 0 || l.cols <= 0 ||
        l.layers > 1000000 / l.rows || l.layers * l.rows > 1000000 / l.cols ||
        static_cast<std::int64_t>(l.layers)*l.rows*l.cols != static_cast<std::int64_t>(l.cells.size()) ||
        occupancy.size() != l.cells.size() || history.size() != l.cells.size())
        throw std::invalid_argument("Invalid search grid dimensions");
    // Bound penalties so accumulated costs cannot overflow even along a simple path.
    const Cost limit = std::numeric_limits<Cost>::max() / 8 / static_cast<Cost>(l.cells.size());
    for (std::size_t i=0; i<history.size(); ++i)
        if (history[i] < 0 || history[i] > limit || occupancy[i] < 0)
            throw std::invalid_argument("Invalid search penalty");
}
inline Cost edgeCost(Point3D a, Point3D b, int id, const std::vector<int>& occ,
                     const std::vector<Cost>& history) {
    return (a.z == b.z ? 1 : VIA_STEP_COST) + (occ[id] > 0 ? OCCUPANCY_PENALTY : 0) + history[id];
}
inline Path reconstruct(const Layout& l, int src, int dst, const std::vector<int>& parent) {
    Path path;
    for (std::size_t count=0; count<l.cells.size(); ++count) {
        if (dst < 0 || static_cast<std::size_t>(dst) >= parent.size())
            throw std::logic_error("Broken predecessor chain");
        path.push_back(l.point(dst));
        if (dst == src) { std::reverse(path.begin(), path.end()); return path; }
        dst = parent[dst];
    }
    throw std::logic_error("Cyclic predecessor chain");
}
inline SearchResult weightedSearch(const Layout& l, const Net3D& net,
                                   const std::vector<int>& occ, const std::vector<Cost>& history,
                                   bool useHeuristic) {
    checkSearchInputs(l, occ, history);
    SearchResult result;
    if (!l.legal(net.src,net) || !l.legal(net.dst,net)) return result;
    auto heuristic = [&](Point3D p) -> Cost {
        return useHeuristic ? std::abs(p.x-net.dst.x) + std::abs(p.y-net.dst.y)
                            + VIA_STEP_COST*std::abs(p.z-net.dst.z) : 0;
    };
    // Stable tie break: f, insertion sequence. Neighbor order is shared with BFS.
    using Entry = std::tuple<Cost, std::uint64_t, Cost, int>;
    std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>> open;
    std::vector<Cost> best(l.cells.size(), std::numeric_limits<Cost>::max());
    std::vector<int> parent(l.cells.size(), -1);
    const int src=l.index(net.src), dst=l.index(net.dst);
    std::uint64_t sequence=0;
    best[src]=0;
    open.emplace(heuristic(net.src), sequence++, 0, src);
    while (!open.empty()) {
        auto [f, order, g, id]=open.top(); open.pop();
        (void)f; (void)order;
        if (g != best[id]) continue;
        ++result.expanded;
        if (id == dst) {
            result.path=reconstruct(l,src,dst,parent);
            result.search_cost=g;
            return result;
        }
        Point3D p=l.point(id);
        for (Point3D q: neighbors(p)) {
            if (!l.legal(q,net)) continue;
            int next=l.index(q);
            Cost candidate=g+edgeCost(p,q,next,occ,history);
            if (candidate < best[next]) {
                best[next]=candidate; parent[next]=id;
                open.emplace(candidate+heuristic(q),sequence++,candidate,next);
            }
        }
    }
    return result;
}
#endif
