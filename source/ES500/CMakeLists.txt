set(GLOBALS_DIR ${PROJECT_SOURCE_DIR}/extern/caldera_charge_icm/source/charging_models)

pybind11_add_module(ES500_Aggregator_Helper ${GLOBALS_DIR}/datatypes_global.cpp 
					${GLOBALS_DIR}/${PROJECT}/datatypes_global_SE_EV_definitions.cpp 
					ES500_aggregator_helper.cpp python_bind.cpp)

message(ES500_Aggregator_Helper " current source dir = ${CMAKE_CURRENT_SOURCE_DIR}")

target_include_directories(ES500_Aggregator_Helper PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_include_directories(ES500_Aggregator_Helper PUBLIC ${GLOBALS_DIR})
target_include_directories(ES500_Aggregator_Helper PUBLIC ${GLOBALS_DIR}/${PROJECT})

install(TARGETS ES500_Aggregator_Helper
		DESTINATION ${PROJECT_SOURCE_DIR}/libs)