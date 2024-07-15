import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import os
import sys

from scipy.linalg import solve

path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))
figures_folder = os.path.join(path_to_here, "figures")
cost_models_folder = os.path.join(figures_folder, "cost_models")

os.makedirs(cost_models_folder, exist_ok = True)

gen_min = 500.0 # (Power MW)
gen_max = 2000.0

cost_min = 39.0 # ($ per MWh)
cost_max = 221.0

x_axis_data = np.arange(gen_min, gen_max+1, 10)

# Linear

linear_data = np.array([ cost_min + (cost_max - cost_min) * ((val - gen_min) / (gen_max - gen_min))  for val in x_axis_data])

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

fig, ax = plt.subplots(1, 1)
ax.plot(x_axis_data, linear_data, label = "Linear")
ax.plot(x_axis_data, steep_cubic_data, label = "Steep-cubic")
ax.plot(x_axis_data, inverse_s_data, label = "Inverse-s")
ax.set_xlabel("Power | MW")
ax.set_ylabel("Cost | $ per MWh")
ax.legend()
ax.set_title("Power vs Cost for fossil fuel")
ax.grid()

fig.savefig(os.path.join(cost_models_folder, "cost_curves_time_vs_cost.png"), dpi = 300)