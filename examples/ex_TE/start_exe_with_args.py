import subprocess
import sys
import os
import time
import glob

path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))

# folders = ["uncontrolled", "linear/choppy", "linear/smooth", "steep_cubic/choppy", "steep_cubic/smooth", "inverse_s/choppy", "inverse_s/smooth"]

folders = []
folders.extend(glob.glob(os.path.join(path_to_here,"inputs/*/uncontrolled/")))
folders.extend(glob.glob(os.path.join(path_to_here,"inputs/*/time_of_use/")))

folders.extend(glob.glob(os.path.join(path_to_here,"inputs/*/good_forecast/linear/*/")))
folders.extend(glob.glob(os.path.join(path_to_here,"inputs/*/bad_forecast/linear/*/")))

#folders.extend(glob.glob(os.path.join(path_to_here,"inputs/good_forecast/*/*/")))
#folders.extend(glob.glob(os.path.join(path_to_here,"inputs/bad_forecast/*/*/")))

for input_folder in folders:
    print("folder: ",input_folder)

    # Prepare the command and run it.
    path_to_libs = os.path.join( path_to_here, "../../" )
    input_directory = input_folder
    output_directory = input_folder.replace("inputs", "outputs")
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

    time.sleep(5)