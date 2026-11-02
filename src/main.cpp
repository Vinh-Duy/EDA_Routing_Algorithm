#include "AStar3D.hpp"
#include "BFS3D.hpp"
#include "Dijkstra3D.hpp"
#include "LayoutIO.hpp"
#include "JsonOutput.hpp"
#include <iostream>
#include <memory>
#include <filesystem>

int main(int argc, char** argv) {
    try {
        std::string input="data/chip_layout_hell.txt", output="output.json", algorithm="astar";
        int maxIterations=10;
        NetOrder order=NetOrder::Numeric;
        TerminalOrder terminalOrder=TerminalOrder::Input;
        NearestSelector nearestSelector=NearestSelector::MultiSource;
        for (int i=1;i<argc;++i) {
            std::string arg=argv[i];
            if (arg=="--help") {
                std::cout << "Usage: router [--input FILE] [--algorithm astar|bfs|dijkstra]\n"
                             "              [--output FILE] [--max-iterations N] [--net-order numeric|reverse]\n"
                             "              [--terminal-order input|nearest] [--nearest-selector repeated|multisource]\n"
                             "              [--help]\n"
                             "Defaults: data/chip_layout_hell.txt, astar, output.json, 10 total passes.\n"
                             "Nearest selector defaults to multisource; it applies only with --terminal-order nearest.\n"
                             "Exit: 0 validated success; 2 routing incomplete/conflicted; 1 input/I/O error.\n";
                return 0;
            }
            if (arg!="--input" && arg!="--output" && arg!="--algorithm" &&
                arg!="--max-iterations" && arg!="--net-order" && arg!="--terminal-order" &&
                arg!="--nearest-selector")
                throw std::invalid_argument("Unknown option: "+arg);
            if (++i>=argc) throw std::invalid_argument("Missing value for "+arg);
            std::string value=argv[i];
            if (arg=="--input") input=value;
            else if (arg=="--output") output=value;
            else if (arg=="--algorithm") algorithm=value;
            else if (arg=="--net-order") {
                if (value!="numeric" && value!="reverse")
                    throw std::invalid_argument("net-order must be numeric or reverse");
                order=value=="reverse" ? NetOrder::Reverse : NetOrder::Numeric;
            }
            else if (arg=="--terminal-order") {
                if (value!="input" && value!="nearest")
                    throw std::invalid_argument("terminal-order must be input or nearest");
                terminalOrder=value=="nearest" ? TerminalOrder::Nearest : TerminalOrder::Input;
            }
            else if (arg=="--nearest-selector") {
                if (value!="repeated" && value!="multisource")
                    throw std::invalid_argument("nearest-selector must be repeated or multisource");
                nearestSelector=value=="repeated" ? NearestSelector::Repeated : NearestSelector::MultiSource;
            }
            else maxIterations=positiveInteger(value);
        }
        std::unique_ptr<IRouter3D> router;
        if (algorithm=="astar") router=std::make_unique<AStar3D>();
        else if (algorithm=="bfs") router=std::make_unique<BFS3D>();
        else if (algorithm=="dijkstra") router=std::make_unique<Dijkstra3D>();
        else throw std::invalid_argument("Algorithm must be astar, bfs, or dijkstra");
        // equivalent() detects relative aliases, symlinks, and hardlinks alike.
        // Check before opening an output stream, which would truncate the input.
        if (std::filesystem::exists(output) && std::filesystem::equivalent(input,output))
            throw std::invalid_argument("Input and output must refer to different files");
        Layout layout=readLayoutFile(input);
        RoutingRun run=routeAll(layout,*router,maxIterations,order,terminalOrder,nearestSelector);
        writeRun(output,algorithm,layout,run);
        std::cout << (run.validation.success ? "SUCCESS" : "INCOMPLETE") << ": "
                  << run.validation.routed_nets << '/' << layout.nets.size() << " valid nets, "
                  << run.validation.unrouted_nets << " empty paths, " << run.validation.unresolved_conflicts
                  << " conflicting cells, " << run.validation.unconnected_terminals
                  << " unconnected terminals; " << run.runtime_ms << " ms\n";
        return run.validation.success ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << "ERROR: " << error.what() << '\n';
        return 1;
    }
}
