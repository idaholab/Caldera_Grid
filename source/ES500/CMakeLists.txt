message(ES500_Aggregator_Helper " current source dir = ${CMAKE_CURRENT_SOURCE_DIR}")

set(GLOBALS_DIR ${PROJECT_SOURCE_DIR}/extern/Caldera_ICM/source/globals)
set(CHARGING_MODELS_DIR ${PROJECT_SOURCE_DIR}/extern/Caldera_ICM/source/charging_models)

#pybind11_add_module(ES500_Aggregator_Helper ${GLOBALS_DIR}/datatypes_global.cpp 
#					${CHARGING_MODELS_DIR}/datatypes_global_SE_EV_definitions.cpp 
#					ES500_aggregator_helper.cpp python_bind.cpp)

pybind11_add_module(ES500_Aggregator_Helper MODULE ES500_aggregator_helper.cpp python_bind.cpp)
target_link_libraries(ES500_Aggregator_Helper PRIVATE Globals)
target_link_libraries(ES500_Aggregator_Helper PRIVATE Charging_models)
target_include_directories(ES500_Aggregator_Helper PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_include_directories(ES500_Aggregator_Helper PUBLIC ${GLOBALS_DIR})
target_include_directories(ES500_Aggregator_Helper PUBLIC ${CHARGING_MODELS_DIR})

install(TARGETS ES500_Aggregator_Helper
		DESTINATION ${PROJECT_SOURCE_DIR}/libs)