
from math import floor

from Caldera_global import L2_control_strategies_enum, supply_equipment_enum, vehicle_enum, SE_setpoint
from global_aux import Caldera_message_types, OpenDSS_message_types, input_datasets, container_class
from control_templates import typeB_control


class control_strategy_B(typeB_control):
    
    def __init__(self, io_dir, simulation_time_constraints):
        super().__init__(io_dir, simulation_time_constraints)
    
    def get_input_dataset_enum_list(self):
        return [input_datasets.SE_group_configuration, input_datasets.SE_group_charge_event_data, input_datasets.SEid_to_SE_type]

    def load_input_datasets(self, datasets_dict):
        # datasets_dict is a dictionary with input_datasets as keys.
        self.datasets_dict = datasets_dict
    
    def terminate_this_federate(self):
        return False
    
    def initialize(self):
        pass
       
    def log_data(self):
        pass
    
    def get_messages_to_request_state_info_from_Caldera(self, current_simulation_unix_time):
        return_dict = {}
        #return_dict[Caldera_message_types.get_active_charge_events_by_SE_groups] = [10]
        return_dict[Caldera_message_types.get_active_charge_events_by_extCS] = ['ext0002q']
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

        #=================================
        #      Get Node Voltages
        #=================================
        node_voltages = DSS_state_info_dict[OpenDSS_message_types.get_all_node_voltages]
        
        '''
        for (node_id, puV) in node_voltages.items():
            print('node_id:{}  puV:{}'.format(node_id, puV))
        '''
        
        #=====================================================
        #     Look at active charge events
        #=====================================================

        # returns dictionary -> {SE_group : active_CE}
        #CEs_by_SE_groups = Caldera_state_info_dict[Caldera_message_types.get_active_charge_events_by_SE_groups]

        # returns dictionary -> {extCS : active_CE}
        CEs_by_extCS = Caldera_state_info_dict[Caldera_message_types.get_active_charge_events_by_extCS]

        # retuns list        -> [active_CE]
        #CEs_by_SE_id = Caldera_state_info_dict[Caldera_message_types.get_active_charge_events_by_SEids]

        # return list        -> [active_CE]
        #CEs_all = Caldera_state_info_dict[Caldera_message_types.get_all_active_charge_events]
        
        for (extCS, active_CEs) in CEs_by_extCS.items():
            for CE in active_CEs:
                SE_id = CE.SE_id
                charge_event_id = CE.charge_event_id
                now_unix_time = CE.now_unix_time
                now_soc = CE.now_soc
                now_charge_energy_ackWh = CE.now_charge_energy_ackWh
                energy_of_complete_charge_ackWh = CE.energy_of_complete_charge_ackWh
                remaining_charge_energy_ackWh = energy_of_complete_charge_ackWh - now_charge_energy_ackWh
                DC_power = CE.now_dcPkW
                AC_real_power = CE.now_acPkW
                AC_reactive_power = CE.now_acQkVAR

                str = 'time:{}  SE_id:{}  soc:{}  total_charge_ackWh:{}  remain_charge_ackWh:{}  DC_power:{}  AC_real_power:{}  AC_reactive_power:{}'.format(round(current_simulation_unix_time/3600.0, 4), SE_id, now_soc, round(energy_of_complete_charge_ackWh, 4), round(remaining_charge_energy_ackWh, 4), DC_power, AC_real_power, AC_reactive_power)
                #print(str)
                
        #=================================
        #      Control PEV Charging
        #=================================
        current_simulation_unix_time_hrs = (current_simulation_unix_time/3600)        
        clock_mins = 60*(current_simulation_unix_time_hrs - floor(current_simulation_unix_time_hrs))
        
        P_kW = 0
        Q_kVAR = 10
        
        if (clock_mins > 0) and (clock_mins < 30):
            P_kW = 1000
            Q_kVAR = 0

        #-----------------------------
        
        PQ_setpoints = []        
        
        extCS = 'ext0002q'
        for CE in CEs_by_extCS[extCS]:
            remaining_charge_energy_ackWh = CE.energy_of_complete_charge_ackWh - CE.now_charge_energy_ackWh
            #print(CE.SE_id, remaining_charge_energy_ackWh)
            if 0 < remaining_charge_energy_ackWh:
                X = SE_setpoint()
                X.SE_id = CE.SE_id
                X.PkW = P_kW
                X.QkVAR = Q_kVAR
            
                PQ_setpoints.append(X)
        
        #-----------------------------
        
        Caldera_control_info_dict = {}
        if len(PQ_setpoints) > 0:
            Caldera_control_info_dict[Caldera_message_types.set_pev_charging_PQ] = PQ_setpoints
        
        DSS_control_info_dict = {}
        
        # Caldera_control_info_dict must be a dictionary with Caldera_message_types as keys.
        # DSS_control_info_dict must be a dictionary with OpenDSS_message_types as keys.
        # If either value has nothing to return, return an empty dictionary.
        return (Caldera_control_info_dict, DSS_control_info_dict)