# -*- coding: utf-8 -*-
"""
Created on Sun May  5 17:41:03 2024

@author: CEBOM
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import glob 
import os

def plot_histogram(filename, ylims = None):
    
    histogram_type = ""
    data_start_time = -1
    data_time_step = -1
    data = []
    
    f = open(filename, "r")
    
    # line 1
    first_line = f.readline()
    first_line_split = first_line.split(",")
    histogram_type = first_line_split[1]
    
    # line 2
    second_line = f.readline()
    second_line_split = second_line.split(",")
    data_start_time = float(second_line_split[1])
    
    # line 3
    third_line = f.readline()
    third_line_split = third_line.split(",")
    data_time_step = float(third_line_split[1])
    
    # line 4, dummy line
    f.readline()
    
    while True:
        
        line = f.readline()
        
        if not line:
            break
    
        line_split = line.split(",")
        data.append(float(line_split[0]))
        
    
    df = pd.DataFrame()
    df["x_axis"] = np.arange(data_start_time, data_start_time + data_time_step * len(data), data_time_step)
    df["y_axis"] = data
    
    if histogram_type == "park_start_time_enum" or histogram_type == "park_duration_enum":
        df["x_axis"] = df["x_axis"]/3600.0
        
    f.close()
    
    fig, ax = plt.subplots(1, 1)

    ax.plot(df["x_axis"], df["y_axis"])
    
    print(filename)
    title = filename.split(os.sep)[1].replace(".csv", "")
    ax.set_title(title)
    if(ylims):
        ax.set_ylim(ylims[0], ylims[1])
    
    fig.savefig(title, dpi = 500)

filenames = glob.glob("L2_Work\park_start_time_*.csv")

for filename in filenames:
    plot_histogram(filename, (0, 2200))
    

filenames = glob.glob("L2_Work\park_duration_*.csv")

for filename in filenames:
    plot_histogram(filename)
    
filenames = glob.glob("L2_Work\charge_end_soc.csv")

for filename in filenames:
    plot_histogram(filename)
    
filenames = glob.glob("L2_Work\charge_size_soc.csv")

for filename in filenames:
    plot_histogram(filename)