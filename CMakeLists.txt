cmake_minimum_required(VERSION 3.16)
project(ExplanationGuidedCBS LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
cmake_policy(SET CMP0167 OLD)  # use FindBoost for compatibility

find_package(yaml-cpp QUIET)
if(NOT TARGET yaml-cpp::yaml-cpp)
  find_package(PkgConfig REQUIRED)
  pkg_check_modules(YAML_CPP REQUIRED yaml-cpp)
endif()

find_package(Boost REQUIRED COMPONENTS program_options)

add_executable(Planner
  src/main.cpp
  src/Astar.cpp
  src/Cbs.cpp
  src/Environment.cpp
  src/parseYAML.cpp
  src/ResultsWriter.cpp
  src/XG-Astar.cpp
  src/XG-Astar-H.cpp
  src/XG-CBS.cpp
  src/S-Astar.cpp
  src/Benchmark.cpp
)

target_include_directories(Planner PRIVATE ${CMAKE_SOURCE_DIR})

if(TARGET yaml-cpp::yaml-cpp)
  target_link_libraries(Planner PRIVATE yaml-cpp::yaml-cpp Boost::program_options)
else()
  target_include_directories(Planner PRIVATE ${YAML_CPP_INCLUDE_DIRS})
  target_link_libraries(Planner PRIVATE ${YAML_CPP_LIBRARIES} Boost::program_options)
endif()
