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
        ++result.heap_pushes;
    }
    while (!open.empty()) {
        auto [f, order, g, id]=open.top(); open.pop();
        ++result.heap_pops;
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
            ++result.edges_examined;
            int next=l.index(q);
            Cost candidate=g+edgeCost(p,q,next,occ,history,ownTree[next]);
            if (candidate < best[next]) {
                best[next]=candidate; parent[next]=id;
                open.emplace(candidate+heuristic(q),sequence++,candidate,next);
                ++result.heap_pushes;
            }
        }
    }
    return result;
}

struct NearestTerminalSelection {
    bool found=false;
    std::size_t terminal_index=0;
    Cost distance=std::numeric_limits<Cost>::max();
    std::uint64_t dijkstra_runs=0;
    std::uint64_t settled_vertices=0;
    std::uint64_t edges_examined=0;
    std::uint64_t heap_pushes=0;
    std::uint64_t heap_pops=0;
};

inline bool nearestTerminalKeyLess(Cost distance, Point3D terminal, std::size_t index,
                                   const NearestTerminalSelection& current,
                                   const std::vector<Point3D>& terminals) {
    if (!current.found) return true;
    const Point3D selected=terminals[current.terminal_index];
    return std::tie(distance,terminal.z,terminal.x,terminal.y,index) <
           std::tie(current.distance,selected.z,selected.x,selected.y,current.terminal_index);
}

inline NearestTerminalSelection selectNearestByRepeatedDijkstra(
        const Layout& l, const Net3D& net, const std::vector<Point3D>& terminals,
        const std::vector<int>& occupancy, const std::vector<Cost>& history,
        const std::vector<bool>& ownTree) {
    NearestTerminalSelection selection;
    for (std::size_t t=1;t<terminals.size();++t) {
        const Point3D terminal=terminals[t];
        if (!l.contains(terminal) || ownTree[l.index(terminal)]) continue;
        std::vector<int> sources;
        for (std::size_t cell=0;cell<ownTree.size();++cell)
            if (ownTree[cell]) sources.push_back(static_cast<int>(cell));
        const auto result=weightedSearchToTree(l,net,sources,l.index(terminal),
                                               occupancy,history,ownTree,false);
        ++selection.dijkstra_runs;
        selection.settled_vertices+=result.expanded;
        selection.edges_examined+=result.edges_examined;
        selection.heap_pushes+=result.heap_pushes;
        selection.heap_pops+=result.heap_pops;
        if (!result.path.empty() &&
            nearestTerminalKeyLess(result.search_cost,terminal,t,selection,terminals)) {
            selection.found=true;
            selection.terminal_index=t;
            selection.distance=result.search_cost;
        }
    }
    return selection;
}

inline NearestTerminalSelection selectNearestByMultiSourceDijkstra(
        const Layout& l, const Net3D& net, const std::vector<Point3D>& terminals,
        const std::vector<int>& sources, const std::vector<int>& occupancy,
        const std::vector<Cost>& history, const std::vector<bool>& ownTree) {
    checkSearchInputs(l,occupancy,history);
    if (ownTree.size()!=l.cells.size() || sources.empty())
        throw std::invalid_argument("Invalid multi-source nearest-terminal roots");
    std::vector<bool> roots(l.cells.size(),false);
    for (int source:sources) {
        if (source<0 || static_cast<std::size_t>(source)>=l.cells.size() ||
            !ownTree[source] || !l.legal(l.point(source),net))
            throw std::invalid_argument("Invalid multi-source nearest-terminal root");
        roots[source]=true;
    }

    NearestTerminalSelection selection;
    std::vector<std::size_t> candidateAt(l.cells.size(),terminals.size());
    bool hasCandidate=false;
    for (std::size_t t=1;t<terminals.size();++t) {
        const Point3D terminal=terminals[t];
        if (!l.contains(terminal) || ownTree[l.index(terminal)]) continue;
        const std::size_t id=static_cast<std::size_t>(l.index(terminal));
        if (candidateAt[id]==terminals.size() || t<candidateAt[id]) candidateAt[id]=t;
        hasCandidate=true;
    }
    if (!hasCandidate) return selection;

    selection.dijkstra_runs=1;
    const Cost infinity=std::numeric_limits<Cost>::max();
    std::vector<Cost> best(l.cells.size(),infinity);
    using Entry=std::pair<Cost,int>;
    std::priority_queue<Entry,std::vector<Entry>,std::greater<Entry>> open;
    for (int source:sources) {
        if (best[source]==0) continue;
        best[source]=0;
        open.emplace(0,source);
        ++selection.heap_pushes;
    }
    while (!open.empty()) {
        const auto [distance,id]=open.top();
        if (selection.found && distance>selection.distance) break;
        open.pop();
        ++selection.heap_pops;
        if (distance!=best[id]) continue;
        ++selection.settled_vertices;
        const std::size_t candidateIndex=candidateAt[static_cast<std::size_t>(id)];
        if (candidateIndex<terminals.size()) {
            const Point3D terminal=terminals[candidateIndex];
            if (nearestTerminalKeyLess(distance,terminal,candidateIndex,selection,terminals)) {
                selection.found=true;
                selection.terminal_index=candidateIndex;
                selection.distance=distance;
            }
        }
        if (selection.found && distance==selection.distance) continue;
        const Point3D point=l.point(id);
        for (Point3D neighbor:neighbors(point)) {
            if (!l.legal(neighbor,net)) continue;
            ++selection.edges_examined;
            const int next=l.index(neighbor);
            const Cost candidate=distance+edgeCost(point,neighbor,next,occupancy,history,
                                                    ownTree[static_cast<std::size_t>(next)]);
            if (candidate<best[static_cast<std::size_t>(next)] &&
                (!selection.found || candidate<=selection.distance)) {
                best[static_cast<std::size_t>(next)]=candidate;
                open.emplace(candidate,next);
                ++selection.heap_pushes;
            }
        }
    }
    return selection;
}
#endif
