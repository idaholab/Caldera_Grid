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

def extract_power_profile_df(folder : str, start = None, end = None):
    
    df = pd.read_csv(os.path.join(folder, "real_power_profiles.csv"))
    df["sim_time"] = pd.to_datetime((df["simulation_time_hrs"]*3600).round(0), unit='s')
    
    if start != None and end != None:
        mask1 = (df["simulation_time_hrs"] >= start)
        mask2 = (df["simulation_time_hrs"] < end)
        df = df.loc[mask1 & mask2, :]

    return df

#----------------------------------

input_folder = os.path.join(path_to_here, "inputs")
output_folder = os.path.join(path_to_here, "outputs")
figures_folder = os.path.join(path_to_here, "figures")

sim_start = 168
sim_end = 288

home_start = sim_start + 12 + 24
home_end = sim_end - 12 - 24

work_start = sim_start + 48
work_end = sim_end - 24

home_start_dt = pd.to_datetime(home_start*3600, unit ='s')
home_end_dt = pd.to_datetime(home_end*3600, unit ='s')

work_start_dt = pd.to_datetime(work_start*3600, unit ='s')
work_end_dt = pd.to_datetime(work_end*3600, unit ='s')

profile = "total_demand_kW"
offset = 204
figsize = (18, 9)
scenario_range = np.arange(0, 101, 25)

colors = ['red', 'orangered', 'goldenrod', 'olivedrab', 'seagreen', 'darkgreen']

#----------------------------------

cost_forecaster = TE_cost_forecaster_v3(os.path.join(input_folder, "home_uncontrolled", "TE_inputs"), ".", False)

forecasted_cost_arr = []
actual_cost_arr = []
for i in range(sim_start-6, sim_end+24-6, 24):
    
    forecasted_cost_arr.extend(cost_forecaster.get_cost_for_time_range(
                "forecasted", i*3600, i*3600, (i+24)*3600, 15*60, True).data)
    
    actual_cost_arr.extend(cost_forecaster.get_cost_for_time_range(
                "actual", i*3600, i*3600, (i+24)*3600, 15*60, True).data)

cost_df = pd.DataFrame()
cost_df["time_hrs"] = np.arange(sim_start-6, sim_end+24-6, 0.25)
cost_df["time_dt"] = pd.to_datetime((cost_df["time_hrs"]*3600).round(0), unit='s')
cost_df["forecasted_cost"] = forecasted_cost_arr
cost_df["actual_cost"] = actual_cost_arr

#----------------------------------

for scenario in ["home", "work"]:
    
    if scenario == "home":
        start = home_start
        end = home_end
        start_dt = home_start_dt
        end_dt = home_end_dt
    else:
        start = work_start
        end = work_end
        start_dt = work_start_dt
        end_dt = work_end_dt
        
    uncontrolled_df = extract_power_profile_df(os.path.join(output_folder, "{}_uncontrolled".format(scenario)), start, end)
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
    ax1.plot(dynamic_df["sim_time"], dynamic_df["total_demand_kW"], label = "dynamic", color = 'blue')
    ax1.plot(dynamic_comm_df["sim_time"], dynamic_comm_df["total_demand_kW"], label = "dynamic comm", color = 'green')
    
    ax1.set_xlabel("Time | hrs")
    ax1.set_ylabel("Power | kW")
    
    ax1.set_xlim(start_dt, end_dt)
    ax1.set_ylim(0, 40000)
    ax1.set_yticks(np.linspace(0, 40000, 11))
    
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))
    
    ax1.legend(loc = 2)
    ax1.grid(True)
    
    ax2 = ax1.twinx()
    
    ax2.plot(sub_cost_df["time_dt"], sub_cost_df["forecasted_cost"], label = "cost", color = 'black', linestyle = "dashed")
    
    ax2.set_xlabel("Time | hrs")
    ax2.set_ylabel("Cost | $/kWh")
    
    ax2.set_xlim(start_dt, end_dt)
    ax2.set_ylim(0, 0.20)
    ax2.set_yticks(np.linspace(0, 0.20, 11))
    
    ax2.xaxis.set_major_locator(mdates.HourLocator(interval = 6))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))
    
    ax2.legend(loc = 1)
    ax2.grid(True)

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