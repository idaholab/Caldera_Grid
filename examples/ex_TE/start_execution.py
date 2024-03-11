import sys
import os, copy, errno, shutil
import argparse, time
import json
from multiprocessing import Process
import subprocess
path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))

# Parse the command-line arguments
parser = argparse.ArgumentParser(description='Caldera Grid startup script')
parser.add_argument(
    '-json',
    '--json_inputs_file',
    help="Path to a json file that contains the inputs. If this argument is used, \
    then no other arguments are allowed because the values in the json file will \
    be used instead.",
    required=False)
parser.add_argument(
    '-libs',
    '--libraries',
    help="Path to the root directory of the \
    Caldera Grid project folder, from which the python libraries can be found. \
    If the argument is not present, the default location will be used.",
    required=False)
parser.add_argument(
    '-in',
    '--input_path',
    help="Path to the inputs \
    folder. If the path does not exist then it will be created. If the \
    argument is not present, the default inputs folder will be used.",
    required=False)
parser.add_argument(
    '-out',
    '--output_path',
    help="Path to the outputs \
    folder. If the path does not exist then it will be created. If the \
    argument is not present, the default outputs folder will be used.",
    required=False)
parser.add_argument(
    '-ts',
    '--time_step_sec',
    help="The timestep in seconds. Defaults to 60 seconds.",
    required=False)
parser.add_argument(
    '-start',
    '--start_time_sec',
    help="The start time in seconds. Defaults to 0 seconds.",
    required=False)
parser.add_argument(
    '-end',
    '--end_time_sec',
    help="The end time in seconds. Defaults to 86400 seconds (or 1 day).",
    required=False)
parser.add_argument(
    '-opendss',
    '--use_opendss',
    help="If 'True' or 'true', then OpenDSS will be used. If 'False' or 'false', then OpenDSS will not be used. Defaults to False.",
    required=False)
parser.add_argument(
    '-epcnmfecs',
    '--ensure_pev_charge_needs_met_for_ext_control_strategy',
    help="Ensure PEV charge needs met for ext control strategy. Specify with True or False. Defaults to False.",
    required=False)
args = vars(parser.parse_args())

# Check for a json inputs file.
if args["json_inputs_file"] != None:
    # Check that all other arguments are None
    for arg in args:
        if arg != "json_inputs_file" and args[arg] != None:
            print("Error: If a json input file is used, then no other arguments are allowed.")
            exit(1)
    # We read in the json inputs file.
    json_file = args["json_inputs_file"]
    with open(json_file) as f:
        json_dictionary = json.load(f)
        for key in json_dictionary:
            args[key] = json_dictionary[key]

# Set the path to the python libraries.
if args["libraries"] != None:
    caldera_grid_proj_dir = args["libraries"]
else:
    caldera_grid_proj_dir = path_to_here
    print("Defaulting the path to the python libraries to be in the same directory as start_execution.py")

# This should never be inserted at index = 0 because  
# the path at index = 0 should not be changed because
# some libraries require this.
# We are inserting at index 1.
index = 1
sys.path.insert( index+0, os.path.join( caldera_grid_proj_dir, "./" ) )
sys.path.insert( index+1, os.path.join( caldera_grid_proj_dir, "./libs" ) )
sys.path.insert( index+2, os.path.join( caldera_grid_proj_dir, "./source/base" ) )
sys.path.insert( index+3, os.path.join( caldera_grid_proj_dir, "./source/custom_controls" ) )
sys.path.insert( index+4, os.path.join( caldera_grid_proj_dir, "./source/ES500" ) )
sys.path.insert( index+5, os.path.join( caldera_grid_proj_dir, "./source/federates" ) )

# line below should be updated based on project
sys.path.insert( index+6, os.path.join( caldera_grid_proj_dir, "./source/customized_inputs/eMosaic" ) )

#---------------------------------

from Caldera_ICM_federate import caldera_ICM_federate
from OpenDSS_federate import open_dss_federate
from Caldera_globals import queuing_mode_enum, charge_event_queuing_inputs
from Load_inputs_federate import load_inputs_federate
from typeA_control_federate import typeA_control_federate
from typeB_control_federate import typeB_control_federate
from global_aux import container_class
from ES500_aux import ES500_aux
from get_customized_inputs import get_customized_pev_ramping
from control_strategy_A import control_strategy_A
from control_strategy_B import control_strategy_B
from control_strategy_C import control_strategy_C
from control_strategy_TE import control_strategy_TE

#================================================

if __name__ == '__main__':
    
    start = time.time()
    
    #---------------------

    if args["input_path"] != None:
        input_path = args["input_path"]
    else:
        # The default location of the 'inputs' and 'outputs
        # directories are to be in the same directory as 'start_execution.py'.
        input_path = os.path.join( path_to_here, "inputs" )
        print("Defaulting the inputs/ folder to be in the same directory as start_execution.py")
    
    if args["output_path"] != None:
        output_path = "{}".format(args["output_path"])
    else:
        # The default location of the 'inputs' and 'outputs
        # directories are to be in the same directory as 'start_execution.py'.
        output_path = os.path.join( path_to_here, "outputs" )
        print("Defaulting the outputs/ folder to be in the same directory as start_execution.py")
    
    print("Input path : {}".format(input_path))
    print("Output path : {}".format(output_path))

    #---------------------
    
    # Set the timestep.
    if args["time_step_sec"] != None:
        grid_timestep_sec = int(args["time_step_sec"])
    else:
        grid_timestep_sec = 60
    
    # Set the start time.
    if args["start_time_sec"] != None:
        start_simulation_unix_time = int(args["start_time_sec"])
    else:
        start_simulation_unix_time = 0
    
    # Set the end time.
    if args["end_time_sec"] != None:
        end_simulation_unix_time = int(args["end_time_sec"])
    else:
        end_simulation_unix_time = 1*24*3600

    # The flag to use or not use OpenDSS
    if args["use_opendss"] != None and ( (isinstance(args["use_opendss"], str) and args["use_opendss"].lower() == "true") or args["use_opendss"] == True ):
        use_opendss = True
    else:
        use_opendss = False
        
    # Other options.
    epcnmfecs = args["ensure_pev_charge_needs_met_for_ext_control_strategy"]
    if epcnmfecs != None and ( (isinstance(epcnmfecs, str) and epcnmfecs.lower() == "true") or epcnmfecs == True ):
            ensure_pev_charge_needs_met_for_ext_control_strategy = True
    else:
        ensure_pev_charge_needs_met_for_ext_control_strategy = False

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
    
    working_dir = os.getcwd()
    io_dir = container_class()
    io_dir.base_dir = caldera_grid_proj_dir
    io_dir.inputs_dir = os.path.join( working_dir, input_path )
    io_dir.outputs_dir = os.path.join( working_dir, output_path )
    
    if not os.path.exists(io_dir.inputs_dir):
        print("Input directory does not exist", io_dir.inputs_dir)
        exit()
        
    shutil.rmtree(io_dir.outputs_dir, ignore_errors=True)
    os.makedirs(io_dir.outputs_dir, exist_ok=True)
    
    #---------------------
    
    num_of_federates = 1    # Load_Input_Files
    num_of_federates += 1   # Caldera_ICM
    num_of_federates += 1   # OpenDSS
    num_of_federates += 1   # Caldera_ES500
    #num_of_federates += 1   # control_strategy_A
    #num_of_federates += 1   # control_strategy_B
    #num_of_federates += 1   # control_strategy_C
    num_of_federates += 1   # control_strategy_transactive_energy
    
    broker = subprocess.Popen(['helics_broker', '--loglevel=no_print', '-f{}'.format(num_of_federates)])
    #broker = subprocess.Popen(['helics_broker', '-f{}'.format(num_of_federates)])
    
    #---------------------
    
    processes = []

    # Load Input Files Federate
    json_config_file_name = 'Load_Input_Files.json'
    p = Process(target=load_inputs_federate, args=(io_dir, json_config_file_name, simulation_time_constraints,), name="load_inputs_federate")
    processes.append(p)
    
    # Caldera ICM Federate
    json_config_file_name = 'Caldera_ICM.json'
    create_charge_profile_library = True 
    p = Process(target=caldera_ICM_federate, args=(io_dir, json_config_file_name, simulation_time_constraints, customized_pev_ramping, create_charge_profile_library, ensure_pev_charge_needs_met_for_ext_control_strategy, CE_queuing_inputs,), name="caldera_ICM_federate")
    processes.append(p)
    
    # OpenDSS Federate
    json_config_file_name = 'OpenDSS.json'
    p = Process(target=open_dss_federate, args=(io_dir, json_config_file_name, simulation_time_constraints, use_opendss,), name="open_dss_federate")
    processes.append(p)
	
    #---------------------------
    #   ES500 Control Federate
    #---------------------------
    json_config_file_name = 'Caldera_ES500.json'
    ES500_obj = ES500_aux(io_dir, simulation_time_constraints)    
    p = Process(target=typeA_control_federate, args=(io_dir, json_config_file_name, simulation_time_constraints, ES500_obj,), name="caldera_ES500_federate")
    processes.append(p)
    
    #-------------------------------
    #   Control Strategy_A Federate
    #-------------------------------
    json_config_file_name = 'control_strategy_A.json'
    CS_A_obj = control_strategy_A(io_dir, simulation_time_constraints)    
    p = Process(target=typeA_control_federate, args=(io_dir, json_config_file_name, simulation_time_constraints, CS_A_obj,), name="control_strategy_A_federate")
    #processes.append(p)
    
    #-------------------------------
    #   Control Strategy_B Federate
    #-------------------------------
    json_config_file_name = 'control_strategy_B.json'
    CS_B_obj = control_strategy_B(io_dir, simulation_time_constraints)    
    p = Process(target=typeB_control_federate, args=(io_dir, json_config_file_name, simulation_time_constraints, CS_B_obj,), name="control_strategy_B_federate")
    #processes.append(p)
    
    #-------------------------------
    #   Control Strategy_C Federate
    #-------------------------------
    json_config_file_name = 'control_strategy_C.json'
    CS_C_obj = control_strategy_C(io_dir, simulation_time_constraints)
    p = Process(target=typeB_control_federate, args=(io_dir, json_config_file_name, simulation_time_constraints, CS_C_obj,), name="control_strategy_C_federate")
    #processes.append(p)
    
    #-------------------------------
    #   Control Strategy_transactive_energy Federate
    #-------------------------------
    json_config_file_name = 'control_strategy_TE.json'
    CS_TE_obj = control_strategy_TE(io_dir, simulation_time_constraints)
    p = Process(target=typeA_control_federate, args=(io_dir, json_config_file_name, simulation_time_constraints, CS_TE_obj,), name="control_strategy_TE_federate")
    processes.append(p)

    for p in processes:
        p.start()

    for p in processes:
        p.join()
        
        
    end = time.time()
    
    print("Total simulation time = {} minutes".format((end - start)/60.0))
