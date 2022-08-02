
#include <iostream>
#include <algorithm>
#include <cmath>
#include <string>

#include "ES500_aggregator_helper.h"


//#=========================================================================
//#					    Allocate Energy to DCMs 
//#=========================================================================

ES500_aggregator_allocate_energy_to_PEVs::ES500_aggregator_allocate_energy_to_PEVs(double aggregator_time_step_mins_,	double charge_flexibility_threshold_,
																					int num_pevs_to_start_charging_each_controlled_cycle_iteration_, 
							 														int max_number_of_controlled_cycle_iterations_, 
																					std::vector<ES500_charge_cycling_control_boundary_point>& charge_cycling_control_boundary_)
{
	this->aggregator_time_step_mins = aggregator_time_step_mins_;
	this->charge_flexibility_threshold = charge_flexibility_threshold_;
	this->max_number_of_controlled_cycle_iterations = max_number_of_controlled_cycle_iterations_;
	this->num_pevs_to_start_charging_each_controlled_cycle_iteration = num_pevs_to_start_charging_each_controlled_cycle_iteration_;
	this->charge_cycling_control_boundary = charge_cycling_control_boundary_;
	
	this->E_residual_kWh = 0;
}


double ES500_aggregator_allocate_energy_to_PEVs::get_E_residual_kWh()
{
	return this->E_residual_kWh;
}


std::vector<ES500_stop_charge_cycling_decision_parameters> ES500_aggregator_allocate_energy_to_PEVs::get_stop_charge_cycling_decision_parameters()
{
    std::vector<ES500_stop_charge_cycling_decision_parameters> return_val;
    return_val = this->stop_charge_cycling_params;
    this->stop_charge_cycling_params.clear();
    
    return return_val;
}


bool ES500_aggregator_allocate_energy_to_PEVs::stop_charge_cycling(double cycling_vs_ramping, double cycling_magnitude)
{
	int array_size = this->charge_cycling_control_boundary.size();
	int i, index = -1;
	
	for (i = 0; i < array_size; i++)
	{
		if (cycling_magnitude < this->charge_cycling_control_boundary[i].cycling_magnitude)
		{
			index = i;
			break;
		}
	}
	
	if (index == 0)
		return false;
	else if (index == -1)
		return true;		
	else
	{
		double c_vs_r_1 = this->charge_cycling_control_boundary[index-1].cycling_vs_ramping;
		double c_vs_r_2 = this->charge_cycling_control_boundary[index].cycling_vs_ramping;
		double cm_1 = this->charge_cycling_control_boundary[index-1].cycling_magnitude;
		double cm_2 = this->charge_cycling_control_boundary[index].cycling_magnitude;
	
		double cycling_vs_ramping_boundary_point = c_vs_r_1 +  (c_vs_r_2 - c_vs_r_1)*(cycling_magnitude - cm_1)/(cm_2 - cm_1);
		
		if (cycling_vs_ramping < cycling_vs_ramping_boundary_point)
			return false;
		else
			return true;
	}
}

/*
void ES500_aggregator_allocate_energy_to_PEVs::minimize_absolute_value_of_delta_energy(double& delta_energy_kWh, int& i_charging, int& i_notCharging, double& on_to_off_nrg_kWh, double& off_to_on_nrg_kWh, bool& stop_charge_cycling)
{
	int num_SE_charging = this->SE_priority_elements_charging.size();
	int num_SE_notCharging = this->SE_priority_elements_notCharging.size();
	
	int index, SE_id;
	double e_step_target_kWh;
	
	stop_charge_cycling = false;
	
	if (delta_energy_kWh < 0)  // Turn off PEVs
	{
		if (i_charging < num_SE_charging)
		{
			while(true)
			{
				index = this->SE_priority_elements_charging[i_charging].index;
				SE_id = this->all_SE_ids[index];
				e_step_target_kWh = this->all_e_steps_kWh[index];
				
				if (this->must_charge_SE_ids.count(SE_id) == 0)
				{
					this->is_charging_SE_ids.erase(SE_id);
					on_to_off_nrg_kWh += e_step_target_kWh;
					delta_energy_kWh += e_step_target_kWh;
					
					// if (delta_energy_kWh < -0.5*e_step_target_kWh) then continue
                    if (delta_energy_kWh >= -0.5*e_step_target_kWh)
					{
						i_charging += 1;
						break;
					}
				}
				
				i_charging += 1;
				if (i_charging >= num_SE_charging)
				{
					stop_charge_cycling = true;
					break;
				}
			}
		}
		else
			stop_charge_cycling = true;
	}
	else	// Turn on PEVs
	{
		if (i_notCharging < num_SE_notCharging)
		{
			while(true)
			{
				index = this->SE_priority_elements_notCharging[i_notCharging].index;
				SE_id = this->all_SE_ids[index];
				e_step_target_kWh = this->all_e_steps_kWh[index];
				
				this->is_charging_SE_ids.insert(SE_id);
				off_to_on_nrg_kWh += e_step_target_kWh;
				delta_energy_kWh -= e_step_target_kWh;
				
				// if(delta_energy_kWh > 0.5*e_step_target_kWh) then continue
                if(delta_energy_kWh <= 0.5*e_step_target_kWh)
				{
					i_notCharging += 1;
					break;
				}
				
				i_notCharging += 1;
				if(i_notCharging >= num_SE_notCharging)
				{
					stop_charge_cycling = true;
					break;
				}
			}
		}
		else
			stop_charge_cycling = true;
	}
}
*/

void ES500_aggregator_allocate_energy_to_PEVs::minimize_absolute_value_of_delta_energy(double& delta_energy_kWh, int& i_charging, int& i_notCharging, double& on_to_off_nrg_kWh, double& off_to_on_nrg_kWh, bool& stop_charge_cycling)
{
	int num_SE_charging = this->SE_priority_elements_charging.size();
	int num_SE_notCharging = this->SE_priority_elements_notCharging.size();
	
	int index, SE_id;
	double e_step_target_kWh;
	
	stop_charge_cycling = false;
	
	if (delta_energy_kWh < 0)  // Turn off PEVs
	{
		if (i_charging < num_SE_charging)
		{
			while(true)
			{
				index = this->SE_priority_elements_charging[i_charging].index;
				SE_id = this->all_SE_ids[index];
				e_step_target_kWh = this->all_e_steps_kWh[index];
				
                if(delta_energy_kWh < -0.5*e_step_target_kWh)
                {
                    if (this->must_charge_SE_ids.count(SE_id) == 0)
                    {   // must_charge == false
                        this->is_charging_SE_ids.erase(SE_id);
                        on_to_off_nrg_kWh += e_step_target_kWh;
                        delta_energy_kWh += e_step_target_kWh;
                    }
                    
                    i_charging += 1;
                    if (i_charging >= num_SE_charging)
                    {
                        stop_charge_cycling = true;
                        break;
                    }
                }
                else
				    break;
			}
		}
		else
			stop_charge_cycling = true;
	}
	else	// Turn on PEVs
	{
		if (i_notCharging < num_SE_notCharging)
		{
			while(true)
			{
				index = this->SE_priority_elements_notCharging[i_notCharging].index;
				SE_id = this->all_SE_ids[index];
				e_step_target_kWh = this->all_e_steps_kWh[index];
				
                if(delta_energy_kWh > 0.5*e_step_target_kWh)
                {
                    this->is_charging_SE_ids.insert(SE_id);
                    off_to_on_nrg_kWh += e_step_target_kWh;
                    delta_energy_kWh -= e_step_target_kWh;
                    
                    i_notCharging += 1;
                    if(i_notCharging >= num_SE_notCharging)
                    {
                        stop_charge_cycling = true;
                        break;
                    }
                }
                else
                    break;
			}
		}
		else
			stop_charge_cycling = true;
	}
}


void ES500_aggregator_allocate_energy_to_PEVs::allocate_energy_to_PEVs(double next_aggregator_timestep_start_time, double E_step_kWh, std::map<process_id, ES500_aggregator_charging_needs>& charging_needs_map,
                                                                       std::map<process_id, ES500_aggregator_e_step_setpoints>& e_step_kWh)
{
    e_step_kWh.clear();

	std::set<int> SE_ids;
	int num_SE = 0;
	
	for(const std::pair<process_id, ES500_aggregator_charging_needs>& kv_pair : charging_needs_map)
	{
        if(0.0000001 < std::abs(next_aggregator_timestep_start_time - kv_pair.second.next_aggregator_timestep_start_time))
            std::cout << "Error in ES500_aggregator_allocate_energy_to_PEVs: Conflicting next_aggregator_timestep_start_time values." << std::endl;
        
        const std::vector<ES500_aggregator_pev_charge_needs>& pev_charge_needs = kv_pair.second.pev_charge_needs;
        num_SE += pev_charge_needs.size();
        
        for(const ES500_aggregator_pev_charge_needs& x: pev_charge_needs)
			SE_ids.insert(x.SE_id);
	}
/*
std::cout << "Allocate Energy to PEVs (Beginning).   ES500_aggregator_allocate_energy_to_PEVs::allocate_energy_to_PEVs()" << std::endl;
std::cout << "next_agg_time_hrs: " << next_aggregator_timestep_start_time/3600.0 << std::endl;
std::string str1 = "must_charge_SE_ids: ";
for(int id_1 : this->must_charge_SE_ids)
    str1 += std::to_string(id_1) + " ";
std::cout << str1 << std::endl;

str1 = "is_charging_SE_ids: ";
for(int id_1 : this->is_charging_SE_ids)
    str1 += std::to_string(id_1) + " ";
std::cout << str1 << std::endl;

str1 = "SE_ids: ";
for(int id_1 : SE_ids)
    str1 += std::to_string(id_1) + " ";
std::cout << str1 << std::endl << std::endl;
*/	
	//-------------------------------------------------------------------------------	
	//   Remove non-existant SE_ids from  must_charge_SE_ids  &  is_charging_SE_ids
	//-------------------------------------------------------------------------------
	
	std::vector<int> SE_ids_to_delete;

	for (int x: this->must_charge_SE_ids)
	{
		if (SE_ids.count(x) == 0) // Does not contain
			SE_ids_to_delete.push_back(x);
	}
	
	for (int x: SE_ids_to_delete)
		must_charge_SE_ids.erase(x);
	
	//---------------------------
	
	SE_ids_to_delete.clear();
	for (int x: is_charging_SE_ids)
	{
		if (SE_ids.count(x) == 0) // Does not contain
			SE_ids_to_delete.push_back(x);
	}
	
	for (int x: SE_ids_to_delete)
		is_charging_SE_ids.erase(x);

	SE_ids.clear();

	//-------------------------------------------------------------------------
	//					  Initialize Values
	//-------------------------------------------------------------------------
	
	this->all_SE_ids.clear();
	this->all_charge_progressions.clear();
	this->all_e_steps_kWh.clear();
	this->all_process_ids.clear();
	
	this->SE_priority_elements_charging.clear();
	this->SE_priority_elements_notCharging.clear();
	
	double off_to_on_nrg_kWh, on_to_off_nrg_kWh, total_on_nrg_kWh, calc_delta_energy_total_on_nrg_kWh;
		
	off_to_on_nrg_kWh = 0;	
	on_to_off_nrg_kWh = 0;	
	total_on_nrg_kWh = 0;
	calc_delta_energy_total_on_nrg_kWh = 0;
	
	//#--------------------------------------------------------------------------
	//#							General Setup
	//#--------------------------------------------------------------------------
	
	double time_step_hrs = this->aggregator_time_step_mins/60;
	double e_step_target_kWh;
	int SE_id, index = 0;
	
	for (const std::pair<process_id, ES500_aggregator_charging_needs>& kv_pair : charging_needs_map)
	{
		const std::string& process_id_val = kv_pair.first;
        const std::vector<ES500_aggregator_pev_charge_needs>& pev_charge_needs = kv_pair.second.pev_charge_needs;
        
		double min_remaining_charge_time_hrs, min_time_to_complete_entire_charge_hrs;
		double remaining_park_time_hrs, total_park_time_hrs, charge_progression, charge_flexibility;
		bool SE_is_charging;
		
		for(const ES500_aggregator_pev_charge_needs& X : pev_charge_needs)
		{
			SE_id = X.SE_id;
			e_step_target_kWh = X.e3_step_target_kWh;
			min_remaining_charge_time_hrs = X.min_remaining_charge_time_hrs;
			min_time_to_complete_entire_charge_hrs = X.min_time_to_complete_entire_charge_hrs;
			remaining_park_time_hrs = X.remaining_park_time_hrs;
			total_park_time_hrs = X.total_park_time_hrs;
		
			//-------------------------------------------------------
			//  Calculate Charge Flexibility and Charge Progression
			//-------------------------------------------------------
			charge_flexibility = (remaining_park_time_hrs - min_remaining_charge_time_hrs)/time_step_hrs;
			
			charge_progression = (total_park_time_hrs - remaining_park_time_hrs)/total_park_time_hrs - (min_time_to_complete_entire_charge_hrs - min_remaining_charge_time_hrs)/min_time_to_complete_entire_charge_hrs;
			//charge_progression = (charge_progression < 1) ? charge_progression : 1;
			
			//-------------------------------------------------------
			//			 Calculate total_on_nrg_kWh
			//-------------------------------------------------------			
			SE_is_charging = false;			
			
			if (this->is_charging_SE_ids.count(SE_id) == 1)
			{
				total_on_nrg_kWh += e_step_target_kWh;
				calc_delta_energy_total_on_nrg_kWh += e_step_target_kWh;
				SE_is_charging = true;
			}
			
			//-------------------------------------------------------
			//  		Update Must Charge State Variable
			//-------------------------------------------------------						
			if (charge_flexibility < this->charge_flexibility_threshold)
			{
				if (this->must_charge_SE_ids.count(SE_id) == 0)
					this->must_charge_SE_ids.insert(SE_id);
				
				if (this->is_charging_SE_ids.count(SE_id) == 0)
				{
					this->is_charging_SE_ids.insert(SE_id);
					off_to_on_nrg_kWh += e_step_target_kWh;
					calc_delta_energy_total_on_nrg_kWh += e_step_target_kWh;
					SE_is_charging = true;
				}
			}
			
			//-------------------------------------------------------
			//  		  Load  SE_priority_elements
			//-------------------------------------------------------			
			if (SE_is_charging)
				SE_priority_elements_charging.push_back({index, charge_progression});
			else
				SE_priority_elements_notCharging.push_back({index, charge_progression});
			
			index++;
			
			//-------------------------------------------------------
			//		  Add values to the 'all' vectors
			//-------------------------------------------------------
			this->all_SE_ids.push_back(SE_id);
			this->all_charge_progressions.push_back(charge_progression);
			this->all_e_steps_kWh.push_back(e_step_target_kWh);
			this->all_process_ids.push_back(process_id_val);
		}
	}

	//-------------------------------------------------------
	//  			Sort  SE_priority_elements
	//-------------------------------------------------------	
	std::sort(this->SE_priority_elements_charging.begin(), this->SE_priority_elements_charging.end());
	std::sort(this->SE_priority_elements_notCharging.rbegin(), this->SE_priority_elements_notCharging.rend());
    
	//-------------------------------------------------------
	//		   Calculate Initial Delta Energy
	//-------------------------------------------------------	
	double delta_energy_kWh = E_step_kWh - calc_delta_energy_total_on_nrg_kWh;
	
	//-------------------------------------------------------
	//	   Minimize Absolute Value of Delta Energy
	//-------------------------------------------------------
    
	int num_SE_charging, num_SE_notCharging, i_charging, i_notCharging;
	bool stop_charge_cycling;
    ES500_stop_charge_cycling_decision_parameters stop_CC_params;
	
	num_SE_charging = this->SE_priority_elements_charging.size();
	num_SE_notCharging = this->SE_priority_elements_notCharging.size();
	i_charging = 0;
	i_notCharging = 0;
	
	this->minimize_absolute_value_of_delta_energy(delta_energy_kWh, i_charging, i_notCharging, on_to_off_nrg_kWh, off_to_on_nrg_kWh, stop_charge_cycling);
    
    stop_CC_params.next_aggregator_timestep_start_time = next_aggregator_timestep_start_time;
    stop_CC_params.iteration = 0;
    stop_CC_params.is_last_iteration = false;
    stop_CC_params.off_to_on_nrg_kWh = off_to_on_nrg_kWh;
    stop_CC_params.on_to_off_nrg_kWh = on_to_off_nrg_kWh;
    stop_CC_params.total_on_nrg_kWh = total_on_nrg_kWh;
    stop_CC_params.cycling_vs_ramping = -1;
    stop_CC_params.cycling_magnitude = -1;
    stop_CC_params.delta_energy_kWh = delta_energy_kWh;
    this->stop_charge_cycling_params.push_back(stop_CC_params);
    
	//-------------------------------------------------------
	//		   Execute Controlled Charge Cycling
	//-------------------------------------------------------
	
	double cycling_vs_ramping, cycling_magnitude, min_val, max_val;
	int num_controlled_cycle_iterations = 0;
	
	if (i_notCharging >= num_SE_notCharging || i_charging >= num_SE_charging)
		stop_charge_cycling = true;
		
	if(!stop_charge_cycling)
	{
		while(true)
		{
			//-------------------------------------------
			//		   Start Charging PEVs
			//-------------------------------------------
			for(int i=0; i<this->num_pevs_to_start_charging_each_controlled_cycle_iteration; i++)
			{
				index = this->SE_priority_elements_notCharging[i_notCharging].index;
				SE_id = this->all_SE_ids[index];
				e_step_target_kWh = this->all_e_steps_kWh[index];
				
				if(this->all_charge_progressions[index] < 0)
				{
					stop_charge_cycling = true;
					break;
				}
				
				this->is_charging_SE_ids.insert(SE_id);
				off_to_on_nrg_kWh += e_step_target_kWh;
				delta_energy_kWh -= e_step_target_kWh;
				
				i_notCharging += 1;
				if (i_notCharging >= num_SE_notCharging)
				{
					stop_charge_cycling = true;
					break;
				}				
			}
		
			if(stop_charge_cycling)
				break;
		
			//-------------------------------------------------------
			//	   Minimize Absolute Value of Delta Energy
			//-------------------------------------------------------
			this->minimize_absolute_value_of_delta_energy(delta_energy_kWh, i_charging, i_notCharging, on_to_off_nrg_kWh, off_to_on_nrg_kWh, stop_charge_cycling);
		
			if(stop_charge_cycling)
				break;
				
			//-------------------------------------------------------
			//		Decide if Charge Cycling Should Stop
			//-------------------------------------------------------
			min_val = std::min(on_to_off_nrg_kWh, off_to_on_nrg_kWh);
			max_val = std::max(on_to_off_nrg_kWh, off_to_on_nrg_kWh);
			
			if(max_val < 0.1 || total_on_nrg_kWh < 0.1)
				continue;
			
			cycling_vs_ramping = min_val/max_val;
			cycling_magnitude = min_val/total_on_nrg_kWh;
			
			stop_charge_cycling = this->stop_charge_cycling(cycling_vs_ramping, cycling_magnitude);
			
            stop_CC_params.next_aggregator_timestep_start_time = next_aggregator_timestep_start_time;
            stop_CC_params.iteration = num_controlled_cycle_iterations + 1;
            stop_CC_params.is_last_iteration = false;
            stop_CC_params.off_to_on_nrg_kWh = off_to_on_nrg_kWh;
            stop_CC_params.on_to_off_nrg_kWh = on_to_off_nrg_kWh;
            stop_CC_params.total_on_nrg_kWh = total_on_nrg_kWh;
            stop_CC_params.cycling_vs_ramping = cycling_vs_ramping;
            stop_CC_params.cycling_magnitude = cycling_magnitude;
            stop_CC_params.delta_energy_kWh = delta_energy_kWh;
            this->stop_charge_cycling_params.push_back(stop_CC_params);
            
			if(stop_charge_cycling)
				break;
				
			//-------------------------------------------------------
			//		 Limit Controlled Cycle Iterations
			//-------------------------------------------------------
			num_controlled_cycle_iterations += 1;
			
			if(num_controlled_cycle_iterations >= this->max_number_of_controlled_cycle_iterations)
				break;
		}		
	}
    
    this->stop_charge_cycling_params[this->stop_charge_cycling_params.size()-1].is_last_iteration = true;
	this->E_residual_kWh = delta_energy_kWh;
	
	//-------------------------------------------------------
	//		   		Package Results
	//-------------------------------------------------------
	ES500_aggregator_e_step_setpoints* tmp_ptr;
	
	process_id process_id_val;
	num_SE = this->all_SE_ids.size();

	for (int i=0; i<num_SE; i++)
	{
		SE_id = this->all_SE_ids[i];
		process_id_val = this->all_process_ids[i];
		
		if(this->is_charging_SE_ids.count(SE_id) == 0)
			e_step_target_kWh = 0;
		else
			e_step_target_kWh = this->all_e_steps_kWh[i];
        
		//------------------------------

		if(e_step_kWh.count(process_id_val) == 0)
		{
			ES500_aggregator_e_step_setpoints X;
			X.next_aggregator_timestep_start_time = next_aggregator_timestep_start_time;
			X.SE_id.push_back(SE_id);
			X.e3_step_kWh.push_back(e_step_target_kWh);
			X.charge_progression.push_back(this->all_charge_progressions[i]);
			
			e_step_kWh[process_id_val] = X;
		}
		else
		{
			tmp_ptr = &e_step_kWh[process_id_val];
			tmp_ptr->SE_id.push_back(SE_id);
			tmp_ptr->e3_step_kWh.push_back(e_step_target_kWh);
			tmp_ptr->charge_progression.push_back(this->all_charge_progressions[i]);
		}
	}
    
    //------------------------------
    
    for(const std::pair<process_id, ES500_aggregator_charging_needs>& kv_pair : charging_needs_map)
    {
        if(e_step_kWh.count(kv_pair.first) == 0)
        {
            ES500_aggregator_e_step_setpoints X;
            X.next_aggregator_timestep_start_time = next_aggregator_timestep_start_time;
            e_step_kWh[kv_pair.first] = X;
        }
    }

/*
std::cout << "Allocate Energy to PEVs (End).   ES500_aggregator_allocate_energy_to_PEVs::allocate_energy_to_PEVs()" << std::endl;
std::cout << "next_agg_time_hrs: " << next_aggregator_timestep_start_time/3600.0 << std::endl;
std::cout << "E_step_kWh: " << E_step_kWh << "  delta_energy_kWh: " << delta_energy_kWh << std::endl;

str1 = "must_charge_SE_ids: ";
for(int id_1 : this->must_charge_SE_ids)
    str1 += std::to_string(id_1) + " ";
std::cout << str1 << std::endl;

str1 = "is_charging_SE_ids: ";
for(int id_1 : this->is_charging_SE_ids)
    str1 += std::to_string(id_1) + " ";
std::cout << str1 << std::endl << std::endl;
*/
}


//=========================================================================
//			  			ES500_Aggregator_Helper 
//=========================================================================

ES500_aggregator_helper::ES500_aggregator_helper(double aggregator_time_step_mins_, double  data_lead_time_secs_, int num_agg_time_steps_in_prediction_horizon_,
												   double charge_flexibility_threshold_, int num_pevs_to_start_charging_each_controlled_cycle_iteration_,
												   int max_number_of_controlled_cycle_iterations_, double calc_obj_fun_constraints_depart_time_adjustment_sec_,
                                                   std::vector<ES500_charge_cycling_control_boundary_point>& charge_cycling_control_boundary_)
{
	this->aggregator_time_step_mins = aggregator_time_step_mins_;
	this->data_lead_time_secs = data_lead_time_secs_;
 	this->num_agg_time_steps_in_prediction_horizon = num_agg_time_steps_in_prediction_horizon_;
    this->calc_obj_fun_constraints_depart_time_adjustment_sec = calc_obj_fun_constraints_depart_time_adjustment_sec_;

	ES500_aggregator_allocate_energy_to_PEVs energy_to_PEVs_(aggregator_time_step_mins_, charge_flexibility_threshold_, num_pevs_to_start_charging_each_controlled_cycle_iteration_, max_number_of_controlled_cycle_iterations_, charge_cycling_control_boundary_);
	this->energy_to_PEVs = energy_to_PEVs_;
}


double ES500_aggregator_helper::get_E_residual_kWh()
{
    return this->energy_to_PEVs.get_E_residual_kWh();
}


std::vector<ES500_stop_charge_cycling_decision_parameters> ES500_aggregator_helper::get_stop_charge_cycling_decision_parameters()
{
    return this->energy_to_PEVs.get_stop_charge_cycling_decision_parameters();
}


void ES500_aggregator_helper::combine_actual_and_forecasted_pev_data(double next_aggregator_timestep_start_time, std::vector<bool>& is_forecasted_pev, std::vector<double>& arrival_time,
																	std::vector<double>& departure_time, std::vector<double>& e_charge_remain_kWh, std::vector<double>& e_step_max_kWh)
{
	is_forecasted_pev.clear();
	arrival_time.clear();
	departure_time.clear();
	e_charge_remain_kWh.clear();
	e_step_max_kWh.clear();

	//----------------------------------

	for(const std::pair<process_id, ES500_aggregator_charging_needs>& x : this->charging_needs_map)
	{
        for(const ES500_aggregator_pev_charge_needs y : x.second.pev_charge_needs)
        {
            is_forecasted_pev.push_back(false);
			arrival_time.push_back(next_aggregator_timestep_start_time);
			departure_time.push_back(y.departure_unix_time);
			e_charge_remain_kWh.push_back(y.e3_charge_remain_kWh);
			e_step_max_kWh.push_back(y.e3_step_max_kWh);
        }
	}

	//----------------------------------
	
	int size_val = this->charge_forecast.departure_unix_time.size();

	std::vector<double>& a_time = this->charge_forecast.arrival_unix_time;
	std::vector<double>& d_time = this->charge_forecast.departure_unix_time;
	std::vector<double>& e_remain = this->charge_forecast.e3_charge_remain_kWh;
	std::vector<double>& e_step = this->charge_forecast.e3_step_max_kWh;	

	for(int i=0; i<size_val; i++)
	{
		is_forecasted_pev.push_back(true);
		arrival_time.push_back(a_time[i]);
		departure_time.push_back(d_time[i]);
		e_charge_remain_kWh.push_back(e_remain[i]);
		e_step_max_kWh.push_back(e_step[i]);
	}
}


void ES500_aggregator_helper::calc_obj_fun_constraints(double next_aggregator_timestep_start_time, std::vector<bool>& is_forecasted_pev, 
														std::vector<double>& arrival_time, std::vector<double>& departure_time, std::vector<double>& e_charge_remain_kWh, 
							 	  						std::vector<double>& e_step_max_kWh, ES500_aggregator_obj_fun_constraints& constraints)
{   
    double time_step_sec = 60*this->aggregator_time_step_mins;
	double begin_next_timestep = next_aggregator_timestep_start_time;
	double max_depart_time = *std::max_element(departure_time.begin(), departure_time.end());
	int k_max = std::floor(std::max(time_step_sec*this->num_agg_time_steps_in_prediction_horizon, max_depart_time - begin_next_timestep)/time_step_sec) + 2;

	std::vector<double> E_enrgy_ALAP_(k_max);
	std::vector<double> E_enrgy_ASAP_(k_max);	
	std::vector<double> E_step_ALAP_(k_max);

	std::fill(E_enrgy_ALAP_.begin(), E_enrgy_ALAP_.end(), 0);
	std::fill(E_enrgy_ASAP_.begin(), E_enrgy_ASAP_.end(), 0);
	std::fill(E_step_ALAP_.begin(), E_step_ALAP_.end(), 0);
	
	//===================================================
	
	int p, P, k, EndIndex_Park, StartIndex_ASAP;
	double e_remain, e_step_val, e_tmp, e_Park_EndIndex;
	double e_chrg_remain_kWh_tmp, e_step_max_kWh_tmp, arrival_time_tmp, depart_time_tmp;
	bool loop;

	P = departure_time.size();
	
	for(p = 0; p < P; p++)
	{
		e_chrg_remain_kWh_tmp = e_charge_remain_kWh[p];
		e_step_max_kWh_tmp = e_step_max_kWh[p];
		arrival_time_tmp = arrival_time[p];
		depart_time_tmp = departure_time[p];
	
        if(2*time_step_sec < depart_time_tmp - arrival_time_tmp - this->calc_obj_fun_constraints_depart_time_adjustment_sec)
            depart_time_tmp -= this->calc_obj_fun_constraints_depart_time_adjustment_sec;
    
		if(!is_forecasted_pev[p])
			StartIndex_ASAP = 0;
		else
		{
			StartIndex_ASAP = std::floor((arrival_time_tmp - begin_next_timestep)/time_step_sec) + 1;
			if (begin_next_timestep + time_step_sec*(StartIndex_ASAP) - arrival_time_tmp < this->data_lead_time_secs)
			   StartIndex_ASAP = StartIndex_ASAP + 1;
		}
		
		EndIndex_Park = std::floor((depart_time_tmp - begin_next_timestep)/time_step_sec);
		e_Park_EndIndex = e_step_max_kWh_tmp*((depart_time_tmp - begin_next_timestep) - time_step_sec*EndIndex_Park)/time_step_sec;
		
		if (EndIndex_Park < StartIndex_ASAP)
		{
			std::cerr << "EndIndex_Park < StartIndex_ASAP (Check input data!  Min park duration must be greater than max_agg_timestep (15 min) plus (data_lead_time_sec))" << std::endl;
			continue;
		}
		
		//----------------------------------		
	   	//		 E_enrgy_ASAP 
	   	//----------------------------------		
		e_remain = e_chrg_remain_kWh_tmp;
		k = StartIndex_ASAP;
		loop = true;
		
		while (loop)
		{
			if (e_remain <= e_step_max_kWh_tmp)
			{
				loop = false;
				if (k == EndIndex_Park)
					e_tmp = std::min(e_remain, e_Park_EndIndex);
				else
					e_tmp = e_remain;
			}		
			else
			{
				if (k == EndIndex_Park)
				{
					e_tmp = e_Park_EndIndex;
					loop = false;
				}
				else
					e_tmp = e_step_max_kWh_tmp;
			}
			
			E_enrgy_ASAP_[k] += e_tmp;
			e_remain -= e_tmp;			
			k += 1;
		}
	
		//----------------------------------		
	   	//		 E_enrgy_ALAP 
	   	//----------------------------------
		e_remain = e_chrg_remain_kWh_tmp;
		k = EndIndex_Park;
		loop = true;
		
		while (loop)
		{
			if (StartIndex_ASAP == EndIndex_Park)
			{
				e_tmp = std::min(e_remain, e_Park_EndIndex);
				loop = false;
			}
			else if (e_remain <= e_step_max_kWh_tmp)
			{
				if (k == EndIndex_Park && e_Park_EndIndex < e_remain)
					e_tmp = e_Park_EndIndex;
				else
				{
					e_tmp = e_remain;
					loop = false;
				}
			}
			else
			{
				if (k == StartIndex_ASAP)
					loop = false;
					
				if (k == EndIndex_Park)
					e_tmp = e_Park_EndIndex;
				else
					e_tmp = e_step_max_kWh_tmp;
			}
			
			E_enrgy_ALAP_[k] += e_tmp;
			e_remain -= e_tmp;
			k -= 1;
		}
		
		//----------------------------------		
	   	//		 E_step_UB_ALAP 
	   	//----------------------------------
		e_step_val = std::min(e_chrg_remain_kWh_tmp, e_step_max_kWh_tmp);
		k = StartIndex_ASAP;
		loop = true;
		
		while (loop)
		{
			if (k == EndIndex_Park)
			{
				e_tmp = std::min(e_step_val, e_Park_EndIndex);
				loop = false;
			}
			else
				e_tmp = e_step_val;

			E_step_ALAP_[k] += e_tmp;
			k += 1;
		}
	}
	
	//===================================================
	
	int K = this->num_agg_time_steps_in_prediction_horizon;
	constraints.E_cumEnergy_ALAP_kWh.resize(K);
	constraints.E_cumEnergy_ASAP_kWh.resize(K);
	constraints.E_energy_ALAP_kWh.resize(K);
	constraints.E_energy_ASAP_kWh.resize(K);
	constraints.E_step_ALAP.resize(K);
	
	constraints.E_cumEnergy_ALAP_kWh[0] = E_enrgy_ALAP_[0];
	constraints.E_cumEnergy_ASAP_kWh[0] = E_enrgy_ASAP_[0];						
	
	for (k = 1; k < K; k++)
	{
		constraints.E_cumEnergy_ALAP_kWh[k] = constraints.E_cumEnergy_ALAP_kWh[k-1] + E_enrgy_ALAP_[k];
		constraints.E_cumEnergy_ASAP_kWh[k] = constraints.E_cumEnergy_ASAP_kWh[k-1] + E_enrgy_ASAP_[k];
	}
	
	for (k = 0; k < K; k++)
	{
		if (std::abs(constraints.E_cumEnergy_ASAP_kWh[k] - constraints.E_cumEnergy_ALAP_kWh[k]) < 0.001)
			constraints.E_cumEnergy_ALAP_kWh[k] = constraints.E_cumEnergy_ASAP_kWh[k] - 0.001;
	}
	
	constraints.E_step_ALAP = E_step_ALAP_;
	constraints.E_energy_ALAP_kWh = E_enrgy_ALAP_;
	constraints.E_energy_ASAP_kWh = E_enrgy_ASAP_;
}


bool ES500_aggregator_helper::load_charging_forecast(ES500_aggregator_charging_forecast charging_forecast_)
{
    this->charge_forecast = charging_forecast_;
    return true;
}


bool ES500_aggregator_helper::load_charging_needs(std::map<process_id, ES500_aggregator_charging_needs> charging_needs)
{
    this->charging_needs_map.clear();
    this->charging_needs_map = charging_needs;
	return true;
}


std::map<process_id, ES500_aggregator_e_step_setpoints> ES500_aggregator_helper::allocate_energy_to_PEVs(double next_aggregator_timestep_start_time, double E_step_kWh)
{
    std::map<process_id, ES500_aggregator_e_step_setpoints> e_step_kWh;
	this->energy_to_PEVs.allocate_energy_to_PEVs(next_aggregator_timestep_start_time, E_step_kWh, this->charging_needs_map, e_step_kWh);	
    return e_step_kWh;
}


bool ES500_aggregator_helper::load_charging_forecast_protobuf(serialized_protobuf_obj charging_forecast)
{
	//return this->proto_translator_obj.GM0085_aggregator_charging_forecastdeserialize(charging_forecast, this->charge_forecast);
return false;
}


bool ES500_aggregator_helper::load_charging_needs_protobuf(std::map<process_id, serialized_protobuf_obj> charging_needs)
{
return false;
/*    
    this->charging_needs_map.clear();

	ES500_aggregator_charging_needs cpp_object;
	bool success;

	for(std::pair<const process_id, serialized_protobuf_obj> x : charging_needs)
	{
	//	success = this->proto_translator_obj.GM0085_aggregator_charging_needs__deserialize(x.second, cpp_object);
		if(!success)
		{			
			this->charging_needs_map.clear();
			return false;
		}

		this->charging_needs_map[x.first] = cpp_object;
	}

	return true;
*/
}


std::map<process_id, py::bytes> ES500_aggregator_helper::allocate_energy_to_PEVs_protobuf(double next_aggregator_timestep_start_time, double E_step_kWh)
{
	std::map<process_id, ES500_aggregator_e_step_setpoints> e_step_kWh;
	this->energy_to_PEVs.allocate_energy_to_PEVs(next_aggregator_timestep_start_time, E_step_kWh, this->charging_needs_map, e_step_kWh);	

	//-----------------------------

	std::map<process_id, py::bytes> return_val;
	serialized_protobuf_obj pb_object;
	bool success;

	for(std::pair<const process_id, ES500_aggregator_e_step_setpoints> x : e_step_kWh)
	{
		//success = this->proto_translator_obj.GM0085_aggregator_e_step_setpoints_serialize(x.second, pb_object);
		if(!success)
		{
			return_val.clear();
			break;
		}

		return_val[x.first] = py::bytes(pb_object);
	}

	return return_val;
}


ES500_aggregator_obj_fun_constraints ES500_aggregator_helper::get_obj_fun_constraints(double next_aggregator_timestep_start_time)
{
	ES500_aggregator_obj_fun_constraints constraints;

	std::vector<bool> is_forecasted_pev;
	std::vector<double> arrival_time;
	std::vector<double> departure_time;
	std::vector<double> e_charge_remain_kWh;
	std::vector<double> e_step_max_kWh;

	this->combine_actual_and_forecasted_pev_data(next_aggregator_timestep_start_time, is_forecasted_pev, arrival_time, departure_time, e_charge_remain_kWh, e_step_max_kWh);
	
    if(arrival_time.size() == 0)
        constraints.canSolve_aka_pev_charging_in_prediction_window = false;
    else
    {
        constraints.canSolve_aka_pev_charging_in_prediction_window = true;
        this->calc_obj_fun_constraints(next_aggregator_timestep_start_time, is_forecasted_pev, arrival_time, departure_time, e_charge_remain_kWh, e_step_max_kWh, constraints);
    }

	return constraints;
}
