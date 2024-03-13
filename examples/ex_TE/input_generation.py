# -*- coding: utf-8 -*-
"""
Created on Fri Mar  1 08:24:24 2024

@author: CEBOM
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
import glob
import shutil
from numpy.random import default_rng
import json

plot_ev_demand_plots = False
plot_solar_plots = False

required_timestep = 5*60
num_days = 3

path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))
input_path = os.path.join(path_to_here, "inputs")
output_path = os.path.join(path_to_here, "outputs")

#===============================

# Region demand
non_ev_demand_file = "el_paso_demand.csv"
non_ev_demand_day = 2
non_ev_demand_timestep_sec = 5*60

# EV charing demand
ev_demand_file = "EV_charging.csv"
ev_demand_timestep_sec = 1*60

# Solar demand
solar_file = "el_paso_solar_2022_results.csv"
solar_timestep_sec = 5*60
days = {
        "sunny day" : "2022-09-05",
        "sunny day with short dip" : "2022-09-04",
        "sunny day with dip start of day" : "2022-10-10",
        "sunny day with dip mid of day" : "2022-09-22",
        "sunny day with dip end of day" : "2022-08-29",
        "cloudy day" : "2022-10-17",
        }

# TE_profiles directory
TE_profiles_dir = os.path.join(path_to_here, "TE_profiles")

# Charge Event file
CE_file = "CE_ICM_work_dominant_original.csv"
ratio = 0.001 # ratio of charge events to filter. 1 means all charge events are included and 0 means no charge events are included

# Supply Equipment file
SE_file = "SE_ICM_work_dominant_original.csv"

# Scenarios

# Right forecast scenarios

# 1. forecast : sunny day,  actual :  sunny day
# 2. forecast : sunny day with short dip, actual : sunny day with short dip
# 3. forecast : sunny day with dip start of day, actual : sunny day with dip start of day
# 4. forecast : sunny day with dip mid of day, actual : sunny day with dip mid of day
# 5. forecast : sunny day with dip end of day, actual : sunny day with dip end of day
# 6. forecast : cloudy day, actual : cloudy day

# Wrong forecast scenarios

# 1. forecast : sunny day, actual : sunny day with short dip
# 2. forecast : sunny day, actual : sunny day with dip start of day
# 3. forecast : sunny day, actual : sunny day with dip mid of day
# 4. forecast : sunny day, actual : sunny day with dip end of day
# 5. forecast : sunny day, actual : cloudy day

good_forecast_scenarios = [
    ("sunny day", "sunny day"),
    ("sunny day with short dip", "sunny day with short dip"),
    ("sunny day with dip start of day", "sunny day with dip start of day"),
    ("sunny day with dip mid of day", "sunny day with dip mid of day"),
    ("sunny day with dip end of day", "sunny day with dip end of day"),
    ("cloudy day", "cloudy day")
    ]

bad_forecast_scenarios = [
    ("sunny day", "sunny day with short dip"),
    ("sunny day", "sunny day with dip start of day"),
    ("sunny day", "sunny day with dip mid of day"),
    ("sunny day", "sunny day with dip end of day"),
    ("sunny day", "cloudy day")
    ]

#===============================

time_hrs = np.arange(0, num_days*24*3600, required_timestep)/3600.0

#===============================

non_ev_demand_df = pd.read_csv(os.path.join(TE_profiles_dir, non_ev_demand_file))

non_ev_demand_df_demand_MW = non_ev_demand_df['demand_MW'].to_numpy()
non_ev_demand_df_time_hrs = non_ev_demand_df['time_hrs'].to_numpy()

#Plot all days demand and gen data
if plot_ev_demand_plots == True:
    fig, ax = plt.subplots()
    ax.plot(non_ev_demand_df_time_hrs, non_ev_demand_df_demand_MW)
    ax.set_title("demand_MW")
    ax.set_xlabel("hours")
    ax.set_ylabel("MW")
    ax.set_xticks(np.arange(0,non_ev_demand_df_time_hrs.max()+1.0,24.0))
    ax.set_ylim((0,(int(non_ev_demand_df_demand_MW.max()/100.0)+1)*100.0))

non_ev_demand_start_idx = int(non_ev_demand_day*24*3600/non_ev_demand_timestep_sec)
non_ev_demand_end_idx = int((non_ev_demand_day+1)*24*3600/non_ev_demand_timestep_sec)

non_ev_demand_MW = np.tile(non_ev_demand_df["demand_MW"][non_ev_demand_start_idx:non_ev_demand_end_idx], num_days)

#Plot demand
if plot_ev_demand_plots == True:
    fig, ax = plt.subplots()
    ax.plot(time_hrs, non_ev_demand_MW)
    ax.set_title("non_ev_demand_MW")
    ax.set_xlabel("hours")
    ax.set_ylabel("MW")
    ax.set_xticks(np.arange(0,time_hrs.max()+1.0,24.0))
    ax.set_ylim((0,(int(non_ev_demand_df_demand_MW.max()/100.0)+1)*100.0))

#===============================

ev_demand_df = pd.read_csv(os.path.join(TE_profiles_dir, ev_demand_file))

# Filter charging demand for only 1 day i.e. middle day
ev_demand_df = ev_demand_df[(ev_demand_df["simulation_time_hrs"] >= 24.0) & (ev_demand_df["simulation_time_hrs"] < 48.0)]

# Convert EV demand data to Other demand data's timestep by averaging the data
divisor =  non_ev_demand_timestep_sec / ev_demand_timestep_sec
ev_demand_kW = (ev_demand_df['total_demand_kW'].groupby(ev_demand_df.index // divisor).sum()/divisor)

# repeat the data n times, df_charging_demand is pd.series here
ev_demand_MW = np.tile(ev_demand_kW, num_days)/1000.0

#Plot demand
if plot_ev_demand_plots == True:
    fig, ax = plt.subplots()
    ax.plot(time_hrs, ev_demand_MW)
    ax.set_title("ev_demand_MW")
    ax.set_xlabel("hours")
    ax.set_ylabel("MW")
    ax.set_xticks(np.arange(0,time_hrs.max()+1.0,24.0))
    ax.set_ylim((0,(int(non_ev_demand_df_demand_MW.max()/100.0)+1)*100.0))

#===============================

solar_df = pd.read_csv(os.path.join(TE_profiles_dir, solar_file))
solar_df["Time stamp"] = pd.to_datetime(solar_df['Time stamp'], format = "%b %d, %I:%M %p")
solar_df["Time stamp"] = solar_df["Time stamp"] + pd.DateOffset(years=122)

solar_profiles = {}

for scenario, date in days.items():
    
    sub_solar_df = solar_df[solar_df["Time stamp"].dt.date.astype(str) == date]
    
    solar_MW = sub_solar_df["System power generated | (kW)"].to_numpy()/1000.0

    # repeat for 3 days
    solar_MW = np.tile(solar_MW, num_days)
    
    solar_profiles[scenario] = solar_MW
    
    if plot_solar_plots == True:
        fig, ax = plt.subplots(1, 1)
        ax.plot(time_hrs, solar_MW)
        ax.set_xlabel("Time (hrs)")
        ax.set_xlim(0, num_days*24)
        ax.set_xticks(np.linspace(0, num_days*24, 12+1))
        ax.set_ylim(-2, 1400)
        ax.set_ylabel("System power generated (kW)")
        ax.set_title("{} ({})".format(scenario, date))

#===============================

CE_df = pd.read_csv(os.path.join(TE_profiles_dir, CE_file), keep_default_na=False)

CE_df['start_time'] = CE_df['start_time'] - 7*24
CE_df['end_time_prk'] = CE_df['end_time_prk'] - 7*24

df_home = CE_df[(CE_df["charge_event_id"] >= 100000000) & (CE_df["charge_event_id"] < 200000000)]
df_work = CE_df[(CE_df["charge_event_id"] >= 200000000) & (CE_df["charge_event_id"] < 300000000)]
df_destin = CE_df[(CE_df["charge_event_id"] >= 300000000) & (CE_df["charge_event_id"] < 400000000)]

rng = default_rng(seed = 0)

# rng.choice generates n random numbers between 0 and input val, replace = False make the numbers unique
random_home_indices = np.sort(rng.choice(len(df_home), size=int(ratio*len(df_home)), replace=False))
random_work_indices = np.sort(rng.choice(len(df_work), size=int(ratio*len(df_work)), replace=False))
random_destin_indices = np.sort(rng.choice(len(df_destin), size=int(ratio*len(df_destin)), replace=False))

df_home2 = df_home.iloc[random_home_indices, :]
df_work2 = df_work.iloc[random_work_indices, :]
df_destin2 = df_destin.iloc[random_destin_indices, :]

final_CE_df = pd.concat([df_home2, df_work2, df_destin2])

SE_df = pd.read_csv(os.path.join(TE_profiles_dir, SE_file), keep_default_na=False)

final_SE_df = SE_df[SE_df["SE_id"].isin(final_CE_df["SE_id"])]

#===============================

def clean_input_folder(folder : str):

    files_to_clean = []
    files_to_clean.extend(glob.glob(os.path.join(folder, "CE_*.csv")))
    files_to_clean.extend(glob.glob(os.path.join(folder, "SE_*.csv")))
    files_to_clean.extend(glob.glob(os.path.join(folder, "TE_inputs", "forecast.csv")))
    files_to_clean.extend(glob.glob(os.path.join(folder, "TE_inputs", "actual.csv")))
    files_to_clean.extend(glob.glob(os.path.join(folder, "TE_inputs", "generation_cost.json")))
    
    for file in files_to_clean:
        os.remove(file)


def write_input_files(input_path : str, output_path : str, subfolder : str, cost_function : str, scenarios):
    
    generation_cost = {
        "cost_function" : cost_function,
        "fossil_fuel": {
            "gen_min": 500,
            "gen_max": 2000,
            "cost_min": 39.00,
            "cost_max": 221.00
        },
        "nuclear": {
            "gen_min": 622,
            "gen_max": 622,
            "cost_min": 167.00,
            "cost_max": 167.00
        },
        "solar": {
            "gen_min": -2,
            "gen_max": 1800,
            "cost_min": 36.00,
            "cost_max": 36.00
        },
        "units":{
            "gen_min": "MW",
            "gen_max": "MW",
            "cost_min" : "USD per MW",
            "cost_max" : "USD per MW"
        }
    }
    
    for i, (forecast, actual) in enumerate(scenarios):
        
        uncontrolled_folder = os.path.join(input_path, "uncontrolled")
        input_subfolder = os.path.join(input_path, subfolder, cost_function, "scenario_{}".format(i))
        output_subfolder = os.path.join(output_path, subfolder, cost_function, "scenario_{}".format(i))

        if os.path.exists(input_subfolder) and os.path.isdir(input_subfolder):
            shutil.rmtree(input_subfolder, ignore_errors=False)
        
        shutil.copytree(uncontrolled_folder, input_subfolder)
        
        clean_input_folder(input_subfolder)
        create_output_folder(output_subfolder)
        
        final_CE_df.to_csv(os.path.join(input_subfolder, "CE_controlled.csv"), index = False)
        final_SE_df.to_csv(os.path.join(input_subfolder, "SE_controlled.csv"), index = False)
        
        # forecast
        forecast_df = pd.DataFrame()
        forecast_df["time | hrs"] = time_hrs
        forecast_df["forecasted_demand | MW"] = non_ev_demand_MW + ev_demand_MW
        forecast_df["nuclear | MW"] = [622] * len(time_hrs)
        forecast_df["solar | MW"] = solar_profiles[forecast]
        forecast_df["fossil_fuel | MW"] = forecast_df["forecasted_demand | MW"] - forecast_df["nuclear | MW"] - forecast_df["solar | MW"]
        
        forecast_df.to_csv(os.path.join(input_subfolder, "TE_inputs", "forecast.csv"), index = False)
        
        # actual
        actual_df = pd.DataFrame()
        actual_df["time | hrs"] = time_hrs
        actual_df["actual_demand | MW"] = non_ev_demand_MW + ev_demand_MW
        actual_df["nuclear | MW"] = [622] * len(time_hrs)
        actual_df["solar | MW"] = solar_profiles[actual]
        actual_df["fossil_fuel | MW"] = actual_df["actual_demand | MW"] - actual_df["nuclear | MW"] - actual_df["solar | MW"]
        
        actual_df.to_csv(os.path.join(input_subfolder, "TE_inputs", "actual.csv"), index = False)
        
        with open(os.path.join(input_subfolder, "TE_inputs", "generation_cost.json"), 'w') as fp:
            json.dump(generation_cost, fp, indent=4)

def create_output_folder(output_folder):

    if os.path.exists(output_folder) and os.path.isdir(output_folder):
        shutil.rmtree(output_folder, ignore_errors=False)
    
    os.makedirs(os.path.join(output_folder))    # intermediate directory is also created

# Uncontrolled
uncontrolled_input_folder = os.path.join(input_path, "uncontrolled")
uncontrolled_output_folder = os.path.join(output_path, "uncontrolled")

clean_input_folder(uncontrolled_input_folder)
create_output_folder(uncontrolled_output_folder)

final_CE_df.to_csv(os.path.join(uncontrolled_input_folder, "CE_uncontrolled.csv"), index = False)
final_SE_df.to_csv(os.path.join(uncontrolled_input_folder, "SE_uncontrolled.csv"), index = False)

# Activate Control Strategy
final_CE_df["Ext_strategy"] = "ext0001"

# Good Forecast
write_input_files(input_path, output_path, "good_forecast", "linear", good_forecast_scenarios)
write_input_files(input_path, output_path, "good_forecast", "steep_cubic", good_forecast_scenarios)
write_input_files(input_path, output_path, "good_forecast", "inverse_s", good_forecast_scenarios)

# Bad Forecast
write_input_files(input_path, output_path, "bad_forecast", "linear", bad_forecast_scenarios)
write_input_files(input_path, output_path, "bad_forecast", "steep_cubic", bad_forecast_scenarios)
write_input_files(input_path, output_path, "bad_forecast", "inverse_s", bad_forecast_scenarios)
