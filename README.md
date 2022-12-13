# Caldera_Charge_Grid

Caldera and OpenDSS co-simulation platform using HELICS 

## Overview
Caldera Grid enables modeling EV charging on the electric grid. Caldera Grid cosimulation platform is built using HELICS (Hierarchical Engine for Large Scale Infrastructure Co-simulation) and cosimulates Caldera ICM with OpenDSS. The platfrom also provides an interface to apply custom control strategies to EV charge events.

## Prerequisites

Caldera Grid depends on `C++ compiler`, `git`, `cmake`, `python` and `pybind11` to compile.

## Installation

Get a copy of Caldera ICM.
```
git clone https://hpcgitlab.hpc.inl.gov/caldera_charge/caldera_charge_grid.git
```
If you are interested in the most up to date version of Caldera ICM, the development version is available in the `develop` branch.    
```
git switch develop
```
To install Caldera Grid using cmake
```
cd caldera_charge_grid
mkdir build
cmake -DPROJECT=<PROJECT_NAME> -DICM=<ON/OFF> ../
make
make install
```
If cmake cannot find C++ compiler, python or pybind11. They need to be pointed to its installed paths to find them. Refer to [pybind11](https://pybind11.readthedocs.io/en/stable/compiling.html#building-with-cmake) and [cmake](https://cmake.org/cmake/help/latest/guide/tutorial/index.html) documentations. 


Caldera Grid compiles the Caldera ICM submodule and installs compiled python libraries in the `libs/` folder. 

`-DPROJECT` flag is used to specify the project specific EV-EVSE models to be used. Options are `DirectXFC`, `eMosaic` and `EVs_at_Risk`. `-DICM` flag turns ON/OFF compiling `Caldera_ICM` lib. Please refer to Caldera ICM project for more information with respect to Caldera ICM compilation.

## Usage
Please refer to [usage documentation](https://hpcgitlab.hpc.inl.gov/caldera_charge/caldera_charge_grid/-/raw/main/docs/Caldera-OpenDSS%20simulation%20platform.pptx) to learn on how to use the tool.

`start_execution.py` is set up to run a simple example of EVs charging on the IEEE 34 node test feeder.

## Authors
1. Don Scoffield, Senior Research Engineer, Idaho National Laboratory
2. Manoj Sundarrajan, Research Software Developer, Idaho National Laboratory

## License
For open source projects, say how it is licensed.
