#pragma once
#include "test_session.h"
#include <string>
namespace racer {
struct CourseGuidance {
  double distance = 0, bearing = 0;
  bool returnToApproach = false;
  std::string turn, crossing;
};
CourseGuidance courseGuidance(const Gate &, const Car &);
} // namespace racer
