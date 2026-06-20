# EDA Router Project

A high-performance **Multi-layer (3D) VLSI routing framework** implemented in C++. Utilizing Object-Oriented Programming (OOP) and the Strategy Design Pattern, this project provides a modular, extensible, and memory-efficient pathfinding environment for Electronic Design Automation (EDA).

---

## Project Structure

    EDA-Router/
    ├── data/                 # Benchmark chip layouts (2D & 3D Multi-layer .txt)
    ├── src/
    │   ├── main.cpp          # System entry point, auto-parser & orchestration
    │   ├── IRouter3D.hpp     # Universal 3D Interface definition (Strategy Pattern)
    │   ├── AStar3D.hpp       # 3D A* search with VIA penalty heuristic
    │   └── BFS3D.hpp         # 3D Breadth-First Search implementation
    ├── visualize.py          # Python 3D interactive visualization script
    └── README.md

---

## Core Features

* **Universal 3D Routing Architecture:** The core grid and coordinate systems (`Point3D {z, x, y}`) seamlessly handle both single-layer (2D) and multi-layer (3D) chip layouts. The system dynamically auto-detects the dimensionality from the benchmark files.
* **3D Interactive Visualization:** Integrated a Python-based Plotly frontend that reads generated JSON coordinates (`output.json`) from the C++ backend. It renders fully interactive, 3D multi-layer routing paths and VIA (vertical interconnect access) intersections in the browser.
* **Advanced Cost Metrics (VIA Penalty):** The A* implementation incorporates a sophisticated 3D heuristic that mathematically penalizes cross-layer transitions (VIAs). This optimizes routing logic to mimic real-world semiconductor manufacturing constraints.
* **Extensible Architecture:** Implements the Strategy Pattern (`IRouter3D` interface), allowing seamless integration of new routing algorithms without modifying the core parsing and orchestration logic.
* **Automated Data Processing:** Dynamically parses grid layouts, automatically maps multi-net connectivity (Source-Target pairs), and handles boundary checking across metal layers.
* **Performance Benchmarking:** Integrated with `<chrono>` to provide microsecond-level (µs) execution time analysis, proving the efficiency of heuristic searches versus brute-force algorithms.

---

## Getting Started

### Prerequisites

* A **C++17** compatible compiler (e.g., `g++`, `clang++`).
* **Python 3.x** (for 3D visualization).
* Python `plotly` library:
  
      pip3 install plotly

### Build & Run

From the root directory, follow these steps to compile the algorithm and visualize the results:

    # 1. Compile the C++ project
    g++ -std=c++17 src/main.cpp -o router

    # 2. Execute the binary (This routes the nets and generates output.json)
    ./router

    # 3. Launch the 3D Visualization in your web browser
    python3 visualize.py

> **Note:** Ensure `main.cpp` points to your desired layout file (e.g., `data/chip_layout_complex.txt`) before compiling. Every time you change the layout, re-run `./router` followed by `python3 visualize.py` to see the updated 3D paths.

---

## Future Roadmap

* **Congestion-Driven Routing (Rip-up and Reroute):** Implement negotiation-based routing to automatically resolve conflicts and short-circuits when multiple nets attempt to occupy the same grid spaces.
* **Multi-Terminal Nets:** Extend the routing capability from simple 2-pin (Source-Target) connections to complex multi-pin subnets using Rectilinear Steiner Minimum Trees (RSMT).

---

*Developed for research and academic exploration in Electronic Design Automation (EDA).*