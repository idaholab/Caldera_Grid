import os
from math import ceil, floor, fmod
import numpy as np
import matplotlib.pyplot as plt
from typing import List


from Caldera_globals import SE_setpoint, active_CE, timeseries
from Caldera_ICM_Aux import CP_interface_v2
from global_aux import container_class



class charge_controller_data:
    
    def __init__(self, charge_controller_data_input):
        
        self.SE_ids = charge_controller_data_input.SE_ids
        self.controller_starttime_sec = charge_controller_data_input.controller_starttime_sec
        self.controller_endtime_sec = charge_controller_data_input.controller_endtime_sec
        self.controller_timestep_sec = charge_controller_data_input.controller_timestep_sec

        # controller_2Darr keeps track of what SE's should be controlled at any given time
        num_SEs = len(self.SE_ids)
        num_steps = ceil((self.controller_endtime_sec - self.controller_starttime_sec)/ self.controller_timestep_sec) + 1
        self.controller_2Darr = np.full((num_SEs, num_steps), False)
        
        # mappings of SE_id into controller_2Darr
        self.SE_id_to_controller_index_map = {}
        self.controller_index_to_SE_id_map = {}
        
        for (idx, SE_id) in enumerate(self.SE_ids):
            self.SE_id_to_controller_index_map[SE_id] = idx
            self.controller_index_to_SE_id_map[idx] = SE_id

    def get_indices_from_time_s(self, time_sec_arr):
        '''
        Description:
            Given a list of time indices return coresponding time in seconds.
        '''
        time_sec_arr = np.array(time_sec_arr)
        return ((time_sec_arr - self.controller_starttime_sec)/self.controller_timestep_sec).astype(int)
        
    def get_time_s_from_indices(self, time_indices_arr) -> float:
        '''
        Description:
            Given a time index return the corresponding time in controller_2Darr.
        '''
        time_indices_arr = np.array(time_indices_arr)
        return(self.controller_starttime_sec + self.controller_timestep_sec * time_indices_arr).astype(float)
        
    def get_indices_from_SE_ids(self, SE_ids_arr):
        '''
        Description:
            Given a SE_ids return the corresponding SE_id indices.
        '''
        
        return np.vectorize(self.SE_id_to_controller_index_map.get)(np.array(SE_ids_arr))
            
    def get_SE_ids_from_indices(self, SE_indices):
        '''
        Description:
            Given a SE_id indices return the corresponding SE_id.
        '''
        
        return np.vectorize(self.controller_index_to_SE_id_map.get)(np.array(SE_indices))
                
          

class charge_controller:
    '''
    Description:
        charge_controller is the controller that decides cheapest time for charge to occur based on cost of electricity.
    '''
    
    def __init__(self, charge_controller_input):
        '''
        Description:
            constuctor initializes the charge controller, allocates the controller_2Darr that maintains the status of charge events being controlled.
        '''
        
        self.plot = True
        self.debug_plot = False
        self.plots = set()
        self.input_folder = charge_controller_input.io_dir.inputs_dir
        self.figures_folder = charge_controller_input.io_dir.figures_dir
        
        self.forecast_duration_sec = 12*3600                                    # Max forecast of 12 hours
        self.controller_starttime_sec = charge_controller_input.controller_starttime_sec   
        self.controller_endtime_sec = charge_controller_input.controller_endtime_sec + self.forecast_duration_sec
        self.controller_timestep_sec = charge_controller_input.controller_timestep_sec
        self.communication = charge_controller_input.communication
        self.charge_profile_timestep_sec = 60                                   # 1 minute timestep
        self.SE_ids = charge_controller_input.SE_ids
        
        self.use_cost_forecaster_v3 = True
        
        # CP_interface_v2 generates charge profiles
        self.charge_profiles = CP_interface_v2(self.input_folder)
        
        charge_controller_data_input = container_class()
        charge_controller_data_input.SE_ids = self.SE_ids
        charge_controller_data_input.controller_starttime_sec = self.controller_starttime_sec
        charge_controller_data_input.controller_endtime_sec = self.controller_endtime_sec
        charge_controller_data_input.controller_timestep_sec = self.controller_timestep_sec

        self.controller_data = charge_controller_data(charge_controller_data_input)
                            
    def __compute_charge_event_general(self, next_control_starttime_sec, active_charge_event, cost_profile):
        
        # get the required info from active_charge_event
        SE_id = active_charge_event.SE_id
        CE_id = active_charge_event.charge_event_id
        departure_unix_time = active_charge_event.departure_unix_time
        charge_time_remaining_hrs = active_charge_event.min_remaining_charge_time_hrs
            
        #-------------------------------------------
        #       Build time parameters
        #-------------------------------------------
        start_time_sec = next_control_starttime_sec
        end_time_sec = min(
            next_control_starttime_sec + self.forecast_duration_sec, 
            departure_unix_time - fmod(departure_unix_time, self.controller_timestep_sec)   # by subtracting the remainder, we ensure controller doesn't extend time beyond departure_unix_time
            )
        
        if(end_time_sec <= start_time_sec):
            print("{}: Remaining charge event is smaller than controller timestep. Cannot be controlled".format(CE_id))
            return
        
        # round up to the nearest self.controller_timestep_sec
        charge_time_remaining_in_controller_step_sec = ceil(charge_time_remaining_hrs * 3600 / self.controller_timestep_sec) * self.controller_timestep_sec
        
        # Number of steps controller needs to charge the vehicle
        num_steps_to_charge_by_controller = int(charge_time_remaining_in_controller_step_sec / self.controller_timestep_sec)
            
        #-------------------------------------------
        #       Build cost profile timeseries
        #-------------------------------------------
        
        start_idx = int((start_time_sec - next_control_starttime_sec) / self.controller_timestep_sec)
        end_idx = int((end_time_sec - next_control_starttime_sec)/ self.controller_timestep_sec)
        cost_profile_ts = timeseries(start_time_sec, self.controller_timestep_sec, cost_profile.data[start_idx:end_idx])
        
        #-------------------------------------------
        #       Select least cost times 
        #-------------------------------------------
        
        cost_profile_indices_sorted = sorted(range(len(cost_profile_ts.data)), key = lambda k: cost_profile_ts.data[k])
        
        # select first n cheapest cost profiles 
        # TODO : make the cost profile as contiguous as possible
        cost_profile_indeces_cheapest = cost_profile_indices_sorted[:num_steps_to_charge_by_controller]
        
        #-------------------------------------------
        #       Update controller_2Darr 
        #-------------------------------------------
        
        SE_idx = self.controller_data.get_indices_from_SE_ids([SE_id])[0]
        
        start = self.controller_data.get_indices_from_time_s([next_control_starttime_sec])[0]
        end = self.controller_data.get_indices_from_time_s([next_control_starttime_sec + self.forecast_duration_sec])[0]
        prev_solution = np.copy(self.controller_data.controller_2Darr[SE_idx, start:end].astype(int))
        
        # Resetting any previous data
        self.controller_data.controller_2Darr[SE_idx, start:end] = False 
        
        cheap_times_to_charge_arr = np.array([cost_profile_ts.get_time_from_index_sec(cost_profile_index) for cost_profile_index in cost_profile_indeces_cheapest])
        control_time_indices = self.controller_data.get_indices_from_time_s(cheap_times_to_charge_arr)
        self.controller_data.controller_2Darr[SE_idx, control_time_indices] = True
        
        
        if self.debug_plot == True:
            self.__debug_plot(next_control_starttime_sec, start_time_sec, end_time_sec, SE_idx, active_charge_event)
            
        return (num_steps_to_charge_by_controller, cost_profile_indeces_cheapest, prev_solution)

    def add_new_charge_events(self, next_control_starttime_sec, CEs, forecasted_cost_arr):

        original = np.zeros(int((next_control_starttime_sec + self.forecast_duration_sec - next_control_starttime_sec)/self.controller_timestep_sec))
        actual = np.zeros(int((next_control_starttime_sec + self.forecast_duration_sec - next_control_starttime_sec)/self.controller_timestep_sec))
        result = np.zeros(int((next_control_starttime_sec + self.forecast_duration_sec - next_control_starttime_sec)/self.controller_timestep_sec))
        
        for active_charge_event in CEs:
        
            (num_steps_to_charge_by_controller, cost_profile_indeces_cheapest, prev_solution) = self.__compute_charge_event_general(next_control_starttime_sec, active_charge_event, forecasted_cost_arr)
            
            if self.communication:
                
                original[:num_steps_to_charge_by_controller] += 1
                actual[cost_profile_indeces_cheapest] += 1                
                result += actual - original
        
        return result
            
    
    def adjust_old_charge_events(self, next_control_starttime_sec, CEs, forecasted_cost_arr):
        
        actual = np.zeros(int((next_control_starttime_sec + self.forecast_duration_sec - next_control_starttime_sec)/self.controller_timestep_sec))
        result = np.zeros(int((next_control_starttime_sec + self.forecast_duration_sec - next_control_starttime_sec)/self.controller_timestep_sec))

        for active_charge_event in CEs:
        
            (num_steps_to_charge_by_controller, cost_profile_indeces_cheapest, prev_solution) = self.__compute_charge_event_general(next_control_starttime_sec, active_charge_event, forecasted_cost_arr)
            
            if self.communication:
                
                actual[cost_profile_indeces_cheapest] += 1
                result += actual - prev_solution
        
        return result
    
    def get_SE_setpoints(self, next_control_timestep_sec : float, active_SEs : List[int] ) -> List[SE_setpoint]:
        '''
        Description:
            Looks up controller_2Darr to see which SEs needs to charge at the specific time
        '''
        
        time_index = floor((next_control_timestep_sec - self.controller_starttime_sec)/ self.controller_timestep_sec)
        
        # check all rows with active charge events that need to charge
        SE_indexes_to_charge = np.array(np.where(self.controller_data.controller_2Darr[:, time_index] == True))
        
        PQ_setpoints = []
        for SE_id in active_SEs:
            X = SE_setpoint()
            X.SE_id = SE_id
            if np.any(SE_indexes_to_charge == self.controller_data.get_indices_from_SE_ids([SE_id])[0]):
                X.PkW = 1000
            else:
                X.PkW = 0

            PQ_setpoints.append(X)
        
        return PQ_setpoints
    

    def __debug_plot(self, next_control_starttime_sec, start_time_sec, end_time_sec, SE_idx, active_charge_event):
        
        # get the required info from active_charge_event
        SE_id = active_charge_event.SE_id
        CE_id = active_charge_event.charge_event_id
        supply_equipment_type = active_charge_event.supply_equipment_type
        vehicle_type = active_charge_event.vehicle_type
        departure_unix_time = active_charge_event.departure_unix_time
        arrival_SOC = active_charge_event.arrival_SOC
        departure_SOC = active_charge_event.departure_SOC
        now_soc = active_charge_event.now_soc
        charge_time_remaining_hrs = active_charge_event.min_remaining_charge_time_hrs
        charge_time_total_hrs = active_charge_event.min_time_to_complete_entire_charge_hrs
        
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
            
        start_idx = self.get_time_idx_from_time_sec(start_time_sec)  
        end_idx = self.get_time_idx_from_time_sec(end_time_sec)            
        profile_size = end_idx - start_idx
            
        time_profile = np.arange(start_time_sec, end_time_sec, self.controller_timestep_sec)/3600.0
        charge_profile = charge_profile.data[:profile_size] + [0.0]*(profile_size - len(charge_profile.data))     # make charge profile length same as other profiles by adding 0's to the end
        cost_profile = cost_profile.data
        control_profile = self.controller_data.controller_2Darr[SE_idx, start_idx:end_idx]
               
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
            
        os.makedirs(self.figures_folder, exist_ok=True)
        plt.savefig(os.path.join(self.figures_folder, plot_name+".png"))    
