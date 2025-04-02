
from math import floor

from Caldera_globals import L2_control_strategies_enum, SE_setpoint
from global_aux import Caldera_message_types, OpenDSS_message_types, input_datasets, container_class
from control_templates import typeA_control
import os
import pandas as pd
import glob

class control_strategy_emosaic(typeA_control):
    
    def __init__(self, io_dir, simulation_time_constraints):
        super().__init__(io_dir, simulation_time_constraints)

        self.io_dir = io_dir
        self.control_timestep_min = 60        
        self.request_state_lead_time_min = 3
        self.send_control_info_lead_time_min = 2
    
    def get_input_dataset_enum_list(self):
        return [input_datasets.SE_group_configuration, input_datasets.SE_group_charge_event_data, input_datasets.SEid_to_SE_type, input_datasets.charge_event_builder]

    def load_input_datasets(self, datasets_dict):
        # datasets_dict is a dictionary with input_datasets as keys.
        self.datasets_dict = datasets_dict
    
    def terminate_this_federate(self):
        return False
    
    def initialize(self):
        X = container_class()
        X.control_timestep_min = self.control_timestep_min
        X.request_state_lead_time_min = self.request_state_lead_time_min
        X.send_control_info_lead_time_min = self.send_control_info_lead_time_min
        self._calculate_timing_parameters(X, self.__class__.__name__)

        self.agent = RE_agent(os.path.join(self.io_dir.inputs_dir, 'charge_event_generator'))

        # Sample 24 hour price profile for Reinforcement learning
        self.price_profile = [0.8, 0.9, 1.0, 1.1, 1.2, 0.8, 0.9, 1.0, 1.1, 1.2, 0.8, 0.9, 1.0, 1.1, 1.2, 0.8, 0.9, 1.0, 1.1, 1.2, 0.8, 0.9, 1.0, 1.1]

        self.iteration_number = 0
       
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
        #return_dict[OpenDSS_message_types.get_hourly_node_voltages] = None
        
        # The return value (return_dict) must be a dictionary with OpenDSS_message_types as keys.
        # If there is nothing to return, return an empty dictionary.
        return return_dict
        
    def solve(self, current_simulation_unix_time, Caldera_state_info_dict, DSS_state_info_dict):
        # Caldera_state_info_dict is a dictionary with Caldera_message_types as keys.
        # DSS_state_info_dict is a dictionary with OpenDSS_message_types as keys.
        
        Caldera_control_info_dict = {}
        Caldera_control_info_dict[Caldera_message_types.add_charge_events] = []
        DSS_control_info_dict = {}

        hour = int(current_simulation_unix_time/3600)
        print("Solving for hour {}".format(hour))

        pu_price = self.price_profile[hour%24]
        
        CEs_852 = self.agent.get_charge_events_to_add(pu_price, '852', hour)
        CEs_862 = self.agent.get_charge_events_to_add(pu_price, '862', hour)

        all_CEs = CEs_852 + CEs_862

        for CE in all_CEs:
            errors, charge_event = self.datasets_dict[input_datasets.charge_event_builder].get_charge_event(
                CE[0], # charge_event_id
                CE[1], # SE_id
                CE[2], # vehicle_type
                CE[3], # start_time_hrs
                CE[4], # end_time_hrs
                CE[5]/100, # start_SOC
                CE[6]/100, # end_SOC
                CE[7], # ES_str
                CE[8], # VS_str
                "NA") # Ext_str

            if(len(errors) == 0):
                print("charge_event_id:", charge_event.charge_event_id, "SE_id:", charge_event.SE_id, "vehicle_type:", charge_event.vehicle_type, "arrival_unix_time:", charge_event.arrival_unix_time/3600, "departure_unix_time:", charge_event.departure_unix_time/3600, "arrival_SOC:", charge_event.arrival_SOC, "departure_SOC:", charge_event.departure_SOC)
                
                Caldera_control_info_dict[Caldera_message_types.add_charge_events].append(charge_event)
            else:
                for error in errors:
                    print(error)

        print("len(Caldera_control_info_dict):", len(Caldera_control_info_dict))
            
        #errors, charge_event = self.datasets_dict[input_datasets.charge_event_builder].get_charge_event( hour, 11, 'ld_100kWh', hour+(10/60), hour+(50/60), 0.2, 0.8, 'NA','NA', 'NA')
        
        #Caldera_control_info_dict[Caldera_message_types.add_charge_events].append(charge_event)

        #node_voltages = DSS_state_info_dict[OpenDSS_message_types.get_all_node_voltages]
        #print(node_voltages.keys())

        #node_id = '852'   
        #print('node_id:{}  puV:{}'.format(node_id, node_voltages[node_id]))
        
        #node_id = '862'   
        #print('node_id:{}  puV:{}'.format(node_id, node_voltages[node_id]))



        # Caldera_control_info_dict must be a dictionary with Caldera_message_types as keys.
        # DSS_control_info_dict must be a dictionary with OpenDSS_message_types as keys.
        # If either value has nothing to return, return an empty dictionary.
        return (Caldera_control_info_dict, DSS_control_info_dict)

class RE_agent():
    def __init__(self, input_folder):

        self.input_folder = input_folder        
        self.df_dicts = {}

        files = glob.glob(self.input_folder + "/CE_Site*_Ppu_*.csv")

        for file in files:
            self.df_dicts[os.path.basename(file)] = pd.read_csv((file), keep_default_na = False)
            #print(self.df_dicts[file].head(5))
        
    def get_charge_events_to_add(self, pu_price, node, hour):

        base_filename = "CE_Site{}_Ppu_{}.csv".format(node, str(pu_price).replace('.', 'p'))

        df1 = self.df_dicts[base_filename]
        df2 = df1.loc[(df1['start_time']>(hour)) & (df1['start_time']<(hour+1))]

        #return charge events as a list of tuples
        zipped_list = list(zip(
            df2['charge_event_id'], 
            df2['SE_id'], 
            df2['pev_type'], 
            df2['start_time'], 
            df2['end_time_prk'], 
            df2['soc_i'], 
            df2['soc_f'], 
            df2['ES_strategy'], 
            df2['VS_strategy'], 
            df2['Ext_strategy'])
            )


        return zipped_list

