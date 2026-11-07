#include "performance_class.h"
#include "test_session.h"
#include <cmath>
#include <iostream>
#include <stdexcept>
int main() try {
  const char expected[]={'D','C','B','A'};int index=0;
  for (double acceleration:{.8,1.,1.15,1.2}) {
    racer::VehicleSetup setup{acceleration,1,1};
    const auto rating=racer::prototypeRating(setup);
    if (rating.className!=expected[index++]) throw std::runtime_error("class band");
    racer::Simulation sim;racer::TestSession test;
    test.start(racer::TestKind::Acceleration,0,setup,sim);
    for (int i=0;i<2400 && test.active();++i) test.tick(sim,{});
    if (!test.result().valid || std::abs(test.result().seconds-rating.targetSeconds)>racer::step)
      throw std::runtime_error("class prediction differs from measured automatic test");
    std::cout<<rating.className<<" target="<<rating.targetSeconds<<" measured="<<test.result().seconds<<'\n';
  }
  std::cout<<"PASS: authored performance bands track measured prototype acceleration\n";
} catch (const std::exception &e) { std::cerr<<"FAIL: "<<e.what()<<'\n';return 1; }
