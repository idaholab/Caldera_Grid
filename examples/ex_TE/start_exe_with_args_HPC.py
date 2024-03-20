import subprocess
import sys
import os
import time
import glob

path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))

path_to_libs = os.path.join( path_to_here, "../../" )
input_directory = os.path.join( path_to_here, "inputs/", sys.argv[1] )
output_directory = os.path.join( path_to_here, "outputs/", sys.argv[1] )

print("start_exe_with_args_HPC input_directory:", input_directory)
print("start_exe_with_args_HPC output_directory:", output_directory)

timestep = 1*60
starttime = 12*3600
endtime = 60*3600
command = [
    "python", os.path.join( path_to_here, "./start_execution.py" ),
    "-libs", path_to_libs,
    "-in", input_directory,
    "-out", output_directory,
    "-hel", os.path.join( input_directory, "helics_config" ),
    "-ts", str(timestep),
    "-start", str(starttime),
    "-end", str(endtime),
    "-opendss","False",
    "-epcnmfecs","True",
]
print("Running command:  ",command)
subprocess.call(command)