import subprocess
import glob
import os
import sys

path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))

folders = []

folders.append(os.path.join(path_to_here,"inputs/uncontrolled/"))
folders.append(os.path.join(path_to_here,"inputs/time_of_use/"))

folders.extend(glob.glob(os.path.join(path_to_here,"inputs/good_forecast/*/*/")))
folders.extend(glob.glob(os.path.join(path_to_here,"inputs/bad_forecast/*/*/")))

folders = [folder.replace(os.path.join(path_to_here, "inputs/"), "") for folder in folders]

for folder in folders[:]:
    
    subprocess.call("qsub -v folder=\"{}\" job.sh".format(folder), shell = True)
    print("job {} submitted".format(folder))