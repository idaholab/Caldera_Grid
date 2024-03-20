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
input_folder = os.path.join(path_to_here, "inputs")
figures_folder = os.path.join(path_to_here, "figures")
power_profiles_figures_folder = os.path.join(figures_folder, "power_profiles_plots")

profile = "total_demand_kW"

def extract_power_profile_df(folder : str):
    
    data_folder = os.path.join(output_folder, folder)
    df = pd.read_csv(os.path.join(data_folder, "real_power_profiles.csv"))

    df = df[(df["simulation_time_hrs"] >= 24) & (df["simulation_time_hrs"] < 48)]
    df["simulation_time_hrs"] = df["simulation_time_hrs"] % 24.0

    return df


def extract_cost_profile_df(folder : str):
    
    data_folder = os.path.join(output_folder, folder)
    df = pd.read_csv(os.path.join(data_folder, "cost_profile.csv"))

    df.columns = [column.split("|")[0].strip() for column in df.columns.to_series()]

    df = df[(df["time"] >= 24) & (df["time"] < 48)]
    df["time"] = df["time"] % 24.0

    return df


#-----------------------------------
# Solar profiles
#-----------------------------------

# Handled in input_generation.py

#-----------------------------------
# Fossil fuel profiles
#-----------------------------------

# Handled in input_generation.py

#-----------------------------------
# Uncontrolled
#-----------------------------------

x_lims = (0, 24)
x_ticks = np.linspace(x_lims[0], x_lims[1], 13)

y_lims = (0, 1000000)
y_ticks = np.linspace(y_lims[0], y_lims[1], 11)

fig_size = (13, 10)

text_x = 0.5
text_y = 950000


df_u = extract_power_profile_df("uncontrolled")

fixed_charging_cost_usd_per_kWh = 0.12

timestep_hrs = df_u["simulation_time_hrs"].iloc[1] - df_u["simulation_time_hrs"].iloc[0]

E_uncontrolled_total = df_u[profile].sum()*timestep_hrs
uncontrolled_total_charging_cost = E_uncontrolled_total * fixed_charging_cost_usd_per_kWh

if True:
    fig, ax1 = plt.subplots(1, 1, figsize = fig_size)
    ax1.plot(df_u["simulation_time_hrs"], df_u[profile], label = "uncontrolled", color = "red")
    ax1.set_title("Uncontrolled power profile")
    ax1.set_xticks(x_ticks)
    ax1.set_yticks(y_ticks)
    ax1.set_xlim(x_lims[0], x_lims[1])
    ax1.set_ylim(y_lims[0], y_lims[1])
    ax1.set_xlabel('Simulation Time | hrs', labelpad=30)
    ax1.set_ylabel('Power | kW', labelpad=30)
    ax1.grid(alpha = 0.5, linestyle='--')

    plt.text(text_x, text_y, 
        "Fixed \$/kWh : \${:.3f}".format(fixed_charging_cost_usd_per_kWh) + "\n" +
        "Uncontrolled \$ total : \${:.3f}".format(uncontrolled_total_charging_cost),
        ha='left', va='top', fontsize = 'xx-large')
    
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

df_tou = extract_power_profile_df("time_of_use")

fixed_charging_cost_tou_usd_per_kWh = 0.08
fixed_charging_cost_non_tou_usd_per_kWh = 0.14

E_uncontrolled_tou = df_u[(df_u["simulation_time_hrs"] >= 8) & (df_u["simulation_time_hrs"] < 16)][profile].sum()*timestep_hrs
E_uncontrolled_non_tou = df_u[(df_u["simulation_time_hrs"] < 8) | (df_u["simulation_time_hrs"] >= 16)][profile].sum()*timestep_hrs

E_controlled_tou = df_tou[(df_tou["simulation_time_hrs"] >= 8) & (df_tou["simulation_time_hrs"] < 16)][profile].sum()*timestep_hrs
E_controlled_non_tou = df_tou[(df_tou["simulation_time_hrs"] < 8) | (df_tou["simulation_time_hrs"] >= 16)][profile].sum()*timestep_hrs

uncontrolled_EV_charging_cost = E_uncontrolled_tou*fixed_charging_cost_tou_usd_per_kWh + E_uncontrolled_non_tou*fixed_charging_cost_non_tou_usd_per_kWh
tou_EV_charging_cost = E_controlled_tou*fixed_charging_cost_tou_usd_per_kWh + E_controlled_non_tou*fixed_charging_cost_non_tou_usd_per_kWh

if True:
    fig, ax1 = plt.subplots(1, 1, figsize = fig_size)
    ax1.plot(df_u["simulation_time_hrs"], df_u[profile], label = "uncontrolled", color = "red")
    ax1.plot(df_tou["simulation_time_hrs"], df_tou[profile], label = "time_of_use", color = "orange")
    ax1.set_title("Time of use power profile")
    ax1.set_xticks(x_ticks)
    ax1.set_yticks(y_ticks)
    ax1.set_xlim(x_lims[0], x_lims[1])
    ax1.set_ylim(y_lims[0], y_lims[1])
    ax1.set_xlabel('Simulation Time | hrs', labelpad=30)
    ax1.set_ylabel('Power | kW', labelpad=30)
    ax1.grid(alpha = 0.5, linestyle='--')

    plt.text(text_x, text_y, 
        "TOU period fixed \$/kWh: \${:.3f}".format(fixed_charging_cost_tou_usd_per_kWh) + "\n" +
        "Non TOU period fixed \$/kWh: \${:.3f}".format(fixed_charging_cost_non_tou_usd_per_kWh) + "\n" +
        "Uncontrolled \$ total: \${:.3f}".format(uncontrolled_EV_charging_cost) + "\n" +
        "TOU control \$ total: \${:.3f}".format(tou_EV_charging_cost), 
        ha='left', va='top', fontsize = 'xx-large')
    
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

timestep_hrs = 15*50/3600

files = glob.glob(os.path.join(output_folder, high_folder, low_folder, "*"))

all_profiles = [] 
for file in files[:]:

    scenario = os.path.split(file)[1]
    
    df = extract_power_profile_df(os.path.join(high_folder, low_folder, scenario))
    df2 = extract_cost_profile_df(os.path.join(high_folder, low_folder, scenario))

    avg_charging_cost = df2["actual_cost"].mean()

    E_uncontrolled = np.mean(df_u[profile].to_numpy().reshape(-1, 15), axis=1) * timestep_hrs # average power for every 15 timesteps then converty to energy
    uncontrolled_total_charging_cost = np.sum(E_uncontrolled * df2["actual_cost"])

    E_tou_controlled = np.mean(df_tou[profile].to_numpy().reshape(-1, 15), axis=1) * timestep_hrs
    tou_total_charging_cost = np.sum(E_tou_controlled * df2["actual_cost"])

    E_TE_control = np.mean(df[profile].to_numpy().reshape(-1, 15), axis=1) * timestep_hrs
    TE_total_charging_cost = np.sum(E_TE_control * df2["actual_cost"])
    

    all_profiles.append((scenario, df[profile]))
    
    if True:
        fig, ax1 = plt.subplots(figsize = fig_size)
        ax1.plot(df_u["simulation_time_hrs"], df_u[profile], label = "uncontrolled", color = "red", alpha = 0.3)
        ax1.plot(df_tou["simulation_time_hrs"], df_tou[profile], label = "time_of_use", color = "orange", alpha = 0.3)
        ax1.plot(df["simulation_time_hrs"], df[profile], label = "TE_control", color = "blue", linewidth = 2)

        ax1.set_title(high_folder + " " + low_folder + " " + scenario + " power profile")
        ax1.set_xticks(x_ticks)
        ax1.set_yticks(y_ticks)
        ax1.set_xlim(x_lims[0], x_lims[1])
        ax1.set_ylim(y_lims[0], y_lims[1])
        ax1.set_xlabel('Simulation Time | hrs', labelpad=30)
        ax1.set_ylabel('Power | kW', labelpad=30)
        ax1.grid(alpha = 0.5, linestyle='--')

        plt.text(text_x, text_y, 
        "average \$/kWh: \${:.3f}".format(avg_charging_cost) + "\n" +
        "Uncontrolled \$ total: \${:.3f}".format(uncontrolled_total_charging_cost) + "\n" +
        "TOU control \$ total: \${:.3f}".format(tou_total_charging_cost) + "\n" +
        "TE control \$ total: \${:.3f}".format(TE_total_charging_cost), 
        ha='left', va='top', fontsize = 'xx-large')
        
        ax2 = ax1.twinx()
        ax2.plot(df2["time"], df2["forecasted_cost"], color = "purple", label = "forecasted and actual cost", linestyle='dashed', linewidth = 2)
        ax2.set_ylabel('Cost | $/kWh', labelpad=30)
        ax2.set_ylim(0.05, 0.25)
    
    fig.legend()
    fig.tight_layout()
    fig_file_name = high_folder + "_" + low_folder + "_" + scenario + ".png"
    fig.savefig( os.path.join(power_profiles_figures_folder, fig_file_name), dpi = 300)

#-----------------------------------
# Bad Forecast Scenarios
#-----------------------------------

high_folder = "bad_forecast"
low_folder = "linear"

files = glob.glob(os.path.join(output_folder, high_folder, low_folder, "*"))

all_profiles = [] 
for file in files[:]:

    scenario = os.path.split(file)[1]
    
    df = extract_power_profile_df(os.path.join(high_folder, low_folder, scenario))
    df2 = extract_cost_profile_df(os.path.join(high_folder, low_folder, scenario))

    avg_forecasted_charging_cost = df2["forecasted_cost"].mean()
    avg_actual_charging_cost = df2["actual_cost"].mean()

    E_uncontrolled = np.mean(df_u[profile].to_numpy().reshape(-1, 15), axis=1) * timestep_hrs # average power for every 15 timesteps then converty to energy
    uncontrolled_total_charging_cost = np.sum(E_uncontrolled * df2["actual_cost"])

    E_tou_controlled = np.mean(df_tou[profile].to_numpy().reshape(-1, 15), axis=1) * timestep_hrs
    tou_total_charging_cost = np.sum(E_tou_controlled * df2["actual_cost"])

    E_TE_control = np.mean(df[profile].to_numpy().reshape(-1, 15), axis=1) * timestep_hrs
    TE_total_charging_cost = np.sum(E_TE_control * df2["actual_cost"])

    
    all_profiles.append((scenario, df[profile]))
    
    if True:
        fig, ax1 = plt.subplots(figsize = fig_size)
        ax1.plot(df_u["simulation_time_hrs"], df_u[profile], label = "uncontrolled", color = "red", alpha = 0.3)
        ax1.plot(df_tou["simulation_time_hrs"], df_tou[profile], label = "time_of_use", color = "orange", alpha = 0.3)
        ax1.plot(df["simulation_time_hrs"], df[profile], label = "TE_control", color = "blue", linewidth = 2)

        ax1.set_title(high_folder + " " + low_folder + " " + scenario + " power profile")
        ax1.set_xticks(x_ticks)
        ax1.set_yticks(y_ticks)
        ax1.set_xlim(x_lims[0], x_lims[1])
        ax1.set_ylim(y_lims[0], y_lims[1])
        ax1.set_xlabel('Simulation Time | hrs', labelpad=30)
        ax1.set_ylabel('Power | kW', labelpad=30)
        ax1.grid(alpha = 0.5, linestyle='--')

        plt.text(text_x, text_y, 
        "Average forecasted \$/kWh: \${:.3f}".format(avg_forecasted_charging_cost) + "\n" +
        "Average actual \$/kWh: \${:.3f}".format(avg_actual_charging_cost) + "\n" +
        "Uncontrolled \$ total: \${:.3f}".format(uncontrolled_total_charging_cost) + "\n" +
        "TOU control \$ total: \${:.3f}".format(tou_total_charging_cost) + "\n" +
        "TE control \$ total: \${:.3f}".format(TE_total_charging_cost), 
        ha='left', va='top', fontsize = 'xx-large')
    
        ax2 = ax1.twinx()
        ax2.plot(df2["time"], df2["forecasted_cost"], color = "chocolate", label = "forecasted cost", linestyle='dashed', linewidth = 2)
        ax2.plot(df2["time"], df2["actual_cost"], color = "teal", label = "actual cost", linestyle='dashed', linewidth = 2)
        ax2.set_ylabel('Cost | $/kWh', labelpad=30)
        ax2.set_ylim(0.05, 0.25)
    
    fig.legend()
    fig.tight_layout()
    fig_file_name = high_folder + "_" + low_folder + "_" + scenario + ".png"
    fig.savefig( os.path.join(power_profiles_figures_folder, fig_file_name), dpi = 300)