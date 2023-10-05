import sys

# This should never be inserted at index = 0 because  
# the path at index = 0 should not be changed because
# some libraries require this.
# We are inserting at index 1.
index = 1
sys.path.insert(index, './')
sys.path.insert(index+1, './libs')
sys.path.insert(index+2, './source/base')
sys.path.insert(index+3, './source/custom_controls')
sys.path.insert(index+4, './source/ES500')
sys.path.insert(index+5, './source/federates')

# line below should be updated based on project
sys.path.insert(index+6, './source/customized_inputs/eMosaic')

#---------------------------------

import os, copy

from multiprocessing import Process
from multiprocessing import set_start_method
import subprocess

from Caldera_ICM_federate import caldera_ICM_federate
from OpenDSS_federate import open_dss_federate
from Caldera_global import queuing_mode_enum, charge_event_queuing_inputs
from Load_inputs_federate import load_inputs_federate
from typeA_control_federate import typeA_control_federate
from typeB_control_federate import typeB_control_federate
from global_aux import container_class
from ES500_aux import ES500_aux
from get_customized_inputs import get_customized_pev_ramping
from control_strategy_A import control_strategy_A
from control_strategy_B import control_strategy_B
from control_strategy_C import control_strategy_C

#================================================

print("In start_execution.py, __name__: ",__name__)

if __name__ == '__main__':
    
    print("calling 'set_start_method'...")
    set_start_method('spawn')
    #set_start_method('fork')
    
    grid_timestep_sec = 60
    start_simulation_unix_time = 6*3600
    end_simulation_unix_time = 25*3600
    
    ensure_pev_charge_needs_met_for_ext_control_strategy = False
    use_opendss = False
    
    #---------------------
    
    start_simulation_unix_time = int(start_simulation_unix_time)
    end_simulation_unix_time = int(end_simulation_unix_time)
    
    if start_simulation_unix_time - 2*grid_timestep_sec < 0:
        print('Simulation not Started.  The start_simulation_unix_time must be greater than the grid_timestep_sec.')
        exit()
    
    if not isinstance(grid_timestep_sec, int) or not isinstance(start_simulation_unix_time, int) or not isinstance(end_simulation_unix_time, int):
        print('Either grid_timestep_sec or start_simulation_unix_time or end_simulation_unix_time is not an integer.')
        exit()
    
    simulation_time_constraints = container_class()
    simulation_time_constraints.start_simulation_unix_time = start_simulation_unix_time
    simulation_time_constraints.end_simulation_unix_time = end_simulation_unix_time
    simulation_time_constraints.grid_timestep_sec = grid_timestep_sec
    
    # queuing_mode -> overlapAllowed_earlierArrivalTimeHasPriority, overlapLimited_mostRecentlyQueuedHasPriority
    CE_queuing_inputs = charge_event_queuing_inputs()
    CE_queuing_inputs.max_allowed_overlap_time_sec = 0.1
    CE_queuing_inputs.queuing_mode = queuing_mode_enum.overlapAllowed_earlierArrivalTimeHasPriority
    
    #---------------------
    
    (is_valid, customized_pev_ramping) = get_customized_pev_ramping()
    
    if not is_valid:
        exit()
    
    #---------------------
    
    base_dir = os.getcwd()
    
    #---------------------
    
    num_of_federates = 1    # Load_Input_Files
    num_of_federates += 1   # Caldera_ICM
    num_of_federates += 1   # OpenDSS
    num_of_federates += 1   # Caldera_ES500
    num_of_federates += 1   # control_strategy_A
    num_of_federates += 1   # control_strategy_B
    num_of_federates += 1   # control_strategy_C
    
    broker = subprocess.Popen(['helics_broker', '--loglevel=no_print', '-f{}'.format(num_of_federates)])
    #broker = subprocess.Popen(['helics_broker', '-f{}'.format(num_of_federates)])
    
    #---------------------
    
    processes = []

    # Load Input Files Federate
    json_config_file_name = 'Load_Input_Files.json'
    p = Process(target=load_inputs_federate, args=(base_dir, json_config_file_name, simulation_time_constraints,), name="load_inputs_federate")
    processes.append(p)
    
    # Caldera ICM Federate
    json_config_file_name = 'Caldera_ICM.json'
    create_charge_profile_library = True 
    p = Process(target=caldera_ICM_federate, args=(base_dir, json_config_file_name, simulation_time_constraints, customized_pev_ramping, create_charge_profile_library, ensure_pev_charge_needs_met_for_ext_control_strategy, CE_queuing_inputs,), name="caldera_ICM_federate")
    processes.append(p)
    
    # OpenDSS Federate
    json_config_file_name = 'OpenDSS.json'
    p = Process(target=open_dss_federate, args=(base_dir, json_config_file_name, simulation_time_constraints, use_opendss,), name="open_dss_federate")
    processes.append(p)
	
    #---------------------------
    #   ES500 Control Federate
    #---------------------------
    json_config_file_name = 'Caldera_ES500.json'
    ES500_obj = ES500_aux(base_dir, simulation_time_constraints)    
    p = Process(target=typeA_control_federate, args=(base_dir, json_config_file_name, simulation_time_constraints, ES500_obj,), name="caldera_ES500_federate")
    processes.append(p)
    
    #-------------------------------
    #   Control Strategy_A Federate
    #-------------------------------
    json_config_file_name = 'control_strategy_A.json'
    CS_A_obj = control_strategy_A(base_dir, simulation_time_constraints)    
    p = Process(target=typeA_control_federate, args=(base_dir, json_config_file_name, simulation_time_constraints, CS_A_obj,), name="control_strategy_A_federate")
    processes.append(p)
    
    #-------------------------------
    #   Control Strategy_B Federate
    #-------------------------------
    json_config_file_name = 'control_strategy_B.json'
    CS_B_obj = control_strategy_B(base_dir, simulation_time_constraints)    
    p = Process(target=typeB_control_federate, args=(base_dir, json_config_file_name, simulation_time_constraints, CS_B_obj,), name="control_strategy_B_federate")
    processes.append(p)
    
    #-------------------------------
    #   Control Strategy_C Federate
    #-------------------------------
    json_config_file_name = 'control_strategy_C.json'
    CS_C_obj = control_strategy_C(base_dir, simulation_time_constraints)
    p = Process(target=typeB_control_federate, args=(base_dir, json_config_file_name, simulation_time_constraints, CS_C_obj,), name="control_strategy_C_federate")
    processes.append(p)
    

    for p in processes:
        p.start()

    for p in processes:
        p.join()
