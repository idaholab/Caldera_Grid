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

def extract_power_profile_df(folder : str):
    
    df = pd.read_csv(os.path.join(folder, "real_power_profiles.csv"))
    df["sim_time"] = pd.to_datetime((df["simulation_time_hrs"]*3600).round(0), unit='s')

    return df

#----------------------------------

output_folder = os.path.join(path_to_here, "outputs")
figures_folder = os.path.join(path_to_here, "figures")

sim_start = 168
sim_end = 288

home_start = 204
home_end = 252

work_start = 216
work_end = 264

profile = "total_demand_kW"

offset = 204

figsize = (18, 9)

scenario_range = np.arange(0, 101, 25)

colors = ['red', 'orangered', 'goldenrod', 'olivedrab', 'seagreen', 'darkgreen']

home_time = pd.to_datetime((np.arange(home_start, home_end, 0.25)*3600).round(0), unit='s')
work_time = pd.to_datetime((np.arange(work_start, work_end, 0.25)*3600).round(0), unit='s')

#----------------------------------

# Cost Forecaster

cost_forecaster = TE_cost_forecaster_v3(os.path.join("TE_profiles", "base_inputs_folder", "TE_inputs"), ".", False)

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

#----------------------------------

# Home Charging

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
    scenario = "home_dynamic_{}".format(val)
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
fig.suptitle("Home Charging")

#os.makedirs(power_profiles_figures_folder, exist_ok = True)
fig.savefig( os.path.join(figures_folder, "home.png"), dpi = 300)

#----------------------------------

# Work Charging

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
    scenario = "work_dynamic_{}".format(val)
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
fig.suptitle("Work Charging")

#os.makedirs(power_profiles_figures_folder, exist_ok = True)
fig.savefig( os.path.join(figures_folder, "work.png"), dpi = 300)