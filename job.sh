#!/usr/bin/bash

#PBS -N FUSE_milestone
#PBS -l select=1:ncpus=48
#PBS -l walltime=12:00:00
#PBS -M manojkumar.cebolsundarrajan@inl.gov
#PBS -P Caldera
#PBS -j oe

echo module load conda/init
module load conda/init

echo conda activate ${condenvname}
conda activate ${condenvname}

echo cd $PBS_O_WORKDIR
cd $PBS_O_WORKDIR

echo ${io}

echo "starting simulation"
echo python start_execution.py -io ${io}
python start_execution.py -io ${io}
echo "done simulation"

