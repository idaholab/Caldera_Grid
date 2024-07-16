import os
from math import ceil, floor, fmod
from typing import List
from Caldera_globals import SE_setpoint, active_CE, timeseries
from Caldera_ICM_Aux import CP_interface_v2
from dynamic_price_control.cost_forecaster import TE_cost_forecaster_v2, TE_cost_forecaster_v3
import numpy as np

class charge_controller:
    '''
    Description:
        charge_controller is the controller that decides cheapest time for charge to occur based on cost of electricity.
    '''
    
    def __init__(self, io_dir, starttime_sec : float, endtime_sec : float, timestep_sec : float, SE_ids : List[int]):
        '''
        Description:
            constuctor initializes the charge controller, allocates the controller_2Darr that maintains the status of charge events being controlled.
        '''
        
        self.plot = True
        self.debug_plot = False
        self.plots = set()
        self.input_folder = io_dir.inputs_dir
        self.figures_folder = io_dir.figures_dir
        
        self.forecast_duration_sec = 12*3600            # Max forecast of 12 hours
        self.controller_starttime_sec = starttime_sec   
        self.controller_endtime_sec = endtime_sec + self.forecast_duration_sec
        self.controller_timestep_sec = timestep_sec
        self.charge_profile_timestep_sec = 60           # 1 minute timestep
        
        self.use_cost_forecaster_v3 = True
        
        # CP_interface_v2 generates charge profiles
        self.charge_profiles = CP_interface_v2(self.input_folder)
        
        if self.use_cost_forecaster_v3:
            self.cost_forecaster = TE_cost_forecaster_v3(os.path.join(self.input_folder, "TE_inputs"), self.figures_folder, self.plot)
        else:
            
            forecast_file = os.path.join(self.input_folder, "TE_inputs", "forecast.csv")
            actual_file = os.path.join(self.input_folder, "TE_inputs", "actual.csv")
            cost_file = os.path.join(self.input_folder, "TE_inputs", "generation_cost.json")
        
            # cost_forcaster contains the cost of energy
            self.cost_forecaster = TE_cost_forecaster_v2(forecast_file, actual_file, cost_file, self.figures_folder, self.plot)
        
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
                
    #def log_controller(self):
    #    df = pd.DataFrame()
    #    time_arr = np.array([i for i in range(self.controller_starttime_sec, self.controller_endtime_sec + self.controller_timestep_sec, self.controller_timestep_sec)])
    #    df["time"] = time_arr/3600.0
    #    df["SE_100239126"] = self.controller_2Darr[self.SE_id_to_controller_index_map[100239126], :].astype(int)
    #    df.to_csv(os.path.join(self.input_folder, "controller_state.csv"), index = False)
        
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
        self.add_active_charge_event(next_control_starttime_sec, active_charge_event)
    
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
        charge_time_remaining_hrs = active_charge_event.min_remaining_charge_time_hrs
        charge_time_total_hrs = active_charge_event.min_time_to_complete_entire_charge_hrs
        
        #-------------------------------------------
        #       Build time parameters
        #-------------------------------------------
        start_time_sec = next_control_starttime_sec
        end_time_sec = min(next_control_starttime_sec + self.forecast_duration_sec, departure_unix_time - fmod(departure_unix_time, self.controller_timestep_sec))
        
        if(end_time_sec <= start_time_sec):
            print("Charge event {} too small. Cannot be controlled".format(CE_id))
            return
        
        # round up to the nearest self.controller_timestep_sec
        charge_time_remaining_in_controller_step_sec = ceil(charge_time_remaining_hrs * 3600 / self.controller_timestep_sec) * self.controller_timestep_sec
        
        # Number of steps controller needs to charge the vehicle
        num_steps_to_charge_by_controller = int(charge_time_remaining_in_controller_step_sec / self.controller_timestep_sec)

        #-------------------------------------------
        #       Build cost profile timeseries
        #-------------------------------------------
        
        if self.use_cost_forecaster_v3:
            cost_profile = self.cost_forecaster.get_cost_for_time_range(next_control_starttime_sec, start_time_sec, end_time_sec, self.controller_timestep_sec)
        else:
            cost_profile = self.cost_forecaster.get_cost_for_time_range(start_time_sec, end_time_sec, self.controller_timestep_sec)
        
        #-------------------------------------------
        #       Select least cost times 
        #-------------------------------------------
        
        cost_profile_indices_sorted = sorted(range(len(cost_profile.data)), key = lambda k: cost_profile.data[k])
        
        # select first n cheapest cost profiles 
        # TODO : make the cost profile as contiguous as possible
        cost_profile_indeces_cheapest = cost_profile_indices_sorted[:num_steps_to_charge_by_controller]
        
        #-------------------------------------------
        #       Update controller_2Darr 
        #-------------------------------------------
        
        for cost_profile_index in cost_profile_indeces_cheapest:
            profile_time_sec = cost_profile.get_time_from_index_sec(cost_profile_index)
            control_time_index = self.get_time_idx_from_time_sec(profile_time_sec)          
            self.controller_2Darr[self.SE_id_to_controller_index_map[SE_id], control_time_index] = True
        
        if self.debug_plot == True:
            
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
            
            os.makedirs(self.figures_folder, exist_ok=True)
            plt.savefig(os.path.join(self.figures_folder, plot_name+".png"))
   
            #self.plot = False
               
    def get_SE_setpoints(self, next_control_timestep_sec : float, active_SEs : List[int] ) -> List[SE_setpoint]:
        '''
        Description:
            Looks up controller_2Darr to see which SEs needs to charge at the specific time
        '''
        
        time_index = floor((next_control_timestep_sec - self.controller_starttime_sec)/ self.controller_timestep_sec)
        
        # check all rows with active charge events that need to charge
        SE_indexes_to_charge = np.array(np.where(self.controller_2Darr[:, time_index] == True))
        
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