Welcome to Caldera Grid
===================================
**Caldera Gird**:
-------------
Caldera and OpenDSS co-simulation platform using HELICS

**Overview**:
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

1) Install git for windows.  


2) Install Anaconda.  


3) Install visual studio with C++ and cmake. 


**Anaconda environment setup:** 
----------------------------------

1) Open anaconda prompt

2) Create a new conda environment

.. code-block:: bash

  conda create -n Caldera python=3.9      # (recommended version >= 3.7.0)

4) Activate the new conda environment

.. code-block:: bash

  conda activate Caldera
 
6) Install required python packages

.. code-block:: bash

  conda install pybind11                  # (recommended version >= 2.10)
  conda install numpy                     # (recommended version >= 1.23.5)
  conda install pandas                    # (recommended version >= 1.5.2)
  conda install cvxopt                    # (recommended version >= 1.2.6)
  pip install "OpenDSSDirect.py[extras]"  # (recommended version >= 0.7.0)
  pip install helics                      # (recommended version >= 3.4.0)
  


**Download Caldera Grid**

1) open git for windows.

2) navigate to desired folder where you would like to download Caldera Grid

.. code-block:: bash

  cd <path_to_desired_download_folder>

3) clone Caldera Grid from Github

.. code-block:: bash

  git clone https://github.com/idaholab/Caldera_Grid.git

4) Switch to develop branch. Develop branch has the most recent updates and bug fixes for Caldera Grid

.. code-block:: bash

  git switch develop

**Compile Caldera Grid**

1) Open the downloaded Caldera Grid folder in Visual Studio

.. code-block:: bash

  File -> Open -> Folder -> <path_to_Caldera_Grid>

2) Open CMakeSettings.json

.. code-block:: bash

   Project -> CMake Settings

3) Set flages for the cmake compilation process in the CMake command arguments test box

.. code-block:: bash

  -DPROJECT=eMosaic -DICM=ON -DPYTHON_EXECUTABLE=<path_to_anaconda3>\envs\<env_name>\python.exe -Dpybind11_DIR=<path_to_anaconda3>\envs\ 
   <env_name>\Library\share\cmake\pybind11

PROJECT - options are DirectXFC, eMosaic and EVs_at_RiskICM - needs to be ON, Caldera_Grid needs ICM module

4) Configure CMake
  Saving CMakeSettings.json will kick off the configuration in the output tab

5) Build libraries

.. code-block:: bash

  build -> build all

6) Install libraries

.. code-block:: bash
  
  build -> Install Grid


**On Ubuntu Linux**
-----------------------

.. code-block:: bash
  
   First, installed Ubuntu.
 
   sudo apt inatall git

   mkdir ~/Documents/dev

   **Checked out the repos, put in ~/Documents/dev**

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

  pip install

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
------------------
To install anaconda:
-------------------

.. code-block:: bash

    brew install --cask anaconda

    source /usr/local/anaconda3/bin/activate

    conda create -n caldera python=3.7

    conda activate caldera

**Running Caldera Grid**
-----------------------------
1) Open Anaconda prompt

2) Navigate to project folder

.. code-block:: bash

  cd <path_to_Caldera_Grid>

3) Activate Anaconda environment

.. code-block:: bash

  conda activate Caldera

4) Run simulation

.. code-block:: bash

  python start_execution.py

**start_execution.py is set up to run a simple example of EVs charging on the IEEE 34 node test feeder.**

**NOTE :** If the excution takes longer time to run, Try using release mode to build

**Usage**
------------
Please refer to  `usage documentation <https://hpcgitlab.hpc.inl.gov/caldera_charge/caldera_charge_grid/-/raw/main/docs/Caldera-OpenDSS%20simulation%20platform.pptx>`_ for more details.
