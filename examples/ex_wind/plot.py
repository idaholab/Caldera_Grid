# -*- coding: utf-8 -*-
"""
Created on Mon May 13 11:23:51 2024

@author: CEBOM
"""

import pandas as pd
import matplotlib.pyplot as plt 
import glob

files = glob.glob("outputs/**/real_power_profiles.csv")

fig, ax = plt.subplots(1, 1, figsize=(15, 7))

for file in files:
    
    df = pd.read_csv(file)
    ax.plot(df["simulation_time_hrs"], df["total_demand_kW"])
    ax.set_xlim(24, 48)
    ax.set_xticks([x for x in range(24, 49, 6)])