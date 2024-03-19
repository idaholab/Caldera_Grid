# -*- coding: utf-8 -*-
"""
Created on Tue Feb 20 13:46:41 2024

@author: CEBOM
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob
import sys

path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))

output_folder = os.path.join(path_to_here, "outputs")
figures_folder = os.path.join(path_to_here, "figures")
power_profiles_figures_folder = os.path.join(figures_folder, "power_profiles_plots")

profile = "total_demand_kW"

def extract_df(folder : str):
    
    data_folder = os.path.join(output_folder, folder)
    df = pd.read_csv(os.path.join(data_folder, "real_power_profiles.csv"))

    df = df[(df["simulation_time_hrs"] >= 24) & (df["simulation_time_hrs"] < 48)]
    df["simulation_time_hrs"] = df["simulation_time_hrs"] % 24.0

    return df

#-----------------------------------
# Solar profiles
#-----------------------------------

# Handled in input_generation.py

#-----------------------------------
# Uncontrolled
#-----------------------------------

x_lims = (0, 24)
x_ticks = np.linspace(x_lims[0], x_lims[1], 13)

y_lims = (0, 1000)
y_ticks = np.linspace(y_lims[0], y_lims[1], 11)

df_u = extract_df("uncontrolled")

timestep_hrs = df_u["simulation_time_hrs"].iloc[1] - df_u["simulation_time_hrs"].iloc[0]
E_uncon = df_u[profile].sum()*timestep_hrs/3600
print("Total Energy uncontrolled: {}".format(E_uncon))

if True:
    fig, ax1 = plt.subplots(1, 1, figsize = (18, 14))
    ax1.plot(df_u["simulation_time_hrs"], df_u[profile], label = "uncontrolled", color = "red")
    ax1.set_title("Uncontrolled power profile")
    ax1.set_xticks(x_ticks)
    ax1.set_yticks(y_ticks)
    ax1.set_xlim(x_lims[0], x_lims[1])
    ax1.set_ylim(y_lims[0], y_lims[1])
    ax1.set_xlabel('Simulation Time | hrs', labelpad=30)
    ax1.set_ylabel('Power | kW', labelpad=30)
    ax1.grid()

    ax2 = ax1.twinx()
    ax2.plot([], [], label = "")
    ax2.set_ylabel(' ', labelpad=30)
    ax2.set_yticks([-10, 10])
    ax2.set_ylim(0, 1)
        
    fig.legend()
    fig.tight_layout()
    fig_file_name = "uncontrolled.png"

    os.makedirs(power_profiles_figures_folder, exist_ok = True)
    fig.savefig( os.path.join(power_profiles_figures_folder, fig_file_name), dpi = 300)

#-----------------------------------
# Time of Use
#-----------------------------------

df_tou = extract_df("time_of_use")

timestep_hrs = df_tou["simulation_time_hrs"].iloc[1] - df_tou["simulation_time_hrs"].iloc[0]
E_tou = df_tou[profile].sum()*timestep_hrs/3600
print("Total Energy time_of_use: {}".format(E_tou))

if True:
    fig, ax1 = plt.subplots(1, 1, figsize = (18, 14))
    ax1.plot(df_u["simulation_time_hrs"], df_u[profile], label = "uncontrolled", color = "red")
    ax1.plot(df_tou["simulation_time_hrs"], df_tou[profile], label = "time_of_use", color = "orange")
    ax1.set_title("Time of use power profile")
    ax1.set_xticks(x_ticks)
    ax1.set_yticks(y_ticks)
    ax1.set_xlim(x_lims[0], x_lims[1])
    ax1.set_ylim(y_lims[0], y_lims[1])
    ax1.set_xlabel('Simulation Time | hrs', labelpad=30)
    ax1.set_ylabel('Power | kW', labelpad=30)
    ax1.grid()

    ax2 = ax1.twinx()
    ax2.plot([], [], label = "")
    ax2.set_ylabel(' ', labelpad=30)
    ax2.set_yticks([-10, 10])
    ax2.set_ylim(0, 1)
    
    fig.legend()
    fig.tight_layout()
    fig_file_name = "time_of_use.png"

    os.makedirs(power_profiles_figures_folder, exist_ok = True)
    fig.savefig( os.path.join(power_profiles_figures_folder, fig_file_name), dpi = 300)


#-----------------------------------
# Good Forecast Scenarios
#-----------------------------------


high_folder = "good_forecast"
low_folder = "linear"

files = glob.glob(os.path.join(output_folder, high_folder, low_folder, "*"))

all_profiles = [] 
for file in files[:]:

    scenario = os.path.split(file)[1]
    
    df = extract_df(os.path.join(high_folder, low_folder, scenario))

    timestep_hrs = df_u["simulation_time_hrs"].iloc[1] - df_u["simulation_time_hrs"].iloc[0]
    E_uncon = df_u[profile].sum()*timestep_hrs/3600
    E_con = df[profile].sum()*timestep_hrs/3600
    print("Total Energy uncontrolled: {}".format(E_uncon))
    print("Total Energy controlled: {}".format(E_con))
    print("percent diff : {}".format((E_con - E_uncon) / E_uncon))
    
    all_profiles.append((scenario, df[profile]))
    
    if True:
        fig, ax1 = plt.subplots(figsize = (18, 14))
        ax1.plot(df_u["simulation_time_hrs"], df_u[profile], label = "uncontrolled", color = "red", alpha = 0.3)
        ax1.plot(df_tou["simulation_time_hrs"], df_tou[profile], label = "time_of_use", color = "orange", alpha = 0.3)
        ax1.plot(df["simulation_time_hrs"], df[profile], label = "TE_control", color = "blue", linewidth = 2)

        ax1.set_title(scenario)
        ax1.set_xticks(x_ticks)
        ax1.set_yticks(y_ticks)
        ax1.set_xlim(x_lims[0], x_lims[1])
        ax1.set_ylim(y_lims[0], y_lims[1])
        ax1.set_xlabel('Simulation Time | hrs', labelpad=30)
        ax1.set_ylabel('Power | kW', labelpad=30)
        ax1.grid()
        
        if scenario != "uncontrolled":
            df2 = pd.read_csv(os.path.join(file, "cost_profile.csv"))
            
            df2 = df2[(df2["time_hrs"] >= 24) & (df2["time_hrs"] < 48)]
            df2["time_hrs"] = df2["time_hrs"] % 24.0
            
            ax2 = ax1.twinx()
            ax2.plot(df2["time_hrs"], df2["cost_usd_per_kWh"], color = "purple", label = "forecasted and actual cost", linestyle='dashed', linewidth = 2)
            ax2.set_ylabel('Cost ($/kWh)', labelpad=30)
            ax2.set_ylim(0.05, 0.25)
        else:
            ax2 = ax1.twinx()
            ax2.plot([], [], label = "")
            ax2.set_ylabel(' ', labelpad=30)
    
    fig.legend()
    fig.tight_layout()
    fig_file_name = high_folder + "_" + low_folder + "_" + scenario + ".png"
    fig.savefig( os.path.join(power_profiles_figures_folder, fig_file_name), dpi = 300)