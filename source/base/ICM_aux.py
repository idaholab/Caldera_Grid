
from Caldera_ICM import interface_to_SE_groups
from Caldera_global import pev_charge_ramping_workaround
from Helper import build_L2_control_strategy_parameters
from global_aux import input_datasets, Caldera_message_types
from time import time

class ICM_aux:

    def __init__(self, SE_CE_data_obj, baseLD_data_obj, global_parameters, L2_control_strategy_parameters_dict, grid_timestep_sec, customized_pev_ramping, create_charge_profile_library, CE_queuing_inputs):
        self.grid_timestep_sec = grid_timestep_sec
  
        #------------------------
        
        self.ICM_obj = interface_to_SE_groups()
        
        #-----------------
        
        ramping_by_pevType_seType = []        
        for ((pev_type, SE_type), pev_charge_ramping_obj) in customized_pev_ramping.ramping_by_pevType_seType.items():
            X = pev_charge_ramping_workaround()
            X.pev_charge_ramping_obj = pev_charge_ramping_obj
            X.pev_type = pev_type
            X.SE_type = SE_type
            ramping_by_pevType_seType.append(X)
        
        #-----------------
        start_time = time()
        self.ICM_obj.initialize(create_charge_profile_library, customized_pev_ramping.ramping_by_pevType_only, ramping_by_pevType_seType)
        print('Time to initialize ICM (sec): {}'.format(time()-start_time))
        
        L2_control_strategy_parameters = build_L2_control_strategy_parameters(L2_control_strategy_parameters_dict)
        self.ICM_obj.initialize_L2_control_strategy_parameters(L2_control_strategy_parameters)
        
        data_start_unix_time = baseLD_data_obj.data_start_unix_time
        data_timestep_sec = baseLD_data_obj.data_timestep_sec
        actual_load_akW = baseLD_data_obj.actual_load_akW 
        forecast_load_akW = baseLD_data_obj.forecast_load_akW
        adjustment_interval_hrs = global_parameters['base_load_forecast_adjust_interval_hrs']
        self.ICM_obj.initialize_baseLD_forecaster(data_start_unix_time, data_timestep_sec, actual_load_akW, forecast_load_akW, adjustment_interval_hrs)
        
        self.ICM_obj.initialize_infrastructure(CE_queuing_inputs, SE_CE_data_obj.SE_group_configuration_list)
        self.ICM_obj.add_charge_events_by_SE_group(SE_CE_data_obj.SE_group_charge_events)
    
    
    def set_ensure_pev_charge_needs_met_for_ext_control_strategy(self, ensure_pev_charge_needs_met):
        self.ICM_obj.set_ensure_pev_charge_needs_met_for_ext_control_strategy(ensure_pev_charge_needs_met)
        
    
    def get_charging_power(self, now_unix_time, node_Vrms):
        prev_unix_time = now_unix_time - self.grid_timestep_sec
        pev_PQ = self.ICM_obj.get_charging_power(prev_unix_time, now_unix_time, node_Vrms)        
        return pev_PQ


    def process_control_messages(self, simulation_unix_time, msg_dict):
        # msg_dict is a dictionary with Caldera_message_types as keys.
        
        return_dict = {}
        
        for (msg_enum, parameters) in msg_dict.items():
            if msg_enum == Caldera_message_types.ES500_get_charging_needs:
                unix_time_begining_of_next_agg_step = parameters
                return_dict[msg_enum] = self.ICM_obj.ES500_get_charging_needs(simulation_unix_time, unix_time_begining_of_next_agg_step)
            
            elif msg_enum == Caldera_message_types.ES500_set_energy_setpoints:
                pev_energy_setpoints = parameters
                self.ICM_obj.ES500_set_energy_setpoints(pev_energy_setpoints)
    
            elif msg_enum == Caldera_message_types.set_pev_charging_PQ:
                SE_setpoints = parameters
                self.ICM_obj.set_PQ_setpoints(simulation_unix_time, SE_setpoints)
                
            elif msg_enum == Caldera_message_types.get_active_charge_events_by_extCS:
                external_control_strategies = parameters
                return_dict[msg_enum] = self.ICM_obj.get_active_CEs_by_extCS(external_control_strategies)
            
            elif msg_enum == Caldera_message_types.get_active_charge_events_by_SE_groups:
                SE_group_ids = parameters
                return_dict[msg_enum] = self.ICM_obj.get_active_CEs_by_SE_groups(SE_group_ids)
            
            elif msg_enum == Caldera_message_types.get_active_charge_events_by_SEids:
                SEids = parameters
                return_dict[msg_enum] = self.ICM_obj.get_active_CEs_by_SEids(SEids)
            
            elif msg_enum == Caldera_message_types.get_all_active_charge_events:
                return_dict[msg_enum] = self.ICM_obj.get_all_active_CEs()
            
            elif msg_enum == Caldera_message_types.stop_active_charge_events:
                SE_ids = parameters
                self.ICM_obj.stop_active_charge_events(SE_ids)
                
            elif msg_enum == Caldera_message_types.add_charge_events:
                charge_events = parameters
                self.ICM_obj.add_charge_events(charge_events)
            
            else:
                raise ValueError('Invalid message in caldera_ICM_aux::process_message.')
        
        # The return value (return_dict) must be a dictionary with Caldera_message_types as keys.
        # If there is nothing to return, return an empty dictionary.
        return return_dict


