from Caldera_globals import timeseries

from dynamic_price_control.load_control_inputs import load_demand_gen_files
from dynamic_price_control.cost_solver import cost_solver

import pandas as pd
import numpy as np
import json

from math import fmod

from scipy.interpolate import CubicSpline

class TE_cost_forecaster_v2():
    '''
    Description:
        The TE_cost_forecaster will read the input file and compute costs and loads forecasted cost and actual cost as timeseries data 
    '''
    
    def __init__(self, forecast_input_file : str, actual_input_file : str, cost_input_file : str, figures_folder : str, plot : bool) -> None:
        '''
        Description:
            Loads data, computes cost and stores as timeseries data
        '''
        
        self.figures_folder = figures_folder
        self.plot = plot
        
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
        
        df_type = None 
        if df.columns[1] == "forecasted_demand":
            df_type = "forecast"         
        elif df.columns[1] == "actual_demand":
            df_type = "actual"
        else:
            raise ValueError('ERROR : Second column in input csv file should be forecasted_demand or actual_demand')
            
        start_time_sec = round(df["time"][0] * 3600.0)
        timestep_sec = round((df["time"][1] - df["time"][0])*3600)
        
        # Ignore first 2 columns time and forecasted_demand/actual_demand
        gen_types = df.columns[2:].to_series()
        
        cost_usd_per_kWh = np.zeros(df.shape[0], dtype=float)
        total_cost_usd = np.zeros(df.shape[0], dtype=float)
        
        individual_costs = {}
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
                    individual_costs[gen_type] = individual_cost_function
                    
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
                    individual_costs[gen_type] = individual_cost_function
                    
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
                    individual_costs[gen_type] = individual_cost_function
                    
                    total_cost_usd += individual_cost_function*df[gen_type]*timestep_sec/3600.0
                    
                else:
                    
                    raise ValueError('ERROR : solver_method should be linear or steep_cubic or inverse_s')
            
            #if self.plot:
            #    fig, ax = plt.subplots(1, 1, figsize=(25, 15))
            #
            #    ax.plot(df[gen_type], individual_cost_function)
            #    ax.set_xlabel("Power | MW")
            #    ax.set_ylabel("Cost | $ per MWh")
            #
            #    fig.savefig("fig_" + gen_type + ".png", dpi = 300)
            
        
        total_MWh_per_timestep = df[gen_types].sum(axis=1) * timestep_sec/3600.0
        cost_usd_per_MWh = total_cost_usd/total_MWh_per_timestep
        cost_usd_per_kWh = cost_usd_per_MWh/1000.0
        
#        if self.plot:
#            
#            os.makedirs(self.figures_folder, exist_ok= True)
#        
#            start_idx = (1*24*3600) / timestep_sec
#            end_idx = (2*24*3600) / timestep_sec
#            
#            fig, ax = plt.subplots(1, 1)
#            ax.plot(df["time"], individual_costs["fossil_fuel"])
#            ax.set_xlabel("Time | hrs")
#            ax.set_ylabel("Cost | $ per kWh")
#            ax.set_title("Time vs Cost for fossil fuel with {} pricing".format(solver_method))
#            ax.grid()
#            fig.savefig(os.path.join(self.figures_folder, "ff_" + df_type + "_" + solver_method + "_time_vs_cost.png"), dpi = 300)
#        
#            fig, ax = plt.subplots(1, 1)
#            ax.scatter(df["fossil_fuel"], individual_costs["fossil_fuel"])
#            ax.set_xlabel("Power | kW")
#            ax.set_ylabel("Cost | $ per kWh")
#            ax.grid()
#            fig.savefig(os.path.join(self.figures_folder, "ff_" + df_type + "_" + solver_method + "_power_vs_cost.png"), dpi = 300)
                
        return timeseries(start_time_sec, timestep_sec, cost_usd_per_kWh)
            
    def error_check(self, starttime_sec : float, endtime_sec : float, req_timestep_sec : float) -> timeseries:
        '''
        Description:
            Check if the parameters match up.
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

        
    def get_cost_for_time_range(self, starttime_sec : float, endtime_sec : float, req_timestep_sec : float) -> timeseries:
        '''
        Description:
            Given a timerange and timestep, looksup the data and returns the cost. 
            the timerange should match up with data timeperiod.
        '''
        
        self.error_check(starttime_sec, endtime_sec, req_timestep_sec)

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

    def get_forecasted_cost_for_time_range(self, starttime_sec : float, endtime_sec : float, req_timestep_sec : float) -> timeseries:
        '''
        Description:
            Given a timerange and timestep, looksup the data and returns the forecasted cost. 
            the timerange should match up with data timeperiod.
        '''
        
        self.error_check(starttime_sec, endtime_sec, req_timestep_sec)
        
        data = []
        if (self.forecasted_cost_profile.data_timestep_sec >= req_timestep_sec):
            for time_sec in range(int(starttime_sec), int(endtime_sec), int(req_timestep_sec)):
            
                cost = self.forecasted_cost_profile.get_val_from_time(time_sec % self.cost_profile_length_sec)
                data.append(cost)
                
        elif (self.forecasted_cost_profile.data_timestep_sec < req_timestep_sec):
            for time_sec in range(int(starttime_sec), int(endtime_sec), int(req_timestep_sec)):
                
                start_sec = time_sec
                end_sec = time_sec + req_timestep_sec
                divisor = req_timestep_sec/self.forecasted_cost_profile.data_timestep_sec
                
                total_cost = 0    
                
                for subtime_sec in range(int(start_sec), int(end_sec), int(self.forecasted_cost_profile.data_timestep_sec)):
                    total_cost += self.forecasted_cost_profile.get_val_from_time(subtime_sec % self.cost_profile_length_sec)
                
                avg_cost = total_cost/divisor
                data.append(avg_cost)
                
        else:
            raise ValueError('ERROR : get_cost_for_time_range')

        return timeseries(starttime_sec, req_timestep_sec, data)

    def get_actual_cost_for_time_range(self, starttime_sec : float, endtime_sec : float, req_timestep_sec : float) -> timeseries:
        '''
        Description:
            Given a timerange and timestep, looksup the data and returns the actual cost. 
            the timerange should match up with data timeperiod.
        '''
        
        self.error_check(starttime_sec, endtime_sec, req_timestep_sec)
        
        data = []
        if (self.actual_cost_profile.data_timestep_sec >= req_timestep_sec):
            for time_sec in range(int(starttime_sec), int(endtime_sec), int(req_timestep_sec)):
            
                cost = self.actual_cost_profile.get_val_from_time(time_sec % self.cost_profile_length_sec)    
                data.append(cost)
                
        elif (self.actual_cost_profile.data_timestep_sec < req_timestep_sec):
            for time_sec in range(int(starttime_sec), int(endtime_sec), int(req_timestep_sec)):
                
                start_sec = time_sec
                end_sec = time_sec + req_timestep_sec
                divisor = req_timestep_sec/self.forecasted_cost_profile.data_timestep_sec
                
                total_cost = 0
                for subtime_sec in range(int(start_sec), int(end_sec), int(self.forecasted_cost_profile.data_timestep_sec)):
                    total_cost += self.actual_cost_profile.get_val_from_time(subtime_sec % self.cost_profile_length_sec)
                
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

class TE_cost_forecaster_v3():
    
    def __init__(
            self, input_folder: str, figures_folder: str, plot: bool) -> None:
        
        loader = load_demand_gen_files(input_folder)                            # loader object
        (self.dem_dict, self.gen_dict, self.cost_dict) = loader.load()          # loads all input file
        
        if "EV" in self.dem_dict:
            self.EV_demand_df = self.dem_dict["EV"][2]["forecast_00"]               # EV_demand_forecaster()

        #------------------------------------        
        #Temporary
        
        '''
        
        for key in self.dem_dict.keys():
            reduction = 10
            if key != "EV":
                (metadata_dict, frcst_metadata_dict, data_dict) = self.dem_dict[key]
                metadata_dict['gen_min'] = metadata_dict['gen_min']/reduction
                metadata_dict['gen_max'] = metadata_dict['gen_max']/reduction
                
                for data_id in data_dict.keys():
                    
                    data_dict[data_id][data_id] = data_dict[data_id][data_id]/reduction
                    
                
                self.dem_dict[key] = (metadata_dict, frcst_metadata_dict, data_dict)
                
        for key in self.gen_dict.keys():
            reduction = 10
            if key == 'nuclear':
                reduction = 20
            
            (metadata_dict, frcst_metadata_dict, data_dict) = self.gen_dict[key]
            metadata_dict['gen_min'] = metadata_dict['gen_min']/reduction
            metadata_dict['gen_max'] = metadata_dict['gen_max']/reduction
            
            for data_id in data_dict.keys():
                data_dict[data_id][data_id] = data_dict[data_id][data_id]/reduction

            self.gen_dict[key] = (metadata_dict, frcst_metadata_dict, data_dict)
        '''
        #------------------------------------
        
        if len(self.gen_dict) == 0:
            raise ValueError('ERROR: No generation data exists to compute costs')

        self.solver = cost_solver(self.cost_dict)
        
        self.forecast_dur_s = 48*3600                                           # How long in the future can we forecast
        self.forecast_ts_s = 1*3600                                             # The timestep in which forecast data is available 
        self.actual_ts_s = 1*3600                                               # The timestep in which actual data is available
        self.adjustment_time_sec = 4*3600
    
    def adjust_EV_charging_demand(self, adjustment_num_EVs, start_time, forecast_dur):
        
        ajustment_kW = adjustment_num_EVs * (10.58 / 1000.0)                      # Assuming average of 10.58 kW
        
        ajustment_kW_in_demand_ts = np.repeat(ajustment_kW, 15)  # Hardcoding timesteps as 15 min and 1 min for now
        
        time_col = "forecast_00_time"
        val_col = "forecast_00"
        
        mask1 = self.EV_demand_df[time_col] >= start_time
        mask2 = self.EV_demand_df[time_col] < start_time + forecast_dur

        self.EV_demand_df.loc[mask1 & mask2, val_col] += ajustment_kW_in_demand_ts

    def replace_EV_charging_demand(self, ajustment_kW, start_time):
        
        #ajustment_kW_in_demand_ts = np.mean(ajustment_kW.reshape(-1, 15), axis=1)
        
        ajustment_kW_in_demand_ts = ajustment_kW
        time_col = "forecast_00_time"
        val_col = "forecast_00"
        
        mask1 = self.EV_demand_df[time_col] >= start_time
        mask2 = self.EV_demand_df[time_col] < start_time + len(ajustment_kW_in_demand_ts) * 60


        print(len(ajustment_kW_in_demand_ts))
        print(len(self.EV_demand_df.loc[mask1 & mask2, val_col]))
        
        self.EV_demand_df.loc[mask1 & mask2, val_col] = ajustment_kW_in_demand_ts
        
        
    def check_time_values(
            self, start_time_sec: float, end_time_sec: float, 
            req_time_step_sec: float) -> None:
        
        # Ensure time_range doesn't go beyond forecast_duration
        assert end_time_sec - start_time_sec <= self.forecast_dur_s, \
            "requested time range ({}, {}) hrs is beyond forecast duration of {} hrs"\
            .format(start_time_sec/3600, end_time_sec/3600, self.forecast_dur_s/3600)
        
        # Ensure self.forecast_time_step_sec is a multiple of req_time_step_sec
        assert abs(fmod(self.actual_ts_s, req_time_step_sec)) < 0.001, \
            "req_time_step_sec {} hrs is not a multiple of actual_ts_s {} hrs"\
            .format(self.actual_ts_s/3600, req_time_step_sec/3600)
        
        # Ensure start_time_sec is a perfect multiple of req_time_step_sec
        assert abs(fmod(start_time_sec, req_time_step_sec)) < 0.001 , \
            "start_time_sec: {} should be a multiple of actual_ts_s: {}"\
            .format(start_time_sec, self.actual_ts_s)
        
        # Ensure end_time_sec is a perfect multiple of time_range
        assert abs(fmod(end_time_sec, req_time_step_sec)) < 0.001 , \
            "end_time_sec: {} should be a multiple of req_time_step_sec: {}"\
            .format(end_time_sec, req_time_step_sec)
        
        # Ensure time_step is a perfect multiple of time_range
        assert abs(fmod(end_time_sec - start_time_sec, req_time_step_sec)) < 0.001 , \
            "requested time_range_sec: {} should be a multiple of req_time_step_sec: {}"\
            .format(end_time_sec - start_time_sec, req_time_step_sec)
     
    def get_data_for_time_range(
            self, data_id: str, data_type: str, cur_time_sec: float,
            start_time_sec: float, end_time_sec: float, req_time_step_sec: float, debug = False):
        
        if debug == False:
            self.check_time_values(start_time_sec, end_time_sec, req_time_step_sec)
        
        if data_id == "EV":
            
            mask1 = self.EV_demand_df["forecast_00_time"] >= start_time_sec
            mask2 = self.EV_demand_df["forecast_00_time"] < end_time_sec
            EV_demand = self.EV_demand_df.loc[ mask1 & mask2, "forecast_00"].to_numpy()
            
            # Assuming EV data TS is 1 min and 
            # Control TS is 15 min
            vals_to_aggregate = 15 

            EV_demand = np.reshape(EV_demand, (-1, vals_to_aggregate))

            # Calculate the average along the columns
            averaged_EV_demand = np.mean(EV_demand, axis=1)

            if (len(averaged_EV_demand) != (end_time_sec - start_time_sec) / req_time_step_sec):
                print("ERROR: EV demand step and requested_step dont match")
            return averaged_EV_demand

        if data_id in self.dem_dict:
            (metadata_dict, frcst_metadata_dict, data_dict) = self.dem_dict[data_id]
        elif data_id in self.gen_dict:
            (metadata_dict, frcst_metadata_dict, data_dict) = self.gen_dict[data_id]
        else:
            assert False, "data_id: {} is not present in demand data nor generation data"

        final_data = np.zeros(int((end_time_sec - start_time_sec) / req_time_step_sec))
        
        if data_type == "actual":
            column_ts = self.actual_ts_s
            rel_t_to_id_d = {0 : "actual"}
            
        elif data_type == "forecast":
            column_ts = self.forecast_ts_s
            # switch key and values in forecast_metadata_dict so that we can iterate through release_time
            rel_t_to_id_d = {y[0]: x for x, y in frcst_metadata_dict.items()}
            
        # Start from 1st forecast until the forecast that's active during cur_time_sec
        for (release_time_hrs, col_id) in rel_t_to_id_d.items():
            if (release_time_hrs*3600 <= cur_time_sec):

                if col_id in frcst_metadata_dict:
                    # rel_t_s = Release Time Sec
                    # st_t_s = Start Time Sec
                    # end_t_s = End Time Sec
                    # ts_s = Time Step Sec
                    # of_s = Offset Sec
                    (rel_t_s, st_t_s, end_t_s, ts_s, of_s) = frcst_metadata_dict[col_id]
                else:
                    time_arr = data_dict[col_id]["{}_time".format(col_id)].to_numpy()
                    rel_t_s = time_arr[0]
                    st_t_s = time_arr[0]
                    ts_s = time_arr[1] - time_arr[0]
                    end_t_s = st_t_s + ts_s * len(time_arr)
                    of_s = st_t_s - rel_t_s

                # Check for overlap between forecast start end and requested start end
                overlap_start = max(start_time_sec, st_t_s)
                overlap_end = min(end_time_sec, end_t_s)
                
                if (overlap_start < overlap_end):
                    df = data_dict[col_id]
                    
                    overlap_start_floor = overlap_start - (overlap_start % column_ts)
                    overlap_end_ceil = overlap_end + (column_ts - (overlap_end % column_ts))
                    
                    # linear interpolation
                    arr = np.interp(np.arange(overlap_start, overlap_end, req_time_step_sec), df["{}_time".format(col_id)], df["{}".format(col_id)])

                    # cubic spline interpolation
                    #spl = CubicSpline(df["{}_time".format(col_id)], df["{}".format(col_id)])
                    #arr = spl(np.arange(overlap_start, overlap_end, req_time_step_sec))

                    #for time in np.arange(overlap_start, overlap_end, req_time_step_sec):
                    #    time_in_df_timestep = time - (time%column_ts)
                    #    arr.append(float(df[df["{}_time".format(col_id)] == time_in_df_timestep][col_id]))
                     
                    #arr = np.array(arr)
                    
                    idx = np.arange(int((overlap_start-start_time_sec)/req_time_step_sec), int((overlap_end-start_time_sec)/req_time_step_sec))
                    np.put(final_data, idx, arr)
            else:
                break

        return final_data
    
    def get_adjusted_data_for_time_range(
            self, data_id:float, cur_time_sec:float, start_time_sec: float, 
            end_time_sec: float, req_time_step_sec: float, debug = False):
        
        forecast_arr = self.get_data_for_time_range(data_id, "forecast", cur_time_sec, start_time_sec, end_time_sec, req_time_step_sec, debug)
        
        actual_arr = self.get_data_for_time_range(data_id, "actual", cur_time_sec, start_time_sec, end_time_sec, req_time_step_sec, debug)
        
        weight_arr = np.zeros(int((end_time_sec - start_time_sec) / req_time_step_sec))
        num_elements_in_gradient = int((self.adjustment_time_sec) / req_time_step_sec)
        
        weight_arr[:num_elements_in_gradient] = np.linspace(1, 0, num_elements_in_gradient)        
        
        return actual_arr * weight_arr + forecast_arr * (1 - weight_arr)

    def get_cost_for_time_range(
            self, cost_type: str, cur_time_sec: float, start_time_sec: float, 
            end_time_sec: float, req_time_step_sec: float, debug = False):
        
        dem_data = pd.DataFrame()
        gen_data = pd.DataFrame()
            
        if (cost_type == "adjusted"):
            # get all known data
            dem_data["demand"] = self.get_adjusted_data_for_time_range(
                "demand", cur_time_sec, start_time_sec, end_time_sec, 
                req_time_step_sec, debug)
            if "EV" in self.dem_dict: 
                dem_data["EV"] = self.get_adjusted_data_for_time_range(
                    "EV", cur_time_sec, start_time_sec, end_time_sec, 
                    req_time_step_sec, debug)
            if "nuclear" in self.gen_dict: 
                gen_data["nuclear"] = self.get_adjusted_data_for_time_range(
                    "nuclear", cur_time_sec, start_time_sec, end_time_sec, 
                    req_time_step_sec, debug)
            if "solar" in self.gen_dict: 
                gen_data["solar"] = self.get_adjusted_data_for_time_range(
                    "solar", cur_time_sec, start_time_sec, end_time_sec, 
                    req_time_step_sec, debug)
            if "wind" in self.gen_dict: 
                gen_data["wind"] = self.get_adjusted_data_for_time_range(
                    "wind", cur_time_sec, start_time_sec, end_time_sec, 
                    req_time_step_sec, debug)        

        elif (cost_type == "forecasted"):
            # get all known data
            dem_data["demand"] = self.get_data_for_time_range(
                "demand", "forecast", cur_time_sec, start_time_sec, 
                end_time_sec, req_time_step_sec, debug)
            if "EV" in self.dem_dict: 
                dem_data["EV"] = self.get_data_for_time_range(
                    "EV", "forecast", cur_time_sec, start_time_sec, 
                    end_time_sec, req_time_step_sec, debug)
            if "nuclear" in self.gen_dict: 
                gen_data["nuclear"] = self.get_data_for_time_range(
                    "nuclear", "forecast", cur_time_sec, start_time_sec, 
                    end_time_sec, req_time_step_sec, debug)
            if "solar" in self.gen_dict: 
                gen_data["solar"] = self.get_data_for_time_range(
                    "solar", "forecast", cur_time_sec, start_time_sec, 
                    end_time_sec, req_time_step_sec, debug)
            if "wind" in self.gen_dict: 
                gen_data["wind"] = self.get_data_for_time_range(
                    "wind", "forecast", cur_time_sec, start_time_sec, 
                    end_time_sec, req_time_step_sec, debug)        

        elif (cost_type == "actual"):
            # get all known data
            dem_data["demand"] = self.get_data_for_time_range(
                "demand", "actual", cur_time_sec, start_time_sec, 
                end_time_sec, req_time_step_sec, debug)
            if "EV" in self.dem_dict: 
                dem_data["EV"] = self.get_data_for_time_range(
                    "EV", "actual", cur_time_sec, start_time_sec, 
                    end_time_sec, req_time_step_sec, debug)
            if "nuclear" in self.gen_dict: 
                gen_data["nuclear"] = self.get_data_for_time_range(
                    "nuclear", "actual", cur_time_sec, start_time_sec, 
                    end_time_sec, req_time_step_sec, debug)
            if "solar" in self.gen_dict: 
                gen_data["solar"] = self.get_data_for_time_range(
                    "solar", "actual", cur_time_sec, start_time_sec, 
                    end_time_sec, req_time_step_sec, debug)
            if "wind" in self.gen_dict: 
                gen_data["wind"] = self.get_data_for_time_range(
                    "wind", "actual", cur_time_sec, start_time_sec, 
                    end_time_sec, req_time_step_sec, debug)        

        else:
            print("")
            print("")
            print("ERROR!!!: cost type unknown:", cost_type)
            print("")
            print("")


        gen_data["fossil_fuel"] = dem_data["demand"]
        if "EV" in self.dem_dict: 
            gen_data["fossil_fuel"] += dem_data["EV"]
        if "nuclear" in self.gen_dict: 
            gen_data["fossil_fuel"] -= gen_data["nuclear"]
        if "solar" in self.gen_dict:
            gen_data["fossil_fuel"] -= gen_data["solar"]
        if "wind" in self.gen_dict: 
            gen_data["fossil_fuel"] -= gen_data["wind"]

        gen_data["fossil_fuel"][ np.where(gen_data["fossil_fuel"] < 0.0 )[0] ] = 0.0
        
        total_cost_usd = np.zeros(int((end_time_sec - start_time_sec) / req_time_step_sec))
        
        for (data_id, arr) in gen_data.items():
            cost_function = self.solver.solve(arr, self.cost_dict[data_id])
            total_cost_usd += cost_function*arr*req_time_step_sec/3600.0
            
        total_MWh_per_timestep = gen_data.sum(axis=1) * req_time_step_sec/3600.0
        cost_usd_per_MWh = total_cost_usd/total_MWh_per_timestep
        cost_usd_per_kWh = cost_usd_per_MWh/1000.0
        
        return timeseries(start_time_sec, req_time_step_sec, cost_usd_per_kWh)
    
    def get_cost_at_time_sec(self, cost_type: str, time_sec: float, req_time_step_sec: float):
        
        dem_data = pd.DataFrame()
        gen_data = pd.DataFrame()

        dem_data["demand"] = self.get_data_for_time_range(
            "demand", cost_type, time_sec, time_sec, 
            time_sec + req_time_step_sec, req_time_step_sec)
        
        if "EV" in self.dem_dict: 
            dem_data["EV"] = self.get_data_for_time_range(
                "EV", cost_type, time_sec, time_sec, 
                time_sec + req_time_step_sec, req_time_step_sec)
        
        if "nuclear" in self.gen_dict: 
            gen_data["nuclear"] = self.get_data_for_time_range(
                "nuclear", cost_type, time_sec, time_sec, 
                time_sec + req_time_step_sec, req_time_step_sec)
        
        if "solar" in self.gen_dict:
            gen_data["solar"] = self.get_data_for_time_range(
                "solar", cost_type, time_sec, time_sec, 
                time_sec + req_time_step_sec, req_time_step_sec)
        if "wind" in self.gen_dict: 
            gen_data["wind"] = self.get_data_for_time_range(
                "wind", cost_type, time_sec, time_sec, 
                time_sec + req_time_step_sec, req_time_step_sec) 
        
        gen_data["fossil_fuel"] = dem_data["demand"]
        if "EV" in self.dem_dict: 
            gen_data["fossil_fuel"] += dem_data["EV"]
        if "nuclear" in self.gen_dict: 
            gen_data["fossil_fuel"] -= gen_data["nuclear"]
        if "solar" in self.gen_dict:
            gen_data["fossil_fuel"] -= gen_data["solar"]
        if "wind" in self.gen_dict: 
            gen_data["fossil_fuel"] -= gen_data["wind"]
                    
        gen_data["fossil_fuel"][ np.where(gen_data["fossil_fuel"] < 0.0 )[0] ] = 0.0
        
        total_cost_usd = 0.0
        
        for (data_id, arr) in gen_data.items():
            cost_function = self.solver.solve(arr, self.cost_dict[data_id])
            total_cost_usd += cost_function*arr*req_time_step_sec/3600.0
            
        total_MWh_per_timestep = gen_data.sum(axis=1) * req_time_step_sec/3600.0
        cost_usd_per_MWh = total_cost_usd/total_MWh_per_timestep
        cost_usd_per_kWh = cost_usd_per_MWh/1000.0
        
        return cost_usd_per_kWh
        
    def get_forecasted_cost_at_time_sec(self, time_sec: float, req_time_step_sec: float):
        
        return self.get_cost_at_time_sec("forecast", time_sec, req_time_step_sec)[0]
    
    def get_actual_cost_at_time_sec(self, time_sec: float, req_time_step_sec: float):
        
        return self.get_cost_at_time_sec("actual", time_sec, req_time_step_sec)[0]
