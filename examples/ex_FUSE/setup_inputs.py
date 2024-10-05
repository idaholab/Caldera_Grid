# -*- coding: utf-8 -*-
"""
Created on Thu Sep 19 21:14:27 2024

@author: CEBOM
"""

import subprocess
import os
import sys
import time
import pandas as pd
import numpy as np
import shutil

path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))

#-------------------------------------

MIN_PYTHON = (3, 8)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)
    
#-------------------------------
#      Helper Functions
#-------------------------------

def reset_dir(dir_path : str):

    if os.path.exists(dir_path) and os.path.isdir(dir_path):
        shutil.rmtree(dir_path, ignore_errors=False)

    os.makedirs(os.path.join(dir_path))    # intermediate directory is also created
    
# Setup CE and SE df
def load_CE_SE_df(scenario, n_samples):
    input_path = os.path.join("TE_profiles", "CE_ICM_work_dominant_original.csv")
    
    CE_orig_df = pd.read_csv(input_path, keep_default_na=False)
    
    if 'home' in scenario:
        start = 100000000
        node_id = 'HOME'
        SE_group = 1
        location_type = 'H'
    elif 'work' in scenario:
        start = 200000000
        node_id = 'WORK'
        SE_group = 2
        location_type = 'W'
    else:
        raise ValueError("scenario undefined")
    
    mask1 = CE_orig_df["charge_event_id"] >= start
    mask2 = CE_orig_df["charge_event_id"] < start + 100000000
    CE_df = CE_orig_df.loc[mask1 & mask2, :]

    mask1 = CE_df['start_time'] >= 9*24
    mask2 = CE_df['start_time'] < 10*24

    CE_1_day_df =  CE_df.loc[mask1 & mask2, :]
    CE_1_day_df.loc[:, 'start_time'] = CE_1_day_df['start_time'] - 9*24
    CE_1_day_df.loc[:, 'end_time_prk'] = CE_1_day_df['end_time_prk'] - 9*24
    
    CE_1_day_df = CE_1_day_df.sample(n=n_samples)
    
    CE_final_df = pd.DataFrame()
    # Repeat data for 2 weeks
    for i in range(14):
        CE_1_day_df.loc[:, 'start_time'] += 24
        CE_1_day_df.loc[:, 'end_time_prk'] += 24
        
        CE_final_df = pd.concat([CE_final_df, CE_1_day_df], axis = 0)
    
    ids = np.arange(start, start+len(CE_final_df), 1)
    
    CE_final_df['charge_event_id'] = ids
    CE_final_df['SE_id'] = ids
    CE_final_df['pev_id'] = ids
    
    SE_final_df = pd.DataFrame()
    SE_final_df['SE_id'] = ids
    SE_final_df['SE_type'] = ['L2_17280'] * len(CE_final_df)
    SE_final_df['lon'] = [-93.1] * len(CE_final_df)
    SE_final_df['lat'] = [45.2] * len(CE_final_df)
    SE_final_df['node_id'] = [node_id] * len(CE_final_df)
    SE_final_df['SE_group'] = [SE_group] * len(CE_final_df)
    SE_final_df['location_type'] = [location_type] * len(CE_final_df)
    
    return CE_final_df, SE_final_df

def copy_EV_demand(from_file, to_file):
    df = pd.read_csv(from_file)
    
    data_start = round(df.loc[0, 'simulation_time_hrs'] * 3600)
    data_step = round((df.loc[1, 'simulation_time_hrs'] - df.loc[0, 'simulation_time_hrs']) * 3600)
    data_end = round(data_start + data_step * len(df))
    
    
    min_val = df['total_demand_kW'].min()
    max_val = df['total_demand_kW'].max()
    
    metadata_df = pd.DataFrame()
    metadata_df["metadata_key | str"] = ["cost_min | $/MWh", "cost_max | $/MWh", "gen_min | MW", "gen_max | MW", "cost_function | str", "description | str"]
    metadata_df["metadata_value | any"] = [-1, -1, min_val/1000 - 0.001, max_val/1000 + 0.001, "linear", "EV Demand"]
  
    forecast_metadata_df = pd.DataFrame()
    forecast_metadata_df["forecast_id | str"] = ["forecast_00"]
    forecast_metadata_df["forecast_release_time | hrs"] = [0]
    
    actual_df = pd.DataFrame()
    actual_df["actual_time | hrs"] = []
    actual_df["actual | MW"] = []
    
    forecast_df = pd.DataFrame()
    forecast_df["forecast_00_time | sec"] = np.arange(data_start, data_start + 2*(data_end - data_start), data_step)    # repeat twice
    forecast_df["forecast_00 | kW"] = np.tile(df['total_demand_kW'], 2) # repeat twice
    
    #print(forecast_df)
    
    final_df = pd.concat([metadata_df, forecast_metadata_df, actual_df, forecast_df], axis = 1)
    final_df.to_csv(to_file, index = False, na_rep='')    

def create_TE_demand_input(demand_path, max_demand, start_sec, end_sec, step_sec):
    
    start_hrs = int(start_sec/3600)
    end_hrs = int(end_sec/3600)
    step_hrs = int(step_sec/3600)
    
    metadata_df = pd.DataFrame()
    metadata_df["metadata_key | str"] = ["cost_min | $/MWh", "cost_max | $/MWh", "gen_min | MW", "gen_max | MW", "cost_function | str", "description | str"]
    metadata_df["metadata_value | any"] = [-1, -1, max_demand - 0.001, max_demand + 0.001, "linear", "Demand"]
  
    forecast_metadata_df = pd.DataFrame()
    forecast_metadata_df["forecast_id | str"] = ["forecast_00"]
    forecast_metadata_df["forecast_release_time | hrs"] = [0]
    
    actual_df = pd.DataFrame()
    actual_df["actual_time | hrs"] = np.arange(start_hrs, end_hrs, step_hrs)
    actual_df["actual | MW"] = np.ones(int((end_hrs-start_hrs)/step_hrs))*max_demand
    
    forecast_df = pd.DataFrame()
    forecast_df["forecast_00_time | hrs"] = np.arange(start_hrs, end_hrs, step_hrs)
    forecast_df["forecast_00 | MW"] = np.ones(int((end_hrs-start_hrs)/step_hrs))*max_demand
    
    final_df = pd.concat([metadata_df, forecast_metadata_df, actual_df, forecast_df], axis = 1)
    
    final_df.to_csv(demand_path, index = False, na_rep='')
    

def clean_TE_inputs(input_folder, start_sec, end_sec):
    
    step_sec = 1*3600
    
    if 'solar' in input_folder:
        for gen_type in ['nuclear', 'wind']:
            path = os.path.join(input_folder, "TE_inputs", gen_type + '.csv')
            os.remove(path)
        
        max_demand = 1000
        demand_path = os.path.join(input_folder, "TE_inputs", "demand.csv")
        create_TE_demand_input(demand_path, max_demand, start_sec, end_sec, step_sec)
        
    elif 'wind' in input_folder:
        for gen_type in ['nuclear', 'solar']:
            path = os.path.join(input_folder, "TE_inputs", gen_type + '.csv')
            os.remove(path)
            
        max_demand = 2000
        demand_path = os.path.join(input_folder, "TE_inputs", "demand.csv")
        create_TE_demand_input(demand_path, max_demand, start_sec, end_sec, step_sec)
        
    elif 'full' in input_folder:
        pass
    else:
        pass

def update_CE_SE_file(CE_df, SE_df, scenario, input_folder):
    
    if "uncontrolled" in scenario:
        percent_of_control = 0 
    else:
        percent_of_control = int(scenario.split("_")[-1])

    CE_df["ES_strategy"] = "NA"
    CE_df["VS_strategy"] = "NA"
    CE_df["Ext_strategy"] = "NA"
    
    CE_control_df = CE_df.sample(n = int(len(CE_df)*percent_of_control/100))
    
    if "dynamic" in scenario:
        CE_df.loc[CE_control_df.index, "Ext_strategy"] = "ext0001"
    elif "TOU" in scenario:
        if "home" in scenario:
            CE_df.loc[CE_control_df.index, "ES_strategy"] = "ES100-A"
        elif "work" in scenario:
            CE_df.loc[CE_control_df.index, "ES_strategy"] = "ES100-B"
            
    CE_df.to_csv(os.path.join(input_folder, "CE_{}.csv".format(scenario)), index = False)
            
    SE_df.to_csv(os.path.join(input_folder, "SE_{}.csv".format(scenario)), index = False)

def update_base_LD_file(input_folder, sim_start_sec, sim_end_sec, sim_step_sec):
    data = "data_start_time_unix_time,{}\n".format(sim_start_sec)
    data += "time_step_sec,{}\n".format(sim_step_sec)
    data += "actual_non_pev_net_load_akW,forecasted_non_pev_net_load_akW\n"
    for i in range(sim_start_sec, sim_end_sec, sim_step_sec):
        data += "{},{}\n".format(1000, 1000)    
    
    file = open(os.path.join(input_folder, "baseLD_.csv"), "w")
    file.write(data)
    file.close()
        
def setup_io_folder(CE_df, SE_df, scenario, sim_start_sec, sim_end_sec, sim_step_sec):

    input_path = os.path.join(path_to_here, "inputs")
    output_path = os.path.join(path_to_here, "outputs")
    
    #-------------------------------
    #      Setup input folders
    #-------------------------------
    
    base_input_folder = os.path.join(path_to_here, "TE_profiles", "base_inputs_folder") # base copy of input dir
    
    input_folder = os.path.join(input_path, scenario)
    
    # dirs_exist_ok exist only in python 3.8 and above
    shutil.copytree(base_input_folder, input_folder, dirs_exist_ok = True)  # copy base input folder to input folder
    
    clean_TE_inputs(input_folder, sim_start_sec, sim_end_sec)

    # Update CE and SE files    
    update_CE_SE_file(CE_df, SE_df, scenario, input_folder)
    
    # Update baseLD input file
    update_base_LD_file(input_folder, sim_start_sec, sim_end_sec, sim_step_sec)
        
    #-------------------------------
    #      Setup output folders
    #-------------------------------

    output_folder = os.path.join(output_path, scenario)
    reset_dir(output_folder)        # reset also creates empty dir


if __name__ == "__main__":
    
    sim_start_sec = 3*24*3600   # start from day 1 and not day 0, Caldera Grid has issues running first timestep
    sim_end_sec = 6*24*3600    # not including last day
    sim_step_sec = 1*60     # grid timestep of 1 minute
    
    n_samples = 1000
    
    #----------------------------------
    
    scenarios = []

    scenarios.append("home_uncontrolled")
    scenarios.append("work_uncontrolled")
    
    for i in ["home", "work"]:
        for j in ["full"]: # "solar", "wind", 
            for k in ["TOU", "dynamic", "dynamic_comm"]:
                for l in [100]:
                    scenario = "{}_{}_{}_{}".format(i, j, k, l)
                    scenarios.append(scenario)
        
    #----------------------------------
    
    if len(sys.argv) < 2:
        print("Error: The script run_all.py takes 1 argument, and it should be local or HPC depending on the environment being run")
        exit()
    
    if sys.argv[1] != "HPC" and sys.argv[1] != "local":
        print("Error: The script run_all.py takes 1 argument, and it should be local or HPC depending on the environment being run")
        exit()

    sim_env = sys.argv[1]
    
    #----------------------------------
    
    input_path = os.path.join(path_to_here, "inputs")
    output_path = os.path.join(path_to_here, "outputs")
    
    reset_dir(input_path)       # Clean folder
    reset_dir(output_path)      # Clean folder
    
    for scenario in scenarios:
        CE_df, SE_df = load_CE_SE_df(scenario, n_samples)
        setup_io_folder(CE_df, SE_df, scenario, sim_start_sec, sim_end_sec, sim_step_sec)
    
    #----------------------------------
    
    # run uncontrolled sims and set forecasted EV demand in sims inputs

    for location in ['home', 'work']:
        sim = '{}_uncontrolled'.format(location)
        subprocess.call("python start_exe_with_args.py \"{}\" {} {} {}".format(sim, sim_start_sec, sim_end_sec, sim_step_sec), shell = True)
        time.sleep(5) # Finally run all sims
    
        # Copy uncontrolled results as EV demand to other home and work scenarios 
        from_file = os.path.join(output_path, sim, "real_power_profiles.csv")
        for sim in scenarios:
            if location in sim:
                to_file = os.path.join(input_path, sim, "TE_inputs", "EV.csv")
                copy_EV_demand(from_file, to_file)

    
    # Finally run all remaining sims
    for sim in scenarios:
        
        if "uncontrolled" not in sim:
            
            if sim_env == "HPC":
                subprocess.call("qsub -v \'folder=\"{}\", sim_start={}, sim_end={}, sim_step={}\' job.sh".format(sim, sim_start_sec, sim_end_sec, sim_step_sec), shell = True)
                print("job {} submitted".format(sim))
            
            if sim_env == "local":
                subprocess.call("python start_exe_with_args.py \"{}\" {} {} {}".format(sim, sim_start_sec, sim_end_sec, sim_step_sec), shell = True)
                time.sleep(5)# Finally run all sims
    
    # plots
    