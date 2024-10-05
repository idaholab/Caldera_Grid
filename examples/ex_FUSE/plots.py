# -*- coding: utf-8 -*-
"""
Created on Tue Feb 20 13:46:41 2024

@author: CEBOM
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import os
import sys

path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))

caldera_grid_proj_dir = os.path.join(path_to_here, "..", "..")

index = 1
sys.path.insert( index+0, os.path.join( caldera_grid_proj_dir, "./" ) )
sys.path.insert( index+1, os.path.join( caldera_grid_proj_dir, "./libs" ) )
sys.path.insert( index+2, os.path.join( caldera_grid_proj_dir, "./source/base" ) )
sys.path.insert( index+3, os.path.join( caldera_grid_proj_dir, "./source/custom_controls" ) )
sys.path.insert( index+4, os.path.join( caldera_grid_proj_dir, "./source/ES500" ) )
sys.path.insert( index+5, os.path.join( caldera_grid_proj_dir, "./source/federates" ) )

from dynamic_price_control.cost_forecaster import TE_cost_forecaster_v3

#----------------------------------

def extract_power_profile_df(folder : str, start = None, end = None, step = None):
    
    default_step = 1/60
    aggregate = int(step/default_step)
    
    df = pd.read_csv(os.path.join(folder, "real_power_profiles.csv"))
    df["sim_time"] = pd.to_datetime((df["simulation_time_hrs"]*3600).round(0), unit='s')
    
    if start != None and end != None:
        mask1 = (df["simulation_time_hrs"] >= start)
        mask2 = (df["simulation_time_hrs"] < end)
        df = df.loc[mask1 & mask2, :]
    
    new_df = pd.DataFrame()
    new_df["simulation_time_hrs"] = df.loc[::aggregate, "simulation_time_hrs"]
    new_df["sim_time"] = df.loc[::aggregate, 'sim_time']
    new_df['total_demand_kW'] = np.mean(df.loc[:, 'total_demand_kW'].to_numpy().reshape(-1, aggregate), axis=1)
    
    new_df = new_df.reset_index()
    return new_df

#----------------------------------

input_folder = os.path.join(path_to_here, "inputs")
output_folder = os.path.join(path_to_here, "outputs")
figures_folder = os.path.join(path_to_here, "figures")

sim_start = 3*24      # Two weeks of simulation
sim_end = 6*24

home_start = sim_start
home_end = sim_end

work_start = sim_start
work_end = sim_end

home_start_dt = pd.to_datetime(home_start*3600, unit ='s')
home_end_dt = pd.to_datetime(home_end*3600, unit ='s')

work_start_dt = pd.to_datetime(work_start*3600, unit ='s')
work_end_dt = pd.to_datetime(work_end*3600, unit ='s')

profile = "total_demand_kW"
offset = 204
figsize = (18, 9)
fontsize = 18
scenario_range = np.arange(0, 101, 25)

colors = ['red', 'orangered', 'goldenrod', 'olivedrab', 'seagreen', 'darkgreen']

#----------------------------------

scenario = "home_uncontrolled"
cost_forecaster = TE_cost_forecaster_v3(os.path.join(input_folder, scenario, "TE_inputs"), ".", False)


energy_df = pd.DataFrame()
energy_df["time_hrs"] = np.arange(sim_start, sim_end, 0.25)
energy_df["time_dt"] = pd.to_datetime((energy_df["time_hrs"]*3600).round(0), unit='s')
energy_df["cost"] = cost_forecaster.get_cost_for_time_range("actual", sim_start*3600, sim_start*3600, sim_end*3600, 15*60, True).data
energy_df["fossil_fuel"] = np.zeros(len(energy_df["time_hrs"]))

for data_name in ['demand', 'EV', 'solar', 'wind', 'nuclear']:
    energy_df[data_name] = cost_forecaster.get_data_for_time_range(data_name, "actual", sim_start*3600, sim_start*3600, sim_end*3600, 15*60, True)

energy_df["EV"] = energy_df["EV"]

energy_df['fossil_fuel'] = energy_df["demand"] + energy_df["EV"] - energy_df["solar"] - energy_df["wind"] - energy_df["nuclear"]
energy_df.loc[energy_df["fossil_fuel"] < 0, "fossil_fuel"] =  0.0

energy_df['de'] = energy_df["demand"] + energy_df["EV"]      
energy_df['nsw'] = energy_df["nuclear"]+energy_df["solar"]+energy_df["wind"]
energy_df['ns'] = energy_df["nuclear"]+energy_df["solar"]
energy_df['n'] = energy_df["nuclear"]

energy_df.loc[energy_df['nsw'] > energy_df['de'], 'nsw'] = energy_df['de']
energy_df.loc[energy_df['ns'] > energy_df['de'], 'ns'] = energy_df['de']
energy_df.loc[energy_df['n'] > energy_df['de'], 'n'] = energy_df['de']

fig, ax1 = plt.subplots(1, 1, figsize=figsize)

ax1.fill_between(energy_df["time_dt"], energy_df['de'], color='red', label = 'Fossil Fuel')
ax1.fill_between(energy_df["time_dt"], energy_df['nsw'], color='green', label = 'Wind' )
ax1.fill_between(energy_df["time_dt"], energy_df['ns'], color='orange', label = 'Solar' )
ax1.fill_between(energy_df["time_dt"], energy_df['n'], color='darkblue', label = 'Nuclear' )
ax1.plot(energy_df["time_dt"], energy_df['de'], color='black', linewidth = 2)
ax1.plot(energy_df["time_dt"], energy_df['nsw'], color='black', linewidth = 2)
ax1.plot(energy_df["time_dt"], energy_df['ns'], color='black', linewidth = 2)
ax1.plot(energy_df["time_dt"], energy_df['n'], color='black', linewidth = 2)

ax1.set_xlabel("Time | hrs", fontsize = fontsize, labelpad=30)
ax1.set_ylabel("Power | MW", fontsize = fontsize, labelpad=30)

ax1.set_xlim(energy_df["time_dt"].iloc[0], energy_df["time_dt"].iloc[-1])

if 'solar' in scenario:
    ax1.set_ylim(0, 2000)

elif 'wind' in scenario:
    ax1.set_ylim(0, 4000)

ax1.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))

ax1.legend(loc = 'upper left')

fig.suptitle("Energy Mix", fontsize = 20)

fig.tight_layout(rect=[0, 0.03, 1, 0.95])

fig.savefig('Energy_mix_full.png', dpi = 300)

fig, ax1 = plt.subplots(1, 1, figsize=figsize)

ax1.plot(energy_df["time_dt"], energy_df['cost'], color='black', label = 'Energy Cost', linewidth = 3)
ax1.set_xlim(energy_df["time_dt"].iloc[0], energy_df["time_dt"].iloc[-1])
ax1.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))

ax1.set_xlabel("Time | hrs", fontsize = fontsize, labelpad=30)
ax1.set_ylabel("Cost | $/kWh", fontsize = fontsize, labelpad=30)

ax1.legend()

fig.suptitle("Cost profile", fontsize = 20)

fig.tight_layout(rect=[0, 0.03, 1, 0.95])

fig.savefig('Cost_profile_full.png', dpi = 300)

#%%
#----------------------------------

for i in ["home", "work"]:
    for j in ["solar", "wind"]:
        for k in ["TOU", "dynamic", "dynamic_comm"]:

            data_to_look_at = {}
            
            data_to_look_at["solar"] = ["demand", "EV", "solar"]
            data_to_look_at["wind"] = ["demand", "EV", "wind"]
            
            scenario = "{}_{}_{}_100".format(i, j, k)
            
            cost_forecaster = TE_cost_forecaster_v3(os.path.join(input_folder, scenario, "TE_inputs"), ".", False)
            result_df = extract_power_profile_df(os.path.join(output_folder, scenario), sim_start, sim_end, 15/60)
            
            energy_df = pd.DataFrame()
            
            energy_df["time_hrs"] = np.arange(sim_start, sim_end, 0.25)
            energy_df["time_dt"] = pd.to_datetime((energy_df["time_hrs"]*3600).round(0), unit='s')
            energy_df['cost'] = cost_forecaster.get_cost_for_time_range("actual", sim_start*3600, sim_start*3600, sim_end*3600, 15*60, True).data
            energy_df["fossil_fuel"] = np.zeros(len(energy_df["time_hrs"]))
            
            
            for data_name in ['demand', 'EV', 'solar', 'wind', 'nuclear']:
                
                if 'solar' in scenario:
                    if data_name in data_to_look_at['solar']:
                        energy_df[data_name] = cost_forecaster.get_data_for_time_range(data_name, "actual", sim_start*3600, sim_start*3600, sim_end*3600, 15*60, True)
                        
                    else:
                        energy_df[data_name] = np.zeros(len(energy_df["time_hrs"]))
            
                elif 'wind' in scenario:
                    if data_name in data_to_look_at['wind']:
                        energy_df[data_name] = cost_forecaster.get_data_for_time_range(data_name, "actual", sim_start*3600, sim_start*3600, sim_end*3600, 15*60, True)
                    else:
                        energy_df[data_name] = np.zeros(len(energy_df["time_hrs"]))
            
            energy_df['fossil_fuel'] = energy_df["demand"] - energy_df["solar"] - energy_df["wind"] - energy_df["nuclear"]
            energy_df.loc[energy_df["fossil_fuel"] < 0, "fossil_fuel"] =  0.0
            
            energy_df['de'] = energy_df["demand"] + energy_df["EV"]*10    
            energy_df['deo'] = energy_df["demand"] +  result_df['total_demand_kW']*10 / 1000.0
            energy_df['d'] = energy_df["demand"]
            energy_df['nsw'] = energy_df["nuclear"]+energy_df["solar"]+energy_df["wind"]
            energy_df['ns'] = energy_df["nuclear"]+energy_df["solar"]
            energy_df['n'] = energy_df["nuclear"]
            
            energy_df.loc[energy_df['nsw'] > energy_df['d'], 'nsw'] = energy_df['d']
            energy_df.loc[energy_df['ns'] > energy_df['d'], 'ns'] = energy_df['d']
            energy_df.loc[energy_df['n'] > energy_df['d'], 'n'] = energy_df['d']
            
            fig, ax1 = plt.subplots(1, 1, figsize=figsize)
            
            ax1.fill_between(energy_df["time_dt"], energy_df['de'], color='blue', label = 'EV uncontrolled' , alpha = 0.5)
            ax1.fill_between(energy_df["time_dt"], energy_df['deo'], color='green', label = 'EV optimized' , alpha = 0.5)
            ax1.fill_between(energy_df["time_dt"], energy_df['d'], color='red', label = 'Fossil Fuel')
            ax1.fill_between(energy_df["time_dt"], energy_df['nsw'], color='green', label = 'Wind' )
            ax1.fill_between(energy_df["time_dt"], energy_df['ns'], color='orange', label = 'Solar' )
            ax1.fill_between(energy_df["time_dt"], energy_df['n'], color='darkblue', label = 'Nuclear' )
            ax1.plot(energy_df["time_dt"], energy_df['deo'], color='black', linewidth = 2)
            ax1.plot(energy_df["time_dt"], energy_df['de'], color='black', linewidth = 2)
            ax1.plot(energy_df["time_dt"], energy_df['d'], color='black', linewidth = 2)
            ax1.plot(energy_df["time_dt"], energy_df['nsw'], color='black', linewidth = 2)
            ax1.plot(energy_df["time_dt"], energy_df['ns'], color='black', linewidth = 2)
            ax1.plot(energy_df["time_dt"], energy_df['n'], color='black', linewidth = 2)
            
            ax1.set_xlabel("Time | hrs", fontsize = fontsize, labelpad=30)
            ax1.set_ylabel("Power | MW", fontsize = fontsize, labelpad=30)
            
            ax1.set_xlim(energy_df["time_dt"].iloc[0], energy_df["time_dt"].iloc[-1])
            
            if 'solar' in scenario:
                ax1.set_ylim(0, 400)
            
            elif 'wind' in scenario:
                ax1.set_ylim(0, 600)
            
            ax1.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))
            
            ax1.legend(loc = 'upper left')
            
            ax2 = ax1.twinx()
            
            ax2.plot(energy_df["time_dt"], energy_df['cost'], color='blue', label = 'Energy Cost', linewidth = 3, linestyle = 'dashed')
            
            ax2.set_ylabel("Energy Cost | $/kWh", fontsize = fontsize, labelpad=30)
            
            ax2.set_ylim(0, 0.10)
            ax2.legend(loc = 'upper right')
            
            fig.suptitle(scenario, fontsize = 20)
            
            fig.tight_layout(rect=[0, 0.03, 1, 0.95])
            
            fig.savefig(scenario, dpi = 300)


#%%

for i in ["home", "work"]:
    for j in ["full"]:
        for k in ["TOU", "dynamic", "dynamic_comm"]:

            data_to_look_at = {}
            
            data_to_look_at["solar"] = ["demand", "EV", "solar"]
            data_to_look_at["wind"] = ["demand", "EV", "wind"]
            
            scenario = "{}_{}_{}_100".format(i, j, k)
            
            cost_forecaster = TE_cost_forecaster_v3(os.path.join(input_folder, scenario, "TE_inputs"), ".", False)
            result_df = extract_power_profile_df(os.path.join(output_folder, scenario), sim_start, sim_end, 15/60)
            
            energy_df = pd.DataFrame()
            
            energy_df["time_hrs"] = np.arange(sim_start, sim_end, 0.25)
            energy_df["time_dt"] = pd.to_datetime((energy_df["time_hrs"]*3600).round(0), unit='s')
            energy_df['cost'] = cost_forecaster.get_cost_for_time_range("actual", sim_start*3600, sim_start*3600, sim_end*3600, 15*60, True).data
            energy_df["fossil_fuel"] = np.zeros(len(energy_df["time_hrs"]))
            
            
            for data_name in ['demand', 'EV', 'solar', 'wind', 'nuclear']:
                
                if 'solar' in scenario:
                    if data_name in data_to_look_at['solar']:
                        energy_df[data_name] = cost_forecaster.get_data_for_time_range(data_name, "actual", sim_start*3600, sim_start*3600, sim_end*3600, 15*60, True)
                        
                    else:
                        energy_df[data_name] = np.zeros(len(energy_df["time_hrs"]))
            
                elif 'wind' in scenario:
                    if data_name in data_to_look_at['wind']:
                        energy_df[data_name] = cost_forecaster.get_data_for_time_range(data_name, "actual", sim_start*3600, sim_start*3600, sim_end*3600, 15*60, True)
                    else:
                        energy_df[data_name] = np.zeros(len(energy_df["time_hrs"]))
                
                else:
                    energy_df[data_name] = cost_forecaster.get_data_for_time_range(data_name, "actual", sim_start*3600, sim_start*3600, sim_end*3600, 15*60, True)
            
            energy_df['fossil_fuel'] = energy_df["demand"] - energy_df["solar"] - energy_df["wind"] - energy_df["nuclear"]
            energy_df.loc[energy_df["fossil_fuel"] < 0, "fossil_fuel"] =  0.0
            
            energy_df['de'] = energy_df["demand"] + energy_df["EV"]*10    
            energy_df['deo'] = energy_df["demand"] +  result_df['total_demand_kW']*10 / 1000.0
            energy_df['d'] = energy_df["demand"]
            energy_df['nsw'] = energy_df["nuclear"]+energy_df["solar"]+energy_df["wind"]
            energy_df['ns'] = energy_df["nuclear"]+energy_df["solar"]
            energy_df['n'] = energy_df["nuclear"]
            
            energy_df.loc[energy_df['nsw'] > energy_df['d'], 'nsw'] = energy_df['d']
            energy_df.loc[energy_df['ns'] > energy_df['d'], 'ns'] = energy_df['d']
            energy_df.loc[energy_df['n'] > energy_df['d'], 'n'] = energy_df['d']
            
            fig, ax1 = plt.subplots(1, 1, figsize=figsize)
            
            ax1.fill_between(energy_df["time_dt"], energy_df['de'], color='blue', label = 'EV uncontrolled' , alpha = 0.5)
            ax1.fill_between(energy_df["time_dt"], energy_df['deo'], color='green', label = 'EV optimized' , alpha = 0.5)
            ax1.fill_between(energy_df["time_dt"], energy_df['d'], color='red', label = 'Fossil Fuel')
            ax1.fill_between(energy_df["time_dt"], energy_df['nsw'], color='green', label = 'Wind' )
            ax1.fill_between(energy_df["time_dt"], energy_df['ns'], color='orange', label = 'Solar' )
            ax1.fill_between(energy_df["time_dt"], energy_df['n'], color='darkblue', label = 'Nuclear' )
            ax1.plot(energy_df["time_dt"], energy_df['deo'], color='black', linewidth = 2)
            ax1.plot(energy_df["time_dt"], energy_df['de'], color='black', linewidth = 2)
            ax1.plot(energy_df["time_dt"], energy_df['d'], color='black', linewidth = 2)
            ax1.plot(energy_df["time_dt"], energy_df['nsw'], color='black', linewidth = 2)
            ax1.plot(energy_df["time_dt"], energy_df['ns'], color='black', linewidth = 2)
            ax1.plot(energy_df["time_dt"], energy_df['n'], color='black', linewidth = 2)
            
            ax1.set_xlabel("Time | hrs", fontsize = fontsize, labelpad=30)
            ax1.set_ylabel("Power | MW", fontsize = fontsize, labelpad=30)
            
            ax1.set_xlim(energy_df["time_dt"].iloc[0], energy_df["time_dt"].iloc[-1])
            
            if 'solar' in scenario:
                ax1.set_ylim(0, 400)
            
            elif 'wind' in scenario:
                ax1.set_ylim(0, 600)
                
            else:
                ax1.set_ylim(0, 500)
            
            ax1.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))
            
            ax1.legend(loc = 'upper left')
            
            ax2 = ax1.twinx()
            
            ax2.plot(energy_df["time_dt"], energy_df['cost'], color='blue', label = 'Energy Cost', linewidth = 3, linestyle = 'dashed')
            
            ax2.set_ylabel("Energy Cost | $/kWh", fontsize = fontsize, labelpad=30)
            
            ax2.set_ylim(0, 0.10)
            ax2.legend(loc = 'upper right')
            
            fig.suptitle(scenario, fontsize = 20)
            
            fig.tight_layout(rect=[0, 0.03, 1, 0.95])
            
            fig.savefig(scenario, dpi = 300)


#%%

#----------------------------------


cost_forecaster_home = TE_cost_forecaster_v3(os.path.join(input_folder, "home_uncontrolled", "TE_inputs"), ".", False)
cost_forecaster_work = TE_cost_forecaster_v3(os.path.join(input_folder, "work_uncontrolled", "TE_inputs"), ".", False)

uncontrolled_df_home = extract_power_profile_df(os.path.join(output_folder, "home_uncontrolled"), sim_start, sim_end)
uncontrolled_df_work = extract_power_profile_df(os.path.join(output_folder, "work_uncontrolled"), sim_start, sim_end)

#cost_forecaster_home.replace_EV_charging_demand(np.array(uncontrolled_df_home[profile])/1000.0, sim_start)
#cost_forecaster_work.replace_EV_charging_demand(np.array(uncontrolled_df_work[profile])/1000.0, sim_start)


forecasted_cost_arr_home = []
actual_cost_arr_home = []
forecasted_cost_arr_work = []
actual_cost_arr_work = []

for i in range(sim_start-6, sim_end+24-6, 24):
    
    forecasted_cost_arr_home.extend(cost_forecaster_home.get_cost_for_time_range(
                "forecasted", i*3600, i*3600, (i+24)*3600, 15*60, True).data)
    
    actual_cost_arr_home.extend(cost_forecaster_home.get_cost_for_time_range(
                "actual", i*3600, i*3600, (i+24)*3600, 15*60, True).data)

    forecasted_cost_arr_work.extend(cost_forecaster_work.get_cost_for_time_range(
                "forecasted", i*3600, i*3600, (i+24)*3600, 15*60, True).data)
    
    actual_cost_arr_work.extend(cost_forecaster_work.get_cost_for_time_range(
                "actual", i*3600, i*3600, (i+24)*3600, 15*60, True).data)

cost_df = pd.DataFrame()
cost_df["time_hrs"] = np.arange(sim_start-6, sim_end+24-6, 0.25)
cost_df["time_dt"] = pd.to_datetime((cost_df["time_hrs"]*3600).round(0), unit='s')
cost_df["forecasted_cost_home"] = forecasted_cost_arr_home
cost_df["actual_cost_home"] = actual_cost_arr_home
cost_df["forecasted_cost_work"] = forecasted_cost_arr_work
cost_df["actual_cost_work"] = actual_cost_arr_work


#----------------------------------

#This is only for Home
energy_df = pd.DataFrame()

energy_df["time_hrs"] = np.arange(sim_start, sim_end, 0.25)
energy_df["time_dt"] = pd.to_datetime((energy_df["time_hrs"]*3600).round(0), unit='s')
energy_df["demand"] = cost_forecaster_home.get_data_for_time_range("demand", "actual", sim_start*3600, sim_start*3600, sim_end*3600, 15*60, True)
#energy_df["EV_home"] = cost_forecaster_home.get_data_for_time_range("EV", "actual", sim_start*3600, sim_start*3600, sim_end*3600, 15*60, True)
#energy_df["EV_work"] = cost_forecaster_work.get_data_for_time_range("EV", "actual", sim_start*3600, sim_start*3600, sim_end*3600, 15*60, True)
energy_df["solar"] = cost_forecaster_home.get_data_for_time_range("solar", "actual", sim_start*3600, sim_start*3600, sim_end*3600, 15*60, True)
energy_df["wind"] = cost_forecaster_home.get_data_for_time_range("wind", "actual", sim_start*3600, sim_start*3600, sim_end*3600, 15*60, True)
energy_df["nuclear"] = cost_forecaster_home.get_data_for_time_range("nuclear", "actual", sim_start*3600, sim_start*3600, sim_end*3600, 15*60, True)
energy_df["fossil_fuel"] = energy_df["demand"] - energy_df["solar"] - energy_df["wind"] - energy_df["nuclear"]# + energy_df["EV_home"] + energy_df["EV_work"]
energy_df.loc[energy_df["fossil_fuel"] < 0, "fossil_fuel"] =  0.0
energy_df["cost"] = cost_forecaster_home.get_cost_for_time_range("actual", sim_start*3600, sim_start*3600, sim_end*3600, 15*60, True).data

energy_df['de'] = energy_df["demand"]# + energy_df["EV_home"] + energy_df["EV_work"]
energy_df['nsw'] = energy_df["nuclear"]+energy_df["solar"]+energy_df["wind"]
energy_df['ns'] = energy_df["nuclear"]+energy_df["solar"]
energy_df['n'] = energy_df["nuclear"]

energy_df.loc[energy_df['nsw'] > energy_df['de'], 'nsw'] = energy_df['de']
energy_df.loc[energy_df['ns'] > energy_df['de'], 'ns'] = energy_df['de']
energy_df.loc[energy_df['n'] > energy_df['de'], 'n'] = energy_df['de']


fig, ax1 = plt.subplots(1, 1, figsize=figsize)

ax1.fill_between(energy_df["time_dt"], energy_df['de'], color='red', label = 'Fossil Fuel')
ax1.fill_between(energy_df["time_dt"], energy_df['nsw'], color='green', label = 'Wind' )
ax1.fill_between(energy_df["time_dt"], energy_df['ns'], color='orange', label = 'Solar' )
ax1.fill_between(energy_df["time_dt"], energy_df['n'], color='darkblue', label = 'Nuclear' )
ax1.plot(energy_df["time_dt"], energy_df['de'], color='black', linewidth = 2)
ax1.plot(energy_df["time_dt"], energy_df['nsw'], color='black', linewidth = 2)
ax1.plot(energy_df["time_dt"], energy_df['ns'], color='black', linewidth = 2)
ax1.plot(energy_df["time_dt"], energy_df['n'], color='black', linewidth = 2)

ax1.set_xlabel("Time | hrs", fontsize = fontsize, labelpad=30)
ax1.set_ylabel("Power | MW", fontsize = fontsize, labelpad=30)

ax1.set_xlim(energy_df["time_dt"].iloc[0], energy_df["time_dt"].iloc[-1])
ax1.set_ylim(0, 6000)

ax1.xaxis.set_major_locator(mdates.HourLocator(interval = 24))
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))

ax1.legend(loc = 'upper left')

ax2 = ax1.twinx()

ax2.plot(energy_df["time_dt"], energy_df['cost'], color='blue', label = 'Energy Cost', linewidth = 3, linestyle = 'dashed')

ax2.set_ylabel("Energy Cost | $/kWh", fontsize = fontsize, labelpad=30)

ax2.set_ylim(0, 0.20)
ax2.legend(loc = 'upper right')

fig.suptitle("Energy Mix", fontsize = 20)

fig.tight_layout(rect=[0, 0.03, 1, 0.95])

fig.savefig('Energy_mix.png', dpi = 300)


#%%

#----------------------------------

for scenario in ["home", "work"]:
    
    if scenario == "home":
        start = home_start
        end = home_end
        start_dt = home_start_dt
        end_dt = home_end_dt
        forecast_cost = "forecasted_cost_home"
        actual_cost = "actual_cost_home"
        
    else:
        start = work_start
        end = work_end
        start_dt = work_start_dt
        end_dt = work_end_dt
        forecast_cost = "forecasted_cost_work"
        actual_cost = "actual_cost_work"
        
        
    uncontrolled_df = extract_power_profile_df(os.path.join(output_folder, "{}_uncontrolled".format(scenario)), start, end)
    TOU_df = extract_power_profile_df(os.path.join(output_folder, "{}_TOU_100".format(scenario)), start, end)
    dynamic_df = extract_power_profile_df(os.path.join(output_folder, "{}_dynamic_100".format(scenario)), start, end)
    dynamic_comm_df = extract_power_profile_df(os.path.join(output_folder, "{}_dynamic_comm_100".format(scenario)), start, end)
    
    mask1 = (cost_df["time_hrs"] >= start)
    mask2 = (cost_df["time_hrs"] < end)
    
    sub_cost_df = cost_df.loc[mask1 & mask2, :]
    
    '''
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize)
    
    ax1.plot(sub_cost_df["time_dt"], sub_cost_df["forecasted_cost"], label = "Forecast")
    ax1.plot(sub_cost_df["time_dt"], sub_cost_df["actual_cost"], label = "Actual")
    
    ax1.set_xlabel("Time | hrs")
    ax1.set_ylabel("Cost | $/kWh")
    
    ax1.set_xlim(start_dt, end_dt)
    
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))
    
    ax1.legend()
    
    ax1.grid(True)
    
    ax2.plot(uncontrolled_df["sim_time"], uncontrolled_df["total_demand_kW"], label = "uncontrolled")
    ax2.plot(dynamic_df["sim_time"], dynamic_df["total_demand_kW"], label = "dynamic")
    ax2.plot(dynamic_comm_df["sim_time"], dynamic_comm_df["total_demand_kW"], label = "dynamic comm")
    
    ax2.set_xlabel("Time | hrs")
    ax2.set_ylabel("Power | kW")
    
    ax2.set_xlim(start_dt, end_dt)
    ax2.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))
    
    ax2.legend()
    
    ax2.grid(True)
    '''
    #------------------------------------
    
    
    fig, ax1 = plt.subplots(1, 1, figsize=figsize)
    
    ax1.plot(uncontrolled_df["sim_time"], uncontrolled_df["total_demand_kW"], label = "uncontrolled", color = 'red')
    ax1.plot(TOU_df["sim_time"], TOU_df["total_demand_kW"], label = "TOU random", color = 'orange')
    ax1.plot(dynamic_df["sim_time"], dynamic_df["total_demand_kW"], label = "dynamic", color = 'blue')
    ax1.plot(dynamic_comm_df["sim_time"], dynamic_comm_df["total_demand_kW"], label = "dynamic comm", color = 'green')
    
    ax1.set_xlabel("Time | hrs", fontsize = fontsize, labelpad=30)
    ax1.set_ylabel("Power | kW", fontsize = fontsize, labelpad=30)
    
    ax1.set_xlim(start_dt, end_dt)
    
    if "100k" in output_folder:
        ax1.set_ylim(0, 250000)
        ax1.set_yticks(np.linspace(0, 250000, 11))
        
    else:
        ax1.set_ylim(0, 40000)
        ax1.set_yticks(np.linspace(0, 40000, 11))
        
        
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))
    
    ax1.legend(loc = 2)
    ax1.grid(True)
    
    ax2 = ax1.twinx()
    
    ax2.plot(sub_cost_df["time_dt"], sub_cost_df[forecast_cost], label = "cost", color = 'black', linestyle = "dashed")
    
    ax2.set_ylabel("Cost | $/kWh", fontsize = fontsize, labelpad=30)
    
    ax2.set_xlim(start_dt, end_dt)
    ax2.set_ylim(0, 0.20)
    ax2.set_yticks(np.linspace(0, 0.20, 11))
    
    ax2.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))
    
    ax2.legend(loc = 1)
    ax2.grid(True)
    
    fig.suptitle("EV charging load: {}".format(scenario.capitalize()), fontsize = 20)

    fig.tight_layout(rect=[0, 0.03, 1, 0.95])

    fig.savefig('{}.png'.format(scenario.capitalize()), dpi = 300)


#%%
uncontrolled_df = extract_power_profile_df(os.path.join(output_folder, "work_uncontrolled"))
dynamic_df = extract_power_profile_df(os.path.join(output_folder, "work_dynamic_100"))
dynamic_comm_df = extract_power_profile_df(os.path.join(output_folder, "work_dynamic_comm_100"))
                 

mask1 = (uncontrolled_df["simulation_time_hrs"] >= home_start)
mask2 = (uncontrolled_df["simulation_time_hrs"] < home_end)
uncontrolled_df = uncontrolled_df.loc[mask1 & mask2, :]

mask1 = (dynamic_df["simulation_time_hrs"] >= home_start)
mask2 = (dynamic_df["simulation_time_hrs"] < home_end)
dynamic_df = dynamic_df.loc[mask1 & mask2, :]

mask1 = (dynamic_comm_df["simulation_time_hrs"] >= home_start)
mask2 = (dynamic_comm_df["simulation_time_hrs"] < home_end)
dynamic_comm_df = dynamic_comm_df.loc[mask1 & mask2, :]


fig, (ax3, ax4) = plt.subplots(2, 1, figsize=figsize)

ax3.plot(work_cost_df["time_dt"], work_cost_df["forecasted_cost"], label = "Forecast")
ax3.plot(work_cost_df["time_dt"], work_cost_df["actual_cost"], label = "Actual")

ax3.set_xlabel("Time | hrs")
ax3.set_ylabel("Cost | $/kWh")

ax3.set_xlim(work_time[0], work_time[-1])

ax3.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))

ax3.legend()

ax3.grid(True)


ax4.plot(uncontrolled_df["sim_time"], uncontrolled_df["total_demand_kW"], label = "uncontrolled")
ax4.plot(dynamic_df["sim_time"], dynamic_df["total_demand_kW"], label = "dynamic")
ax4.plot(dynamic_comm_df["sim_time"], dynamic_comm_df["total_demand_kW"], label = "dynamic comm")

ax4.set_xlabel("Time | hrs")
ax4.set_ylabel("Power | kW")

ax4.set_xlim(uncontrolled_df["sim_time"].iloc[0], uncontrolled_df["sim_time"].iloc[-1])
ax4.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
ax4.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))

ax4.legend()

ax4.grid(True)

#%%

home_time = pd.to_datetime((np.arange(home_start, home_end, 0.25)*3600).round(0), unit='s')
work_time = pd.to_datetime((np.arange(work_start, work_end, 0.25)*3600).round(0), unit='s')

#----------------------------------

# Cost Forecaster

cost_forecaster = TE_cost_forecaster_v3(os.path.join(output_folder, "home_dynamic_100", "TE_inputs"), ".", False)

'''
home_forecast = []
home_actual = []

for time_hrs in np.arange(home_start, home_end, 0.25):
    home_forecast.append(cost_forecaster.get_forecasted_cost_at_time_sec(time_hrs*3600, 0.25*3600))
    home_actual.append(cost_forecaster.get_actual_cost_at_time_sec(time_hrs*3600, 0.25*3600))

work_forecast = []
work_actual = []

for time_hrs in np.arange(work_start, work_end, 0.25):
    work_forecast.append(cost_forecaster.get_forecasted_cost_at_time_sec(time_hrs*3600, 0.25*3600))
    work_actual.append(cost_forecaster.get_actual_cost_at_time_sec(time_hrs*3600, 0.25*3600))
'''
#----------------------------------

# Home Charging Dynamic Control

location = "home"
control = "dynamic"

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize)

ax1.step(home_time, home_forecast, label = "forecast $/kWh", color = "brown", where = 'post' )
ax1.step(home_time, home_actual, label = "actual $/kWh", color = "black", where = 'post' )

ax1.set_xlim(home_time[0], home_time[-1])
ax1.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))

ax1.set_ylim([0.05, 0.25])
ax1.set_yticks(np.arange(0.05, 0.26, 0.01))
ax1.set_ylabel('Cost | $/kWh', labelpad=30)

ax1.grid(True)
ax1.legend()

for i, val in enumerate(scenario_range):
    scenario = "{}_{}_{}".format(location, control, val)
    df = extract_power_profile_df(os.path.join(output_folder, scenario))
    df_sub = df[(df["simulation_time_hrs"] >= home_start) & (df["simulation_time_hrs"] < home_end)]
    ax2.plot(df_sub["sim_time"], df_sub[profile], label = scenario, color = colors[i])

ax2.set_xlim(df_sub["sim_time"].iloc[0], df_sub["sim_time"].iloc[-1])
ax2.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))

ax2.set_xlabel('Time | hrs', labelpad=30)
ax2.set_ylabel('Power | kW', labelpad=30)

ax2.grid(True)
ax2.legend()

fig.tight_layout(rect=[0, 0.03, 1, 0.95])
fig.suptitle("{} Charging {} Control".format(location, control).title())

#os.makedirs(power_profiles_figures_folder, exist_ok = True)
fig.savefig( os.path.join(figures_folder, "{}_{}.png".format(location, control)), dpi = 300)

#----------------------------------

# Work Charging Dynamic Control

location = "work"
control = "dynamic"

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize)

ax1.step(work_time, work_forecast, label = "forecast $/kWh", color = "brown", where = 'post' )
ax1.step(work_time, work_actual, label = "actual $/kWh", color = "black", where = 'post' )

#+ pd.Timedelta(days=1)
ax1.set_xlim(work_time[0], work_time[-1])
ax1.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))

ax1.set_ylim([0.05, 0.25])
ax1.set_yticks(np.arange(0.05, 0.26, 0.01))
ax1.set_ylabel('Cost | $/kWh', labelpad=30)

ax1.grid(True)
ax1.legend()

for i, val in enumerate(scenario_range):
    scenario = "{}_{}_{}".format(location, control, val)
    df = extract_power_profile_df(os.path.join(output_folder, scenario))
    df_sub = df[(df["simulation_time_hrs"] >= work_start) & (df["simulation_time_hrs"] < work_end)]
    ax2.plot(df_sub["sim_time"], df_sub[profile], label = scenario, color = colors[i])

ax2.set_xlim(df_sub["sim_time"].iloc[0], df_sub["sim_time"].iloc[-1])
ax2.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))

ax2.set_xlabel('Time | hrs', labelpad=30)
ax2.set_ylabel('Power | kW', labelpad=30)

ax2.grid(True)
ax2.legend()

fig.tight_layout(rect=[0, 0.03, 1, 0.95])
fig.suptitle("{} Charging {} Control".format(location, control).title())

#os.makedirs(power_profiles_figures_folder, exist_ok = True)
fig.savefig( os.path.join(figures_folder, "{}_{}.png".format(location, control)), dpi = 300)

#----------------------------------

# Home Charging TOU Control

location = "home"
control = "TOU"

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize)

ax1.step(home_time, home_forecast, label = "forecast $/kWh", color = "brown", where = 'post' )
ax1.step(home_time, home_actual, label = "actual $/kWh", color = "black", where = 'post' )

ax1.set_xlim(home_time[0], home_time[-1])
ax1.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))

ax1.set_ylim([0.05, 0.25])
ax1.set_yticks(np.arange(0.05, 0.26, 0.01))
ax1.set_ylabel('Cost | $/kWh', labelpad=30)

ax1.grid(True)
ax1.legend()

for i, val in enumerate(scenario_range):
    scenario = "{}_{}_{}".format(location, control, val)
    df = extract_power_profile_df(os.path.join(output_folder, scenario))
    df_sub = df[(df["simulation_time_hrs"] >= home_start) & (df["simulation_time_hrs"] < home_end)]
    ax2.plot(df_sub["sim_time"], df_sub[profile], label = scenario, color = colors[i])

ax2.set_xlim(df_sub["sim_time"].iloc[0], df_sub["sim_time"].iloc[-1])
ax2.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))

ax2.set_xlabel('Time | hrs', labelpad=30)
ax2.set_ylabel('Power | kW', labelpad=30)

ax2.grid(True)
ax2.legend()

fig.tight_layout(rect=[0, 0.03, 1, 0.95])
fig.suptitle("{} Charging {} Control".format(location, control).title())

#os.makedirs(power_profiles_figures_folder, exist_ok = True)
fig.savefig( os.path.join(figures_folder, "{}_{}.png".format(location, control)), dpi = 300)

#----------------------------------

# Work Charging TOU Control

location = "work"
control = "TOU"

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize)

ax1.step(work_time, work_forecast, label = "forecast $/kWh", color = "brown", where = 'post' )
ax1.step(work_time, work_actual, label = "actual $/kWh", color = "black", where = 'post' )

#+ pd.Timedelta(days=1)
ax1.set_xlim(work_time[0], work_time[-1])
ax1.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))

ax1.set_ylim([0.05, 0.25])
ax1.set_yticks(np.arange(0.05, 0.26, 0.01))
ax1.set_ylabel('Cost | $/kWh', labelpad=30)

ax1.grid(True)
ax1.legend()

for i, val in enumerate(scenario_range):
    scenario = "{}_{}_{}".format(location, control, val)
    df = extract_power_profile_df(os.path.join(output_folder, scenario))
    df_sub = df[(df["simulation_time_hrs"] >= work_start) & (df["simulation_time_hrs"] < work_end)]
    ax2.plot(df_sub["sim_time"], df_sub[profile], label = scenario, color = colors[i])

ax2.set_xlim(df_sub["sim_time"].iloc[0], df_sub["sim_time"].iloc[-1])
ax2.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))

ax2.set_xlabel('Time | hrs', labelpad=30)
ax2.set_ylabel('Power | kW', labelpad=30)

ax2.grid(True)
ax2.legend()

fig.tight_layout(rect=[0, 0.03, 1, 0.95])
fig.suptitle("{} Charging {} Control".format(location, control).title())

#os.makedirs(power_profiles_figures_folder, exist_ok = True)
fig.savefig( os.path.join(figures_folder, "{}_{}.png".format(location, control)), dpi = 300)