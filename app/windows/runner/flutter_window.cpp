#include "flutter_window.h"

#include <optional>
#include <cmath>
#include <flutter/standard_method_codec.h>

#include "flutter/generated_plugin_registrant.h"

FlutterWindow::FlutterWindow(const flutter::DartProject& project)
    : project_(project) {}

FlutterWindow::~FlutterWindow() {}

bool FlutterWindow::OnCreate() {
  if (!Win32Window::OnCreate()) {
    return false;
  }

  RECT frame = GetClientArea();

  // The size here must match the window dimensions to avoid unnecessary surface
  // creation / destruction in the startup path.
  flutter_controller_ = std::make_unique<flutter::FlutterViewController>(
      frame.right - frame.left, frame.bottom - frame.top, project_);
  // Ensure that basic setup of the controller was successful.
  if (!flutter_controller_->engine() || !flutter_controller_->view()) {
    return false;
  }
  RegisterPlugins(flutter_controller_->engine());
  SetChildContent(flutter_controller_->view()->GetNativeWindow());
  desktop_channel_ = std::make_unique<flutter::MethodChannel<flutter::EncodableValue>>(
      flutter_controller_->engine()->messenger(), "chesspilot/desktop",
      &flutter::StandardMethodCodec::GetInstance());
  desktop_channel_->SetMethodCallHandler([this](const auto& call, auto result) {
    if (call.method_name() == "setupWindow") {
      const auto* args = std::get_if<flutter::EncodableMap>(call.arguments());
      if (!args) { result->Error("setup", "Expected setup dimensions"); return; }
      const auto enabled_arg = args->find(flutter::EncodableValue("enabled"));
      const auto height_arg = args->find(flutter::EncodableValue("height"));
      const auto* enabled = enabled_arg == args->end() ? nullptr : std::get_if<bool>(&enabled_arg->second);
      const auto* height = height_arg == args->end() ? nullptr : std::get_if<int32_t>(&height_arg->second);
      if (!enabled || !height || *height < 160 || *height > 600) { result->Error("setup", "Invalid setup dimensions"); return; }
      if (!SetSetupMode(*enabled, static_cast<unsigned int>(*height))) { result->Error("setup", "Cannot resize setup window"); return; }
      result->Success(); return;
    }
    if (call.method_name() != "returnTarget") { result->NotImplemented(); return; }
    const auto* args = std::get_if<flutter::EncodableMap>(call.arguments());
    if (!args) { result->Error("coordinates", "Expected a point"); return; }
    auto coordinate = [&](const char* key) -> std::optional<double> {
      const auto value = args->find(flutter::EncodableValue(key));
      if (value == args->end()) return std::nullopt;
      if (const auto* number = std::get_if<double>(&value->second)) return *number;
      return std::nullopt;
    };
    const auto x = coordinate("x"), y = coordinate("y");
    const HWND view = flutter_controller_->view()->GetNativeWindow();
    RECT rect{};
    const double scale = GetDpiForWindow(view) / 96.0;
    if (!x || !y || !std::isfinite(*x) || !std::isfinite(*y) || scale <= 0 ||
        !IsWindowVisible(view) || !GetClientRect(view, &rect) || *x < 0 || *y < 0 ||
        *x * scale >= rect.right || *y * scale >= rect.bottom) {
      result->Success(); return;
    }
    result->Success(flutter::EncodableValue(flutter::EncodableMap{
      {flutter::EncodableValue("window"), flutter::EncodableValue(reinterpret_cast<int64_t>(view))},
      {flutter::EncodableValue("x"), flutter::EncodableValue(static_cast<int32_t>(std::floor(*x * scale)))},
      {flutter::EncodableValue("y"), flutter::EncodableValue(static_cast<int32_t>(std::floor(*y * scale)))}}));
  });

  flutter_controller_->engine()->SetNextFrameCallback([&]() {
    this->Show();
  });

  // Flutter can complete the first frame before the "show window" callback is
  // registered. The following call ensures a frame is pending to ensure the
  // window is shown. It is a no-op if the first frame hasn't completed yet.
  flutter_controller_->ForceRedraw();

  return true;
}

void FlutterWindow::OnDestroy() {
  desktop_channel_.reset();
  if (flutter_controller_) {
    flutter_controller_ = nullptr;
  }

  Win32Window::OnDestroy();
}

LRESULT
FlutterWindow::MessageHandler(HWND hwnd, UINT const message,
                              WPARAM const wparam,
                              LPARAM const lparam) noexcept {
  // Give Flutter, including plugins, an opportunity to handle window messages.
  if (flutter_controller_) {
    std::optional<LRESULT> result =
        flutter_controller_->HandleTopLevelWindowProc(hwnd, message, wparam,
                                                      lparam);
    if (result) {
      return *result;
    }
  }

  switch (message) {
    case WM_FONTCHANGE:
      flutter_controller_->engine()->ReloadSystemFonts();
      break;
  }

  return Win32Window::MessageHandler(hwnd, message, wparam, lparam);
}
