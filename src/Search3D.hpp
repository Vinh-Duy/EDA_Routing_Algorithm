#ifndef SEARCH3D_HPP
#define SEARCH3D_HPP
#include "IRouter3D.hpp"
#include <functional>
#include <limits>
#include <queue>
#include <tuple>

inline void checkSearchInputs(const Layout& l, const std::vector<int>& occupancy,
                              const std::vector<Cost>& history) {
    l.validateShape();
    if (occupancy.size() != l.cells.size() || history.size() != l.cells.size())
        throw std::invalid_argument("Invalid search grid dimensions");
    // Bound penalties so accumulated costs cannot overflow even along a simple path.
    const Cost limit = std::numeric_limits<Cost>::max() / 8 / static_cast<Cost>(l.cells.size());
    for (std::size_t i=0; i<history.size(); ++i)
        if (history[i] < 0 || history[i] > limit || occupancy[i] < 0)
            throw std::invalid_argument("Invalid search penalty");
}
inline Cost edgeCost(Point3D a, Point3D b, int id, const std::vector<int>& occ,
                     const std::vector<Cost>& history, bool ownTree=false) {
    return (a.z == b.z ? 1 : VIA_STEP_COST) +
           (occ[id] > 0 && !ownTree ? OCCUPANCY_PENALTY : 0) + history[id];
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
inline SearchResult weightedSearchToTree(const Layout& l, const Net3D& net,
                                         const std::vector<int>& sources, int target,
                                         const std::vector<int>& occ, const std::vector<Cost>& history,
                                         const std::vector<bool>& ownTree, bool useHeuristic);
inline SearchResult weightedSearch(const Layout& l, const Net3D& net,
                                   const std::vector<int>& occ, const std::vector<Cost>& history,
                                   bool useHeuristic) {
    checkSearchInputs(l,occ,history);
    if (!l.legal(net.src,net) || !l.legal(net.dst,net)) return {};
    std::vector<bool> ownTree(l.cells.size(),false);
    ownTree[l.index(net.src)]=true;
    return weightedSearchToTree(l,net,{l.index(net.src)},l.index(net.dst),occ,history,ownTree,useHeuristic);
}
inline Path reconstructFromTree(const Layout& l, int target, const std::vector<int>& parent,
                                const std::vector<bool>& roots) {
    Path path;
    for (std::size_t count=0;count<l.cells.size();++count) {
        if (target<0 || static_cast<std::size_t>(target)>=parent.size())
            throw std::logic_error("Broken tree-search predecessor chain");
        path.push_back(l.point(target));
        if (roots[target]) { std::reverse(path.begin(),path.end()); return path; }
        target=parent[target];
    }
    throw std::logic_error("Cyclic tree-search predecessor chain");
}
inline SearchResult weightedSearchToTree(const Layout& l, const Net3D& net,
                                         const std::vector<int>& sources, int target,
                                         const std::vector<int>& occ, const std::vector<Cost>& history,
                                         const std::vector<bool>& ownTree, bool useHeuristic) {
    checkSearchInputs(l, occ, history);
    if (ownTree.size()!=l.cells.size() || sources.empty() || target<0 ||
        static_cast<std::size_t>(target)>=l.cells.size())
        throw std::invalid_argument("Invalid multi-source search roots or target");
    SearchResult result;
    Point3D destination=l.point(target);
    if (!l.legal(destination,net)) return result;
    auto heuristic = [&](Point3D p) -> Cost {
        return useHeuristic ? std::abs(p.x-destination.x) + std::abs(p.y-destination.y)
                            + VIA_STEP_COST*std::abs(p.z-destination.z) : 0;
    };
    // Stable tie break: f, insertion sequence. Neighbor order is shared with BFS.
    using Entry = std::tuple<Cost, std::uint64_t, Cost, int>;
    std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>> open;
    std::vector<Cost> best(l.cells.size(), std::numeric_limits<Cost>::max());
    std::vector<int> parent(l.cells.size(), -1);
    std::uint64_t sequence=0;
    std::vector<bool> roots(l.cells.size(),false);
    for (int source:sources) {
        if (source<0 || static_cast<std::size_t>(source)>=l.cells.size() ||
            !ownTree[source] || !l.legal(l.point(source),net))
            throw std::invalid_argument("Invalid multi-source tree root");
        if (roots[source]) continue;
        roots[source]=true; best[source]=0;
        open.emplace(heuristic(l.point(source)),sequence++,0,source);
    }
    while (!open.empty()) {
        auto [f, order, g, id]=open.top(); open.pop();
        (void)f; (void)order;
        if (g != best[id]) continue;
        ++result.expanded;
        if (id == target) {
            result.path=reconstructFromTree(l,target,parent,roots);
            result.search_cost=g;
            return result;
        }
        Point3D p=l.point(id);
        for (Point3D q: neighbors(p)) {
            if (!l.legal(q,net)) continue;
            int next=l.index(q);
            Cost candidate=g+edgeCost(p,q,next,occ,history,ownTree[next]);
            if (candidate < best[next]) {
                best[next]=candidate; parent[next]=id;
                open.emplace(candidate+heuristic(q),sequence++,candidate,next);
            }
        }
    }
    return result;
}
#endif
