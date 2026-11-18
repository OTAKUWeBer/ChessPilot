get_filename_component(CHESSPILOT_NATIVE_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../native" ABSOLUTE)
if(WIN32)
  set(native_library chesspilot_runtime.dll)
  set(runtime_library onnxruntime.dll)
  set(native_os windows)
  set(target_os pc-windows-msvc)
elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")
  set(native_library libchesspilot_runtime.so)
  set(runtime_library libonnxruntime.so)
  set(native_os linux)
  set(target_os unknown-linux-gnu)
else()
  message(FATAL_ERROR "Unsupported native desktop platform")
endif()
if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64|ARM64)$" OR CMAKE_GENERATOR_PLATFORM STREQUAL "ARM64")
  set(native_arch arm64)
  set(target_arch aarch64)
else()
  set(native_arch x64)
  set(target_arch x86_64)
endif()
set(CHESSPILOT_RUST_TARGET "${target_arch}-${target_os}" CACHE STRING "Native Rust target")
set(CHESSPILOT_RUST_TOOLCHAIN "" CACHE STRING "Optional rustup toolchain name")
set(CHESSPILOT_DESKTOP_ASSETS "${CHESSPILOT_NATIVE_ROOT}/target/desktop-assets/${native_os}-${native_arch}"
  CACHE PATH "Prepared native desktop assets")
get_filename_component(model "${CHESSPILOT_NATIVE_ROOT}/../assets/models/chess_detection.onnx" ABSOLUTE)
foreach(required "${model}" "${CHESSPILOT_DESKTOP_ASSETS}/${runtime_library}"
    "${CHESSPILOT_DESKTOP_ASSETS}/licenses/ONNXRuntime-LICENSE.txt"
    "${CHESSPILOT_DESKTOP_ASSETS}/licenses/ONNXRuntime-ThirdPartyNotices.txt"
    "${CHESSPILOT_DESKTOP_ASSETS}/licenses/ONNXRuntime-SOURCE.txt")
  if(NOT EXISTS "${required}")
    message(FATAL_ERROR "Missing desktop asset ${required}. Run cmake -P tool/prepare_desktop.cmake first; see desktop-building.md")
  endif()
endforeach()
find_program(CHESSPILOT_CARGO cargo REQUIRED)
set(toolchain)
if(CHESSPILOT_RUST_TOOLCHAIN)
  list(APPEND toolchain "+${CHESSPILOT_RUST_TOOLCHAIN}")
endif()
set(profile "$<IF:$<CONFIG:Debug>,dev,release>")
set(output_profile "$<IF:$<CONFIG:Debug>,debug,release>")
add_custom_target(chesspilot_native
  COMMAND "${CHESSPILOT_CARGO}" ${toolchain} build --locked
    --manifest-path "${CHESSPILOT_NATIVE_ROOT}/Cargo.toml" -p chesspilot-runtime
    --target "${CHESSPILOT_RUST_TARGET}" --target-dir "${CHESSPILOT_NATIVE_ROOT}/target"
    --profile "${profile}"
  WORKING_DIRECTORY "${CHESSPILOT_NATIVE_ROOT}"
  VERBATIM USES_TERMINAL)
add_dependencies(${BINARY_NAME} chesspilot_native)
install(FILES "${CHESSPILOT_NATIVE_ROOT}/target/${CHESSPILOT_RUST_TARGET}/${output_profile}/${native_library}"
  DESTINATION "${INSTALL_BUNDLE_LIB_DIR}" COMPONENT Runtime)
file(GLOB runtime_files "${CHESSPILOT_DESKTOP_ASSETS}/*.dll" "${CHESSPILOT_DESKTOP_ASSETS}/*.so*")
install(FILES ${runtime_files} DESTINATION "${INSTALL_BUNDLE_LIB_DIR}" COMPONENT Runtime)
install(FILES "${model}" DESTINATION "${CMAKE_INSTALL_PREFIX}" COMPONENT Runtime)
install(FILES "${CHESSPILOT_NATIVE_ROOT}/../assets/logo.png" DESTINATION "${CMAKE_INSTALL_PREFIX}/data" RENAME "chesspilot.png" COMPONENT Runtime)
install(DIRECTORY "${CHESSPILOT_DESKTOP_ASSETS}/licenses/" DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses/ONNXRuntime" COMPONENT Runtime)
install(FILES "${CHESSPILOT_NATIVE_ROOT}/../LICENSE" DESTINATION "${CMAKE_INSTALL_PREFIX}" RENAME "ChessPilot-LICENSE.txt" COMPONENT Runtime)
install(FILES "${CHESSPILOT_NATIVE_ROOT}/runtime/third_party/Pillow-LICENSE.txt"
  DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" COMPONENT Runtime)
