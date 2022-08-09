
#include "ES500_aggregator_helper.h"
#include "datatypes_global.h"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h> 	// Enables conversion between (python lists & c++ vectors) and (python dictionaries & c++ maps)

namespace py = pybind11;

PYBIND11_MODULE(ES500_Aggregator_Helper, m)
{
    py::class_<ES500_aggregator_helper>(m, "ES500_aggregator_helper")
		.def(py::init<double, double, int, double, int, int, double, std::vector<ES500_charge_cycling_control_boundary_point>& >())
		.def("load_charging_forecast", &ES500_aggregator_helper::load_charging_forecast)
		.def("load_charging_needs", &ES500_aggregator_helper::load_charging_needs)
        .def("allocate_energy_to_PEVs", &ES500_aggregator_helper::allocate_energy_to_PEVs)
		.def("get_obj_fun_constraints", &ES500_aggregator_helper::get_obj_fun_constraints)
        .def("get_E_residual_kWh", &ES500_aggregator_helper::get_E_residual_kWh)
        .def("get_stop_charge_cycling_decision_parameters", &ES500_aggregator_helper::get_stop_charge_cycling_decision_parameters);
}


