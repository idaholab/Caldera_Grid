Welcome to Caldera Grid's documentation!
===================================
*Caldera Gird*:
-------------
Caldera and OpenDSS co-simulation platform using HELICS

*Overview*:
-----------
Caldera Grid enables modeling EV charging on the electric grid. Caldera Grid co-simulation platform is built using HELICS (Hierarchical Engine for Large Scale Infrastructure Co-simulation) and cosimulates Caldera ICM with OpenDSS. The platfrom also provides an interface to apply custom control strategies to EV charge events.

**Installation**:
=============
**Windows**:
------------
The installation approach for windows is only a suggested approach which is well tested.

**Prerequisites**:
----------------
Caldera Grid has the following requirements to be able to compile on windows.

1)Install git for windows.  


2)Install Anaconda.  


3)Install visual studio with C++ and cmake. 


*Anaconda environment setup:*  
----------------------------------

1)Open anaconda prompt

   **Create a new conda environment**

3)conda create -n Caldera python=3.9      # (recommended version >= 3.7.0)

4)Activate the new conda environment

5)conda activate Caldera

6)Install required python packages

7)conda install pybind11                  # (recommended version >= 2.10)

8)conda install numpy                     # (recommended version >= 1.23.5)

9)conda install pandas                    # (recommended version >= 1.5.2)

10)conda install cvxopt                    # (recommended version >= 1.2.6)

11)pip install "OpenDSSDirect.py[extras]"  # (recommended version >= 0.7.0)

12)pip install helics                      # (recommended version >= 3.4.0)


Download Caldera Grid
open git for windows
navigate to desired folder where you would like to download Caldera Grid
cd <path_to_desired_download_folder>
clone Caldera Grid from Github
git clone https://github.com/idaholab/Caldera_Grid.git
Swich to develop branch. Develop branch has the most recent updates and bug fixes for Caldera Grid
git switch develop
Compile Caldera Grid
Open the downloaded Caldera Grid folder in Visual Studio
File -> Open -> Folder -> <path_to_Caldera_Grid>
Open CMakeSettings.json
Project -> CMake Settings
Set flages for the cmake compilation process in the CMake command arguments test box
 -DPROJECT=eMosaic -DICM=ON -DPYTHON_EXECUTABLE=<path_to_anaconda3>\envs\<env_name>\python.exe -Dpybind11_DIR=<path_to_anaconda3>\envs\<env_name>\Library\share\cmake\pybind11
PROJECT - options are DirectXFC, eMosaic and EVs_at_Risk
ICM - needs to be ON, Caldera_Grid needs ICM module
Configure CMake
Saving CMakeSettings.json will kick off the configuration in the output tab
Build libraries
build -> build all
Install libraries
build -> Install Grid
On Ubuntu Linux
First, installed Ubuntu.
sudo apt inatall git
mkdir ~/Documents/dev
Checked out the repos, put in ~/Documents/dev
sudo apt install cmake
sudo apt install build-essential

cd ~/Documents/
wget https://repo.anaconda.com/miniconda/Miniconda3-py39_4.12.0-Linux-x86_64.sh
bash Miniconda3-py39_4.12.0-Linux-x86_64.sh

(installed anaconda)
(then restarted the terminal)

conda create -n caldera python=3.7
conda activate caldera
pip install helics
conda install pandas numpy scipy cvxopt
pip install cython
pip install 'OpenDSSDirect.py[extras]'
pip install "pybind11[global]"

cd Caldera_Grid
git switch develop
mkdir build
cd build
cmake -DPROJECT=eMosaic -DICM=ON ../
make -j 4
make install
Notes for macOS
To install anaconda:
-------
brew install --cask anaconda
source /usr/local/anaconda3/bin/activate
conda create -n caldera python=3.7
conda activate caldera
Running Caldera Grid
Open Anaconda prompt

Navigate to project folder

cd <path_to_Caldera_Grid>
Activate Anaconda environment

conda activate Caldera
Run simulation

python start_execution.py
start_execution.py is set up to run a simple example of EVs charging on the IEEE 34 node test feeder.
NOTE : If the excution takes longer time to run, Try using release mode to build

Usage
Please refer to usage documentation to learn on how to use the tool.
