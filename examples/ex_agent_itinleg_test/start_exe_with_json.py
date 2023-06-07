import subprocess
import json
import sys
import os
path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))

# The arguments that go into the json file.
path_to_libs = os.path.join( path_to_here, "../../" )
input_directory = os.path.join( path_to_here, "inputs/" )
output_directory = os.path.join( path_to_here, "outputs/" )

json_dict = dict()
json_dict["libraries"] = path_to_libs
json_dict["input_path"] = input_directory
json_dict["output_path"] = output_directory
json_dict["time_step_sec"] = 15
json_dict["start_time_sec"] = 1*24*3600
json_dict["end_time_sec"] = 2*24*3600
json_dict["use_opendss"] = False
json_dict["ensure_pev_charge_needs_met_for_ext_control_strategy"] = False
json_path = os.path.join( path_to_here, "simulation_args.json" )
with open(json_path, "w") as outfile:
    json_formatted_str = json.dumps(json_dict, indent=4)
    outfile.write(json_formatted_str)

# Prepare the command and run it.
command = [
    "python",
    os.path.join( path_to_here, "../../start_execution.py" ),
    "-json",
    json_path,
]
print("Running command:  ",command)
subprocess.call(command)
