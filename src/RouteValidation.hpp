#ifndef ROUTE_VALIDATION_HPP
#define ROUTE_VALIDATION_HPP
#include "IRouter3D.hpp"
#include <set>

struct Validation {
    bool success=false;
    int routed_nets=0, unrouted_nets=0, invalid_nets=0, unresolved_conflicts=0;
    Cost wirelength=0, via_count=0, weighted_cost=0;
    std::vector<bool> valid, local_valid;
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
#endif
