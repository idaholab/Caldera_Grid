
from math import floor

from Caldera_globals import L2_control_strategies_enum, SE_setpoint
from global_aux import Caldera_message_types, OpenDSS_message_types, input_datasets, container_class
from control_templates import typeB_control


class control_strategy_C(typeB_control):
    
    def __init__(self, base_dir, simulation_time_constraints):
        super().__init__(base_dir, simulation_time_constraints)
    
    def get_input_dataset_enum_list(self):
        return [input_datasets.SE_group_configuration, input_datasets.SE_group_charge_event_data, input_datasets.SEid_to_SE_type, input_datasets.charge_event_builder]

    def load_input_datasets(self, datasets_dict):
        # datasets_dict is a dictionary with input_datasets as keys.
        self.datasets_dict = datasets_dict
    
    def terminate_this_federate(self):
        return False
    
    def initialize(self):
        self.iteration_number = 0
        pass
       
    def log_data(self):
        pass
    
    def get_messages_to_request_state_info_from_Caldera(self, current_simulation_unix_time):
        return_dict = {}
        #return_dict[Caldera_message_types.get_active_charge_events_by_SE_groups] = [10]
        #return_dict[Caldera_message_types.get_active_charge_events_by_extCS] = ['ext0003q']
        #return_dict[Caldera_message_types.get_active_charge_events_by_SEids] = [1, 2, 3, 4]
        #return_dict[Caldera_message_types.get_all_active_charge_events] = None
        
        # The return value (return_dict) must be a dictionary with Caldera_message_types as keys.
        # If there is nothing to return, return an empty dictionary.
        return return_dict
    
    def get_messages_to_request_state_info_from_OpenDSS(self, current_simulation_unix_time):
        return_dict = {}
        return_dict[OpenDSS_message_types.get_all_node_voltages] = None
        
        # The return value (return_dict) must be a dictionary with OpenDSS_message_types as keys.
        # If there is nothing to return, return an empty dictionary.
        return return_dict
        
    def solve(self, current_simulation_unix_time, Caldera_state_info_dict, DSS_state_info_dict):
        # Caldera_state_info_dict is a dictionary with Caldera_message_types as keys.
        # DSS_state_info_dict is a dictionary with OpenDSS_message_types as keys.

        Caldera_control_info_dict = {}
        DSS_control_info_dict = {}
        
        # add 2 similar charge event at different SEs in the first iteration
        if self.iteration_number == 0:
            charge_event_id = 1         # Does not have to be unique for Caldera ICM, but uniqueness could be needed for control
            SE_id = 5                   # Target supply equipment for charge event
            vehicle_type = "bev250_ld2_300kW"
            start_time_hrs = 16
            end_time_hrs = 18
            start_SOC = 0
            end_SOC = 1
            ES_str = "NA"
            VS_str = "NA"
            Ext_str = "NA"

            Caldera_control_info_dict[Caldera_message_types.add_charge_events] = []
            
            errors, charge_event = self.datasets_dict[input_datasets.charge_event_builder].get_charge_event(charge_event_id, SE_id, vehicle_type, start_time_hrs, end_time_hrs, start_SOC, end_SOC, ES_str, VS_str, Ext_str)
            if(len(errors) == 0):
                Caldera_control_info_dict[Caldera_message_types.add_charge_events].append(charge_event)
            else:
                for error in errors:
                    print(error)

            errors, charge_event = self.datasets_dict[input_datasets.charge_event_builder].get_charge_event(charge_event_id, SE_id+1, vehicle_type, start_time_hrs, end_time_hrs, start_SOC, end_SOC, ES_str, VS_str, Ext_str)
            if(len(errors) == 0):
                Caldera_control_info_dict[Caldera_message_types.add_charge_events].append(charge_event)
            else:
                for error in errors:
                    print(error)
            
            self.iteration_number += 1

        # Stop one of the charge event in the middle
        current_simulation_unix_time_hrs = (current_simulation_unix_time/3600)
        
        if 3600*abs(current_simulation_unix_time_hrs - 17) < 0.5*self.grid_timestep_sec:
            print("stopping charge event")
            Caldera_control_info_dict[Caldera_message_types.stop_active_charge_events] = [6]        # -> list of SE_id to stop charging
        
        # Caldera_control_info_dict must be a dictionary with Caldera_message_types as keys.
        # DSS_control_info_dict must be a dictionary with OpenDSS_message_types as keys.
        # If either value has nothing to return, return an empty dictionary.
        return (Caldera_control_info_dict, DSS_control_info_dict)