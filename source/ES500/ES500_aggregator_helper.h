#ifndef AGGREGATOR_HELPER_H
#define AGGREGATOR_HELPER_H

#include <vector>
#include <set>
#include <map>
#include <string>

#include "datatypes_global.h"
// #include "protobuf_translator.h"

#include <pybind11/pybind11.h>
namespace py = pybind11;


//#=========================================================================
//#					    Allocate Energy to PEVs 
//#=========================================================================

class ES500_aggregator_allocate_energy_to_PEVs
{
private:
	struct SE_priority_element
	{
		int index;
		double charge_progression;
		
		bool operator < (const SE_priority_element& rhs)
		{
			return this->charge_progression < rhs.charge_progression;
		}
	};

	double aggregator_time_step_mins, charge_flexibility_threshold;	
	int num_pevs_to_start_charging_each_controlled_cycle_iteration, max_number_of_controlled_cycle_iterations;
	std::vector<ES500_charge_cycling_control_boundary_point> charge_cycling_control_boundary;

	std::vector<int> all_SE_ids;
	std::vector<double> all_charge_progressions;
	std::vector<double> all_e_steps_kWh;
	std::vector<process_id> all_process_ids;
	
	std::vector<SE_priority_element> SE_priority_elements_charging;
	std::vector<SE_priority_element> SE_priority_elements_notCharging;

	std::set<int> must_charge_SE_ids;
	std::set<int> is_charging_SE_ids;
	double E_residual_kWh;
    
    std::vector<ES500_stop_charge_cycling_decision_parameters> stop_charge_cycling_params;
	
	bool stop_charge_cycling(double cycling_vs_ramping, double cycling_magnitude);
	void minimize_absolute_value_of_delta_energy(double& delta_energy_kWh, int& i_charging, int& i_notCharging, double& on_to_off_nrg_kWh, double& off_to_on_nrg_kWh, bool& stop_charge_cycling);
	
public:
	ES500_aggregator_allocate_energy_to_PEVs() {};
	ES500_aggregator_allocate_energy_to_PEVs(double aggregator_time_step_mins_, double charge_flexibility_threshold_, 
											 int num_pevs_to_start_charging_each_controlled_cycle_iteration_, int max_number_of_controlled_cycle_iterations_,
											 std::vector<ES500_charge_cycling_control_boundary_point>& charge_cycling_control_boundary_);

	void allocate_energy_to_PEVs(double next_aggregator_timestep_start_time, double E_step_kWh, std::map<process_id, ES500_aggregator_charging_needs>& charging_needs_map,
								 std::map<process_id, ES500_aggregator_e_step_setpoints>& e_step_kWh);	
	double get_E_residual_kWh();
    std::vector<ES500_stop_charge_cycling_decision_parameters> get_stop_charge_cycling_decision_parameters();
};

//#=========================================================================
//#					    ES500_Aggregator_Helper 
//#=========================================================================

class ES500_aggregator_helper
{
private:
	double aggregator_time_step_mins, data_lead_time_secs;
    double calc_obj_fun_constraints_depart_time_adjustment_sec;
	int num_agg_time_steps_in_prediction_horizon;
	ES500_aggregator_allocate_energy_to_PEVs energy_to_PEVs;

	//protobuf_translator proto_translator_obj;
	
	std::map<process_id, ES500_aggregator_charging_needs> charging_needs_map;
    ES500_aggregator_charging_forecast charge_forecast;

	void combine_actual_and_forecasted_pev_data(double next_aggregator_timestep_start_time, std::vector<bool>& is_forecasted_pev, std::vector<double>& arrival_time, 
												std::vector<double>& departure_time, std::vector<double>& e_charge_remain_kWh, std::vector<double>& e_step_max_kWh);

	void calc_obj_fun_constraints(double next_aggregator_timestep_start_time, std::vector<bool>& is_forecasted_pev, std::vector<double>& arrival_time, 
							 	  std::vector<double>& departure_time, std::vector<double>& e_charge_remain_kWh, 
								  std::vector<double>& e_step_max_kWh, ES500_aggregator_obj_fun_constraints& constraints);
        
public:
	ES500_aggregator_helper(double aggregator_time_step_mins_, double  data_lead_time_secs_, int num_agg_time_steps_in_prediction_horizon_,
							double charge_flexibility_threshold_, int num_pevs_to_start_charging_each_controlled_cycle_iteration_,
							int max_number_of_controlled_cycle_iterations_, double calc_obj_fun_constraints_depart_time_adjustment_sec_,
                            std::vector<ES500_charge_cycling_control_boundary_point>& charge_cycling_control_boundary_);

    double get_E_residual_kWh();
    std::vector<ES500_stop_charge_cycling_decision_parameters> get_stop_charge_cycling_decision_parameters();

    bool load_charging_forecast(ES500_aggregator_charging_forecast charging_forecast_);
	bool load_charging_needs(std::map<process_id, ES500_aggregator_charging_needs> charging_needs);
    std::map<process_id, ES500_aggregator_e_step_setpoints> allocate_energy_to_PEVs(double next_aggregator_timestep_start_time, double E_step_kWh);
    
	bool load_charging_forecast_protobuf(serialized_protobuf_obj charging_forecast);
	bool load_charging_needs_protobuf(std::map<process_id, serialized_protobuf_obj> charging_needs);
    std::map<process_id, py::bytes> allocate_energy_to_PEVs_protobuf(double next_aggregator_timestep_start_time, double E_step_kWh);
    
	ES500_aggregator_obj_fun_constraints get_obj_fun_constraints(double next_aggregator_timestep_start_time);
};

#endif
