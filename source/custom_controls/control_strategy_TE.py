
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

class control_strategy_TE(typeA_control):
    
    def __init__(self, io_dir, simulation_time_constraints):
        super().__init__(io_dir, simulation_time_constraints)
        
        self.io_dir = io_dir
        self.control_timestep_min = 15    
        self.request_state_lead_time_min = (2*simulation_time_constraints.grid_timestep_sec + 0.5)/60
        self.send_control_info_lead_time_min = (simulation_time_constraints.grid_timestep_sec + 0.5)/60
        
        self.start_simulation_unix_time = simulation_time_constraints.start_simulation_unix_time
        self.end_simulation_unix_time = simulation_time_constraints.end_simulation_unix_time
        self.control_timestep_sec = self.control_timestep_min * 60
        
    
    def get_input_dataset_enum_list(self):
        return [input_datasets.SE_group_configuration, input_datasets.SE_group_charge_event_data, input_datasets.SEid_to_SE_type, input_datasets.charge_event_builder]

    def load_input_datasets(self, datasets_dict):
        # datasets_dict is a dictionary with input_datasets as keys.
        self.datasets_dict = datasets_dict
    
    def terminate_this_federate(self):
        return False
    
    def initialize(self):
        # All supply_equipments in the simulation
        SE_ids = list(self.datasets_dict[input_datasets.SEid_to_SE_type].keys())
        
        self.controller = charge_controller(self.io_dir.inputs_dir, self.start_simulation_unix_time, self.end_simulation_unix_time, self.control_timestep_sec, SE_ids)
        
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
        #return_dict[Caldera_message_types.get_all_active_charge_events] = None
        return_dict[Caldera_message_types.get_active_charge_events_by_extCS] = ['ext0001']
        return return_dict
    
    def get_messages_to_request_state_info_from_OpenDSS(self, current_simulation_unix_time):
        return_dict = {}
        
        return return_dict
        
    def solve(self, current_simulation_unix_time, Caldera_state_info_dict, DSS_state_info_dict):
        # current_simulation_unix_time refers to when the next control action would start. i.e. begining of next control timestep 
        # and end of current control timestep

        #next_control_timestep_sec = floor(current_simulation_unix_time / self.control_timestep_sec + 1) * self.control_timestep_sec
        #print("Control Strategy current_simulation_unix_time : ", current_simulation_unix_time/3600.0)
        
        next_control_starttime_sec = current_simulation_unix_time
        print("Control Strategy next_control_timestep_sec : ", next_control_starttime_sec/3600.0)

        self.controller.update_charging(next_control_starttime_sec)
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
        
        CEs_all = Caldera_state_info_dict[Caldera_message_types.get_active_charge_events_by_extCS]['ext0001']
        
        for CE in CEs_all:
            
            # get the charge_event id
            charge_event_id = CE.charge_event_id
            SE_id = CE.SE_id
            now_soc = CE.now_soc
            
            str = 'time:{}  SE_id:{}  soc:{}  '.format(round(next_control_starttime_sec/3600.0, 4), SE_id, now_soc)
            print(str)
            
            if (cost_deviated_from_forecast):
                print("updating existing charge event")
                self.controller.recalculate_active_charge_event(next_control_starttime_sec, CE)
            else:
                
                # process this charge event only if it is not already processed
                if charge_event_id not in self.processed_charge_events:
                    
                    print("adding new charge event")
                    self.processed_charge_events.append(charge_event_id)                
                    # Add charge event to charge controller
                    self.controller.add_active_charge_event(next_control_starttime_sec, CE)

        #-----------------------------
        
        Caldera_control_info_dict = {}
        DSS_control_info_dict = {}
        
        # get control setpoints from controller
        PQ_setpoints = self.controller.get_SE_setpoints(next_control_starttime_sec)
        
        #for X in PQ_setpoints:
        #    print("X.SE_id :", X.SE_id)
        #    print("X.PkW :", X.PkW)

        print("")
        print("===========================================")
        print("")
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
        charge_controller decides cheapest time for charge to occur.
    '''
    
    def __init__(self, input_folder : str, starttime_sec : float, endtime_sec : float, timestep_sec : float, SE_ids : List[int]):
        '''
        Description:
            constuctor
            
        Parameters:
            input_folder - folder where input files are stored
            starttime_sec - simulation start time in seconds
            endtime_sec - simulation end time in seconds
            timestep_sec - controller timestep in seconds
            SE_ids - all supply equipment ids present in the simulation
        '''
        
        self.plot = True
        self.plots = set()
        
        self.forecast_duration_sec = 12*3600
        self.controller_starttime_sec = starttime_sec
        self.controller_endtime_sec = endtime_sec + self.forecast_duration_sec
        self.controller_timestep_sec = timestep_sec
        self.charge_profile_timestep_sec = 60           # 1 minute timestep
                

        if input_folder[-1] == "/":
            input_folder = input_folder[:-1]
            
        # CP_interface_v2 generates charge profiles
        self.charge_profiles = CP_interface_v2(input_folder)
        
        # cost_forcaster contains the cost of energy
        #self.cost_forecaster = TE_cost_forecaster(input_folder + "/TE_cost.csv")
        self.cost_forecaster = TE_cost_forecaster_v2(input_folder + "/TE_inputs/forecast.csv", input_folder + "/TE_inputs/actual.csv", input_folder + "/TE_inputs/generation_cost.json")
        
        # controller_2Darr keeps track of what SE's should be controlled at any given time
        num_SEs = len(SE_ids)
        num_steps = ceil((self.controller_endtime_sec - self.controller_starttime_sec)/ self.controller_timestep_sec) + 1
        self.controller_2Darr = np.full((num_SEs, num_steps), False)
        print("controller_2Darr shape", self.controller_2Darr.shape)
        print("controller_2Darr size", self.controller_2Darr.size)
        print("controller_2Darr nbytes", self.controller_2Darr.nbytes)
        
        # mappings of SE_id into controller_2Darr
        self.SE_id_to_controller_index_map = {}
        self.controller_index_to_SE_id_map = {}
        
        idx = 0
        for SE_id in SE_ids:
            self.SE_id_to_controller_index_map[SE_id] = idx
            self.controller_index_to_SE_id_map[idx] = SE_id
            idx += 1

    def get_forecasted_cost_at_time_sec(self, time_sec : float) -> float:
        return self.cost_forecaster.get_forecasted_cost_at_time_sec(time_sec)
        
    
    def get_actual_cost_at_time_sec(self, time_sec : float) -> float:
        return self.cost_forecaster.get_actual_cost_at_time_sec(time_sec)
    
    
    def get_time_idx_from_time_sec(self, time_sec : float) -> int:
        return int((time_sec - self.controller_starttime_sec)/self.controller_timestep_sec)
        
        
    def recalculate_active_charge_event(self, next_control_starttime_sec : float, active_charge_event : active_CE):
        
        SE_id = active_charge_event.SE_id
        
        # clear old optimized charge event profile
        idx = self.SE_id_to_controller_index_map[SE_id]
        start_time_idx = self.get_time_idx_from_time_sec(next_control_starttime_sec)
        self.controller_2Darr[idx, start_time_idx:] = 0
        
        self.add_active_charge_event(active_charge_event)
    
    def add_active_charge_event(self, next_control_starttime_sec : float, active_charge_event : active_CE):
        '''
        Description:
            Adds charge events to the controller by updating controller_2Darr with cheapest 
            times to charge
            
        Parameters:
            active_charge_event - the active charge event to be managed by the controller
        
        Output:
            None
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
        #for i in range(len(cost_profile.data)):
        #    print("time : {}, cost : {}".format(cost_profile.get_time_from_index_sec(i)/3600.0, cost_profile.data[i]))
        
        #-------------------------------------------
        #       Select least cost times 
        #-------------------------------------------
        
        cost_profile_indices_sorted = sorted(range(len(cost_profile.data)), key = lambda k: cost_profile.data[k])
        
        # select first n cheapest cost profiles 
        # TODO : make the cost profile as contiguous as possible
        cost_profile_indeces_cheapest = cost_profile_indices_sorted[:len(charge_profile.data)]
        
        #for i in cost_profile_indeces_cheapest:
        #    print("time : {}, cost : {}".format(cost_profile.get_time_from_index_sec(i)/3600.0, cost_profile.data[i]))
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
            ax.plot(time_profile, cost_profile)
            ax.set_xlabel("Time (hrs)")
            ax.set_ylabel("Cost ($$$)")
            ax.set_title("Forecasted cost profile")
            ax.set_xlim(time_profile[0], time_profile[-1] + self.controller_timestep_sec/3600.0)
            
            ax.set_xticks(time_profile)
            ax.grid(True, which='both', axis='both')
            
            ax = axes[2]
            cmap = plt.get_cmap('viridis')
           
            ax.bar(time_profile, align='edge', height=1, width = 1, color=cmap(np.array(control_profile, dtype = float)))
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
            
        print("controller_2Darr aftter optimizing charge : ", self.controller_2Darr)
           
    def get_SE_setpoints(self, next_control_timestep_sec : float) -> List[SE_setpoint]:
        '''
        Description:
            Looks up controller_2Darr to see which supply_equipment needs to charge at the specific time
            
        Parameters:
            next_control_timestep_sec - next time when control is appied to in seconds
        
        Output:
            PQ_setpoints - list of setpoint objects
        '''
        
        time_index = floor((next_control_timestep_sec - self.controller_starttime_sec)/ self.controller_timestep_sec)
        
        # check all rows in the current column if they are 1
        SE_indexes = np.array(np.where(self.controller_2Darr[:, time_index] == 1))
        print("SE_indexes", SE_indexes)
        print("type(SE_indexes)", type(SE_indexes))
        
        PQ_setpoints = []
        for SE_id in self.SE_id_to_controller_index_map:
            X = SE_setpoint()
            X.SE_id = SE_id     
            if np.any(SE_indexes == self.SE_id_to_controller_index_map[SE_id]):
                X.PkW = 1000
            else:
                X.PkW = 0          

            PQ_setpoints.append(X)
        
        return PQ_setpoints
    
    def update_charging(self, next_control_starttime_sec : float) -> None:
        
        end_idx = self.get_time_idx_from_time_sec(next_control_starttime_sec)
        self.controller_2Darr[:, :end_idx][self.controller_2Darr[:, :end_idx] == 1] = 2
        

class TE_cost_forecaster_v2():
    '''
    The TE_cost_forecaster will read the TE cost from input file and load it as timeseries data 
    '''
    
    def __init__(self, forecast_input_file : str, actual_input_file : str, cost_input_file : str) -> None:
        '''
        Description:
            Constructor
        
        Parameters:
            input_file - The file where cost data is stored
        '''
        
        df_forecast = pd.read_csv(forecast_input_file)
        df_actual = pd.read_csv(actual_input_file)
        with open(cost_input_file, "r") as f_cost:
            cost_json = json.load(f_cost)

        generation_types = df_forecast.columns[2:].to_series()
        
        df_forecast["cost"] = df_forecast["time_hrs"] * 0.0
        for gen_type in generation_types:    
            df_forecast["cost"] += df_forecast[gen_type] * cost_json[gen_type]["LCOE"]

        df_forecast["cost"] = df_forecast["cost"] * 5/60      # 5 min data convert to MWh
        df_forecast["cost"] = df_forecast["cost"] / 1000      # convert to kWh

        df_actual["cost"] = df_actual["time_hrs"] * 0.0
        for gen_type in generation_types:    
            df_actual["cost"] += df_actual[gen_type] * cost_json[gen_type]["LCOE"]

        df_actual["cost"] = df_actual["cost"] * 5/60      # 5 min data convert to MWh
        df_actual["cost"] = df_actual["cost"] / 1000      # convert to kWh

        data_starttime_sec = 0.0
        data_timestep_sec = 5*60
        ## Do some error checks here. Example data should be there for atleast 1 day and be multiple of day
        self.forecasted_cost_profile = timeseries(data_starttime_sec, data_timestep_sec, df_forecast["cost"].tolist())
        self.actual_cost_profile = timeseries(data_starttime_sec, data_timestep_sec, df_actual["cost"].tolist())
        
        if not len(self.forecasted_cost_profile.data) == len(self.actual_cost_profile.data):
           raise ValueError('ERROR : Input forecasted_cost_profile data and actual_cost_profile should have same length')
        
        if not ((data_timestep_sec * len(self.forecasted_cost_profile.data)) % 24*3600 == 0.0):
           raise ValueError('ERROR : Input forecasted_cost_profile data should be multiple of 24 hours of data')
        
        if not ((data_timestep_sec * len(self.actual_cost_profile.data)) % 24*3600 == 0.0):
           raise ValueError('ERROR : Input actual_cost_profile data should be multiple of 24 hours of data')
        
        self.cost_profile_length_sec = data_timestep_sec * len(self.forecasted_cost_profile.data)

    def get_cost_for_time_range(self, starttime_sec : float, endtime_sec : float, timestep_sec : float) -> timeseries:
        '''
        Description:
            Given a timerange and timestep, looksup the data and returns the cost. 
            the timerange should match up with data timeperiod.
            requested timestep_sec should be smaller that data_timestep_sec.
            data_timestep_sec should be a multiple of requested timestep_sec.
            
        Parameters:
            starttime_sec - The file where cost data is stored
            
        Output:
            timeseries - 
        '''
        data_timestep_sec = self.forecasted_cost_profile.data_timestep_sec
        req_timestep_sec = timestep_sec
        
        if not ((data_timestep_sec == req_timestep_sec) or \
               (data_timestep_sec % req_timestep_sec == 0.0) or \
               (req_timestep_sec % data_timestep_sec == 0.0)):
            raise ValueError('ERROR : timestep parameters to get_forecasted_cost_for_time_range are incompatible')

        
        #print("starttime_sec % self.data_timestep_sec should be equal to 0 :", starttime_sec % self.forecasted_cost_profile.data_timestep_sec)
        #print("endtime_sec % self.data_timestep_sec should be equal to 0: ", endtime_sec % self.forecasted_cost_profile.data_timestep_sec)
        #print("starttime_sec >= endtime_sec should be false: ", starttime_sec >= endtime_sec)
        #print("timestep_sec < 0  should be false: ", timestep_sec < 0)
        if (starttime_sec % data_timestep_sec != 0.0) or \
           (endtime_sec % data_timestep_sec != 0.0) or \
           (starttime_sec >= endtime_sec ) or \
           (req_timestep_sec < 0):
           raise ValueError('ERROR : parameters to get_forecasted_cost_for_time_range are incompatible')

        data = []
        if (data_timestep_sec >= req_timestep_sec):
            for time_sec in range(int(starttime_sec), int(endtime_sec), int(req_timestep_sec)):
                time_sec %= self.cost_profile_length_sec
            
                # The assumption here is that for current time. in this case the starttime_sec, real time actual cost is available.
                # beyond the current time, forecasted cost is used.
                if time_sec == int(starttime_sec):
                    cost = self.actual_cost_profile.get_val_from_time(time_sec)
                else:
                    cost = self.forecasted_cost_profile.get_val_from_time(time_sec)
                
                data.append(cost)
                
        elif (data_timestep_sec < req_timestep_sec):
            for time_sec in range(int(starttime_sec), int(endtime_sec), int(req_timestep_sec)):
                time_sec %= self.cost_profile_length_sec

                start_sec = time_sec
                end_sec = time_sec + req_timestep_sec
                divisor = req_timestep_sec/data_timestep_sec
                
                cost = 0
                for subtime_sec in range(int(start_sec), int(end_sec), int(data_timestep_sec)):
                    if subtime_sec == int(starttime_sec):
                        cost += self.actual_cost_profile.get_val_from_time(subtime_sec)
                    else:
                        cost += self.forecasted_cost_profile.get_val_from_time(subtime_sec)
                cost = cost/divisor
                data.append(cost)

        return timeseries(starttime_sec, timestep_sec, data)     
    
    def get_forecasted_cost_for_time_range(self, starttime_sec : float, endtime_sec : float, timestep_sec : float) -> timeseries:
        '''
        Description:
            Given a timerange and timestep, looksup the data and returns the cost. 
            the timerange should match up with data timeperiod.
            requested timestep_sec should be smaller that data_timestep_sec.
            data_timestep_sec should be a multiple of requested timestep_sec.
            
        Parameters:
            starttime_sec - The file where cost data is stored
            
        Output:
            timeseries - 
        '''
        
        #print("starttime_sec % self.data_timestep_sec should be equal to 0 :", starttime_sec % self.forecasted_cost_profile.data_timestep_sec)
        #print("endtime_sec % self.data_timestep_sec should be equal to 0: ", endtime_sec % self.forecasted_cost_profile.data_timestep_sec)
        #print("self.data_timestep_sec % timestep_sec should be equal to 0: ", self.forecasted_cost_profile.data_timestep_sec % timestep_sec)
        #print("self.forecasted_cost_profile.data_timestep_sec > timestep_sec should be false: ", self.forecasted_cost_profile.data_timestep_sec > timestep_sec)
        #print("starttime_sec >= endtime_sec should be false: ", starttime_sec >= endtime_sec)
        #print("timestep_sec < 0  should be false: ", timestep_sec < 0)
        if (starttime_sec % self.forecasted_cost_profile.data_timestep_sec != 0.0) or \
           (endtime_sec % self.forecasted_cost_profile.data_timestep_sec != 0.0) or \
           (self.forecasted_cost_profile.data_timestep_sec % timestep_sec != 0.0) or \
           (self.forecasted_cost_profile.data_timestep_sec > timestep_sec) or \
           (starttime_sec >= endtime_sec ) or \
           (timestep_sec < 0):
           raise ValueError('ERROR : parameters to get_forecasted_cost_for_time_range are incompatible')


        data = []
        for time_sec in range(int(starttime_sec), int(endtime_sec), int(timestep_sec)):
            time_sec %= self.cost_profile_length_sec
            
            # The assumption here is that for current time. in this case the starttime_sec, real time actual cost is available.
            # beyond the current time, forecasted cost is used.
            cost = self.forecasted_cost_profile.get_val_from_time(time_sec)
            data.append(cost)
        
        return timeseries(starttime_sec, timestep_sec, data)                


    def get_actual_cost_for_time_range(self, starttime_sec : float, endtime_sec : float, timestep_sec : float) -> timeseries:
        '''
        Description:
            Given a timerange and timestep, looksup the data and returns the cost. 
            the timerange should match up with data timeperiod.
            requested timestep_sec should be smaller that data_timestep_sec.
            data_timestep_sec should be a multiple of requested timestep_sec.
            
        Parameters:
            starttime_sec - The file where cost data is stored
            
        Output:
            timeseries - 
        '''
        
        #print("starttime_sec % self.data_timestep_sec should be equal to 0 :", starttime_sec % self.forecasted_cost_profile.data_timestep_sec)
        #print("endtime_sec % self.data_timestep_sec should be equal to 0: ", endtime_sec % self.forecasted_cost_profile.data_timestep_sec)
        #print("self.data_timestep_sec % timestep_sec should be equal to 0: ", self.forecasted_cost_profile.data_timestep_sec % timestep_sec)
        #print("self.forecasted_cost_profile.data_timestep_sec > timestep_sec should be false: ", self.forecasted_cost_profile.data_timestep_sec > timestep_sec)
        #print("starttime_sec >= endtime_sec should be false: ", starttime_sec >= endtime_sec)
        #print("timestep_sec < 0  should be false: ", timestep_sec < 0)
        if (starttime_sec % self.forecasted_cost_profile.data_timestep_sec != 0.0) or \
           (endtime_sec % self.forecasted_cost_profile.data_timestep_sec != 0.0) or \
           (self.forecasted_cost_profile.data_timestep_sec % timestep_sec != 0.0) or \
           (self.forecasted_cost_profile.data_timestep_sec > timestep_sec) or \
           (starttime_sec >= endtime_sec ) or \
           (timestep_sec < 0):
           raise ValueError('ERROR : parameters to get_forecasted_cost_for_time_range are incompatible')


        data = []
        for time_sec in range(int(starttime_sec), int(endtime_sec), int(timestep_sec)):
            time_sec %= self.cost_profile_length_sec
            
            # The assumption here is that for current time. in this case the starttime_sec, real time actual cost is available.
            # beyond the current time, forecasted cost is used.
            cost = self.actual_cost_profile.get_val_from_time(time_sec)
            data.append(cost)
        
        return timeseries(starttime_sec, timestep_sec, data)                


    def get_forecasted_cost_at_time_sec(self, time_sec : float) -> float:
        '''
        Description:
            Given a time in seconds, looksup the data and returns the actual cost of energy at that time. 
            
        Parameters:
            time_sec - The time in seconds for which cost of energy needs to be returned. 
            
        Output:
            cost - cost of energy in dollars at that time.
        '''
        
        #print("time_sec < 0  should be false: ", time_sec < 0)
        if (time_sec < 0):
            raise ValueError('ERROR : parameters to get_actual_cost_at_time_sec are incompatible')

        # TODO: Donot hardcode 24 hrs instead get it from timeseries
        time_sec %= self.cost_profile_length_sec
    
        return self.forecasted_cost_profile.get_val_from_time(time_sec)

    def get_actual_cost_at_time_sec(self, time_sec : float) -> float:
        '''
        Description:
            Given a time in seconds, looksup the data and returns the actual cost of energy at that time. 
            
        Parameters:
            time_sec - The time in seconds for which cost of energy needs to be returned. 
            
        Output:
            cost - cost of energy in dollars at that time.
        '''
        
        #print("time_sec < 0  should be false: ", time_sec < 0)
        if (time_sec < 0):
            raise ValueError('ERROR : parameters to get_actual_cost_at_time_sec are incompatible')

        # TODO: Donot hardcode 24 hrs instead get it from timeseries
        time_sec %= self.cost_profile_length_sec
    
        return self.actual_cost_profile.get_val_from_time(time_sec)
    


##################################################
##################################################
##################################################
##################################################
##################################################
##################################################
##################################################
##################################################
##################################################
##################################################
##################################################

class TE_cost_forecaster():
    '''
    The TE_cost_forecaster will read the TE cost from input file and load it as timeseries data 
    '''
    
    def __init__(self, input_file : str) -> None:
        '''
        Description:
            Constructor
        
        Parameters:
            input_file - The file where cost data is stored
        '''
        
        f = open(input_file)
        all_lines = f.readlines()
                
        data_starttime_sec = float(all_lines[0].split(",")[1])
        data_timestep_sec = float(all_lines[1].split(",")[1])
        forecasted_data = [float(all_lines[i].split(",")[0]) for i in range(3, len(all_lines))]
        actual_data = [float(all_lines[i].split(",")[1]) for i in range(3, len(all_lines))]

        ## Do some error checks here. Example data should be there for atleast 1 day and be multiple of day
        self.forecasted_cost_profile = timeseries(data_starttime_sec, data_timestep_sec, forecasted_data)
        self.actual_cost_profile = timeseries(data_starttime_sec, data_timestep_sec, actual_data)
        

    def get_cost_for_time_range(self, starttime_sec : float, endtime_sec : float, timestep_sec : float) -> timeseries:
        '''
        Description:
            Given a timerange and timestep, looksup the data and returns the cost. 
            the timerange should match up with data timeperiod.
            requested timestep_sec should be smaller that data_timestep_sec.
            data_timestep_sec should be a multiple of requested timestep_sec.
            
        Parameters:
            starttime_sec - The file where cost data is stored
            
        Output:
            timeseries - 
        '''
        
        #print("starttime_sec % self.data_timestep_sec should be equal to 0 :", starttime_sec % self.forecasted_cost_profile.data_timestep_sec)
        #print("endtime_sec % self.data_timestep_sec should be equal to 0: ", endtime_sec % self.forecasted_cost_profile.data_timestep_sec)
        #print("self.data_timestep_sec % timestep_sec should be equal to 0: ", self.forecasted_cost_profile.data_timestep_sec % timestep_sec)
        #print("self.forecasted_cost_profile.data_timestep_sec > timestep_sec should be false: ", self.forecasted_cost_profile.data_timestep_sec > timestep_sec)
        #print("starttime_sec >= endtime_sec should be false: ", starttime_sec >= endtime_sec)
        #print("timestep_sec < 0  should be false: ", timestep_sec < 0)
        if (starttime_sec % self.forecasted_cost_profile.data_timestep_sec != 0.0) or \
           (endtime_sec % self.forecasted_cost_profile.data_timestep_sec != 0.0) or \
           (self.forecasted_cost_profile.data_timestep_sec % timestep_sec != 0.0) or \
           (self.forecasted_cost_profile.data_timestep_sec > timestep_sec) or \
           (starttime_sec >= endtime_sec ) or \
           (timestep_sec < 0):
           raise ValueError('ERROR : parameters to get_forecasted_cost_for_time_range are incompatible')


        data = []
        for time_sec in range(int(starttime_sec), int(endtime_sec), int(timestep_sec)):
            time_sec %= 24*3600
            
            # The assumption here is that for current time. in this case the starttime_sec, real time actual cost is available.
            # beyond the current time, forecasted cost is used.
            if time_sec == int(starttime_sec):
                cost = self.actual_cost_profile.get_val_from_time(time_sec)
            else:
                cost = self.forecasted_cost_profile.get_val_from_time(time_sec)
                
            data.append(cost)
        
        return timeseries(starttime_sec, timestep_sec, data)                
    
    def get_forecasted_cost_for_time_range(self, starttime_sec : float, endtime_sec : float, timestep_sec : float) -> timeseries:
        '''
        Description:
            Given a timerange and timestep, looksup the data and returns the cost. 
            the timerange should match up with data timeperiod.
            requested timestep_sec should be smaller that data_timestep_sec.
            data_timestep_sec should be a multiple of requested timestep_sec.
            
        Parameters:
            starttime_sec - The file where cost data is stored
            
        Output:
            timeseries - 
        '''
        
        #print("starttime_sec % self.data_timestep_sec should be equal to 0 :", starttime_sec % self.forecasted_cost_profile.data_timestep_sec)
        #print("endtime_sec % self.data_timestep_sec should be equal to 0: ", endtime_sec % self.forecasted_cost_profile.data_timestep_sec)
        #print("self.data_timestep_sec % timestep_sec should be equal to 0: ", self.forecasted_cost_profile.data_timestep_sec % timestep_sec)
        #print("self.forecasted_cost_profile.data_timestep_sec > timestep_sec should be false: ", self.forecasted_cost_profile.data_timestep_sec > timestep_sec)
        #print("starttime_sec >= endtime_sec should be false: ", starttime_sec >= endtime_sec)
        #print("timestep_sec < 0  should be false: ", timestep_sec < 0)
        if (starttime_sec % self.forecasted_cost_profile.data_timestep_sec != 0.0) or \
           (endtime_sec % self.forecasted_cost_profile.data_timestep_sec != 0.0) or \
           (self.forecasted_cost_profile.data_timestep_sec % timestep_sec != 0.0) or \
           (self.forecasted_cost_profile.data_timestep_sec > timestep_sec) or \
           (starttime_sec >= endtime_sec ) or \
           (timestep_sec < 0):
           raise ValueError('ERROR : parameters to get_forecasted_cost_for_time_range are incompatible')


        data = []
        for time_sec in range(int(starttime_sec), int(endtime_sec), int(timestep_sec)):
            time_sec %= 24*3600
            
            # The assumption here is that for current time. in this case the starttime_sec, real time actual cost is available.
            # beyond the current time, forecasted cost is used.
            cost = self.forecasted_cost_profile.get_val_from_time(time_sec)
            data.append(cost)
        
        return timeseries(starttime_sec, timestep_sec, data)                


    def get_actual_cost_for_time_range(self, starttime_sec : float, endtime_sec : float, timestep_sec : float) -> timeseries:
        '''
        Description:
            Given a timerange and timestep, looksup the data and returns the cost. 
            the timerange should match up with data timeperiod.
            requested timestep_sec should be smaller that data_timestep_sec.
            data_timestep_sec should be a multiple of requested timestep_sec.
            
        Parameters:
            starttime_sec - The file where cost data is stored
            
        Output:
            timeseries - 
        '''
        
        #print("starttime_sec % self.data_timestep_sec should be equal to 0 :", starttime_sec % self.forecasted_cost_profile.data_timestep_sec)
        #print("endtime_sec % self.data_timestep_sec should be equal to 0: ", endtime_sec % self.forecasted_cost_profile.data_timestep_sec)
        #print("self.data_timestep_sec % timestep_sec should be equal to 0: ", self.forecasted_cost_profile.data_timestep_sec % timestep_sec)
        #print("self.forecasted_cost_profile.data_timestep_sec > timestep_sec should be false: ", self.forecasted_cost_profile.data_timestep_sec > timestep_sec)
        #print("starttime_sec >= endtime_sec should be false: ", starttime_sec >= endtime_sec)
        #print("timestep_sec < 0  should be false: ", timestep_sec < 0)
        if (starttime_sec % self.forecasted_cost_profile.data_timestep_sec != 0.0) or \
           (endtime_sec % self.forecasted_cost_profile.data_timestep_sec != 0.0) or \
           (self.forecasted_cost_profile.data_timestep_sec % timestep_sec != 0.0) or \
           (self.forecasted_cost_profile.data_timestep_sec > timestep_sec) or \
           (starttime_sec >= endtime_sec ) or \
           (timestep_sec < 0):
           raise ValueError('ERROR : parameters to get_forecasted_cost_for_time_range are incompatible')


        data = []
        for time_sec in range(int(starttime_sec), int(endtime_sec), int(timestep_sec)):
            time_sec %= 24*3600
            
            # The assumption here is that for current time. in this case the starttime_sec, real time actual cost is available.
            # beyond the current time, forecasted cost is used.
            cost = self.actual_cost_profile.get_val_from_time(time_sec)
            data.append(cost)
        
        return timeseries(starttime_sec, timestep_sec, data)                


    def get_forecasted_cost_at_time_sec(self, time_sec : float) -> float:
        '''
        Description:
            Given a time in seconds, looksup the data and returns the actual cost of energy at that time. 
            
        Parameters:
            time_sec - The time in seconds for which cost of energy needs to be returned. 
            
        Output:
            cost - cost of energy in dollars at that time.
        '''
        
        #print("time_sec < 0  should be false: ", time_sec < 0)
        if (time_sec < 0):
            raise ValueError('ERROR : parameters to get_actual_cost_at_time_sec are incompatible')

        # TODO: Donot hardcode 24 hrs instead get it from timeseries
        time_sec %= 24*3600
    
        return self.forecasted_cost_profile.get_val_from_time(time_sec)

    def get_actual_cost_at_time_sec(self, time_sec : float) -> float:
        '''
        Description:
            Given a time in seconds, looksup the data and returns the actual cost of energy at that time. 
            
        Parameters:
            time_sec - The time in seconds for which cost of energy needs to be returned. 
            
        Output:
            cost - cost of energy in dollars at that time.
        '''
        
        #print("time_sec < 0  should be false: ", time_sec < 0)
        if (time_sec < 0):
            raise ValueError('ERROR : parameters to get_actual_cost_at_time_sec are incompatible')

        # TODO: Donot hardcode 24 hrs instead get it from timeseries
        time_sec %= 24*3600
    
        return self.actual_cost_profile.get_val_from_time(time_sec)