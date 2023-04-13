#!/bin/bash

#PBS -N FUSE_milestone
#PBS -l select=1:ncpus=48
#PBS -l walltime=12:00:00
#PBS -M manojkumar.cebolsundarrajan@inl.gov
#PBS -P Caldera
#PBS -j oe

module load conda/init
conda activate Caldera

cd $PBS_O_WORKDIR

echo ${io}

echo "starting simulation"
python start_execution.py -io ${io}
echo "done simulation"

