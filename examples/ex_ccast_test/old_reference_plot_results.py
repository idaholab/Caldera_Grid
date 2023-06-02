# -*- coding: utf-8 -*-
"""
Created on Tue Mar 28 22:07:05 2023

@author: CEBOM
"""

import matplotlib.pyplot as plt
import glob
import pandas as pd
import os

start = 10*24
end = 11*24

#region = "EPE"
region = "Vermont"

season = "Summer"
#season = "Winter"

root_results_dir = "./Caldera_Grid/outputs/"+region+"/"

specific_outputs_dir = "home_dominant/centralized_aggregator_demand/"
demand_df = pd.read_csv( root_results_dir + specific_outputs_dir + "real_power_profiles.csv" )
demand_df = demand_df.drop(['total_demand_kW', 'WORK', 'DESTINATION', 'HOME'], axis = 1)
demand_df = demand_df[(demand_df["simulation_time_hrs"] >= start) & (demand_df["simulation_time_hrs"] < end)]

demand = demand_df["base_load_kW"]
demand = demand/1000.0

specific_outputs_dir = "home_dominant/centralized_aggregator_solar/"
inverse_solar_df = pd.read_csv(root_results_dir + specific_outputs_dir + "real_power_profiles.csv")
inverse_solar_df = inverse_solar_df.drop(['total_demand_kW', 'WORK', 'DESTINATION', 'HOME'], axis = 1)
inverse_solar_df = inverse_solar_df[(inverse_solar_df["simulation_time_hrs"] >= start) & (inverse_solar_df["simulation_time_hrs"] < end)]

simulation_time_hrs = inverse_solar_df["simulation_time_hrs"]
simulation_time_hrs = simulation_time_hrs % 24

inverse_solar = inverse_solar_df["base_load_kW"]
solar = - inverse_solar + inverse_solar.max()
solar = solar/1000.0
inverse_solar = inverse_solar / 1000.0

net_demand = demand - solar

# Looking at these initial curves, just to be sure they look right:
if( False ):
    plt.plot(demand,        color="red")
    plt.plot(inverse_solar, color="orange")
    plt.plot(solar,         color="yellow")
    plt.plot(net_demand,    color="blue")
    plt.title("demand[red],inv_sol[orange],solar[yellow],net_demand[blue]")
    plt.show()
    exit()

#==========================

files = glob.glob( root_results_dir + "*/**/real_power_profiles.csv", recursive = True)

# Making sure we collected the files we wanted:
if( False ):
    print("files:")
    print(files)
    print("files in a nice list:")
    for item in files:
        print("      ",item)
    exit()


# Collecting all the 'total_demand" columns (converted to megawatts) into a dictionary.
dfs = {}
for file in files:
    df = pd.read_csv(file)
    df = df[(df["simulation_time_hrs"] >= start) & (df["simulation_time_hrs"] < end)]
    
    # Convert the column into megawatts before storing it.
    dfs[file] = df["total_demand_kW"]/1000.0


#==========================

# Setting the y-limits used in all the plots
y_limits = (-100,1200)
use_legend = False
outputfile_EXT = ".pdf"

#==========================


scenarios = [( root_results_dir + "work_dominant/uncontrolled/real_power_profiles.csv",     "red",    "uncontrolled"     ), 
             ( root_results_dir + "work_dominant/TOU_random_night/real_power_profiles.csv", "orange", "TOU_random_night" ), 
             ( root_results_dir + "work_dominant/TOU_random_solar/real_power_profiles.csv", "green",  "TOU_random_solar" )]

fig1 = plt.figure(figsize=(8, 6))

for (scenario, color, label) in scenarios:
    plt.plot(simulation_time_hrs, dfs[scenario], color = color, label = label, lw = 2)

plt.plot(simulation_time_hrs, solar, color = "gold", label = "solar", alpha = 0.5, lw = 1.5)
plt.plot(simulation_time_hrs, demand, color = "black", label = "non-EV demand", alpha = 0.25)
plt.plot(simulation_time_hrs, net_demand, color = "grey", label = "demand minus solar", alpha = 0.25)


plt.axvspan(8, 18, facecolor='cyan', alpha=0.1, label = "solar time TOU")
plt.axvspan(0, 8, facecolor='black', alpha=0.05, label = "night time TOU")
plt.axvspan(23, 24 , facecolor='black', alpha=0.05)

fig1.suptitle(region+", "+season+" work-dominant TOU random")
plt.xlabel('simulation_time (hrs)')
plt.ylabel('power (MW)')
plt.xticks([x for x in range(0, 25, 6)])
if( use_legend ):
    plt.legend(loc = "upper left")
plt.ylim(y_limits)
outpath = "figures/"+region+"_"+season+"_workdom_TOU_random"+outputfile_EXT
os.makedirs(os.path.dirname(outpath), exist_ok=True)
fig1.savefig(outpath)
#plt.show()

#==========================

scenarios = [( root_results_dir + "work_dominant/uncontrolled/real_power_profiles.csv",                  "red",    "uncontrolled"      ), 
             ( root_results_dir + "work_dominant/centralized_aggregator_demand/real_power_profiles.csv", "orange", "centralized"       ), 
             ( root_results_dir + "work_dominant/centralized_aggregator_solar/real_power_profiles.csv",  "green",  "centralized_solar" )]

fig2 = plt.figure(figsize=(8, 6))



for (scenario, color, label) in scenarios:
    plt.plot(simulation_time_hrs, dfs[scenario], color = color, label = label, lw = 2)

plt.plot(simulation_time_hrs, solar, color = "gold", label = "solar", alpha = 0.5)
plt.plot(simulation_time_hrs, demand, color = "black", label = "non-EV demand", alpha = 0.25)
plt.plot(simulation_time_hrs, net_demand, color = "grey", label = "demand minus solar", alpha = 0.25)


fig2.suptitle(region+", "+season+" work-dominant centralized aggregator")
plt.xlabel('simulation_time (hrs)')
plt.ylabel('power (MW)')
plt.xticks([x for x in range(0, 25, 6)])
if( use_legend ):
    plt.legend(loc = "upper left")
plt.ylim(y_limits)
outpath = "figures/"+region+"_"+season+"_workdom_centralized_aggregator"+outputfile_EXT
os.makedirs(os.path.dirname(outpath), exist_ok=True)
fig2.savefig(outpath)
#plt.show()


#==========================

scenarios = [( root_results_dir + "home_dominant/uncontrolled/real_power_profiles.csv",     "red",    "uncontrolled"     ), 
             ( root_results_dir + "home_dominant/TOU_random_night/real_power_profiles.csv", "orange", "TOU_random_night" ), 
             ( root_results_dir + "home_dominant/TOU_random_solar/real_power_profiles.csv", "green",  "TOU_random_solar" )]

fig3 = plt.figure(figsize=(8, 6))

for (scenario, color, label) in scenarios:
    plt.plot(simulation_time_hrs, dfs[scenario], color = color, label = label, lw = 2)

plt.plot(simulation_time_hrs, solar, color = "gold", label = "solar", alpha = 0.5)
plt.plot(simulation_time_hrs, demand, color = "black", label = "non-EV demand", alpha = 0.25)
plt.plot(simulation_time_hrs, net_demand, color = "grey", label = "demand minus solar", alpha = 0.25)


plt.axvspan(8, 18, facecolor='cyan', alpha=0.1, label = "solar time TOU")
plt.axvspan(0, 8, facecolor='black', alpha=0.05, label = "night time TOU")
plt.axvspan(23, 24 , facecolor='black', alpha=0.05)


fig3.suptitle(region+", "+season+" home-dominant TOU random")
plt.xlabel('simulation_time (hrs)')
plt.ylabel('power (MW)')
plt.xticks([x for x in range(0, 25, 6)])
if( use_legend ):
    plt.legend(loc = "upper left")
plt.ylim(y_limits)
outpath = "figures/"+region+"_"+season+"_homedom_TOU_random"+outputfile_EXT
os.makedirs(os.path.dirname(outpath), exist_ok=True)
fig3.savefig(outpath)
#plt.show()


#==========================


scenarios = [( root_results_dir + "home_dominant/uncontrolled/real_power_profiles.csv",                  "red",    "uncontrolled"      ), 
             ( root_results_dir + "home_dominant/centralized_aggregator_demand/real_power_profiles.csv", "orange", "centralized"       ), 
             ( root_results_dir + "home_dominant/centralized_aggregator_solar/real_power_profiles.csv",  "green",  "centralized_solar" )]

fig4 = plt.figure(figsize=(8, 6))



for (scenario, color, label) in scenarios:
    plt.plot(simulation_time_hrs, dfs[scenario], color = color, label = label, lw = 2)

plt.plot(simulation_time_hrs, solar, color = "gold", label = "solar", alpha = 0.5)
plt.plot(simulation_time_hrs, demand, color = "black", label = "non-EV demand", alpha = 0.25)
plt.plot(simulation_time_hrs, net_demand, color = "grey", label = "demand minus solar", alpha = 0.25)

fig4.suptitle(region+", "+season+" home-dominant centralized aggregator")
plt.xlabel('simulation_time (hrs)')
plt.ylabel('power (MW)')
plt.xticks([x for x in range(0, 25, 6)])
if( use_legend ):
    plt.legend(loc = "upper left")
plt.ylim(y_limits)
outpath = "figures/"+region+"_"+season+"_homedom_centralized_aggregator"+outputfile_EXT
os.makedirs(os.path.dirname(outpath), exist_ok=True)
fig4.savefig(outpath)
#plt.show()


# Show all the plots at the end.
if( True ):
    plt.show()
