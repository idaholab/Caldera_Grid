
from math import floor

from Caldera_global import L2_control_strategies_enum, supply_equipment_enum, vehicle_enum, SE_setpoint
from global_aux import Caldera_message_types, OpenDSS_message_types, input_datasets, container_class
from control_templates import typeA_control


class control_strategy_A(typeA_control):

    def __init__(self, io_dir, simulation_time_constraints):        
        super().__init__(io_dir, simulation_time_constraints)
        
        self.control_timestep_min = 15        
        self.request_state_lead_time_min = 10.1
        self.send_control_info_lead_time_min = (simulation_time_constraints.grid_timestep_sec + 0.5)/60
    
    
    def get_input_dataset_enum_list(self):
        return [input_datasets.SE_group_configuration, input_datasets.SE_group_charge_event_data, input_datasets.SEid_to_SE_type]


    def load_input_datasets(self, datasets_dict):
        # datasets_dict is a dictionary with input_datasets as keys.
        self.datasets_dict = datasets_dict
    
    
    def terminate_this_federate(self):
        return False
    
    
    def initialize(self):
        #-------------------------------------
        #    Calculate Timing Parameters
        #-------------------------------------        
        X = container_class()
        X.control_timestep_min = self.control_timestep_min
        X.request_state_lead_time_min = self.request_state_lead_time_min
        X.send_control_info_lead_time_min = self.send_control_info_lead_time_min
        self._calculate_timing_parameters(X, self.__class__.__name__)
    
        #-------------------------------------
        #      Get Charge Event Data
        #-------------------------------------
        charge_events = self.datasets_dict[input_datasets.SE_group_charge_event_data]
        
        # Example
        for CE_group in charge_events:
            SE_group_id = CE_group.SE_group_id
            
            for CE in CE_group.charge_events:
                id = CE.charge_event_id
                SE_id = CE.SE_id
                arrival_time = CE.arrival_unix_time
                arrival_SOC = CE.arrival_SOC
                #...
           
        '''
        Charge Events
            charge_events.SE_group_id (int)
            charge_events.charge_events -> List of charge events
            
                X = charge_events.charge_events
                X.charge_event_id       (int)
                X.SE_group_id           (int)
                X.SE_id                 (int)
                X.vehicle_id            (int)
                X.vehicle_type          (vehicle_enum)
                X.arrival_unix_time     (double)
                X.departure_unix_time   (double)
                X.arrival_SOC           (double)
                X.departure_SOC         (double)
                X.control_enums         (control_strategy_enums)
            
                vehicle_enum.phev20
                vehicle_enum.phev50
                vehicle_enum.phev_SUV
                vehicle_enum.bev150_ld1_50kW
                vehicle_enum.bev250_ld1_75kW
                vehicle_enum.bev275_ld1_150kW
                vehicle_enum.bev200_ld4_150kW
                vehicle_enum.bev250_ld2_300kW
                
                control_strategy_enums.inverter_model_supports_Qsetpoint    (boolean)
                control_strategy_enums.ES_control_strategy                  (L2_control_strategies_enum)
                control_strategy_enums.VS_control_strategy                  (L2_control_strategies_enum)
                control_strategy_enums.ext_control_strategy                 (string)
                 
                L2_control_strategies_enum.NA
                L2_control_strategies_enum.ES100_A
                L2_control_strategies_enum.ES100_B
                L2_control_strategies_enum.ES110
                L2_control_strategies_enum.ES500
                L2_control_strategies_enum.VS200_A
                L2_control_strategies_enum.VS200_B
        '''
        
        #-------------------------------------
        #      Get Supply Equipment Data
        #-------------------------------------
        SE_group_config = self.datasets_dict[input_datasets.SE_group_configuration]        
        SEid_to_SE_type = self.datasets_dict[input_datasets.SEid_to_SE_type]
        
        # Example
        for SE_group in SE_group_config:
            group_id = SE_group.SE_group_id
            
            for SE in SE_group.SEs:
                group_id = SE.SE_group_id
                SE_id = SE.SE_id
                SE_type = SE.supply_equipment_type
                lat = SE.lattitude
                long = SE.longitude
                node_id = SE.grid_node_id
                loc_type = SE.location_type

        '''
        Supply Equipment Types
            supply_equipment_enum.L1_1440
            supply_equipment_enum.L2_3600
            supply_equipment_enum.L2_7200
            supply_equipment_enum.L2_9600
            supply_equipment_enum.L2_11520
            supply_equipment_enum.L2_17280
            supply_equipment_enum.dcfc_50
            supply_equipment_enum.xfc_150
            supply_equipment_enum.xfc_350
        '''
    
       
    def log_data(self):
        pass
        
    
    def get_messages_to_request_state_info_from_Caldera(self, next_control_timestep_start_unix_time):
        return_dict = {}
        return_dict[Caldera_message_types.get_active_charge_events_by_SE_groups] = [10]
        #return_dict[Caldera_message_types.get_active_charge_events_by_extCS] = ['ext0001q']
        #return_dict[Caldera_message_types.get_active_charge_events_by_SEids] = [1, 2, 3, 4]
        #return_dict[Caldera_message_types.get_all_active_charge_events] = None
        
        # The return value (return_dict) must be a dictionary with Caldera_message_types as keys.
        # If there is nothing to return, return an empty dictionary.
        return return_dict
    
    
    def get_messages_to_request_state_info_from_OpenDSS(self, next_control_timestep_start_unix_time):
        return_dict = {}
        return_dict[OpenDSS_message_types.get_all_node_voltages] = None
        
        # The return value (return_dict) must be a dictionary with OpenDSS_message_types as keys.
        # If there is nothing to return, return an empty dictionary.
        return return_dict
    
    
    def solve(self, next_control_timestep_start_unix_time, Caldera_state_info_dict, DSS_state_info_dict):
        # Caldera_state_info_dict is a dictionary with Caldera_message_types as keys.
        # DSS_state_info_dict is a dictionary with OpenDSS_message_types as keys. 

        #=================================
        #      Display Node Voltages
        #=================================
        node_voltages = DSS_state_info_dict[OpenDSS_message_types.get_all_node_voltages]
        
        '''
        for (node_id, puV) in node_voltages.items():
            print('node_id:{}  puV:{}'.format(node_id, puV))
        '''
        
        #=====================================================
        #     Look at active charge events
        #=====================================================

        # returns dictionary -> {SE_group : [active_CE]}
        CEs_by_SE_groups = Caldera_state_info_dict[Caldera_message_types.get_active_charge_events_by_SE_groups]

        # returns dictionary -> {extCS : [active_CE]}
        #CEs_by_extCS = Caldera_state_info_dict[Caldera_message_types.get_active_charge_events_by_extCS]

        # retuns list        -> [active_CE]
        #CEs_by_SE_id = Caldera_state_info_dict[Caldera_message_types.get_active_charge_events_by_SEids]

        # return list        -> [active_CE]
        #CEs_all = Caldera_state_info_dict[Caldera_message_types.get_all_active_charge_events]
        
        for (group_id, active_CEs) in CEs_by_SE_groups.items():
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
                vehicle_id = CE.vehicle_id
                vehicle_type = CE.vehicle_type

                str = 'time:{}  SE_id:{}  soc:{}  total_charge_ackWh:{}  remain_charge_ackWh:{}  DC_power:{}  AC_real_power:{}  AC_reactive_power:{} vid:{} vtype:{}'.format(round(next_control_timestep_start_unix_time/3600.0, 4), SE_id, now_soc, round(energy_of_complete_charge_ackWh, 4), round(remaining_charge_energy_ackWh, 4), DC_power, AC_real_power, AC_reactive_power, vehicle_id, vehicle_type)
                #print(str)
        
        #=================================
        #      Control PEV Charging
        #=================================        
        next_control_timestep_start_hrs = (next_control_timestep_start_unix_time/3600)        
        clock_mins = 60*(next_control_timestep_start_hrs - floor(next_control_timestep_start_hrs))
        
        P_kW = 0
        Q_kVAR = 10
        if abs(clock_mins - 15) < 0.01 or abs(clock_mins - 45) < 0.01:
            P_kW = 10
            Q_kVAR = 0
        
        #-----------------------------
        
        PQ_setpoints = []        
        
        SE_group_id = 10
        for CE in CEs_by_SE_groups[SE_group_id]:
            remaining_charge_energy_ackWh = CE.energy_of_complete_charge_ackWh - CE.now_charge_energy_ackWh
            
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

