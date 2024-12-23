import subprocess
import os
import sys
import time
import pandas as pd
import numpy as np
import shutil

debug = False
setup_io = True
run_uncontrolled = True

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
    
def copy_EV_demand(from_file, to_file):
    df = pd.read_csv(from_file)
    
    start = 192
    end = 216
        
    mask1 = df["simulation_time_hrs"] >= start
    mask2 = df["simulation_time_hrs"] < end
    
    arr = df.loc[mask1 & mask2, "total_demand_kW"].to_numpy()
    
    num_days = 27
    
    metadata_df = pd.DataFrame()
    metadata_df["metadata_key | str"] = ["cost_min | $/MWh", "cost_max | $/MWh", "gen_min | MW", "gen_max | MW", "cost_function | str", "description | str"]
    #metadata_df["metadata_value | any"] = [-1, -1, "{}".format(arr.min() - 0.001), "{}".format(arr.max() + 0.001), "linear", "EV Demand"]
    metadata_df["metadata_value | any"] = [-1, -1, arr.min()/1000 - 0.001, arr.max()/1000 + 0.001, "linear", "EV Demand"]
  
    forecast_metadata_df = pd.DataFrame()
    forecast_metadata_df["forecast_id | str"] = ["forecast_00"]
    forecast_metadata_df["forecast_release_time | hrs"] = [0]
    
    actual_df = pd.DataFrame()
    actual_df["actual_time | hrs"] = []
    actual_df["actual | MW"] = []
    
    forecast_df = pd.DataFrame()
    forecast_df["forecast_00_time | sec"] = np.arange(0*3600, num_days*24*3600, 60)
    forecast_df["forecast_00 | kW"] = np.tile(arr, num_days)
    
    final_df = pd.concat([metadata_df, forecast_metadata_df, actual_df, forecast_df], axis = 1)
    final_df.to_csv(to_file, index = False, na_rep='')    

#-------------------------------
#      Scenarios
#-------------------------------

scenarios = []

if run_uncontrolled == True:
    scenarios.append("home_uncontrolled")
    scenarios.append("work_uncontrolled")

for i in range(0, 101, 25):
    scenarios.append("home_dynamic_comm_{}".format(i))
    scenarios.append("work_dynamic_comm_{}".format(i))
    scenarios.append("home_dynamic_{}".format(i))
    scenarios.append("work_dynamic_{}".format(i))
    scenarios.append("home_TOU_{}".format(i))
    scenarios.append("work_TOU_{}".format(i))

#-------------------------------
#      Inputs
#-------------------------------

sim_start_sec = 168*3600
sim_end_sec = 288*3600
sim_step_sec = 1*60

n_samples = 100000

if debug == False:
    if len(sys.argv) < 2:
        print("Error: The script run_all.py takes 1 argument, and it should be local or HPC depending on the environment being run")
        exit()
    
    if sys.argv[1] != "HPC" and sys.argv[1] != "local":
        print("Error: The script run_all.py takes 1 argument, and it should be local or HPC depending on the environment being run")
        exit()

    sim_env = sys.argv[1]

else:
    print("running in debug mode")
    sim_env = "local"


if setup_io == True:

    
    input_path = os.path.join(path_to_here, "inputs")
    output_path = os.path.join(path_to_here, "outputs")
    
    
    #-------------------------------
    #      Setup input folders
    #-------------------------------
    reset_dir(input_path)       # Clean folder
    
    base_input_folder = os.path.join(path_to_here, "TE_profiles", "base_inputs_folder") # base copy of input dir
    
    for folder in scenarios:
        
        input_folder = os.path.join(input_path, folder)
        
        # dirs_exist_ok exist only in python 3.8 and above
        shutil.copytree(base_input_folder, input_folder, dirs_exist_ok = True)  # copy base input folder to input folder
    
    #-------------------------------
    #      Update CE and SE files
    #-------------------------------
    
    CE_df = pd.read_csv(os.path.join(path_to_here, "TE_profiles", "CE_ICM_work_dominant_original.csv"), keep_default_na=False)
    SE_df = pd.read_csv(os.path.join(path_to_here, "TE_profiles", "SE_ICM_work_dominant_original.csv"), keep_default_na=False)
    
    for scenario_name in scenarios:
        
        input_folder = os.path.join(input_path, scenario_name)
        
        if "uncontrolled" in scenario_name:
            percent_of_control = 0 
        else:
            percent_of_control = int(scenario_name.split("_")[-1])
    
        if "home" in scenario_name:
            range_min = 100000000
            range_max = 200000000
        elif "work" in scenario_name:
            range_min = 200000000
            range_max = 300000000
        else:
            raise ValueError('scenario name should have home or work in it.')
    
        sub_CE_df = CE_df[(CE_df["charge_event_id"] >= range_min)  & (CE_df["charge_event_id"] < range_max)]
        sub_CE_df = sub_CE_df.sample(n=n_samples)
        
        sub_CE_df["ES_strategy"] = "NA"
        sub_CE_df["VS_strategy"] = "NA"
        sub_CE_df["Ext_strategy"] = "NA"
        
        sub_CE_control_df = sub_CE_df.sample(n = int(n_samples*percent_of_control/100))
        
        if "dynamic" in scenario_name:
            sub_CE_df.loc[sub_CE_control_df.index, "Ext_strategy"] = "ext0001"
        elif "TOU" in scenario_name:
            if "home" in scenario_name:
                sub_CE_df.loc[sub_CE_control_df.index, "ES_strategy"] = "ES100-A"
            elif "work" in scenario_name:
                sub_CE_df.loc[sub_CE_control_df.index, "ES_strategy"] = "ES100-B"
                
        sub_CE_df.to_csv(os.path.join(input_folder, "CE_{}.csv".format(scenario_name)), index = False)
        
        sub_SE_df = SE_df[SE_df["SE_id"].isin(sub_CE_df["SE_id"])]
        
        sub_SE_df.to_csv(os.path.join(input_folder, "SE_{}.csv".format(scenario_name)), index = False)
        
    #-------------------------------
    #      Update baseLD input file
    #-------------------------------
    
    data = "data_start_time_unix_time,{}\n".format(sim_start_sec)
    data += "time_step_sec,{}\n".format(sim_step_sec)
    data += "actual_non_pev_net_load_akW,forecasted_non_pev_net_load_akW\n"
    for i in range(sim_start_sec, sim_end_sec, sim_step_sec):
        data += "{},{}\n".format(1000, 1000)    
    
    for scenario_name in scenarios:
    
        input_folder = os.path.join(input_path, scenario_name)
        file = open(os.path.join(input_folder, "baseLD_.csv"), "w")
        file.write(data)
        file.close()
        
    #-------------------------------
    #      Setup output folders
    #-------------------------------
    
    reset_dir(output_path)      # Clean folder
    
    for folder in scenarios:
        output_folder = os.path.join(output_path, folder)
        reset_dir(output_folder)        # reset also creates empty dir


#-------------------------------
#      Kickoff sims
#-------------------------------

if debug == False:

    # Run uncontrolled sceanrios locally since they tend to be faster
    if run_uncontrolled == True:

        sim = "home_uncontrolled"
        subprocess.call("python start_exe_with_args.py \"{}\" {} {} {}".format(sim, sim_start_sec, sim_end_sec, sim_step_sec), shell = True)
        time.sleep(5)
        
        # Copy uncontrolled results as EV demand to other home and work scenarios 

        from_file = os.path.join(output_path, sim, "real_power_profiles.csv")
        
        for sim in scenarios:
            if "home" in sim:
                to_file = os.path.join(input_path, sim, "TE_inputs", "EV.csv")
                copy_EV_demand(from_file, to_file)

        sim = "work_uncontrolled"
        subprocess.call("python start_exe_with_args.py \"{}\" {} {} {}".format(sim, sim_start_sec, sim_end_sec, sim_step_sec), shell = True)
        time.sleep(5)
        
        from_file = os.path.join(output_path, sim, "real_power_profiles.csv")
        
        for sim in scenarios:
            if "work" in sim:
                to_file = os.path.join(input_path, sim, "TE_inputs", "EV.csv")
                copy_EV_demand(from_file, to_file)
        
    if True:
        # Finally run all sims
        for sim in scenarios:
            
            if "uncontrolled" not in sim:
                if sim_env == "HPC":
                    subprocess.call("qsub -v \'folder=\"{}\", sim_start={}, sim_end={}, sim_step={}\' job.sh".format(sim, sim_start_sec, sim_end_sec, sim_step_sec), shell = True)
                    print("job {} submitted".format(sim))
                
                if sim_env == "local":
                    subprocess.call("python start_exe_with_args.py \"{}\" {} {} {}".format(sim, sim_start_sec, sim_end_sec, sim_step_sec), shell = True)
                    time.sleep(5)
