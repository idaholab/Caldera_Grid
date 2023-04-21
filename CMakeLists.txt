cmake_minimum_required(VERSION 3.5)

project(Grid)

set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Check to see PROJECT cmake variable is set
if (NOT DEFINED PROJECT)
	message(WARNING "PROJECT cmake variable not set defaulting to emosiac project")
endif()

SET(PROJECT "eMosaic" CACHE STRING "Project to compile for")

if (NOT (${PROJECT} STREQUAL "eMosaic" OR ${PROJECT} STREQUAL "EVs_at_Risk" OR ${PROJECT} STREQUAL "DirectXFC"))
	message(FATAL_ERROR "PROJECT cmake variable must be equal to eMosaic or EVs_at_Risk or DirectXFC")
endif()

# Find pybind11
find_package(pybind11 CONFIG)

# Make sure C++11 flag is set for macOS.
if(APPLE)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang\$")
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
    endif()
endif()

# Update submodules
find_package(Git QUIET)
if(GIT_FOUND AND EXISTS "${PROJECT_SOURCE_DIR}/.git")
    option(GIT_SUBMODULE "Check submodules during build" ON)
    if(GIT_SUBMODULE)
        message(STATUS "Submodule update")
        execute_process(COMMAND ${GIT_EXECUTABLE} submodule update --init --recursive
                        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
                        RESULT_VARIABLE GIT_SUBMOD_RESULT)
        if(NOT GIT_SUBMOD_RESULT EQUAL "0")
            message(FATAL_ERROR "git submodule update --init --recursive failed with ${GIT_SUBMOD_RESULT}, please checkout submodules")
        endif()
    endif()
endif()

if(NOT EXISTS "${PROJECT_SOURCE_DIR}/extern/Caldera_ICM/CMakeLists.txt")
    message(FATAL_ERROR "The submodules were not downloaded! GIT_SUBMODULE was turned off or failed. Please update submodules and try again.")
endif()


# Set installation dir
SET(INSTALL_DIR ${PROJECT_SOURCE_DIR}/libs)

# Add subdirs to compile the necessary binaries
add_subdirectory(source/ES500)
add_subdirectory(extern/Caldera_ICM)
add_subdirectory(examples)
add_subdirectory(unittests)
