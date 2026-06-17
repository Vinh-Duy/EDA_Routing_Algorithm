# EDA Router Project

A high-performance VLSI routing framework implemented in C++, utilizing Object-Oriented Programming (OOP) and the Strategy Design Pattern to provide a modular, extensible, and efficient pathfinding environment.

---

## Project Structure

    EDA-Router/
    ├── data/                 # Benchmark chip layouts (.txt)
    ├── src/
    │   ├── main.cpp          # System entry point & orchestration
    │   ├── IRouter.hpp       # Interface definition (Strategy Pattern)
    │   ├── AStar2D.hpp       # A* search implementation
    │   └── BFS2D.hpp         # Breadth-First Search implementation
    └── README.md

---

## Core Features

* **Extensible Architecture:** Implements the Strategy Pattern, allowing seamless integration of new routing algorithms (e.g., Dijkstra, Lee's) without modifying core system logic.
* **Automated Data Processing:** Dynamically parses grid layouts and automatically maps multi-net connectivity (Source-Target pairs).
* **Performance Benchmarking:** Integrated with `<chrono>` to provide microsecond-level (µs) execution time analysis.
* **Industry-Standard Practices:** Adheres to modern C++17 standards, ensuring clean, maintainable, and memory-efficient code.

---

## Getting Started

### Prerequisites

* A C++17 compatible compiler (e.g., `g++`, `clang++`).

### Build & Run

From the root directory, compile and run the project:

    # Compile the project
    g++ -std=c++17 src/main.cpp -o router

    # Execute the binary
    ./router

> **Note:** Ensure `main.cpp` points to your desired layout file in the `data/` directory before running.

---

## Future Roadmap

* **Multi-Layer Support:** Transitioning the coordinate system from Point `{x, y}` to Point `{x, y, z}` to support 3D VLSI routing.
* **Advanced Cost Metrics:** Implementation of VIA penalty costs to optimize signal integrity and minimize layer transitions.

---

*Developed for research and academic exploration in Electronic Design Automation (EDA).*