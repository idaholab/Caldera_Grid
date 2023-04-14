
import enum

from Caldera_global import charge_event_data, get_vehicle_enum, supply_equipment_is_L2
from Caldera_global import L2_control_strategies_enum, pev_is_compatible_with_supply_equipment
from Caldera_global import stop_charging_criteria, control_strategy_enums
from Helper import assign_control_strategies_to_CE
from load_input_files import get_control_strategy_enums



class container_class:
    pass


class input_datasets(enum.Enum):
    SE_CE_data_obj = 1
    SE_group_configuration = 2
    SE_group_charge_event_data = 3
    SEid_to_SE_type = 4
    SEid_to_SE_group = 5
    charge_event_builder = 6 
    Caldera_L2_ES_strategies = 7
    Caldera_L2_VS_strategies = 8
    external_strategies = 9
    all_caldera_node_names = 10
    HPSE_caldera_node_names = 11
    baseLD_data_obj = 12
    Caldera_global_parameters = 13
    Caldera_control_strategy_parameters_dict = 14


class OpenDSS_message_types(enum.Enum):
    get_all_node_voltages = 1


class Caldera_message_types(enum.Enum):
    ES500_get_charging_needs = 1
    ES500_set_energy_setpoints = 2
    set_pev_charging_PQ = 3
    get_active_charge_events_by_extCS = 4
    get_active_charge_events_by_SE_groups = 5    
    get_active_charge_events_by_SEids = 6
    get_all_active_charge_events = 7
    stop_active_charge_events = 8
    add_charge_events = 9
    

class non_pev_feeder_load:

    def __init__(self, baseLD_data_obj):
        self.data_start_unix_time = baseLD_data_obj.data_start_unix_time
        self.data_timestep_sec = baseLD_data_obj.data_timestep_sec
        self.non_pev_feeder_load_akW = baseLD_data_obj.actual_load_akW
        
        if 0 < len(self.non_pev_feeder_load_akW):
            sum_val = 0
            for x in self.non_pev_feeder_load_akW:
                sum_val+= x
            
            self.avg_non_pev_feeder_load_akW = sum_val / len(self.non_pev_feeder_load_akW)
        else:
            self.avg_non_pev_feeder_load_akW = 0
    
    
    def get_non_pev_feeder_load_akW(self, simulation_unix_time):
        index = int(round((simulation_unix_time - self.data_start_unix_time) / self.data_timestep_sec, 0))
    
        if index < len(self.non_pev_feeder_load_akW):
            return self.non_pev_feeder_load_akW[index]
        else:
            return self.avg_non_pev_feeder_load_akW


class charge_event_builder:
    
    def __init__(self, SEid_to_SE_type, SEid_to_SE_group, L2_control_strategies_to_include, control_strategy_parameters_dict):
        self.SEid_to_SE_type = SEid_to_SE_type
        self.SEid_to_SE_group = SEid_to_SE_group
        self.L2_control_strategies_to_include = L2_control_strategies_to_include
        self.control_strategy_parameters_dict = control_strategy_parameters_dict
        
    def get_charge_event(self, charge_event_id, SE_id, vehicle_type, start_time_hrs, end_time_hrs, start_SOC, end_SOC, ES_str, VS_str, Ext_str):
        errors = []
        
        start_unix_time = start_time_hrs*3600.0
        end_unix_time = end_time_hrs*3600.0

        start_SOC = start_SOC*100.0
        end_SOC = end_SOC*100.0
        
        (conversion_successfull, vehicle_enum) = get_vehicle_enum(vehicle_type)
        
        if not conversion_successfull:
            errors.append("Invalid vehicle_type: {}".format(vehicle_type))
        
        #---------
        
        if SE_id not in self.SEid_to_SE_type:
            errors.append("Invalid SE_id: {}".format(SE_id))
        
        #---------
        
        if end_unix_time - start_unix_time < 1:
            errors.append("Departure time before arrival time.")
            
        if not (0 <= start_SOC and start_SOC < end_SOC and end_SOC <= 100):
            errors.append("Invalid soc values.")
        
        if len(errors) == 0:
            if not pev_is_compatible_with_supply_equipment(vehicle_enum, self.SEid_to_SE_type[SE_id]):
                errors.append("Incompatible Supply Equipment and PEV types.")
    
        #-------------------------------------
        
        if len(errors) == 0:
            vehicle_id = 0
            SE_group_id = self.SEid_to_SE_group[SE_id]
            charge_event = charge_event_data(charge_event_id, SE_group_id, SE_id, vehicle_id, vehicle_enum, start_unix_time, end_unix_time, start_SOC, end_SOC, stop_charging_criteria(), control_strategy_enums())
            
            #---------

            ES_str = ES_str.strip()
            VS_str = VS_str.strip()
            Ext_str = Ext_str.strip()
            
            line_number = "NA"
            (tmp_errors, control_strategies) = get_control_strategy_enums(ES_str, VS_str, Ext_str, line_number, self.L2_control_strategies_to_include)
            
            if len(tmp_errors) > 0:
                errors += tmp_errors
            else:
                if not supply_equipment_is_L2(self.SEid_to_SE_type[SE_id]):
                    ES_enum = control_strategies.ES_control_strategy
                    VS_enum = control_strategies.VS_control_strategy
                    NA_enum = L2_control_strategies_enum.NA
                    if ES_enum != NA_enum or VS_enum != NA_enum:
                        errors.append("L2 control strategy assigned to non L2 charge.")
                
                if len(errors) == 0:
                    assign_control_strategies_to_CE(control_strategies, charge_event, self.SEid_to_SE_type, self.control_strategy_parameters_dict)

        #-------------------------------------
        
        if len(errors) > 0:
            charge_event = None
        
        return (errors, charge_event)
