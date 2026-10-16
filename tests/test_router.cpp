#include "AStar2D.hpp"
#include "BFS2D.hpp"
#include "AStar3D.hpp"
#include "BFS3D.hpp"
#include "Dijkstra3D.hpp"
#include "LayoutIO.hpp"
#include "RoutingEngine.hpp"
#include <functional>
#include <iostream>
#include <random>
#include <limits>

void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
Layout parse(const std::string& text) { std::istringstream in(text); return readLayout(in); }
SearchResult search(const Layout& l, const IRouter3D& router) {
    return router.route(l,l.nets[0],std::vector<int>(l.cells.size()),std::vector<Cost>(l.cells.size()));
}
// Independent Bellman-Ford oracle: no production edgeCost, neighbors, or priority queue.
Cost oracle(const Layout& l, const std::vector<int>& occ, const std::vector<Cost>& history, bool unit) {
    const Cost inf=1000000000;
    std::vector<Cost> d(l.cells.size(),inf); d[l.index(l.nets[0].src)]=0;
    for (std::size_t round=1;round<l.cells.size();++round) {
        bool changed=false;
        for (std::size_t a=0;a<l.cells.size();++a) for (std::size_t b=0;b<l.cells.size();++b) {
            Point3D p=l.point(static_cast<int>(a)),q=l.point(static_cast<int>(b));
            if (!l.legal(p,l.nets[0]) || !l.legal(q,l.nets[0]) ||
                std::abs(p.z-q.z)+std::abs(p.x-q.x)+std::abs(p.y-q.y)!=1 || d[a]==inf) continue;
            Cost cost=unit ? 1 : (p.z==q.z ? 1 : 6)+history[b]+(occ[b] ? 100 : 0);
            if (d[b]>d[a]+cost) { d[b]=d[a]+cost; changed=true; }
        }
        if (!changed) break;
    }
    return d[l.index(l.nets[0].dst)];
}
int main() {
    int passed=0;
    auto test=[&](const char* name,const std::function<void()>& fn) {
        try { fn(); ++passed; std::cout << "PASS " << name << '\n'; }
        catch(const std::exception& e) { std::cerr << "FAIL " << name << ": " << e.what() << '\n'; std::exit(1); }
    };
    AStar3D astar; BFS3D bfs; Dijkstra3D dijkstra;
    std::vector<const IRouter3D*> routers={&astar,&bfs,&dijkstra};
    test("single net and adjacent endpoints",[&] {
        auto l=parse("1 2\nS1 T1\n");
        for(auto r:routers) { auto run=routeAll(l,*r,10); require(run.validation.success,"single net"); require(run.validation.wirelength==1,"one edge"); }
    });
    test("unreachable is failure with zero conflicts",[&] {
        auto l=parse("1 3\nS1 # T1\n");
        for(auto r:routers) { auto run=routeAll(l,*r,10); require(!run.validation.success && run.validation.unrouted_nets==1 && run.validation.unresolved_conflicts==0,"unreachable"); }
    });
    test("VIA at target and multi-layer accounting",[&] {
        auto l=parse("3 1 1\nS1\n.\nT1\n");
        for(auto r:routers) { auto run=routeAll(l,*r,10); require(run.validation.success && run.validation.via_count==2 && run.validation.wirelength==0 && run.validation.weighted_cost==12,"VIA count"); }
    });
    test("obstacle avoidance and deterministic repeat",[&] {
        auto l=parse("3 3\nS1 # T1\n. # .\n. . .\n");
        for(auto r:routers) { auto a=search(l,*r), b=search(l,*r); require(a.path==b.path && a.path.size()==7 && validateRoutes(l,{a.path}).success,"obstacle detour"); }
    });
    test("source equals destination and invalid endpoints",[&] {
        Layout l{1,1,1,{"."},{{"Net1",{0,0,0},{0,0,0}}}};
        for(auto r:routers) require(search(l,*r).path.size()==1 && routeAll(l,*r,1).validation.success,"zero length");
        l.cells[0]="#"; for(auto r:routers) require(search(l,*r).path.empty(),"blocked source");
        l.nets[0].src={-1,0,0}; for(auto r:routers) require(search(l,*r).path.empty(),"out of bounds");
    });
    test("validator rejects jumps obstacles pins cycles wrong endpoints",[&] {
        auto l=parse("2 3\nS1 # T1\nS2 . T2\n");
        for(const Path& p:std::vector<Path>{{{0,0,0},{0,0,2}},{{0,0,0},{0,0,1},{0,0,2}},
            {{0,0,0},{0,1,0},{0,1,1},{0,1,2},{0,0,2}},{{0,0,0},{0,1,1},{0,0,0},{0,0,2}},
            {{0,0,2}},{{0,0,0},{100,0,0},{0,0,2}}})
            require(!validateRoutes(l,{p,{}}).local_valid[0],"invalid path accepted");
        require(!validateRoutes(l,{}).success,"missing paths");
    });
    test("overlap at VIA cell retains both net identities",[&] {
        Layout l{2,2,3,std::vector<std::string>(12,"."),
            {{"Net1",{0,0,0},{1,0,1}},{"Net2",{1,1,1},{1,0,2}}}};
        auto v=validateRoutes(l,{{{0,0,0},{0,0,1},{1,0,1}},{{1,1,1},{1,0,1},{1,0,2}}});
        require(!v.success && v.unresolved_conflicts==1 && v.routed_nets==0 && v.owners[l.index({1,0,1})].size()==2,"VIA overlap hidden");
    });
    test("input validation and nonconsecutive net ids",[&] {
        for(const std::string& s:std::vector<std::string>{"","0 2\n","-1 2\n","1 2 junk\nS1 T1\n","1 3\nS1 T1\n",
            "1 2\nS1 T1 .\n","1 2\nS1 S1\n","1 2\nS1 .\n","1 2\nT1 T1\n","1 2\nS1 T2\n",
            "1 2\n. .\n","1 2\nS0 T0\n","1 2\nS01 T01\n","1 2\nX T1\n","1 2\nS1 T1\n. .\n",
            "2147483647 2147483647 2147483647\n"}) {
            bool rejected=false; try { parse(s); } catch(const std::exception&) { rejected=true; }
            require(rejected,"bad input accepted");
        }
        require(parse("1 4\nS2 T2 S9 T9\n").nets.size()==2,"gapped ids lost");
    });
    test("successful and impossible multi-net",[&] {
        auto good=parse("3 3\nS1 . T1\n# # #\nS2 . T2\n");
        auto bad=parse("3 3\n# S1 #\nS2 . T2\n# T1 #\n");
        for(auto r:routers) {
            require(routeAll(good,*r,3).validation.success,"separate nets");
            auto run=routeAll(bad,*r,3);
            require(!run.validation.success && run.validation.unresolved_conflicts==1 && run.passes==3,"unavoidable overlap");
        }
    });
    test("history resolves congestion with consistent occupancy",[&] {
        auto l=readLayoutFile("benchmarks/layouts/congestion.txt");
        auto first=routeAll(l,astar,1), later=routeAll(l,astar,10);
        require(!first.validation.success && later.validation.success && later.passes>1,"rerouting regression");
        require(validateRoutes(l,later.paths).success,"stale occupancy");
    });
    test("200 seeded graphs vs independent weighted and unit-cost oracle",[&] {
        std::mt19937 random(20261016);
        for(int trial=0;trial<200;++trial) {
            Layout l{2,3,3,std::vector<std::string>(18,"."),{{"Net1",{0,0,0},{1,2,2}}}};
            std::vector<int> occ(18); std::vector<Cost> history(18);
            for(int i=1;i<17;++i) { if(random()%5==0) l.cells[i]="#"; occ[i]=random()%2; history[i]=random()%11; }
            Cost expected=oracle(l,occ,history,false);
            for(auto r:{static_cast<const IRouter3D*>(&astar),static_cast<const IRouter3D*>(&dijkstra)}) {
                auto found=r->route(l,l.nets[0],occ,history);
                require((expected==1000000000)==found.path.empty(),"reachability mismatch");
                if(!found.path.empty()) require(found.search_cost==expected && validateRoutes(l,{found.path}).success,"weighted optimality");
            }
            auto found=bfs.route(l,l.nets[0],occ,history); expected=oracle(l,occ,history,true);
            require((expected==1000000000)==found.path.empty(),"BFS reachability");
            if(!found.path.empty()) require(static_cast<Cost>(found.path.size()-1)==expected,"BFS step optimality");
        }
    });
    test("negative penalties and broken reconstruction rejected",[&] {
        auto l=parse("1 2\nS1 T1\n"); bool rejected=false;
        try { astar.route(l,l.nets[0],{0,0},{0,-1}); } catch(const std::invalid_argument&) { rejected=true; }
        require(rejected,"negative cost"); rejected=false;
        try { reconstruct(l,0,1,{-1,-1}); } catch(const std::logic_error&) { rejected=true; }
        require(rejected,"broken reconstruction");
    });
    test("legacy 2D implementations edge cases",[&] {
        AStar2D a; BFS2D b;
        for(IRouter2D* r:std::vector<IRouter2D*>{&a,&b}) {
            std::vector<std::vector<std::string>> grid={{"S1",".","T1"}};
            require(r->route(grid,{0,0},{0,2},"o1") && grid[0][1]=="o1","2D route");
            require(r->route(grid,{0,0},{0,0},"o1"),"2D same endpoint");
            grid.clear(); require(!r->route(grid,{0,0},{0,0},"o1"),"empty grid");
            grid={{".","#"}}; require(!r->route(grid,{0,0},{0,1},"o1"),"blocked destination");
        }
    });
    std::cout << passed << " C++ test groups passed\n";
}
