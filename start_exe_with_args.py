import subprocess
import sys
import os
path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))

# Prepare the command and run it.
path_to_libs = os.path.join( path_to_here, "./" )
input_directory = os.path.join( path_to_here, "inputs/" )
output_directory = os.path.join( path_to_here, "outputs/" )
timestep = 1*60
starttime = 6*3600
endtime = 25*3600

command = [
    "python", os.path.join( path_to_here, "./start_execution.py" ),
    "-libs", path_to_libs,
    "-in", input_directory,
    "-out", output_directory,
    "-ts", str(timestep),
    "-start", str(starttime),
    "-end", str(endtime),
    "-opendss","False",
    "-epcnmfecs","True",
]
print("Running command:  ",command)
subprocess.call(command)
