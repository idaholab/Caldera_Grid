
from math import floor, ceil, fmod

from Caldera_globals import L2_control_strategies_enum, SE_setpoint, timeseries, active_CE
from global_aux import Caldera_message_types, OpenDSS_message_types, input_datasets, container_class
from control_templates import typeA_control

from Caldera_ICM_Aux import CP_interface_v2
import os 
import pandas as pd
import numpy as np
from typing import List
import matplotlib.pyplot as plt
import json

from scipy.linalg import solve

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
        
        self.controller = charge_controller(self.io_dir.inputs_dir, self.start_simulation_unix_time, self.end_simulation_unix_time, self.control_timestep_sec, SE_ids)
        
        cost_data = self.controller.cost_forecaster.get_cost_for_time_range(self.start_simulation_unix_time, self.end_simulation_unix_time, self.control_timestep_sec)
        
        cost_df = pd.DataFrame()
        cost_df["time_hrs"] = np.arange(self.start_simulation_unix_time/3600.0, self.end_simulation_unix_time/3600.0, cost_data.data_timestep_sec/3600.0)
        cost_df["cost_usd_per_kWh"] = cost_data.data
        cost_df.to_csv(os.path.join(self.io_dir.outputs_dir, "cost_profile.csv"), index = False)

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

        #----------------------------------------------------------
        #  Compare forecasted cost and actual cost for next step
        #----------------------------------------------------------
        
        forecasted_cost = self.controller.get_forecasted_cost_at_time_sec(next_control_starttime_sec)
        actual_cost = self.controller.get_actual_cost_at_time_sec(next_control_starttime_sec)
        
        print("Control Strategy forecasted_cost : ", forecasted_cost)
        print("Control Strategy actual_cost : ", actual_cost)
        
        tolerance = 0.05        # 5 percent
        cost_deviated_from_forecast = ((actual_cost - forecasted_cost) / forecasted_cost > tolerance)        
        print("Control Strategy cost_deviated_from_forecast : ", cost_deviated_from_forecast)
        
        CEs_all = Caldera_state_info_dict[Caldera_message_types.get_active_charge_events_by_extCS][self.cs_id]

        active_SEs = []
        for CE in CEs_all:
            
            # get the charge_event id
            charge_event_id = CE.charge_event_id
            SE_id = CE.SE_id
            now_soc = CE.now_soc
            
            active_SEs.append(SE_id)
            
            str = 'time:{}  SE_id:{}  soc:{}  '.format(round(next_control_starttime_sec/3600.0, 4), SE_id, now_soc)
            #print(str)
            
            if (cost_deviated_from_forecast):
                print("updating existing charge event: ", charge_event_id)
                self.controller.recalculate_active_charge_event(next_control_starttime_sec, CE)
            else:
                
                # process this charge event only if it is not already processed
                if charge_event_id not in self.processed_charge_events:
                    
                    print("adding new charge event: ", charge_event_id)
                    self.processed_charge_events.append(charge_event_id)                
                    # Add charge event to charge controller
                    self.controller.add_active_charge_event(next_control_starttime_sec, CE)

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

class charge_controller:
    '''
    Description:
        charge_controller is the controller that decides cheapest time for charge to occur based on cost of electricity.
    '''
    
    def __init__(self, input_folder : str, starttime_sec : float, endtime_sec : float, timestep_sec : float, SE_ids : List[int]):
        '''
        Description:
            constuctor initializes the charge controller, allocates the controller_2Darr that maintains the status of charge events being controlled.
        '''
        
        self.plot = False
        self.plots = set()
        
        self.forecast_duration_sec = 12*3600            # Max forecast of 12 hours
        self.controller_starttime_sec = starttime_sec   
        self.controller_endtime_sec = endtime_sec + self.forecast_duration_sec
        self.controller_timestep_sec = timestep_sec
        self.charge_profile_timestep_sec = 60           # 1 minute timestep
            
        # CP_interface_v2 generates charge profiles
        self.charge_profiles = CP_interface_v2(input_folder)
        
        forecast_file = os.path.join(input_folder, "TE_inputs/forecast.csv")
        actual_file = os.path.join(input_folder, "TE_inputs/actual.csv")
        cost_file = os.path.join(input_folder, "TE_inputs/generation_cost.json")
        
        # cost_forcaster contains the cost of energy
        self.cost_forecaster = TE_cost_forecaster_v2(forecast_file, actual_file, cost_file)
        
        # controller_2Darr keeps track of what SE's should be controlled at any given time
        num_SEs = len(SE_ids)
        num_steps = ceil((self.controller_endtime_sec - self.controller_starttime_sec)/ self.controller_timestep_sec) + 1
        self.controller_2Darr = np.full((num_SEs, num_steps), False)
        
        # mappings of SE_id into controller_2Darr
        self.SE_id_to_controller_index_map = {}
        self.controller_index_to_SE_id_map = {}
        
        for (idx, SE_id) in enumerate(SE_ids):
            self.SE_id_to_controller_index_map[SE_id] = idx
            self.controller_index_to_SE_id_map[idx] = SE_id
        
    def get_forecasted_cost_at_time_sec(self, time_sec : float) -> float:
        '''
        Description:
            Given a time return the forecasted cost at that time from cost forecaster.
        '''
        
        return self.cost_forecaster.get_forecasted_cost_at_time_sec(time_sec)
    
    def get_actual_cost_at_time_sec(self, time_sec : float) -> float:
        '''
        Description:
            Given a time return the actual cost at that time from cost forecaster.
        '''

        return self.cost_forecaster.get_actual_cost_at_time_sec(time_sec)
    
    
    def get_time_idx_from_time_sec(self, time_sec : float) -> int:
        '''
        Description:
            Given a time return the time index in controller_2Darr.
        '''
        
        return int((time_sec - self.controller_starttime_sec)/self.controller_timestep_sec)
        
        
    def recalculate_active_charge_event(self, next_control_starttime_sec : float, active_charge_event : active_CE):
        '''
        Description:
            Resets the previously computed control actions for the SE and computes control actions again based on new available cost information.
        '''
        
        SE_id = active_charge_event.SE_id
        
        # clear old optimized charge event profile
        idx = self.SE_id_to_controller_index_map[SE_id]
        start_time_idx = self.get_time_idx_from_time_sec(next_control_starttime_sec)
        self.controller_2Darr[idx, start_time_idx:] = 0
        
        # Compute for this charge event again
        self.add_active_charge_event(active_charge_event)
    
    def add_active_charge_event(self, next_control_starttime_sec : float, active_charge_event : active_CE) -> None:
        '''
        Description:
            Adds charge events control actions to the controller by updating controller_2Darr with cheapest 
            times to charge
        '''
        
        # get the required info from active_charge_event
        SE_id = active_charge_event.SE_id
        CE_id = active_charge_event.charge_event_id
        supply_equipment_type = active_charge_event.supply_equipment_type
        vehicle_type = active_charge_event.vehicle_type
        departure_unix_time = active_charge_event.departure_unix_time
        arrival_SOC = active_charge_event.arrival_SOC
        departure_SOC = active_charge_event.departure_SOC
        now_soc = active_charge_event.now_soc
        
        #-------------------------------------------
        #       Build time parameters
        #-------------------------------------------
        start_time_sec = next_control_starttime_sec
        end_time_sec = min(next_control_starttime_sec + self.forecast_duration_sec, departure_unix_time - fmod(departure_unix_time, self.controller_timestep_sec))
        
        if(end_time_sec <= start_time_sec):
            print("Charge event {} too small. Cannot be controlled".format(CE_id))
            return
        
        #-------------------------------------------
        #       Build Charge profile timeseries
        #-------------------------------------------
        
        # create charge_profile
        all_charge_profile_data = self.charge_profiles.create_charge_profile_from_model(self.charge_profile_timestep_sec, vehicle_type, supply_equipment_type, now_soc, departure_SOC, 1000, {}, {})
        
        # create 15 min buckets, with energy consumed in each bucket.
        num_bins_to_aggregate = int(self.controller_timestep_sec / self.charge_profile_timestep_sec)
        
        charge_profile_data = (np.add.reduceat(all_charge_profile_data.P3_kW, np.arange(0, len(all_charge_profile_data.P3_kW), num_bins_to_aggregate))/num_bins_to_aggregate)*(self.controller_timestep_sec/3600.0)
        
        # convert charge_profile_data to timeseries
        charge_profile = timeseries(start_time_sec, self.controller_timestep_sec, charge_profile_data)
        
        #-------------------------------------------
        #       Build cost profile timeseries
        #-------------------------------------------
        
        cost_profile = self.cost_forecaster.get_cost_for_time_range(start_time_sec, end_time_sec, self.controller_timestep_sec)
        
        #-------------------------------------------
        #       Select least cost times 
        #-------------------------------------------
        
        cost_profile_indices_sorted = sorted(range(len(cost_profile.data)), key = lambda k: cost_profile.data[k])
        
        # select first n cheapest cost profiles 
        # TODO : make the cost profile as contiguous as possible
        cost_profile_indeces_cheapest = cost_profile_indices_sorted[:len(charge_profile.data)]
        
        #-------------------------------------------
        #       Update controller_2Darr 
        #-------------------------------------------
        
        for cost_profile_index in cost_profile_indeces_cheapest:
            profile_time_sec = cost_profile.get_time_from_index_sec(cost_profile_index)
            control_time_index = self.get_time_idx_from_time_sec(profile_time_sec)          
            self.controller_2Darr[self.SE_id_to_controller_index_map[SE_id], control_time_index] = True
        
        if self.plot == True:
            
            start_idx = self.get_time_idx_from_time_sec(start_time_sec)  
            end_idx = self.get_time_idx_from_time_sec(end_time_sec)            
            profile_size = end_idx - start_idx
            
            time_profile = np.arange(start_time_sec, end_time_sec, self.controller_timestep_sec)/3600.0
            charge_profile = charge_profile.data[:profile_size] + [0]*(profile_size - len(charge_profile.data))
            cost_profile = cost_profile.data
            control_profile = self.controller_2Darr[self.SE_id_to_controller_index_map[SE_id], start_idx:end_idx]
               
            fig, axes = plt.subplots(3, 1, figsize=(25, 15))
            
            ax = axes[0]
            ax.plot(time_profile, charge_profile)
            ax.set_xlabel("Time (hrs)")
            ax.set_ylabel("Power (kW)")
            ax.set_title("Charge profile")
            ax.set_xlim(time_profile[0], time_profile[-1] + self.controller_timestep_sec/3600.0)            
            ax.set_xticks(time_profile)
            ax.grid(True, which='both', axis='both')

            ax = axes[1]
            ax.step(time_profile, cost_profile, where = 'post' )
            ax.set_xlabel("Time (hrs)")
            ax.set_ylabel("Cost ($$$)")
            ax.set_title("Forecasted cost profile")
            ax.set_xlim(time_profile[0], time_profile[-1] + self.controller_timestep_sec/3600.0)
            ax.set_xticks(time_profile)
            ax.grid(True, which='both', axis='both')

            
            ax = axes[2]
            cmap = plt.get_cmap('viridis')
            ax.bar(time_profile, align='edge', height=1, width = time_profile[1] - time_profile[0], color=cmap(np.array(control_profile, dtype = float)))
            ax.set_xlabel("Time (hrs)")
            ax.set_title("Forecasted control profile")
            ax.tick_params(left = False)
            ax.set_xlim(time_profile[0], time_profile[-1] + self.controller_timestep_sec/3600.0)
            ax.set_ylim(0, 1)
            ax.set_xticks(time_profile)
            ax.set_yticks([])
            ax.grid()
            
            plt.subplots_adjust(hspace=0.4)
            base_name = 'CE_{}_plot_{:.2f}_'.format(CE_id, next_control_starttime_sec/3600.0)
            
            suffix = 0
            while "{}{}".format(base_name, str(suffix)) in self.plots:
                suffix += 1
            
            plot_name = "{}{}".format(base_name, str(suffix))
            self.plots.add(plot_name)
            plt.savefig(plot_name+".png")
   
            #self.plot = False
               
    def get_SE_setpoints(self, next_control_timestep_sec : float, active_SEs : List[int] ) -> List[SE_setpoint]:
        '''
        Description:
            Looks up controller_2Darr to see which SEs needs to charge at the specific time
        '''
        
        active_SE_indexes = [self.SE_id_to_controller_index_map[SE_id] for SE_id in active_SEs]
        
        time_index = floor((next_control_timestep_sec - self.controller_starttime_sec)/ self.controller_timestep_sec)
        
        # check all rows with active charge events that need to charge
        SE_indexes_to_charge = np.array(np.where(self.controller_2Darr[active_SE_indexes, time_index] == True))
        
        PQ_setpoints = []
        for SE_id in active_SEs:
            X = SE_setpoint()
            X.SE_id = SE_id
            
            if np.any(SE_indexes_to_charge == self.SE_id_to_controller_index_map[SE_id]):
                X.PkW = 1000
            else:
                X.PkW = 0          

            PQ_setpoints.append(X)
        
        return PQ_setpoints    

class TE_cost_forecaster_v2():
    '''
    Description:
        The TE_cost_forecaster will read the input file and compute costs and loads forecasted cost and actual cost as timeseries data 
    '''
    
    def __init__(self, forecast_input_file : str, actual_input_file : str, cost_input_file : str) -> None:
        '''
        Description:
            Loads data, computes cost and stores as timeseries data
        '''
        
        # Load forecast and actual generation as dfs
        df_forecast = pd.read_csv(forecast_input_file)
        df_actual = pd.read_csv(actual_input_file)
        
        # Load costs as json dictionaray 
        with open(cost_input_file, "r") as f_cost:
            cost_json = json.load(f_cost)

        # Three solver methods available linear, steep_cubic and inverse_s
        solver_method = cost_json["cost_function"]
        self.forecasted_cost_profile = self.solver(solver_method, df_forecast, cost_json)
        self.actual_cost_profile = self.solver(solver_method, df_actual, cost_json)
        
        ## Error Checks
        if not len(self.forecasted_cost_profile.data) == len(self.actual_cost_profile.data):
           raise ValueError('ERROR : Input forecasted_cost_profile data and actual_cost_profile should have same length')
        
        if not ((self.forecasted_cost_profile.data_timestep_sec * len(self.forecasted_cost_profile.data)) % 24*3600 == 0.0):
           raise ValueError('ERROR : Input forecasted_cost_profile data should be multiple of 24 hours of data')
        
        if not ((self.forecasted_cost_profile.data_timestep_sec * len(self.actual_cost_profile.data)) % 24*3600 == 0.0):
           raise ValueError('ERROR : Input actual_cost_profile data should be multiple of 24 hours of data')
        
        self.cost_profile_timestep_sec = self.forecasted_cost_profile.data_timestep_sec
        self.cost_profile_length_sec = self.cost_profile_timestep_sec * len(self.forecasted_cost_profile.data)

    def solver(self, solver_method, df, cost_data) -> timeseries:
        '''
        Description:
            Applies cost functions to the generation data
        '''
        df.columns = [column.split("|")[0].strip() for column in df.columns.to_series()]
        
        start_time_sec = round(df["time"][0] * 3600.0)
        timestep_sec = round((df["time"][1] - df["time"][0])*3600)
        
        # Ignore first 2 columns time and forecasted_demand/actual_demand
        gen_types = df.columns[2:].to_series()
        
        cost_usd_per_kWh = np.zeros(df.shape[0], dtype=float)
        total_cost_usd = np.zeros(df.shape[0], dtype=float)
        
        individual_costs = []
        for gen_type in gen_types:
            
            gen_min = cost_data[gen_type]["gen_min"]            #MW
            gen_max = cost_data[gen_type]["gen_max"]            #MW
            cost_min = cost_data[gen_type]["cost_min"]          # USD per MWh
            cost_max = cost_data[gen_type]["cost_max"]          # USD per MWh
            
            # No cost variation
            if abs(cost_min - cost_max) < 0.001:      # cost_min == cost_max        # nuclear and solar come under this scenario
                
                individual_cost_function = np.full_like(total_cost_usd, cost_min, dtype=float)
                total_cost_usd += individual_cost_function*df[gen_type]*timestep_sec/3600.0
            
            # Cost variation
            else:                                                                   # Thermal scenario
            
                if solver_method == "linear":
                    
                    individual_cost_function = (df[gen_type] - gen_min)/(gen_max-gen_min)*(cost_max-cost_min)+ cost_min
                    individual_costs.append(individual_cost_function)
                    
                    total_cost_usd += individual_cost_function*df[gen_type]*timestep_sec/3600.0
                
                elif solver_method == "steep_cubic":
                    
                    dxdy_at_gen_min = 0
                    dxdy_at_gen_max = 0.35

                    
                    A = [[gen_min**0, gen_min**1,   gen_min**2,     gen_min**3], 
                         [0,          1*gen_min**0, 2*gen_min**1,   3*gen_min**2], 
                         [gen_max**0, gen_max**1,   gen_max**2,     gen_max**3],
                         [0,          1*gen_max**0, 2*gen_max**1,   3*gen_max**2]]

                    b = [[cost_min],
                         [dxdy_at_gen_min],
                         [cost_max],
                         [dxdy_at_gen_max]]
                    
                    C = solve(A, b)
                    
                    individual_cost_function = C[0][0] * df[gen_type]**0 + C[1][0] * df[gen_type]**1 + C[2][0] * df[gen_type]**2 + C[3][0] * df[gen_type]**3
                    individual_costs.append(individual_cost_function)
                    
                    total_cost_usd += individual_cost_function*df[gen_type]*timestep_sec/3600.0
                    
                elif solver_method == "inverse_s":
                    
                    dxdy_at_gen_min = 0.3
                    dxdy_at_gen_max = 0.3


                    A = [[gen_min**0, gen_min**1,   gen_min**2,     gen_min**3], 
                         [0,          1*gen_min**0, 2*gen_min**1,   3*gen_min**2], 
                         [gen_max**0, gen_max**1,   gen_max**2,     gen_max**3],
                         [0,          1*gen_max**0, 2*gen_max**1,   3*gen_max**2]]

                    b = [[cost_min],
                         [dxdy_at_gen_min],
                         [cost_max],
                         [dxdy_at_gen_max]]
 
                    C = solve(A, b)

                    individual_cost_function = C[0][0] * df[gen_type]**0 + C[1][0] * df[gen_type]**1 + C[2][0] * df[gen_type]**2 + C[3][0] * df[gen_type]**3
                    individual_costs.append(individual_cost_function)
                    
                    total_cost_usd += individual_cost_function*df[gen_type]*timestep_sec/3600.0
                    
                else:
                    
                    raise ValueError('ERROR : solver_method should be linear or steep_cubic or inverse_s')
            
            # fig, ax = plt.subplots(1, 1, figsize=(25, 15))
            
            # ax.plot(df[gen_type], individual_cost_function)
            # ax.set_xlabel("Power (MW)")
            # ax.set_ylabel("Cost ($$$ per MWh)")
        
            # fig.savefig("fig_" + gen_type + ".png", dpi = 300)
        
        
        total_MWh_per_timestep = df[gen_types].sum(axis=1) * timestep_sec/3600.0
        cost_usd_per_MWh = total_cost_usd/total_MWh_per_timestep
        cost_usd_per_kWh = cost_usd_per_MWh/1000.0
        
        # fig, ax = plt.subplots(1, 1, figsize=(25, 15))
        # ax.plot(df["time_hrs"], cost_usd_per_kWh)
        # fig.savefig("fig_" + solver_method + "_time.png", dpi = 300)
        
        # fig, ax = plt.subplots(1, 1, figsize=(25, 15))
        # ax.scatter(df[gen_types].sum(axis=1), cost_usd_per_kWh)
        # fig.savefig("fig_" + solver_method + "_power.png", dpi = 300)
                
        return timeseries(start_time_sec, timestep_sec, cost_usd_per_kWh)
            
    def get_cost_for_time_range(self, starttime_sec : float, endtime_sec : float, req_timestep_sec : float) -> timeseries:
        '''
        Description:
            Given a timerange and timestep, looksup the data and returns the cost. 
            the timerange should match up with data timeperiod.
        '''
        
        if not ((self.cost_profile_timestep_sec == req_timestep_sec) or \
               (self.cost_profile_timestep_sec % req_timestep_sec == 0.0) or \
               (req_timestep_sec % self.cost_profile_timestep_sec == 0.0)):
            
            print("One of the three checks below needs to be True")
            print("self.cost_profile_timestep_sec == req_timestep_sec:", self.cost_profile_timestep_sec == req_timestep_sec)
            print("self.cost_profile_timestep_sec % req_timestep_sec == 0.0:", self.cost_profile_timestep_sec % req_timestep_sec == 0.0)
            print("req_timestep_sec % self.cost_profile_timestep_sec == 0.0:", req_timestep_sec % self.cost_profile_timestep_sec == 0.0)
            
            raise ValueError('ERROR : timestep parameters to get_cost_for_time_range are incompatible')
        
        if (starttime_sec % self.cost_profile_timestep_sec != 0.0) or \
           (endtime_sec % self.cost_profile_timestep_sec != 0.0) or \
           (starttime_sec >= endtime_sec ) or \
           (req_timestep_sec < 0):

           print("starttime_sec % self.cost_profile_timestep_sec should be equal to 0 :", starttime_sec % self.cost_profile_timestep_sec)
           print("endtime_sec %self.cost_profile_timestep_sec should be equal to 0: ", endtime_sec % self.cost_profile_timestep_sec)
           print("starttime_sec >= endtime_sec should be false: ", starttime_sec >= endtime_sec)
           print("req_timestep_sec < 0  should be false: ", req_timestep_sec < 0)
            
           raise ValueError('ERROR : parameters to get_cost_for_time_range are incompatible')

        data = []
        if (self.forecasted_cost_profile.data_timestep_sec >= req_timestep_sec):
            for time_sec in range(int(starttime_sec), int(endtime_sec), int(req_timestep_sec)):
            
                # The assumption here is that for current time. in this case the starttime_sec, real time actual cost is available.
                # beyond the current time, forecasted cost is used.
                if time_sec == int(starttime_sec):
                    cost = self.actual_cost_profile.get_val_from_time(time_sec % self.cost_profile_length_sec)
                else:
                    cost = self.forecasted_cost_profile.get_val_from_time(time_sec % self.cost_profile_length_sec)
                
                data.append(cost)
                
        elif (self.forecasted_cost_profile.data_timestep_sec < req_timestep_sec):
            for time_sec in range(int(starttime_sec), int(endtime_sec), int(req_timestep_sec)):
                
                start_sec = time_sec
                end_sec = time_sec + req_timestep_sec
                divisor = req_timestep_sec/self.forecasted_cost_profile.data_timestep_sec
                
                total_cost = 0    
                if(time_sec == int(starttime_sec)):
                    # Use actual price in this section
                    for subtime_sec in range(int(start_sec), int(end_sec), int(self.forecasted_cost_profile.data_timestep_sec)):
                        total_cost += self.actual_cost_profile.get_val_from_time(subtime_sec % self.cost_profile_length_sec)
                else:
                    # Use forecasted price in this section
                    for subtime_sec in range(int(start_sec), int(end_sec), int(self.forecasted_cost_profile.data_timestep_sec)):
                        total_cost += self.forecasted_cost_profile.get_val_from_time(subtime_sec % self.cost_profile_length_sec)
                
                avg_cost = total_cost/divisor
                data.append(avg_cost)
                
        else:
            raise ValueError('ERROR : get_cost_for_time_range')

        return timeseries(starttime_sec, req_timestep_sec, data)

    def get_forecasted_cost_at_time_sec(self, time_sec : float) -> float:
        '''
        Description:
            Given a time in seconds, looksup the data and returns the actual cost of energy at that time. 
        '''
        
        if (time_sec < 0):
            print("time_sec < 0  should be false: ", time_sec < 0)
            raise ValueError('ERROR : parameters to get_forecasted_cost_at_time_sec are incompatible')

        time_sec %= self.cost_profile_length_sec
    
        return self.forecasted_cost_profile.get_val_from_time(time_sec)

    def get_actual_cost_at_time_sec(self, time_sec : float) -> float:
        '''
        Description:
            Given a time in seconds, looksup the data and returns the actual cost of energy at that time. 
        '''
        
        if (time_sec < 0):
            print("time_sec < 0  should be false: ", time_sec < 0)
            raise ValueError('ERROR : parameters to get_actual_cost_at_time_sec are incompatible')

        time_sec %= self.cost_profile_length_sec
    
        return self.actual_cost_profile.get_val_from_time(time_sec)