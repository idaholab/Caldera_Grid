import subprocess
import sys
import os
import time
import glob

path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))

# folders = ["uncontrolled", "linear/choppy", "linear/smooth", "steep_cubic/choppy", "steep_cubic/smooth", "inverse_s/choppy", "inverse_s/smooth"]

folders = []
folders.append("inputs/uncontrolled/")
folders.extend(glob.glob("inputs/good_forecast/*/*/"))
#folders.extend(glob.glob("inputs/bad_forecast/*/*/"))

folders = [folder.replace("inputs/", "") for folder in folders]

for folder in folders:

    # Prepare the command and run it.
    path_to_libs = os.path.join( path_to_here, "../../" )
    input_directory = os.path.join( path_to_here, "inputs/", folder )
    output_directory = os.path.join( path_to_here, "outputs/", folder )
    timestep = 1*60
    starttime = 23*3600
    endtime = 49*3600
    print("Here")
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

    time.sleep(5)