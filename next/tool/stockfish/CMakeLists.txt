cmake_minimum_required(VERSION 3.22)
project(chesspilot_stockfish LANGUAGES CXX)
if(NOT ANDROID OR NOT ANDROID_ABI STREQUAL "arm64-v8a")
  message(FATAL_ERROR "This build packages generic Android ARM64 Stockfish")
endif()
file(TO_CMAKE_PATH "${STOCKFISH_SOURCE}" source_root)
set(src "${source_root}/src")
# Source list and ARMv8 switches follow the unmodified sf_17.1 Makefile.
add_executable(stockfish
  ${src}/benchmark.cpp ${src}/bitboard.cpp ${src}/evaluate.cpp ${src}/main.cpp
  ${src}/misc.cpp ${src}/movegen.cpp ${src}/movepick.cpp ${src}/position.cpp
  ${src}/search.cpp ${src}/thread.cpp ${src}/timeman.cpp ${src}/tt.cpp
  ${src}/uci.cpp ${src}/ucioption.cpp ${src}/tune.cpp ${src}/syzygy/tbprobe.cpp
  ${src}/nnue/nnue_accumulator.cpp ${src}/nnue/nnue_misc.cpp
  ${src}/nnue/features/half_ka_v2_hm.cpp ${src}/nnue/network.cpp
  ${src}/engine.cpp ${src}/score.cpp ${src}/memory.cpp)
target_compile_features(stockfish PRIVATE cxx_std_17)
target_compile_definitions(stockfish PRIVATE NDEBUG IS_64BIT USE_POPCNT USE_NEON=8)
target_compile_options(stockfish PRIVATE -O3 -fno-exceptions)
target_link_options(stockfish PRIVATE -Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384)
target_link_libraries(stockfish PRIVATE atomic)
set_target_properties(stockfish PROPERTIES OUTPUT_NAME libstockfish.so)
foreach(net nn-1c0000000000.nnue nn-37f18f62d772.nnue)
  configure_file("${src}/${net}" "${CMAKE_CURRENT_BINARY_DIR}/${net}" COPYONLY)
endforeach()
