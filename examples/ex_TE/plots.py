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

#-----------------------------------
# Solar profiles
#-----------------------------------

# Handled in input_generation.py


#-----------------------------------
# Good Forecast Scenarios
#-----------------------------------

output_folder = os.path.join(path_to_here, "outputs")
figures_folder = os.path.join(path_to_here, "figures")

high_folder = "good_forecast"
low_folder = "linear"

profile = "total_demand_kW"
#profile = "HOME"

files = glob.glob(os.path.join(output_folder, high_folder, low_folder, "*"))

all_profiles = [] 
for file in files[:]:

    df = pd.read_csv(os.path.join(file, "real_power_profiles.csv"))
    df_u = pd.read_csv(os.path.join(output_folder, "uncontrolled", "real_power_profiles.csv"))
    
    scenario = os.path.split(file)[1]
    df = df[(df["simulation_time_hrs"] >= 24) & (df["simulation_time_hrs"] < 48)]
    df["simulation_time_hrs"] = df["simulation_time_hrs"] % 24.0
    
    df_u = df_u[(df_u["simulation_time_hrs"] >= 24) & (df_u["simulation_time_hrs"] < 48)]
    df_u["simulation_time_hrs"] = df_u["simulation_time_hrs"] % 24.0
    
    timestep_hrs = df_u["simulation_time_hrs"].iloc[1] - df_u["simulation_time_hrs"].iloc[0]
    E_uncon = df_u[profile].sum()*timestep_hrs/3600
    E_con = df[profile].sum()*timestep_hrs/3600
    print("Total Energy uncontrolled: {}".format(E_uncon))
    print("Total Energy controlled: {}".format(E_con))
    print("percent diff : {}".format((E_con - E_uncon) / E_uncon))
    
    all_profiles.append((scenario, df[profile]))
    
    if True:
        fig, ax1 = plt.subplots(figsize = (18, 14))
        ax1.plot(df["simulation_time_hrs"], df[profile], label = "controlled")
        ax1.plot(df_u["simulation_time_hrs"], df_u[profile], label = "uncontrolled")
        ax1.set_title(scenario)
        ax1.set_xticks(np.arange(0, 24+1, 2))
        #ax1.set_yticks(np.arange(0, 5000+1, 500))
        ax1.set_xlim(0,24)
        #ax1.set_ylim(0, 5000)
        ax1.set_xlabel('Simulation Time (hrs)', labelpad=30)
        ax1.set_ylabel('Power kW', labelpad=30)
        ax1.grid()
        
        if scenario != "uncontrolled":
            df2 = pd.read_csv(os.path.join(file, "cost_profile.csv"))
            
            df2 = df2[(df2["time_hrs"] >= 24) & (df2["time_hrs"] < 48)]
            df2["time_hrs"] = df2["time_hrs"] % 24.0
            
            ax2 = ax1.twinx()
            ax2.plot(df2["time_hrs"], df2["cost_usd_per_kWh"], color = "red", label = "cost")
            ax2.set_ylabel('Cost ($/kWh)', labelpad=30)
            ax2.set_ylim(0.05, 0.25)
        else:
            ax2 = ax1.twinx()
            ax2.plot([], [], label = "")
            ax2.set_ylabel(' ', labelpad=30)
    
    fig.legend()
    fig.tight_layout()
    fig_file_name = high_folder + "_" + low_folder + "_" + scenario + ".png"
    fig.savefig( os.path.join(figures_folder, fig_file_name), dpi = 300)