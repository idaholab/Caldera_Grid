import subprocess
import sys
import os
import time
import glob

path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))

folders = []
#folders.extend(glob.glob(os.path.join(path_to_here,"inputs/home/")))
folders.extend(glob.glob(os.path.join(path_to_here,"inputs/work/")))
#folders.extend(glob.glob(os.path.join(path_to_here,"inputs/home_uncontrolled/")))
#folders.extend(glob.glob(os.path.join(path_to_here,"inputs/work_uncontrolled/")))

for input_folder in folders:
    print("folder: ",input_folder)

    # Prepare the command and run it.
    path_to_libs = os.path.join( path_to_here, "../../" )
    input_directory = input_folder
    output_directory = input_folder.replace("inputs", "outputs")
    figures_directory = os.path.join( path_to_here, "figures/" )
    timestep = 1*60
    starttime = (198)*3600
    endtime = (200)*3600
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

    time.sleep(5)