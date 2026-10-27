#ifndef BFS_3D_HPP
#define BFS_3D_HPP
#include "Search3D.hpp"
class BFS3D : public IRouter3D {
public:
    bool respondsToCongestion() const override { return false; }
    SearchResult route(const Layout& l, const Net3D& net, const std::vector<int>& occ,
                       const std::vector<Cost>& history) const override {
        checkSearchInputs(l,occ,history);
        SearchResult result;
        if (!l.legal(net.src,net) || !l.legal(net.dst,net)) return result;
        std::vector<int> parent(l.cells.size(),-1);
        std::queue<int> open;
        int src=l.index(net.src), dst=l.index(net.dst);
        parent[src]=src; open.push(src);
        while (!open.empty()) {
            int id=open.front(); open.pop(); ++result.expanded;
            if (id == dst) {
                result.path=reconstruct(l,src,dst,parent);
                for (std::size_t i=1;i<result.path.size();++i)
                    result.search_cost+=edgeCost(result.path[i-1],result.path[i],l.index(result.path[i]),occ,history);
                return result;
            }
            for (Point3D q: neighbors(l.point(id))) {
                if (!l.legal(q,net)) continue;
                int next=l.index(q);
                if (parent[next] != -1) continue;
                parent[next]=id; open.push(next);
            }
        }
        return result;
    }
    SearchResult routeToTree(const Layout& l, const Net3D& net, const std::vector<int>& sources,
                             int target, const std::vector<int>& occ, const std::vector<Cost>& history,
                             const std::vector<bool>& ownTree) const override {
        checkSearchInputs(l,occ,history);
        if (ownTree.size()!=l.cells.size() || sources.empty() || target<0 ||
            static_cast<std::size_t>(target)>=l.cells.size())
            throw std::invalid_argument("Invalid multi-source search roots or target");
        SearchResult result;
        if (!l.legal(l.point(target),net)) return result;
        std::vector<int> parent(l.cells.size(),-1);
        std::vector<bool> roots(l.cells.size(),false);
        std::queue<int> open;
        for (int source:sources) {
            if (source<0 || static_cast<std::size_t>(source)>=l.cells.size() ||
                !ownTree[source] || !l.legal(l.point(source),net))
                throw std::invalid_argument("Invalid multi-source tree root");
            if (roots[source]) continue;
            roots[source]=true; parent[source]=source; open.push(source);
        }
        while (!open.empty()) {
            int id=open.front(); open.pop(); ++result.expanded;
            if (id==target) {
                result.path=reconstructFromTree(l,target,parent,roots);
                for (std::size_t i=1;i<result.path.size();++i)
                    result.search_cost+=edgeCost(result.path[i-1],result.path[i],
                        l.index(result.path[i]),occ,history,ownTree[l.index(result.path[i])]);
                return result;
            }
            for (Point3D q:neighbors(l.point(id))) {
                if (!l.legal(q,net)) continue;
                int next=l.index(q);
                if (parent[next]!=-1) continue;
                parent[next]=id; open.push(next);
            }
        }
        return result;
    }
};
#endif
