import subprocess
import glob
import os
import sys
import time

path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))

if len(sys.argv) < 2:
    print("Error: The script run_all.py takes 1 argument, and it should be local or HPC depending on the environment being run")
    exit()

if sys.argv[1] != "HPC" and sys.argv[1] != "local":
    print("Error: The script run_all.py takes 1 argument, and it should be local or HPC depending on the environment being run")
    exit()

sim_env = sys.argv[1]

sims_to_run = []
sims_to_run.append(os.path.join("work"))
#sims_to_run.extend(os.path.join("home_dynamic"))
#sims_to_run.extend(os.path.join("work_dynamic"))
#sims_to_run.extend(os.path.join("home_uncontrolled"))
#sims_to_run.extend(os.path.join("work_uncontrolled"))

for sim in sims_to_run:

    if sim_env == "HPC":
        subprocess.call("qsub -v folder=\"{}\" job.sh".format(sim), shell = True)
        print("job {} submitted".format(sim))
    
    if sim_env == "local":
        subprocess.call("python start_exe_with_args.py \"{}\" ".format(sim), shell = True)
        time.sleep(5)