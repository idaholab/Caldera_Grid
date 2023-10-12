# -*- coding: utf-8 -*-
"""
Created on Sat May 20 22:27:35 2023

@author: CEBOM
"""

import glob
import pandas as pd
import matplotlib.pyplot as plt
import os

files = glob.glob("outputs_original/*.csv")

error = False

for original_file in files:
    equivalent_file = "outputs/" + os.path.split(original_file)[1]
    
    original_df = pd.read_csv(original_file)
    new_df = pd.read_csv(equivalent_file)
    
    columns = original_df.columns
    
    for column in columns:
        threshold = 0.07    # in percent
        
        percent_diff = (new_df[column] - original_df[column]) / original_df[column]
        
        num_error = percent_diff[abs(percent_diff) > threshold].count()
        error_rate = (num_error/percent_diff.size)*100
        
        if error_rate < threshold:    # error rate below threshold%
            print("{} The column {} is equal within the tolerance.".format(os.path.split(original_file)[1].split(".")[0], column))
        else:
            print("{} The column {} is not equal within the tolerance.".format(os.path.split(original_file)[1].split(".")[0], column))
 
        fig = plt.figure(figsize=(8, 6))
        
        plt.plot([x for x in range(percent_diff.size)], abs(percent_diff), label = "percent_diff")
        plt.plot([x for x in range(percent_diff.size)], original_df[column], label = "original")
        plt.plot([x for x in range(percent_diff.size)], new_df[column], label = "new")
        
        plt.title(os.path.split(original_file)[1].split(".")[0]+"_"+column)
        plt.legend()
        plt.show()
        
        fig.savefig(os.path.split(original_file)[1].split(".")[0]+"_"+column)  
        error = False

if(error == True):
    exit(1)    
