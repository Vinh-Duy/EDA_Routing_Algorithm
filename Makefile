CXX = c++
CXXFLAGS = -std=c++17 -O2 -Wall -Wextra -Wpedantic
PYTHON ?= python3
HEADERS := $(wildcard src/*.hpp)

.PHONY: all test sanitize benchmark figures
all: router
router: src/main.cpp $(HEADERS)
	$(CXX) $(CXXFLAGS) src/main.cpp -o $@
build/test_router: tests/test_router.cpp $(HEADERS)
	mkdir -p build
	$(CXX) $(CXXFLAGS) -Isrc tests/test_router.cpp -o $@
test: router build/test_router
	./build/test_router
	$(PYTHON) -m unittest discover -s tests -v
sanitize:
	mkdir -p build
	$(CXX) -std=c++17 -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer -Isrc tests/test_router.cpp -o build/test_router_sanitized
	./build/test_router_sanitized
benchmark: router
	$(PYTHON) benchmarks/run_benchmarks.py --repetitions 20
figures:
	$(PYTHON) benchmarks/plot_results.py
