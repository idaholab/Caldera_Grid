
import pandas as pd
from numpy import random

from Caldera_globals import L2_control_strategies_enum
from Caldera_globals import ES500_aggregator_charging_forecast
from Caldera_ICM_Aux import get_value_from_normal_distribution


class ES500_Aggregator_charging_needs_forecast:

    def __init__(self, SE_group_charge_events, SEid_to_SE_type, ES500_Aggregator_parameters):
        self.prediction_horizon_duration_sec = 3600*ES500_Aggregator_parameters['prediction_horizon_duration_hrs']
        self.aggregator_timestep_hrs = ES500_Aggregator_parameters['aggregator_timestep_mins'] / 60
    
        #-----------------------
    
        seed = ES500_Aggregator_parameters['charge_event_forecast_arrival_time_sec']['seed']
        stdev = ES500_Aggregator_parameters['charge_event_forecast_arrival_time_sec']['stdev']
        stdev_bounds = ES500_Aggregator_parameters['charge_event_forecast_arrival_time_sec']['stdev_bounds']    
        error_arrival_time_sec = get_value_from_normal_distribution(seed, 0, stdev, stdev_bounds)
        
        seed = ES500_Aggregator_parameters['charge_event_forecast_park_duration_sec']['seed']
        stdev = ES500_Aggregator_parameters['charge_event_forecast_park_duration_sec']['stdev']
        stdev_bounds = ES500_Aggregator_parameters['charge_event_forecast_park_duration_sec']['stdev_bounds']    
        error_park_duration_sec = get_value_from_normal_distribution(seed, 0, stdev, stdev_bounds)
        
        seed = ES500_Aggregator_parameters['charge_event_forecast_e3_charge_remain_soc']['seed']
        stdev = ES500_Aggregator_parameters['charge_event_forecast_e3_charge_remain_soc']['stdev']
        stdev_bounds = ES500_Aggregator_parameters['charge_event_forecast_e3_charge_remain_soc']['stdev_bounds']    
        error_e3_charge_remain_soc = get_value_from_normal_distribution(seed, 0, stdev, stdev_bounds)

        #-----------------------
    
        self.arrival_unix_time = []
        self.departure_unix_time = []
        self.arrival_SOC = []
        self.departure_SOC = []
        self.vehicle_type = []
        self.SE_type = []
        
        for X in SE_group_charge_events:
            for charge_event in X.charge_events:
                if L2_control_strategies_enum.ES500 == charge_event.control_enums.ES_control_strategy:
                    arrival_unix_time = charge_event.arrival_unix_time + error_arrival_time_sec.get_value()
                    
                    park_duration_sec = charge_event.departure_unix_time - charge_event.arrival_unix_time
                    park_error_sec = error_park_duration_sec.get_value()
                    while (park_duration_sec + park_error_sec) <= 0:
                        park_error_sec = error_park_duration_sec.get_value()
                    
                    departure_unix_time = arrival_unix_time + (park_duration_sec + park_error_sec)
                    
                    #----------------
                    
                    charge_remain_soc = charge_event.departure_SOC - charge_event.arrival_SOC
                    charge_remain_error_soc = error_e3_charge_remain_soc.get_value()
                    while (charge_remain_soc + charge_remain_error_soc) <= 1 or 99 <= (charge_remain_soc + charge_remain_error_soc):
                        charge_remain_error_soc = error_e3_charge_remain_soc.get_value()
                    
                    new_charge_remain_soc = (charge_remain_soc + charge_remain_error_soc)
                    center_soc = (charge_event.departure_SOC + charge_event.arrival_SOC)/2
                    
                    if center_soc - new_charge_remain_soc/2 < 0:
                        arrival_SOC = 0
                    else:
                        arrival_SOC = center_soc - new_charge_remain_soc/2
                    
                    departure_SOC = arrival_SOC + new_charge_remain_soc
                    if 100 < departure_SOC:
                        departure_SOC = 100
                        arrival_SOC = departure_SOC - new_charge_remain_soc
                    
                    #----------------
                    
                    self.arrival_unix_time.append(arrival_unix_time)
                    self.departure_unix_time.append(departure_unix_time)
                    self.arrival_SOC.append(arrival_SOC)
                    self.departure_SOC.append(departure_SOC)
                    self.vehicle_type.append(charge_event.vehicle_type)
                    self.SE_type.append(SEid_to_SE_type[charge_event.SE_id])
        
        #------------------------------------------
        # Append additional day to end of forecast
        #------------------------------------------        
        df = pd.DataFrame(self.arrival_unix_time)
        column_name = df.columns[0]        
        max_val = df[column_name].max() 
        df = df[(max_val - 24*3600) < df[column_name]]
        
        indexes = df.index.to_list()
       
        arrival_unix_time_end = []
        departure_unix_time_end = []
        arrival_SOC_end = []
        departure_SOC_end = []
        vehicle_type_end = []
        SE_type_end = []
   
        for i in indexes:
            arrival_unix_time_end.append(self.arrival_unix_time[i] + 24*3600)
            departure_unix_time_end.append(self.departure_unix_time[i] + 24*3600)
            arrival_SOC_end.append(self.arrival_SOC[i])
            departure_SOC_end.append(self.departure_SOC[i])
            vehicle_type_end.append(self.vehicle_type[i])
            SE_type_end.append(self.SE_type[i])
        
        #---------------
                
        self.arrival_unix_time.extend(arrival_unix_time_end)
        self.departure_unix_time.extend(departure_unix_time_end)
        self.arrival_SOC.extend(arrival_SOC_end)
        self.departure_SOC.extend(departure_SOC_end)
        self.vehicle_type.extend(vehicle_type_end)
        self.SE_type.extend(SE_type_end)
        
        self.df_arrival_unix_time = pd.DataFrame(self.arrival_unix_time)
            

    def get_forecast(self, unix_start_time):
        column_name = self.df_arrival_unix_time.columns[0]
        filter_end_time = unix_start_time + self.prediction_horizon_duration_sec
        
        df_tmp = self.df_arrival_unix_time[(unix_start_time < self.df_arrival_unix_time[column_name]) & (self.df_arrival_unix_time[column_name] < filter_end_time)]        
        indexes = df_tmp.index.to_list()
        
        #---------------
        
        arrival_unix_time = []
        departure_unix_time = []
        e3_charge_remain_kWh = []
        e3_step_max_kWh = []
        
        for i in indexes:
            arrival_unix_time.append(self.arrival_unix_time[i])
            departure_unix_time.append(self.departure_unix_time[i])
            
            arrival_SOC = self.arrival_SOC[i]
            departure_SOC = self.departure_SOC[i]
            vehicle_type = self.vehicle_type[i]
            SE_type = self.SE_type[i]
            
            e3_charge_remain = (departure_SOC - arrival_SOC) * 80/100
            
            e3_charge_remain_kWh.append(e3_charge_remain)
            e3_step_max_kWh.append(6.6 * self.aggregator_timestep_hrs)
        
        #---------------
        
        return_val = ES500_aggregator_charging_forecast()
        return_val.arrival_unix_time = arrival_unix_time
        return_val.departure_unix_time = departure_unix_time
        return_val.e3_charge_remain_kWh = e3_charge_remain_kWh
        return_val.e3_step_max_kWh = e3_step_max_kWh
        
        return return_val

