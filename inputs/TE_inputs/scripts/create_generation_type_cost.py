# -*- coding: utf-8 -*-
"""
Created on Wed Jan 31 13:03:42 2024

@author: CEBOM
"""

import json

json_data = {
    "fossil_fuel" : {
        "LCOE" : 75.86, 
        "ramp_up" : 0.25, 
        "ramp_down" : -0.25
    },
    "nuclear" : {
        "LCOE" : 167, 
        "ramp_up" : 0, 
        "ramp_down" : 0
    },
    "solar" : {
        "LCOE" : 36, 
        "ramp_up" : 0, 
        "ramp_down" : 0
    }
}

with open("generation_cost.json", "w") as f:
    json.dump(json_data, f, indent=4)