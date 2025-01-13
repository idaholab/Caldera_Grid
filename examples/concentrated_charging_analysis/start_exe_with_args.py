import subprocess
import sys
import os
import time
import glob

path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))
project_dir = os.path.join( path_to_here, "../../" )
grid_source_dir = os.path.join( project_dir)

sim = sys.argv[1]

if len(sys.argv) == 5:
    starttime = int(sys.argv[2]) 
    endtime = int(sys.argv[3])
    timestep = int(sys.argv[4])
else:
    starttime = 5*60  # 1 minute
    endtime = 34*24*3600 # 7 days
    timestep = 1*60

# Prepare the command and run it.
input_directory = os.path.join(path_to_here, "inputs", sim)
output_directory = os.path.join(path_to_here, "outputs", sim)
figures_directory = os.path.join( path_to_here, "figures/" )
helics_directory = os.path.join( path_to_here, "helics_config" )

command = [
    "python", os.path.join( path_to_here, "./start_execution.py" ),
    "-grid", grid_source_dir,
    "-libs", project_dir,
    "-in", input_directory,
    "-out", output_directory,
    "-fig", figures_directory,
    "-hel", helics_directory,
    "-ts", str(timestep),
    "-start", str(starttime),
    "-end", str(endtime),
    "-opendss","False",
    "-epcnmfecs","True",
]
print("Running command:  ",command)
subprocess.call(command)
