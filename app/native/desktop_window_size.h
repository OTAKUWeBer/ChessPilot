#ifndef CHESSPILOT_DESKTOP_WINDOW_SIZE_H_
#define CHESSPILOT_DESKTOP_WINDOW_SIZE_H_
#include <algorithm>
#include <cmath>
#include <limits>

struct DesktopWindowSize {
  int width, height, minimum_width, minimum_height;
};

inline DesktopWindowSize fit_desktop_window(DesktopWindowSize size, double available_height,
                                           double pixel_ratio, double available_width) {
  const double height = available_height / pixel_ratio;
  const double width = available_width / pixel_ratio;
  if (!std::isfinite(height) || !std::isfinite(width) || height <= 0 || width <= 0 ||
      height > std::numeric_limits<int>::max() || width > std::numeric_limits<int>::max()) return size;
  size.width = std::min(size.width, std::max(80, static_cast<int>(width) - 32));
  size.height = std::min(size.height, std::max(80, static_cast<int>(height) - 64));
  size.minimum_width = std::min(size.minimum_width, size.width);
  size.minimum_height = std::min(size.minimum_height, size.height);
  return size;
}

inline DesktopWindowSize desktop_window_size(double available_height, double pixel_ratio,
                                              double available_width = 1920) {
  double scale = 1.0;
  if (std::isfinite(available_height) && available_height > 0 &&
      std::isfinite(pixel_ratio) && pixel_ratio > 0) {
    // Preserve src/main.py's dampened high-resolution desktop scaling.
    scale = std::max(std::sqrt(available_height / pixel_ratio / 1080.0), 1.0);
    if (!std::isfinite(scale) || scale > std::numeric_limits<int>::max() / 520.0) scale = 1.0;
  }
  return fit_desktop_window({static_cast<int>(380 * scale), static_cast<int>(520 * scale),
          static_cast<int>(360 * scale), static_cast<int>(480 * scale)},
          available_height, pixel_ratio, available_width);
}

inline DesktopWindowSize desktop_setup_size(double available_height, double pixel_ratio,
                                            double available_width, int content_height) {
  return fit_desktop_window({420, std::clamp(content_height, 160, 600), 360, 160},
                            available_height, pixel_ratio, available_width);
}
#endif
