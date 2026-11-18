#include <flutter/dart_project.h>
#include <flutter/flutter_view_controller.h>
#include <windows.h>
#include <shobjidl.h>

#include "flutter_window.h"
#include "utils.h"
#include "../../native/desktop_window_size.h"

int APIENTRY wWinMain(_In_ HINSTANCE instance, _In_opt_ HINSTANCE prev,
                      _In_ wchar_t *command_line, _In_ int show_command) {
  // Attach to console when present (e.g., 'flutter run') or create a
  // new console when running with a debugger.
  if (!::AttachConsole(ATTACH_PARENT_PROCESS) && ::IsDebuggerPresent()) {
    CreateAndAttachConsole();
  }

  // Initialize COM, so that it is available for use in the library and/or
  // plugins.
  ::CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
  ::SetCurrentProcessExplicitAppUserModelID(L"io.github.otakuweber.chesspilot");

  flutter::DartProject project(L"data");

  std::vector<std::string> command_line_arguments =
      GetCommandLineArguments();

  project.set_dart_entrypoint_arguments(std::move(command_line_arguments));

  FlutterWindow window(project);
  Win32Window::Point origin(10, 10);
  const HMONITOR monitor = MonitorFromPoint(POINT{10, 10}, MONITOR_DEFAULTTONEAREST);
  MONITORINFO monitor_info{sizeof(MONITORINFO)};
  const double ratio = FlutterDesktopGetDpiForMonitor(monitor) / 96.0;
  const bool monitor_ready = GetMonitorInfo(monitor, &monitor_info);
  const auto metrics = desktop_window_size(
      monitor_ready ? monitor_info.rcWork.bottom - monitor_info.rcWork.top : 1080.0,
      ratio, monitor_ready ? monitor_info.rcWork.right - monitor_info.rcWork.left : 1920.0);
  Win32Window::Size size(metrics.width, metrics.height);
  window.SetMinimumSize(Win32Window::Size(metrics.minimum_width, metrics.minimum_height));
  if (!window.Create(L"ChessPilot", origin, size)) {
    return EXIT_FAILURE;
  }
  window.SetQuitOnClose(true);
  ::SetWindowPos(window.GetHandle(), HWND_TOPMOST, 0, 0, 0, 0,
                 SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);

  ::MSG msg;
  while (::GetMessage(&msg, nullptr, 0, 0)) {
    ::TranslateMessage(&msg);
    ::DispatchMessage(&msg);
  }

  ::CoUninitialize();
  return EXIT_SUCCESS;
}
