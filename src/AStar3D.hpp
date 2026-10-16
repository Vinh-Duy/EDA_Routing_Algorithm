#ifndef ASTAR_3D_HPP
#define ASTAR_3D_HPP
#include "Search3D.hpp"
class AStar3D : public IRouter3D {
public:
    SearchResult route(const Layout& l, const Net3D& n, const std::vector<int>& o,
                       const std::vector<Cost>& h) const override {
        return weightedSearch(l,n,o,h,true);
    }
};
#endif
