from global_aux import Caldera_message_types, input_datasets, container_class
from control_templates import typeA_control

from dynamic_price_control.charge_controller import charge_controller

import time

from multiprocessing import Pool

class control_strategy_TE(typeA_control):
    
    def __init__(self, io_dir, simulation_time_constraints):
        super().__init__(io_dir, simulation_time_constraints)
        
        self.cs_id = 'ext0001'
        self.io_dir = io_dir
        self.control_timestep_min = 15    
        self.request_state_lead_time_min = (2*simulation_time_constraints.grid_timestep_sec + 0.5)/60
        self.send_control_info_lead_time_min = (simulation_time_constraints.grid_timestep_sec + 0.5)/60
        
        self.start_simulation_unix_time = simulation_time_constraints.start_simulation_unix_time
        self.end_simulation_unix_time = simulation_time_constraints.end_simulation_unix_time
        self.control_timestep_sec = self.control_timestep_min * 60
        
    
    def get_input_dataset_enum_list(self):
        return [input_datasets.SE_group_configuration, input_datasets.SE_group_charge_event_data, input_datasets.SEid_to_SE_type, input_datasets.charge_event_builder, input_datasets.external_strategies]

    def load_input_datasets(self, datasets_dict):
        # datasets_dict is a dictionary with input_datasets as keys.
        self.datasets_dict = datasets_dict
    
    def terminate_this_federate(self):
        
        if self.cs_id not in self.datasets_dict[input_datasets.external_strategies]:
            print("Control Strategy TE is not being used in charge events. Control Strategy TE federate Quitting")
            return True
        
        return False
    
    def initialize(self):
        # All supply_equipments in the simulation
        SE_ids = list(self.datasets_dict[input_datasets.SEid_to_SE_type].keys())
        
        self.controller = charge_controller(self.io_dir, self.start_simulation_unix_time, self.end_simulation_unix_time, self.control_timestep_sec, SE_ids)
        
        #forecasted_cost_data = self.controller.cost_forecaster.get_forecasted_cost_for_time_range(self.start_simulation_unix_time, self.end_simulation_unix_time, self.control_timestep_sec)
        #actual_cost_data = self.controller.cost_forecaster.get_actual_cost_for_time_range(self.start_simulation_unix_time, self.end_simulation_unix_time, self.control_timestep_sec)
        
        #cost_df = pd.DataFrame()
        #cost_df["time | hrs"] = np.arange(self.start_simulation_unix_time/3600.0, self.end_simulation_unix_time/3600.0, forecasted_cost_data.data_timestep_sec/3600.0)
        #cost_df["forecasted_cost | usd_per_kWh"] = forecasted_cost_data.data
        #cost_df["actual_cost | usd_per_kWh"] = actual_cost_data.data
        #cost_df.to_csv(os.path.join(self.io_dir.outputs_dir, "cost_profile.csv"), index = False)

        # keeps track of charge events that are handed over to charge controller
        self.processed_charge_events = []
        #-------------------------------------
        #    Calculate Timing Parameters
        #-------------------------------------        

        X = container_class()
        X.control_timestep_min = self.control_timestep_min
        X.request_state_lead_time_min = self.request_state_lead_time_min
        X.send_control_info_lead_time_min = self.send_control_info_lead_time_min
        self._calculate_timing_parameters(X, self.__class__.__name__)

       
    def log_data(self):
        pass
    
    def get_messages_to_request_state_info_from_Caldera(self, current_simulation_unix_time):
        return_dict = {}
        return_dict[Caldera_message_types.get_active_charge_events_by_extCS] = [self.cs_id]
        return return_dict
    
    def get_messages_to_request_state_info_from_OpenDSS(self, current_simulation_unix_time):
        return_dict = {}
        
        return return_dict
        
    def solve(self, current_simulation_unix_time, Caldera_state_info_dict, DSS_state_info_dict):
        # current_simulation_unix_time refers to when the next control action would start. i.e. begining of next control timestep 
        # and end of current control timestep


        next_control_starttime_sec = current_simulation_unix_time
        print("Control Strategy next_control_timestep_sec : ", next_control_starttime_sec/3600.0)

        self.controller.precompute_costs_for_time(next_control_starttime_sec)
        #----------------------------------------------------------
        #  Compare forecasted cost and actual cost for next step
        #----------------------------------------------------------
        
        start = time.time()
        forecasted_cost = self.controller.get_forecasted_cost_at_time_sec(next_control_starttime_sec)
        actual_cost = self.controller.get_actual_cost_at_time_sec(next_control_starttime_sec)
        
        print("{}: get costs".format(time.time() - start))
        
        #print("Control Strategy forecasted_cost : ", forecasted_cost)
        #print("Control Strategy actual_cost : ", actual_cost)
        
        tolerance = 0.10        # 10 percent
        cost_deviated_from_forecast = ((actual_cost - forecasted_cost) / forecasted_cost > tolerance)        
        print("Control Strategy cost_deviated_from_forecast : ", cost_deviated_from_forecast)
        
        CEs_all = Caldera_state_info_dict[Caldera_message_types.get_active_charge_events_by_extCS][self.cs_id]

        active_SEs = []
        
        
        num_added_events = 0
        start = time.time()
        
        #with Pool() as p:
        #    p.map(sub_solve, CEs_all)

        for CE in CEs_all:
            
            # get the charge_event id
            charge_event_id = CE.charge_event_id
            SE_id = CE.SE_id
            now_soc = CE.now_soc
            
            active_SEs.append(SE_id)
            
            str = 'time:{}  SE_id:{}  soc:{}  '.format(round(next_control_starttime_sec/3600.0, 4), SE_id, now_soc)
            #print(str)
            
            if (cost_deviated_from_forecast):
                #print("updating existing charge event: ", charge_event_id)
                self.controller.recalculate_active_charge_event(next_control_starttime_sec, CE)
            else:
                
                # process this charge event only if it is not already processed
                if charge_event_id not in self.processed_charge_events:
                    
                    num_added_events += 1

                    #print("adding new charge event: ", charge_event_id)
                    self.processed_charge_events.append(charge_event_id)                
                    # Add charge event to charge controller
                    self.controller.add_active_charge_event(next_control_starttime_sec, CE)
        
        if(cost_deviated_from_forecast):
            print("recalculating")
            num_events = len(CEs_all)
        else:
            print("adding")
            num_events = num_added_events

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
