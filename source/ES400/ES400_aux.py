from global_aux import Caldera_message_types, input_datasets, container_class
from control_templates import typeA_control
from Caldera_ICM_Aux import get_baseLD_forecast
from Caldera_globals import L2_control_strategies_enum

from charge_controller import charge_controller
from cost_forecaster import TE_cost_forecaster_v2, TE_cost_forecaster_v3

import time
import os

class ES400_aux(typeA_control):
    
    def __init__(self, io_dir, simulation_time_constraints):
        super().__init__(io_dir, simulation_time_constraints)
        
        self.simulation_time_constraints = simulation_time_constraints
        self.io_dir = io_dir
        
    
    def get_input_dataset_enum_list(self):
        return [
        input_datasets.SE_CE_data_obj, 
        input_datasets.baseLD_data_obj, 
        input_datasets.SE_group_configuration, 
        input_datasets.Caldera_L2_ES_strategies, 
        input_datasets.Caldera_global_parameters, 
        input_datasets.Caldera_control_strategy_parameters_dict, 
        input_datasets.SE_group_charge_event_data, 
        input_datasets.SEid_to_SE_type
        ]

    def load_input_datasets(self, datasets_dict):
        # datasets_dict is a dictionary with input_datasets as keys.
        self.datasets_dict = datasets_dict
    
    def terminate_this_federate(self):
        
        return L2_control_strategies_enum.ES400 not in self.datasets_dict[input_datasets.Caldera_L2_ES_strategies]
    
    def initialize(self):

        SE_CE_data_obj = self.datasets_dict[input_datasets.SE_CE_data_obj]
        baseLD_data_obj = self.datasets_dict[input_datasets.baseLD_data_obj]
        global_parameters = self.datasets_dict[input_datasets.Caldera_global_parameters]
        L2_control_strategy_parameters_dict = self.datasets_dict[input_datasets.Caldera_control_strategy_parameters_dict]
        ES400_params = L2_control_strategy_parameters_dict[L2_control_strategies_enum.ES400]
        
        self.start_simulation_unix_time = self.simulation_time_constraints.start_simulation_unix_time
        self.end_simulation_unix_time = self.simulation_time_constraints.end_simulation_unix_time
        self.controller_timestep_mins = ES400_params['controller_timestep_mins']
        self.communication = ES400_params['communication']
        self.forecast_duration_sec = ES400_params['controller_forecast_horizon_hrs'] * 3600
        self.use_cost_forecaster_v3 = True
        self.plot = True

        #-------------------------------------
        #    Calculate Timing Parameters
        #-------------------------------------        

        X = container_class()
        X.control_timestep_min = self.controller_timestep_mins
        X.send_control_info_lead_time_min = (self.simulation_time_constraints.grid_timestep_sec + 0.5)/60
        X.request_state_lead_time_min = (2*self.simulation_time_constraints.grid_timestep_sec + 0.5)/60
        self._calculate_timing_parameters(X, self.__class__.__name__)

        #-------------------------------------
        #    Initialize ES400 controller
        #-------------------------------------        

        # All supply_equipments in the simulation using this control strategy      

        SE_ids = []
        charge_events = self.datasets_dict[input_datasets.SE_group_charge_event_data]
        
        for CE_group in charge_events:
            for CE in CE_group.charge_events:

                if CE.control_enums.ES_control_strategy == L2_control_strategies_enum.ES400:
                    SE_ids.append(CE.SE_id)

        
        charge_controller_input = container_class()
        charge_controller_input.io_dir = self.io_dir
        charge_controller_input.controller_starttime_sec = self.start_simulation_unix_time
        charge_controller_input.controller_endtime_sec = self.end_simulation_unix_time
        charge_controller_input.controller_timestep_sec = self.controller_timestep_mins
        charge_controller_input.forecast_duration_sec = self.forecast_duration_sec
        charge_controller_input.SE_ids = SE_ids
        charge_controller_input.communication = self.communication
        
        self.controller = charge_controller(charge_controller_input)
        
        if self.use_cost_forecaster_v3:
            self.cost_forecaster = TE_cost_forecaster_v3(os.path.join(self.io_dir.inputs_dir, "TE_inputs"), self.io_dir.figures_dir, self.plot)
        else:
            
            forecast_file = os.path.join(self.io_dir.inputs_dir, "TE_inputs", "forecast.csv")
            actual_file = os.path.join(self.io_dir.inputs_dir, "TE_inputs", "actual.csv")
            cost_file = os.path.join(self.io_dir.inputs_dir, "TE_inputs", "generation_cost.json")
        
            # cost_forcaster contains the cost of energy
            self.cost_forecaster = TE_cost_forecaster_v2(forecast_file, actual_file, cost_file, self.figures_folder, self.plot)
        
        # keeps track of charge events that are handed over to charge controller
        self.processed_charge_events = []
        
       
    def log_data(self):
        pass
    
    def get_messages_to_request_state_info_from_Caldera(self, current_simulation_unix_time):
        return_dict = {}
        return return_dict
    
    def get_messages_to_request_state_info_from_OpenDSS(self, current_simulation_unix_time):
        return_dict = {}
        
        return return_dict
        
    def solve(self, current_simulation_unix_time, Caldera_state_info_dict, DSS_state_info_dict):
        # current_simulation_unix_time refers to when the next control action would start. i.e. begining of next control timestep 
        # and end of current control timestep

        next_control_starttime_sec = current_simulation_unix_time
        print("Control Strategy next_control_timestep_sec : ", next_control_starttime_sec/3600.0)

        forecasted_cost_ts = self.cost_forecaster.get_cost_for_time_range(
            "adjusted", next_control_starttime_sec, next_control_starttime_sec, 
            next_control_starttime_sec + self.forecast_duration_sec, self.controller_timestep_mins)

        #----------------------------------------------------------
        #  Compare forecasted cost and actual cost for next step
        #----------------------------------------------------------
        
        start = time.time()
                
        CEs_all = Caldera_state_info_dict[Caldera_message_types.get_active_charge_events_by_extCS][self.cs_id]

        active_SEs = [CE.SE_id for CE in CEs_all]
        
        new_CEs = []
        CEs_to_adjust = []
        
        start = time.time()
        
        for CE in CEs_all:
            
            CE_id = CE.charge_event_id
            
            if CE_id not in self.processed_charge_events:
                new_CEs.append(CE)
                self.processed_charge_events.append(CE_id)                

#            else:
#                if (cost_deviated_from_forecast):
#                    CEs_to_adjust.append(CE)
        
        EV_forecast_update1 = self.controller.add_new_charge_events(next_control_starttime_sec, new_CEs, forecasted_cost_ts)
        EV_forecast_update2 = self.controller.adjust_old_charge_events(next_control_starttime_sec, CEs_to_adjust, forecasted_cost_ts)

        if self.communication:
            self.cost_forecaster.adjust_EV_charging_demand(EV_forecast_update1, next_control_starttime_sec, self.forecast_duration_sec)
            self.cost_forecaster.adjust_EV_charging_demand(EV_forecast_update2, next_control_starttime_sec, self.forecast_duration_sec)

        num_events = len(new_CEs) + len(CEs_to_adjust)
        print("{}: num events solved".format(num_events))
        time_taken = time.time() - start
        print("{}: solve".format(time_taken))
        if num_events > 0:
            print("{}: avg time per event".format(time_taken/num_events))
        
        #-----------------------------
            
        Caldera_control_info_dict = {}
        DSS_control_info_dict = {}
        
        # get control setpoints from controller
        PQ_setpoints = self.controller.get_SE_setpoints(next_control_starttime_sec, active_SEs)
 
        print("                                           ")
        print("===========================================")
        print("                                           ")
        
        #-----------------------------
        
        if len(PQ_setpoints) > 0:
            Caldera_control_info_dict[Caldera_message_types.set_pev_charging_PQ] = PQ_setpoints
        
        # Caldera_control_info_dict must be a dictionary with Caldera_message_types as keys.
        # DSS_control_info_dict must be a dictionary with OpenDSS_message_types as keys.
        # If either value has nothing to return, return an empty dictionary.
        return (Caldera_control_info_dict, DSS_control_info_dict)
