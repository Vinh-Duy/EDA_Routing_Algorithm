#ifndef JSON_OUTPUT_HPP
#define JSON_OUTPUT_HPP
#include "RoutingEngine.hpp"
#include <fstream>
#include <iomanip>
inline void writePoint(std::ostream& out,Point3D p) {
    out << "{\"z\":" << p.z << ",\"x\":" << p.x << ",\"y\":" << p.y << '}';
}
inline void writeRun(const std::string& filename, const std::string& algorithm,
                     const Layout& l, const RoutingRun& run) {
    std::ofstream out(filename);
    if (!out) throw std::runtime_error("Cannot open output: "+filename);
    const auto& v=run.validation;
    out << std::boolalpha << std::setprecision(12)
        << "{\n  \"schema_version\": 2,\n  \"algorithm\": \"" << algorithm << "\",\n"
        << "  \"success\": " << v.success << ",\n"
        << "  \"termination_reason\": \"" << run.termination_reason << "\",\n"
        << "  \"net_order\": \"" << run.net_order << "\",\n"
        << "  \"dimensions\": [" << l.layers << ',' << l.rows << ',' << l.cols << "],\n"
        << "  \"cost_model\": {\"planar\":1,\"via\":6,\"occupied_cell\":100,\"history_increment\":50},\n"
        << "  \"metrics\": {\n"
        << "    \"total_nets\": " << l.nets.size() << ",\n    \"routed_nets\": " << v.routed_nets
        << ",\n    \"success_rate\": " << static_cast<double>(v.routed_nets)/l.nets.size()
        << ",\n    \"unrouted_nets\": " << v.unrouted_nets << ",\n    \"invalid_nets\": " << v.invalid_nets
        << ",\n    \"unresolved_conflicts\": " << v.unresolved_conflicts
        << ",\n    \"unconnected_terminals\": " << v.unconnected_terminals
        << ",\n    \"wirelength\": " << v.wirelength << ",\n    \"via_count\": " << v.via_count
        << ",\n    \"branch_count\": " << v.branch_count
        << ",\n    \"graph_steps\": " << v.wirelength+v.via_count
        << ",\n    \"weighted_cost\": " << v.weighted_cost;
    out << ",\n    \"search_cost\": " << run.search_cost_total << ",\n    \"routing_passes\": " << run.passes
        << ",\n    \"reroute_iterations\": " << run.passes-1
        << ",\n    \"runtime_ms\": " << run.runtime_ms << ",\n    \"nodes_expanded\": " << run.expanded << "\n  },\n"
        << "  \"obstacles\": [";
    bool first=true;
    for (std::size_t i=0;i<l.cells.size();++i) if (l.cells[i]=="#") {
        if (!first) out << ',';
        first=false; writePoint(out,l.point(static_cast<int>(i)));
    }
    out << "],\n  \"conflicts\": ["; first=true;
    for (std::size_t i=0;i<v.owners.size();++i) if (v.owners[i].size()>1) {
        if (!first) out << ',';
        first=false; out << "{\"cell\":"; writePoint(out,l.point(static_cast<int>(i)));
        out << ",\"nets\":[";
        for (std::size_t j=0;j<v.owners[i].size();++j) {
            if (j) out << ',';
            out << '"' << l.nets[v.owners[i][j]].name << '"';
        }
        out << "]}";
    }
    out << "],\n  \"nets\": [\n";
    for (std::size_t n=0;n<l.nets.size();++n) {
        if (n) out << ",\n";
        out << "    {\"name\":\"" << l.nets[n].name << "\",\"source\":"; writePoint(out,l.nets[n].src);
        out << ",\"target\":"; writePoint(out,l.nets[n].dst);
        const auto& net=l.nets[n];
        const std::vector<Point3D> terminals=net.terminals.empty()
            ? std::vector<Point3D>{net.src,net.dst} : net.terminals;
        out << ",\"terminals\":[";
        for (std::size_t t=0;t<terminals.size();++t) { if (t) out << ','; writePoint(out,terminals[t]); }
        out << "],\"connected_terminals\":" << (terminals.size()-static_cast<std::size_t>(v.unconnected_by_net[n]))
            << ",\"unconnected_terminals\":" << v.unconnected_by_net[n]
            << ",\"branch_count\":" << v.branch_counts[n]
            << ",\"valid\":" << v.valid[n] << ",\"local_valid\":" << v.local_valid[n]
            << ",\"search_cost\":" << run.search_costs[n] << ",\"path\":[";
        for (std::size_t i=0;i<run.paths[n].size();++i) { if (i) out << ','; writePoint(out,run.paths[n][i]); }
        out << ']';
        if (terminals.size()>2) {
            out << ",\"tree_edges\":[";
            for (std::size_t e=0;e<run.trees[n].edges.size();++e) {
                if (e) out << ',';
                out << '['; writePoint(out,run.trees[n].edges[e].a); out << ',';
                writePoint(out,run.trees[n].edges[e].b); out << ']';
            }
            out << ']';
        }
        out << '}';
    }
    out << "\n  ]\n}\n"; out.close();
    if (!out) throw std::runtime_error("Failed writing output: "+filename);
}
#endif
