# -*- coding: utf-8 -*-
"""
Created on Thu Jan  9 23:16:07 2025

@author: CEBOM
"""

import pandas as pd
import glob


files = glob.glob("inputs/half/**/SE_*.csv")
files.extend(glob.glob("inputs/immediate/**/SE_*.csv"))
files.extend(glob.glob("inputs/scheduled/**/SE_*.csv"))

for file in files:
    df = pd.read_csv(file)

    # csv file has index column present. 
    # Solution df.to_csv(file, index = False)
    columns = ['SE_id', 'SE_type', 'lon', 'lat', 'node_id', 'SE_group', 'location_type']
    df = df[columns]
    df['location_type'] = 'O'
    df.to_csv(file, index = False)

files = glob.glob("inputs/half/**/CE_ICM.csv")
files.extend(glob.glob("inputs/immediate/**/CE_ICM.csv"))
files.extend(glob.glob("inputs/scheduled/**/CE_ICM.csv"))

for file in files:
    df = pd.read_csv(file)

    # csv file doesn't have NA for control strategy. 
    # Solution pd.read_csv(filename, keep_default_na = False) usually fixes the issue
    df['ES_strategy'] = 'NA'
    df['VS_strategy'] = 'NA'
    df['Ext_strategy'] = 'NA'

    # Some events have end_time smaller than park time 
    df = df[df['end_time_prk'] -  df['start_time'] > 0.001]
    df = df[df['soc_f'] -  df['soc_i'] > 0.001]
    
    df.to_csv(file, index = False)