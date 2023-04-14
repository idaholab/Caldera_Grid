import sys
import os
path_to_here = os.path.dirname(sys.argv[0])
if( len(path_to_here) > 0 ):
    path_to_here += "/"
else:
    path_to_here = "./"

# Prepare the command and run it.
root_command = "python start_execution.py"
path_to_libs = path_to_here + "../../"
input_directory = path_to_here + "inputs/"
output_directory = path_to_here + "outputs/"
timestep = 60
starttime = 0*24*3600 + 3600
endtime = 1*24*3600 + 3600
command = root_command + \
            " -libs " + path_to_libs + \
            " -in " + input_directory + \
            " -out " + output_directory + \
            " -ts " + str(timestep) + \
            " -start " + str(starttime) +  \
            " -end " + str(endtime)
print("Running command:  ",command)
os.system( command )
