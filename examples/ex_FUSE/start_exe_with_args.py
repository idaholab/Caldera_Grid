import subprocess
import sys
import os
import time
import glob

path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))

sim = sys.argv[1]

# Prepare the command and run it.
path_to_libs = os.path.join( path_to_here, "../../" )
input_directory = os.path.join(path_to_here, "inputs", sim)
output_directory = os.path.join(path_to_here, "outputs", sim)
figures_directory = os.path.join( path_to_here, "figures/" )
timestep = 1*60
starttime = (245)*3600
endtime = (260)*3600
command = [
    "python", os.path.join( path_to_here, "./start_execution.py" ),
    "-libs", path_to_libs,
    "-in", input_directory,
    "-out", output_directory,
    "-fig", figures_directory,
    "-hel", os.path.join( input_directory, "helics_config" ),
    "-ts", str(timestep),
    "-start", str(starttime),
    "-end", str(endtime),
    "-opendss","False",
    "-epcnmfecs","True",
]
print("Running command:  ",command)
subprocess.call(command)