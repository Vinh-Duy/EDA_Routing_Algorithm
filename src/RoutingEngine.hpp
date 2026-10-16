#ifndef ROUTING_ENGINE_HPP
#define ROUTING_ENGINE_HPP
#include "RouteValidation.hpp"
#include <chrono>

struct RoutingRun {
    std::vector<Path> paths;
    std::vector<Cost> search_costs;
    Validation validation;
    int passes=0;
    std::uint64_t expanded=0;
    double runtime_ms=0;
};
inline RoutingRun routeAll(const Layout& l, const IRouter3D& router, int maxIterations) {
    if (maxIterations<1 || maxIterations>10000) throw std::invalid_argument("max-iterations must be 1..10000");
    auto start=std::chrono::steady_clock::now();
    RoutingRun run;
    run.paths.resize(l.nets.size()); run.search_costs.resize(l.nets.size());
    std::vector<int> occupancy(l.cells.size(),0);
    std::vector<Cost> history(l.cells.size(),0);
    for (int pass=0;pass<maxIterations;++pass) {
        ++run.passes;
        // Full rip-up: all occupancy is rebuilt, never erased via display symbols.
        std::fill(occupancy.begin(),occupancy.end(),0);
        for (std::size_t n=0;n<l.nets.size();++n) {
            auto result=router.route(l,l.nets[n],occupancy,history);
            run.expanded+=result.expanded;
            run.paths[n]=std::move(result.path); run.search_costs[n]=result.search_cost;
            for (Point3D p: run.paths[n]) ++occupancy.at(l.index(p));
        }
        run.validation=validateRoutes(l,run.paths);
        if (run.validation.success || run.validation.unresolved_conflicts==0) break;
        for (std::size_t cell=0;cell<history.size();++cell)
            if (run.validation.owners[cell].size()>1) history[cell]+=HISTORY_INCREMENT;
    }
    run.runtime_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
    return run;
}
#endif
