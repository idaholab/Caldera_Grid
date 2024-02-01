# -*- coding: utf-8 -*-
"""
Created on Wed Jan 31 21:24:30 2024

@author: CEBOM
"""

import pandas as pd
import json


df_forecast = pd.read_csv("forecasted_demand.csv")
with open("generation_cost.json", "r") as f_cost:
    cost_json = json.load(f_cost)
    
generation_types = df_forecast.columns[1:].to_series()

df_forecast["cost"] = df_forecast["time_hrs"] * 0.0
for gen_type in generation_types:    
    df_forecast["cost"] += df_forecast[gen_type] * cost_json[gen_type]["LCOE"]

df_forecast["cost"] = df_forecast["cost"] * 5/60
df_forecast["cost"] = df_forecast["cost"] / 1000

#%%


data_timestep_sec = 5
req_timestep_sec = 15

if not ((data_timestep_sec == req_timestep_sec) or \
   (data_timestep_sec % req_timestep_sec == 0.0) or \
   (req_timestep_sec % data_timestep_sec == 0.0)):
    print("Error")
else:
    print("Perfect")
