#ifndef DIJKSTRA_3D_HPP
#define DIJKSTRA_3D_HPP
#include "Search3D.hpp"
class Dijkstra3D : public IRouter3D {
public:
    SearchResult route(const Layout& l, const Net3D& n, const std::vector<int>& o,
                       const std::vector<Cost>& h) const override {
        return weightedSearch(l,n,o,h,false);
    }
    SearchResult routeToTree(const Layout& l, const Net3D& n, const std::vector<int>& roots,
                             int target, const std::vector<int>& o, const std::vector<Cost>& h,
                             const std::vector<bool>& own) const override {
        return weightedSearchToTree(l,n,roots,target,o,h,own,false);
    }
};
#endif
