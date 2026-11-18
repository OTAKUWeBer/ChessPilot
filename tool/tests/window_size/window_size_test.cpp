#include "../../../app/native/desktop_window_size.h"
#include <cstdlib>
#include <limits>

static void expect(double height, double ratio, DesktopWindowSize wanted) {
  const auto actual = desktop_window_size(height, ratio);
  if (actual.width != wanted.width || actual.height != wanted.height ||
      actual.minimum_width != wanted.minimum_width || actual.minimum_height != wanted.minimum_height) {
    std::abort();
  }
}
int main() {
  const DesktopWindowSize baseline{380, 520, 360, 480};
  expect(1080, 1, baseline);
  expect(768, 1, baseline);
  expect(1440, 2, baseline);
  expect(2160, 1, {537, 735, 509, 678});
  expect(2160, 2, baseline);
  expect(0, 1, baseline);
  expect(1080, 0, baseline);
  expect(std::numeric_limits<double>::quiet_NaN(), 1, baseline);
  expect(std::numeric_limits<double>::max(), std::numeric_limits<double>::min(), baseline);
  for (const int width : {1280, 1920, 2560, 3840, 5120, 7680}) {
    for (const int height : {720, 1080, 1440, 2160, 2880, 4320}) {
      for (const double ratio : {1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0}) {
        const auto main = desktop_window_size(height, ratio, width);
        for (const auto size : {main, desktop_setup_size(height, ratio, width, 180),
                               desktop_setup_size(height, ratio, width, 450)}) {
          if (size.width + 32 > width / ratio || size.height + 64 > height / ratio ||
              size.minimum_width > size.width || size.minimum_height > size.height ||
              size.minimum_width <= 0 || size.minimum_height <= 0) std::abort();
        }
      }
    }
  }
}
