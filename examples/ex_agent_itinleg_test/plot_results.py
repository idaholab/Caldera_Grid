import matplotlib.pyplot as plt
import glob
import pandas as pd
import sys
import os
path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))

outputs_dir = os.path.join( path_to_here, "./outputs/" ) 

df = pd.read_csv( os.path.join( outputs_dir, "real_power_profiles.csv" ) )

base_load_kW = df["base_load_kW"]
base_load_MW = base_load_kW/1000.0

total_demand_kW = df["total_demand_kW"]
total_demand_MW = total_demand_kW/1000.0

simulation_time_hrs = df["simulation_time_hrs"]
simulation_time_hrs = simulation_time_hrs % 24;

y_limits = (-0.1,3.0)
x_limits = (0.0,24.0)

fig1 = plt.figure(figsize=(12, 6))
plt.plot(simulation_time_hrs, base_load_MW,color="red")
plt.plot(simulation_time_hrs, total_demand_MW,color="blue")
plt.xlabel('simulation_time (hrs)')
plt.ylabel('power (MW)')
plt.ylim(y_limits)
plt.xlim(x_limits)
plt.xticks([x for x in range(0, 25, 6)])
plt.title("base_load_MW [red], total_demand_MW [blue]")
plt.show()
exit()




