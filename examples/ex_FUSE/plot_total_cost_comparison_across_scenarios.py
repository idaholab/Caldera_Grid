# -*- coding: utf-8 -*-
"""
Created on Mon Apr 29 07:32:39 2024

@author: CEBOM
"""

import numpy as np
import matplotlib.pyplot as plt 
import sys
import os

path_to_here = os.path.abspath(os.path.dirname(sys.argv[0]))
figures_folder = os.path.join(path_to_here, "figures")
charging_costs_figures_folder = os.path.join(figures_folder, "chargings_costs_plots")

# Good forecast
print("Good FOrecast")

scenarios = ['Scenario 0', 'Scenario 1', 'Scenario 2', 'Scenario 3', 'Scenario 4', 'Scenario 5']
uncontrolled_costs = [390.70, 392.75, 459.08, 400.35, 417.68, 563.03]
TOU_control_costs = [337.05, 339.57, 391.07, 350.55, 371.90, 545.89]
TE_control_costs = [318.77, 320.67, 357.46, 326.75, 343.98, 495.05]

TOU_reduction = []

for i in range(len(uncontrolled_costs)):
    TOU_reduction.append((TOU_control_costs[i] - uncontrolled_costs[i])*100/uncontrolled_costs[i])

TOU_reduction = np.array(TOU_reduction)

TE_reduction = []

for i in range(len(uncontrolled_costs)):
    TE_reduction.append((TE_control_costs[i] - uncontrolled_costs[i])*100/uncontrolled_costs[i])

TE_reduction = np.array(TE_reduction)


fig, ax = plt.subplots()

N = 6
ind = np.arange(N)
width = 0.25

bar1 = ax.bar(ind, uncontrolled_costs, width, color = 'r')
bar2 = ax.bar(ind+width, TOU_control_costs, width, color='b')
bar3 = ax.bar(ind+width*2, TE_control_costs, width, color = 'g') 

ax.set_xlabel("Scenarios") 
ax.set_ylabel('Total Charging Costs ($)') 
ax.set_title("Good Forecast Charging Costs")

ax.set_xticks(ind+width, scenarios)
ax.legend( (bar1, bar2, bar3), ('Uncontrolled', 'TOU Controlled', 'TE Controlled') )

fig_file_name = "good_forecast_charging_costs.png"

os.makedirs(charging_costs_figures_folder, exist_ok = True)
fig.savefig( os.path.join(charging_costs_figures_folder, fig_file_name), dpi = 300)


# min and max are interchanged here because the reductions are in negative values.
print("TOU Random Max reduction : {} scenario : {}".format(TOU_reduction.min(), scenarios[TOU_reduction.argmin()]))
print("TOU Random Min reduction : {} scenario : {}".format(TOU_reduction.max(), scenarios[TOU_reduction.argmax()]))
print("TOU Random Average reduction : {}".format(TOU_reduction.mean()))

print("TE Average Max reduction : {} scenario : {}".format(TE_reduction.min(), scenarios[TE_reduction.argmin()]))
print("TE Average Min reduction : {} scenario : {}".format(TE_reduction.max(), scenarios[TE_reduction.argmax()]))
print("TE Average reduction : {}".format(TE_reduction.mean()))

# Bad forecast

print("Bad Forecast")

good_forecast_cost = np.array([320.67, 357.46, 326.75, 343.98, 495.05])
bad_forecast_cost = np.array([320.22, 361.00, 327.13, 343.24, 528.13])

deviation = bad_forecast_cost - good_forecast_cost 

fig, ax = plt.subplots()

N = 5
ind = np.arange(N)
width = 0.25

scenarios = ['Scenario 0', 'Scenario 1', 'Scenario 2', 'Scenario 3', 'Scenario 4']

bar1 = ax.bar(ind, deviation, width, color = 'b', label = 'Cost Difference')

ax.set_xlabel("Scenarios")
ax.set_ylabel('Total Cost Difference ($)') 
ax.set_title("Cost Diffence Between Good and Bad Forecast Scenarios")

ax.set_xticks(ind, scenarios)
ax.legend()
#ax.grid()

fig_file_name = "bad_vs_good_forecast_charging_cost_difference.png"

os.makedirs(charging_costs_figures_folder, exist_ok = True)
fig.savefig( os.path.join(charging_costs_figures_folder, fig_file_name), dpi = 300)

#-----------------

scenarios = ['Scenario 0', 'Scenario 1', 'Scenario 2', 'Scenario 3', 'Scenario 4']
uncontrolled_costs = [392.75, 459.08, 400.35, 417.68, 563.03]
TOU_control_costs = [339.57, 391.07, 350.55, 371.90, 545.89]
TE_control_costs = [320.22, 361.00, 327.13, 343.24, 528.13]

TOU_reduction = []

for i in range(len(uncontrolled_costs)):
    TOU_reduction.append((TOU_control_costs[i] - uncontrolled_costs[i])*100/uncontrolled_costs[i])

TOU_reduction = np.array(TOU_reduction)

TE_reduction = []

for i in range(len(uncontrolled_costs)):
    TE_reduction.append((TE_control_costs[i] - uncontrolled_costs[i])*100/uncontrolled_costs[i])

TE_reduction = np.array(TE_reduction)


fig, ax = plt.subplots()

N = 5
ind = np.arange(N)
width = 0.25

bar1 = ax.bar(ind, uncontrolled_costs, width, color = 'r')
bar2 = ax.bar(ind+width, TOU_control_costs, width, color='b')
bar3 = ax.bar(ind+width*2, TE_control_costs, width, color = 'g')

ax.set_xlabel("Scenarios")
ax.set_ylabel('Total Charging Costs ($)')
ax.set_title("Bad Forecast Charging Costs")

ax.set_xticks(ind+width, scenarios)
ax.legend( (bar1, bar2, bar3), ('Uncontrolled', 'TOU Controlled', 'TE Controlled') )

fig_file_name = "bad_forecast_charging_costs.png"

os.makedirs(charging_costs_figures_folder, exist_ok = True)
fig.savefig( os.path.join(charging_costs_figures_folder, fig_file_name), dpi = 300)


# min and max are interchanged here because the reductions are in negative values.
print("TOU Random Max reduction : {} scenario : {}".format(TOU_reduction.min(), scenarios[TOU_reduction.argmin()]))
print("TOU Random Min reduction : {} scenario : {}".format(TOU_reduction.max(), scenarios[TOU_reduction.argmax()]))
print("TOU Random Average reduction : {}".format(TOU_reduction.mean()))

print("TE Average Max reduction : {} scenario : {}".format(TE_reduction.min(), scenarios[TE_reduction.argmin()]))
print("TE Average Min reduction : {} scenario : {}".format(TE_reduction.max(), scenarios[TE_reduction.argmax()]))
print("TE Average reduction : {}".format(TE_reduction.mean()))
