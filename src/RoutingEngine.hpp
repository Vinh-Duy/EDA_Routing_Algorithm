#ifndef ROUTING_ENGINE_HPP
#define ROUTING_ENGINE_HPP
#include "RouteValidation.hpp"
#include <chrono>

enum class NetOrder { Numeric, Reverse };

struct RoutingRun {
    std::vector<Path> paths;
    std::vector<RouteTree3D> trees;
    std::vector<Cost> search_costs;
    Cost search_cost_total=0;
    Validation validation;
    int passes=0;
    std::uint64_t expanded=0;
    double runtime_ms=0;
    std::string termination_reason="iteration_limit";
    std::string net_order="numeric";
};
inline RoutingRun routeAll(const Layout& l, const IRouter3D& router, int maxIterations,
                           NetOrder order=NetOrder::Numeric) {
    if (maxIterations<1 || maxIterations>10000) throw std::invalid_argument("max-iterations must be 1..10000");
    l.validateShape();
    auto start=std::chrono::steady_clock::now();
    RoutingRun run;
    run.net_order=order==NetOrder::Reverse ? "reverse" : "numeric";
    run.paths.resize(l.nets.size()); run.trees.resize(l.nets.size()); run.search_costs.resize(l.nets.size());
    std::vector<int> occupancy(l.cells.size(),0);
    std::vector<Cost> history(l.cells.size(),0);
    for (int pass=0;pass<maxIterations;++pass) {
        ++run.passes;
        // Full rip-up: all occupancy is rebuilt, never erased via display symbols.
        std::fill(occupancy.begin(),occupancy.end(),0);
        run.search_cost_total=0;
        // Keep stored net/path indices canonical; only the search schedule changes.
        for (std::size_t position=0;position<l.nets.size();++position) {
            const std::size_t n=order==NetOrder::Reverse ? l.nets.size()-1-position : position;
            const auto& net=l.nets[n];
            const std::vector<Point3D> terminals=net.terminals.empty()
                ? std::vector<Point3D>{net.src,net.dst} : net.terminals;
            RouteTree3D tree;
            std::vector<bool> ownTree(l.cells.size(),false);
            if (!terminals.empty() && l.contains(terminals.front())) ownTree[l.index(terminals.front())]=true;
            Path legacyPath;
            if (terminals.size()==2 && terminals.front()==terminals.back())
                legacyPath.push_back(terminals.front());
            Cost netSearchCost=0;
            for (std::size_t t=1;t<terminals.size();++t) {
                Point3D terminal=terminals[t];
                if (!l.contains(terminal)) continue;
                int target=l.index(terminal);
                if (ownTree[target]) continue;
                std::vector<int> sources;
                for (std::size_t cell=0;cell<ownTree.size();++cell)
                    if (ownTree[cell]) sources.push_back(static_cast<int>(cell));
                auto result=router.routeToTree(l,net,sources,target,occupancy,history,ownTree);
                run.expanded+=result.expanded;
                if (result.search_cost>std::numeric_limits<Cost>::max()-netSearchCost ||
                    result.search_cost>std::numeric_limits<Cost>::max()-run.search_cost_total)
                    throw std::overflow_error("Accumulated route-tree search cost overflow");
                netSearchCost+=result.search_cost; run.search_cost_total+=result.search_cost;
                if (result.path.empty()) continue;
                if (terminals.size()==2) legacyPath=result.path;
                for (std::size_t step=1;step<result.path.size();++step) {
                    int a=l.index(result.path[step-1]),b=l.index(result.path[step]);
                    TreeEdge3D edge{result.path[step-1],result.path[step]};
                    if (b<a) std::swap(edge.a,edge.b);
                    tree.edges.push_back(edge);
                    ownTree[a]=true; ownTree[b]=true;
                }
            }
            std::sort(tree.edges.begin(),tree.edges.end(),[](const TreeEdge3D& a,const TreeEdge3D& b) {
                return std::tie(a.a.z,a.a.x,a.a.y,a.b.z,a.b.x,a.b.y) <
                       std::tie(b.a.z,b.a.x,b.a.y,b.b.z,b.b.x,b.b.y);
            });
            tree.edges.erase(std::unique(tree.edges.begin(),tree.edges.end()),tree.edges.end());
            run.paths[n]=std::move(legacyPath); run.trees[n]=std::move(tree);
            run.search_costs[n]=netSearchCost;
            for (std::size_t cell=0;cell<ownTree.size();++cell) if (ownTree[cell]) ++occupancy[cell];
        }
        run.validation=validateRouteTrees(l,run.trees);
        if (run.validation.success) {
            run.termination_reason="success";
            break;
        }
        if (run.validation.unresolved_conflicts==0) {
            run.termination_reason="unreachable";
            break;
        }
        if (!router.respondsToCongestion()) {
            run.termination_reason="congestion_insensitive";
            break;
        }
        for (std::size_t cell=0;cell<history.size();++cell)
            if (run.validation.owners[cell].size()>1) history[cell]+=HISTORY_INCREMENT;
    }
    run.runtime_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
    return run;
}
#endif
