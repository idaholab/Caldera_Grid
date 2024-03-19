import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json

from scipy.linalg import solve


gen_min = 500.0
gen_max = 2000.0

cost_min = 39.0
cost_max = 221.0

x_axis_data = np.arange(gen_min, gen_max, 10)

# Linear

linear_data = np.array([ cost_min + (cost_max - cost_min) * ((val - gen_min) / (gen_max - gen_min))  for val in x_axis_data])

linear_data = linear_data*x_axis_data*5*60/3600.0

# steep_cubic

dxdy_at_gen_min = 0
dxdy_at_gen_max = 0.35


A = [[gen_min**0, gen_min**1,   gen_min**2,     gen_min**3], 
     [0,          1*gen_min**0, 2*gen_min**1,   3*gen_min**2], 
     [gen_max**0, gen_max**1,   gen_max**2,     gen_max**3],
     [0,          1*gen_max**0, 2*gen_max**1,   3*gen_max**2]]

b = [[cost_min],
     [dxdy_at_gen_min],
     [cost_max],
     [dxdy_at_gen_max]]

C = solve(A, b)

steep_cubic_data = C[0][0] * x_axis_data**0 + C[1][0] * x_axis_data**1 + C[2][0] * x_axis_data**2 + C[3][0] * x_axis_data**3

steep_cubic_data = steep_cubic_data*x_axis_data*5*60/3600.0

# inverse_s

dxdy_at_gen_min = 0.3
dxdy_at_gen_max = 0.3


A = [[gen_min**0, gen_min**1,   gen_min**2,     gen_min**3], 
     [0,          1*gen_min**0, 2*gen_min**1,   3*gen_min**2], 
     [gen_max**0, gen_max**1,   gen_max**2,     gen_max**3],
     [0,          1*gen_max**0, 2*gen_max**1,   3*gen_max**2]]

b = [[cost_min],
     [dxdy_at_gen_min],
     [cost_max],
     [dxdy_at_gen_max]]

C = solve(A, b)

inverse_s_data = C[0][0] * x_axis_data**0 + C[1][0] * x_axis_data**1 + C[2][0] * x_axis_data**2 + C[3][0] * x_axis_data**3
inverse_s_data = inverse_s_data*x_axis_data*5*60/3600.0
#inverse_s_data = inverse_s_data*x_axis_data*60/3600.0

fig, ax = plt.subplots(1, 1)
ax.plot(x_axis_data, linear_data, label = "Linear")
ax.plot(x_axis_data, steep_cubic_data, label = "Steep-cubic")
ax.plot(x_axis_data, inverse_s_data, label = "Inverse-s")
ax.set_xlabel("Energy | MWh")
ax.set_ylabel("Cost | $ per MWh")
ax.legend()
ax.set_title("Power vs Cost for fossil fuel")
ax.grid()
plt.show()

#fig.savefig(os.path.join(self.figures_folder, "ff_" + df_type + "_" + solver_method + "_time_vs_cost.png"), dpi = 300)
    


# #-----------------------------------
# # cost models
# #-----------------------------------

# def solver(self, solver_method, df, cost_data) -> timeseries:
    
#     '''
#     Description:
#         Applies cost functions to the generation data
#     '''

#     df.columns = [column.split("|")[0].strip() for column in df.columns.to_series()]
    
#     df_type = None 
#     if df.columns[1] == "forecasted_demand":
#         df_type = "forecast"
#     elif df.columns[1] == "actual_demand":
#         df_type = "actual"
#     else:
#         raise ValueError('ERROR : Second column in input csv file should be forecasted_demand or actual_demand')
        
#     start_time_sec = round(df["time"][0] * 3600.0)
#     timestep_sec = round((df["time"][1] - df["time"][0])*3600)
    
#     # Ignore first 2 columns time and forecasted_demand/actual_demand
#     gen_types = df.columns[2:].to_series()
    
#     cost_usd_per_kWh = np.zeros(df.shape[0], dtype=float)
#     total_cost_usd = np.zeros(df.shape[0], dtype=float)
    
#     individual_costs = {}
#     for gen_type in gen_types:
        
#         gen_min = cost_data[gen_type]["gen_min"]            #MW
#         gen_max = cost_data[gen_type]["gen_max"]            #MW
#         cost_min = cost_data[gen_type]["cost_min"]          # USD per MWh
#         cost_max = cost_data[gen_type]["cost_max"]          # USD per MWh
        
#         # No cost variation
#         if abs(cost_min - cost_max) < 0.001:      # cost_min == cost_max        # nuclear and solar come under this scenario
            
#             individual_cost_function = np.full_like(total_cost_usd, cost_min, dtype=float)
#             total_cost_usd += individual_cost_function*df[gen_type]*timestep_sec/3600.0
        
#         # Cost variation
#         else:                                                                   # Thermal scenario
        
#             if solver_method == "linear":
                
#                 individual_cost_function = (df[gen_type] - gen_min)/(gen_max-gen_min)*(cost_max-cost_min)+ cost_min
#                 individual_costs[gen_type] = individual_cost_function
                
#                 total_cost_usd += individual_cost_function*df[gen_type]*timestep_sec/3600.0
            
#             elif solver_method == "steep_cubic":
                
#                 dxdy_at_gen_min = 0
#                 dxdy_at_gen_max = 0.35

                
#                 A = [[gen_min**0, gen_min**1,   gen_min**2,     gen_min**3], 
#                      [0,          1*gen_min**0, 2*gen_min**1,   3*gen_min**2], 
#                      [gen_max**0, gen_max**1,   gen_max**2,     gen_max**3],
#                      [0,          1*gen_max**0, 2*gen_max**1,   3*gen_max**2]]

#                 b = [[cost_min],
#                      [dxdy_at_gen_min],
#                      [cost_max],
#                      [dxdy_at_gen_max]]
                
#                 C = solve(A, b)
                
#                 individual_cost_function = C[0][0] * df[gen_type]**0 + C[1][0] * df[gen_type]**1 + C[2][0] * df[gen_type]**2 + C[3][0] * df[gen_type]**3
#                 individual_costs[gen_type] = individual_cost_function
                
#                 total_cost_usd += individual_cost_function*df[gen_type]*timestep_sec/3600.0
                
#             elif solver_method == "inverse_s":
                
#                 dxdy_at_gen_min = 0.3
#                 dxdy_at_gen_max = 0.3


#                 A = [[gen_min**0, gen_min**1,   gen_min**2,     gen_min**3], 
#                      [0,          1*gen_min**0, 2*gen_min**1,   3*gen_min**2], 
#                      [gen_max**0, gen_max**1,   gen_max**2,     gen_max**3],
#                      [0,          1*gen_max**0, 2*gen_max**1,   3*gen_max**2]]

#                 b = [[cost_min],
#                      [dxdy_at_gen_min],
#                      [cost_max],
#                      [dxdy_at_gen_max]]
 
#                 C = solve(A, b)

#                 individual_cost_function = C[0][0] * df[gen_type]**0 + C[1][0] * df[gen_type]**1 + C[2][0] * df[gen_type]**2 + C[3][0] * df[gen_type]**3
#                 individual_costs[gen_type] = individual_cost_function
                
#                 total_cost_usd += individual_cost_function*df[gen_type]*timestep_sec/3600.0
                
#             else:
                
#                 raise ValueError('ERROR : solver_method should be linear or steep_cubic or inverse_s')
        
#         #if self.plot:
#         #    fig, ax = plt.subplots(1, 1, figsize=(25, 15))
#         #
#         #    ax.plot(df[gen_type], individual_cost_function)
#         #    ax.set_xlabel("Power | MW")
#         #    ax.set_ylabel("Cost | $ per MWh")
#         #
#         #    fig.savefig("fig_" + gen_type + ".png", dpi = 300)
    
    
#     total_MWh_per_timestep = df[gen_types].sum(axis=1) * timestep_sec/3600.0
#     cost_usd_per_MWh = total_cost_usd/total_MWh_per_timestep
#     cost_usd_per_kWh = cost_usd_per_MWh/1000.0
    
#     if self.plot:
        
#         os.makedirs(self.figures_folder, exist_ok= True)
    
#         start_idx = (1*24*3600) / timestep_sec
#         end_idx = (2*24*3600) / timestep_sec
        
#         fig, ax = plt.subplots(1, 1)
#         ax.plot(df["time"], individual_costs["fossil_fuel"])
#         ax.set_xlabel("Time | hrs")
#         ax.set_ylabel("Cost | $ per kWh")
#         ax.set_title("Time vs Cost for fossil fuel with {} pricing".format(solver_method))
#         ax.grid()
#         fig.savefig(os.path.join(self.figures_folder, "ff_" + df_type + "_" + solver_method + "_time_vs_cost.png"), dpi = 300)
    
#         fig, ax = plt.subplots(1, 1)
#         ax.scatter(df["fossil_fuel"], individual_costs["fossil_fuel"])
#         ax.set_xlabel("Power | kW")
#         ax.set_ylabel("Cost | $ per kWh")
#         ax.grid()
#         fig.savefig(os.path.join(self.figures_folder, "ff_" + df_type + "_" + solver_method + "_power_vs_cost.png"), dpi = 300)
            
#     return timeseries(start_time_sec, timestep_sec, cost_usd_per_kWh)
