import subprocess
import sys
import os
path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))

# Prepare the command and run it.
path_to_libs = os.path.join( path_to_here, "../../" )
input_directory = os.path.join( path_to_here, "inputs/" )
output_directory = os.path.join( path_to_here, "outputs/" )
timestep = 60
starttime = 0*24*3600 + 3600
endtime = 1*24*3600 + 3600

command = [
    "python", os.path.join( path_to_here, "../../start_execution.py" ),
    "-libs", path_to_libs,
    "-in", input_directory,
    "-out", output_directory,
    "-ts", str(timestep),
    "-start", str(starttime),
    "-end", str(endtime),
]
print("Running command:  ",command)
subprocess.call(command)
