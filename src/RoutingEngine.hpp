#ifndef ROUTING_ENGINE_HPP
#define ROUTING_ENGINE_HPP
#include "RouteValidation.hpp"
#include "Search3D.hpp"
#include <chrono>

enum class NetOrder { Numeric, Reverse };
enum class TerminalOrder { Input, Nearest };
enum class NearestSelector { Repeated, MultiSource };

struct RoutingRun {
    std::vector<Path> paths;
    std::vector<RouteTree3D> trees;
    std::vector<Cost> search_costs;
    std::vector<int> search_counts;
    std::vector<std::vector<Point3D>> attached_terminals;
    std::uint64_t selection_dijkstra_runs=0;
    std::uint64_t selection_settled_vertices=0;
    std::uint64_t selection_edges_examined=0;
    std::uint64_t selection_heap_pushes=0;
    std::uint64_t selection_heap_pops=0;
    std::uint64_t route_searches=0;
    std::uint64_t route_nodes_expanded=0;
    double selection_runtime_ms=0;
    double route_runtime_ms=0;
    Cost search_cost_total=0;
    Validation validation;
    int passes=0;
    std::uint64_t expanded=0;
    double runtime_ms=0;
    std::string termination_reason="iteration_limit";
    std::string net_order="numeric";
    std::string terminal_order="input";
    std::string nearest_selector="multisource";
};
inline RoutingRun routeAll(const Layout& l, const IRouter3D& router, int maxIterations,
                           NetOrder order=NetOrder::Numeric,
                           TerminalOrder terminalOrder=TerminalOrder::Input,
                           NearestSelector nearestSelector=NearestSelector::MultiSource) {
    if (maxIterations<1 || maxIterations>10000) throw std::invalid_argument("max-iterations must be 1..10000");
    l.validateShape();
    auto start=std::chrono::steady_clock::now();
    RoutingRun run;
    run.net_order=order==NetOrder::Reverse ? "reverse" : "numeric";
    run.terminal_order=terminalOrder==TerminalOrder::Nearest ? "nearest" : "input";
    run.nearest_selector=nearestSelector==NearestSelector::Repeated ? "repeated" : "multisource";
    run.paths.resize(l.nets.size()); run.trees.resize(l.nets.size()); run.search_costs.resize(l.nets.size());
    run.search_counts.resize(l.nets.size()); run.attached_terminals.resize(l.nets.size());
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
            run.attached_terminals[n].clear();
            RouteTree3D tree;
            std::vector<bool> ownTree(l.cells.size(),false);
            if (!terminals.empty() && l.contains(terminals.front())) ownTree[l.index(terminals.front())]=true;
            Path legacyPath;
            if (terminals.size()==2 && terminals.front()==terminals.back())
                legacyPath.push_back(terminals.front());
            Cost netSearchCost=0;
            auto addRoute=[&](Point3D terminal,const SearchResult& result) {
                if (result.search_cost>std::numeric_limits<Cost>::max()-netSearchCost ||
                    result.search_cost>std::numeric_limits<Cost>::max()-run.search_cost_total)
                    throw std::overflow_error("Accumulated route-tree search cost overflow");
                netSearchCost+=result.search_cost;
                run.search_cost_total+=result.search_cost;
                run.attached_terminals[n].push_back(terminal);
                if (terminals.size()==2) legacyPath=result.path;
                for (std::size_t step=1;step<result.path.size();++step) {
                    int a=l.index(result.path[step-1]),b=l.index(result.path[step]);
                    TreeEdge3D edge{result.path[step-1],result.path[step]};
                    if (b<a) std::swap(edge.a,edge.b);
                    tree.edges.push_back(edge);
                    ownTree[a]=true; ownTree[b]=true;
                }
            };
            auto treeSources=[&]() {
                std::vector<int> sources;
                for (std::size_t cell=0;cell<ownTree.size();++cell)
                    if (ownTree[cell]) sources.push_back(static_cast<int>(cell));
                return sources;
            };
            auto accountRouteSearch=[&](const SearchResult& result) {
                ++run.route_searches;
                run.route_nodes_expanded+=result.expanded;
                run.expanded+=result.expanded;
            };
            if (terminalOrder==TerminalOrder::Input) {
                for (std::size_t t=1;t<terminals.size();++t) {
                    Point3D terminal=terminals[t];
                    if (!l.contains(terminal)) continue;
                    int target=l.index(terminal);
                    if (ownTree[target]) continue;
                    const auto routeStart=std::chrono::steady_clock::now();
                    auto result=router.routeToTree(l,net,treeSources(),target,occupancy,history,ownTree);
                    run.route_runtime_ms+=std::chrono::duration<double,std::milli>(
                        std::chrono::steady_clock::now()-routeStart).count();
                    ++run.search_counts[n];
                    accountRouteSearch(result);
                    if (!result.path.empty()) addRoute(terminal,result);
                }
            } else {
                while (true) {
                    const auto selectionStart=std::chrono::steady_clock::now();
                    const auto selection=nearestSelector==NearestSelector::Repeated
                        ? selectNearestByRepeatedDijkstra(l,net,terminals,occupancy,history,ownTree)
                        : selectNearestByMultiSourceDijkstra(l,net,terminals,treeSources(),
                                                             occupancy,history,ownTree);
                    run.selection_runtime_ms+=std::chrono::duration<double,std::milli>(
                        std::chrono::steady_clock::now()-selectionStart).count();
                    run.selection_dijkstra_runs+=selection.dijkstra_runs;
                    run.selection_settled_vertices+=selection.settled_vertices;
                    run.selection_edges_examined+=selection.edges_examined;
                    run.selection_heap_pushes+=selection.heap_pushes;
                    run.selection_heap_pops+=selection.heap_pops;
                    run.search_counts[n]+=static_cast<int>(selection.dijkstra_runs);
                    run.expanded+=selection.settled_vertices;
                    if (!selection.found) break;
                    const std::size_t selected=selection.terminal_index;
                    const auto routeStart=std::chrono::steady_clock::now();
                    auto result=router.routeToTree(l,net,treeSources(),l.index(terminals[selected]),
                                                   occupancy,history,ownTree);
                    run.route_runtime_ms+=std::chrono::duration<double,std::milli>(
                        std::chrono::steady_clock::now()-routeStart).count();
                    ++run.search_counts[n];
                    accountRouteSearch(result);
                    if (result.path.empty()) break;
                    addRoute(terminals[selected],result);
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
