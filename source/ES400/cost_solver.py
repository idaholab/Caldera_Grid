import numpy as np

class cost_solver():
    
    def __init__(self, cost_dict):
        pass        
        
    
    def solve(self, arr, cost_dict):
        
        gen_min = cost_dict["gen_min"]
        gen_max = cost_dict["gen_max"]
        cost_min = cost_dict["cost_min"]
        cost_max = cost_dict["cost_max"]
        cost_function = cost_dict["cost_function"]
        
        if abs(cost_max - cost_min) < 0.001:
            return_val = self.fixed_cost_solve(arr, cost_min)
            
        elif cost_function == "linear":
            return_val = self.linear_solve(arr, gen_min, gen_max, cost_min, cost_max)
            
        elif cost_function == "steep_cubic":
            return_val = self.steep_cubic_solve(arr, gen_min, gen_max, cost_min, cost_max)
        
        elif cost_function == "inverse_s":
            return_val = self.inverse_s_solve(arr, gen_min, gen_max, cost_min, cost_max)
        
        else:
            assert False, "cost function should be linear, steep_cubic or inverse_s"
        
        return return_val
    
    def fixed_cost_solve(self, arr, cost):
        return np.full_like(arr, cost, dtype=float)

    def linear_solve(self, arr, gen_min, gen_max, cost_min, cost_max):
        return (arr - gen_min)/(gen_max-gen_min)*(cost_max-cost_min)+ cost_min
    
    def steep_cubic_solve(self, arr, gen_min, gen_max, cost_min, cost_max):
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
        
        return C[0][0] * arr**0 + C[1][0] * arr**1 + C[2][0] * arr**2 + C[3][0] * arr**3
    
    def inverse_s_solve(self, arr, gen_min, gen_max, cost_min, cost_max):
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
        
        return C[0][0] * arr**0 + C[1][0] * arr**1 + C[2][0] * arr**2 + C[3][0] * arr**3       
