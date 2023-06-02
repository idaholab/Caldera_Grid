find_package(Python COMPONENTS Interpreter REQUIRED)
add_test(NAME "ex_ccast_test" COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/start_exe_with_args.py WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR} )
