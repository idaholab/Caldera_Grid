#!/bin/bash

#PBS -N OE_TE
#PBS -l select=1:ncpus=40
#PBS -l walltime=6:00:00
#PBS -M manojkumar.cebolsundarrajan@inl.gov
#PBS -P Caldera
#PBS -k doe 
#PBS -j oe
#PBS -m bea

module load apptainer/1.2.2

cd $PBS_O_WORKDIR

echo $folder

singularity exec /projects/Caldera/Singularity_Image/SingularityEnv_2023_09_13/FUSE_environment.simg python start_exe_with_args_HPC.py $folder