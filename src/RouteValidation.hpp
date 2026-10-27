#ifndef ROUTE_VALIDATION_HPP
#define ROUTE_VALIDATION_HPP
#include "IRouter3D.hpp"
#include <set>
#include <map>

struct Validation {
    bool success=false;
    int routed_nets=0, unrouted_nets=0, invalid_nets=0, unresolved_conflicts=0;
    Cost wirelength=0, via_count=0, weighted_cost=0;
    int branch_count=0, unconnected_terminals=0;
    std::vector<bool> valid, local_valid;
    std::vector<int> branch_counts, unconnected_by_net;
    std::vector<std::vector<int>> owners;
    std::vector<std::string> errors;
};
// Independent of search results, cost estimates, grid symbols, and driver occupancy.
inline Validation validateRoutes(const Layout& l, const std::vector<Path>& paths) {
    l.validateShape();
    Validation v;
    v.valid.assign(l.nets.size(),false); v.local_valid=v.valid;
    v.owners.resize(l.cells.size());
    if (paths.size()!=l.nets.size()) v.errors.push_back("Path/net count mismatch");
    for (std::size_t n=0;n<l.nets.size();++n) {
        if (n>=paths.size() || paths[n].empty()) { ++v.unrouted_nets; continue; }
        const auto& path=paths[n]; const auto& net=l.nets[n];
        bool ok=path.front()==net.src && path.back()==net.dst;
        std::set<int> seen;
        Cost wire=0, vias=0;
        for (std::size_t i=0;i<path.size();++i) {
            Point3D p=path[i];
            if (!l.contains(p)) { ok=false; continue; }
            int id=l.index(p);
            if (!seen.insert(id).second) ok=false;
            else v.owners[id].push_back(static_cast<int>(n));
            if (!l.legal(p,net)) ok=false;
            if (i>0) {
                if (!l.contains(path[i-1]) || distance(p,path[i-1])!=1) ok=false;
                else if (p.z!=path[i-1].z) ++vias;
                else ++wire;
            }
        }
        v.local_valid[n]=v.valid[n]=ok;
        if (!ok) { ++v.invalid_nets; v.errors.push_back(net.name+": invalid path"); }
        else { v.wirelength+=wire; v.via_count+=vias; }
    }
    for (const auto& owners: v.owners) if (owners.size()>1) {
        ++v.unresolved_conflicts;
        for (int n: owners) v.valid[n]=false;
    }
    for (bool valid: v.valid) if (valid) ++v.routed_nets;
    v.weighted_cost=v.wirelength+VIA_STEP_COST*v.via_count;
    v.success=!l.nets.empty() && paths.size()==l.nets.size() &&
              v.routed_nets==static_cast<int>(l.nets.size());
    return v;
}

inline Validation validateRouteTrees(const Layout& l, const std::vector<RouteTree3D>& trees) {
    l.validateShape();
    Validation v;
    const std::size_t netCount=l.nets.size();
    v.valid.assign(netCount,false); v.local_valid.assign(netCount,false);
    v.branch_counts.assign(netCount,0); v.unconnected_by_net.assign(netCount,0);
    v.owners.resize(l.cells.size());
    if (trees.size()!=netCount) v.errors.push_back("Tree/net count mismatch");
    for (std::size_t n=0;n<netCount;++n) {
        if (n>=trees.size()) { ++v.unrouted_nets; continue; }
        const auto& net=l.nets[n];
        std::vector<Point3D> terminals=net.terminals.empty()
            ? std::vector<Point3D>{net.src,net.dst} : net.terminals;
        bool malformed=terminals.size()<2;
        std::vector<int> parent(l.cells.size());
        for (std::size_t i=0;i<parent.size();++i) parent[i]=static_cast<int>(i);
        auto find=[&](int x) {
            int root=x;
            while (parent[root]!=root) root=parent[root];
            while (parent[x]!=x) { int next=parent[x]; parent[x]=root; x=next; }
            return root;
        };
        std::set<std::pair<int,int>> edges;
        std::set<int> vertices;
        std::vector<int> degree(l.cells.size(),0);
        Cost wire=0,vias=0;
        bool hasCycle=false;
        int rootId=-1;
        if (!terminals.empty() && l.contains(terminals.front())) {
            rootId=l.index(terminals.front());
            // A coincident source/target is a valid zero-edge net and still
            // occupies its terminal cell for cross-net conflict detection.
            vertices.insert(rootId);
        }
        for (const auto& edge:trees[n].edges) {
            if (!l.contains(edge.a) || !l.contains(edge.b)) { malformed=true; continue; }
            int a=l.index(edge.a),b=l.index(edge.b);
            vertices.insert(a); vertices.insert(b);
            if (!l.legal(edge.a,net) || !l.legal(edge.b,net) || distance(edge.a,edge.b)!=1) {
                malformed=true; continue;
            }
            auto key=std::minmax(a,b);
            if (!edges.emplace(key.first,key.second).second) { malformed=true; continue; }
            ++degree[a]; ++degree[b];
            if (find(a)==find(b)) { hasCycle=true; malformed=true; }
            else parent[find(a)]=find(b);
            if (edge.a.z==edge.b.z) ++wire; else ++vias;
        }
        if (hasCycle) v.errors.push_back(net.name+": route contains a cycle");
        for (int id:vertices) v.owners[id].push_back(static_cast<int>(n));
        for (Point3D terminal:terminals) {
            bool connected=false;
            if (rootId>=0 && l.contains(terminal) && vertices.count(l.index(terminal)))
                connected=find(l.index(terminal))==find(rootId);
            if (!connected) { ++v.unconnected_by_net[n]; ++v.unconnected_terminals; }
        }
        if (vertices.empty()) malformed=true;
        if (!vertices.empty()) {
            const int component=find(*vertices.begin());
            for (int id:vertices) if (find(id)!=component) malformed=true;
        }
        const bool complete=!malformed && v.unconnected_by_net[n]==0;
        if (malformed) { ++v.invalid_nets; v.errors.push_back(net.name+": invalid route tree"); }
        if (!complete && v.unconnected_by_net[n]==0) v.errors.push_back(net.name+": terminals disconnected");
        v.local_valid[n]=v.valid[n]=complete;
        if (!malformed) {
            v.wirelength+=wire; v.via_count+=vias;
            int branches=0;
            for (int id:vertices) if (degree[id]>=3) ++branches;
            v.branch_counts[n]=branches; v.branch_count+=branches;
        }
        if (v.unconnected_by_net[n]>0) ++v.unrouted_nets;
    }
    for (const auto& owners:v.owners) if (owners.size()>1) {
        ++v.unresolved_conflicts;
        for (int n:owners) v.valid[n]=false;
    }
    for (bool valid:v.valid) if (valid) ++v.routed_nets;
    v.weighted_cost=v.wirelength+VIA_STEP_COST*v.via_count;
    v.success=netCount>0 && trees.size()==netCount && v.routed_nets==static_cast<int>(netCount);
    return v;
}
#endif
