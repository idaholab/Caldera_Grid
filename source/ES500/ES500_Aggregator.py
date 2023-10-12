#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Created on 2017/10/23
# Edited on 2019/11/5
# @author: Don Scoffield

from enum import Enum
import time, struct, pickle
from multiprocessing import Lock, Process, Array

import cvxopt as cvx
import numpy as np
#from docplex.mp.advmodel import AdvModel as Model      # cplex model

from ES500_Aggregator_Helper import ES500_aggregator_helper
from Caldera_globals import ES500_charge_cycling_control_boundary_point

#=================================================================================
#                               Helper Functions
#=================================================================================

def convert_string_to_time(time_str):
    time_val = time.strptime(time_str, '%Y-%m-%d %H:%M:%S')
    return time.mktime(time_val)


def convert_time_to_string(time_val):
    tmp = time.localtime(round(time_val))
    return time.strftime('%Y-%m-%d %H:%M:%S', tmp)

#=================================================================================
#                               Helper Classes
#=================================================================================


class ES500_objective_function(Enum):
     minimize_load = 1
     minimize_delta_load = 2
     minimize_delta_pev_load = 3


class ES500_optimization_solver(Enum):
    cvxopt = 1
    cplex = 2


class ES500_aggregator_parameters__allocate_energy_to_PEVs:    
    charge_flexibility_threshold = 2.5
    num_pevs_to_start_charging_each_controlled_cycle_iteration = 20
    max_number_of_controlled_cycle_iterations = 1000
    charge_cycling_control_boundary = [(0.1, 1), (0.15, 0.4), (0.2, 0.2), (0.4, 0.15), (1, 0.1)]    # (cycling_magnitude, cycling_vs_ramping)
    E_step_0_multiplier = 1


class ES500_aggregator_parameters__solve_optimization_model:    
    objective_function_ = ES500_objective_function.minimize_load
    pickle_protocol = pickle.HIGHEST_PROTOCOL
    cvxopt_show_progress = False
    calc_obj_fun_constraints_depart_time_adjustment_sec = 0
    
                                    # (w_LB, w_UB, cvxopt__max_relative_gap, iteration_timeout_sec, optimization_solver_)
    opt_solver_iteration_values = [(0, 1, 0.0001, 2, ES500_optimization_solver.cvxopt), \
                                   (0, 1, 0.001, 2, ES500_optimization_solver.cvxopt), \
                                   (0, 1, 0.005, 2, ES500_optimization_solver.cvxopt)]


class ES500_aggregator_parameters__general:    
    data_lead_time_secs = 30
    prediction_horizon_duration_hrs = 24
    feeder_step_energy_limit_kWh = 1000000000000

#=================================================================================
#                    Optimization Solver Manager Class
#=================================================================================

class ES500_aggregator:
    optimization_model_vals_dict = {}
    optimization_solver_log = []
    
    def __init__(self, aggregator_timestep_mins, general, allocate_energy_to_PEVs, solve_optimization_model):
        self.canSolve_aka_pev_charging_in_prediction_window = False
        
        # ES500_aggregator_parameters__general
        num_agg_time_steps_in_prediction_horizon = int(round(60*general.prediction_horizon_duration_hrs/aggregator_timestep_mins, 0))        
        data_lead_time_secs = general.data_lead_time_secs
        self.feeder_step_energy_limit_kWh = general.feeder_step_energy_limit_kWh
        
        # ES500_aggregator_parameters__allocate_energy_to_PEVs
        charge_flexibility_threshold = allocate_energy_to_PEVs.charge_flexibility_threshold
        num_pevs_to_start_charging_each_controlled_cycle_iteration = int(allocate_energy_to_PEVs.num_pevs_to_start_charging_each_controlled_cycle_iteration)
        max_number_of_controlled_cycle_iterations = int(allocate_energy_to_PEVs.max_number_of_controlled_cycle_iterations)
        self.E_step_0_multiplier = allocate_energy_to_PEVs.E_step_0_multiplier
        
        charge_cycling_control_boundary = []
        for cycling_magnitude, cycling_vs_ramping in allocate_energy_to_PEVs.charge_cycling_control_boundary:
            charge_cycling_control_boundary.append(ES500_charge_cycling_control_boundary_point(cycling_magnitude, cycling_vs_ramping))
        
        # ES500_aggregator_parameters__solve_optimization_model
        objective_function_ = solve_optimization_model.objective_function_
        pickle_protocol = solve_optimization_model.pickle_protocol
        cvxopt_show_progress = solve_optimization_model.cvxopt_show_progress
        opt_solver_iteration_values = solve_optimization_model.opt_solver_iteration_values        
        calc_obj_fun_constraints_depart_time_adjustment_sec = solve_optimization_model.calc_obj_fun_constraints_depart_time_adjustment_sec
        
        #=====================================
        
        self.aggregator_helper = ES500_aggregator_helper(aggregator_timestep_mins, data_lead_time_secs, num_agg_time_steps_in_prediction_horizon, charge_flexibility_threshold, num_pevs_to_start_charging_each_controlled_cycle_iteration, max_number_of_controlled_cycle_iterations, calc_obj_fun_constraints_depart_time_adjustment_sec, charge_cycling_control_boundary)
        self.opt_solver_manager = optimization_solver_manager(num_agg_time_steps_in_prediction_horizon, self.feeder_step_energy_limit_kWh, objective_function_, pickle_protocol, cvxopt_show_progress, opt_solver_iteration_values)


    def get_stop_charge_cycling_decision_params(self):
        return self.aggregator_helper.get_stop_charge_cycling_decision_parameters()


    def get_log_data(self):
        optimization_model_vals = self.optimization_model_vals_dict
        optimization_solver_log = self.optimization_solver_log
    
        self.optimization_model_vals_dict = {}
        self.optimization_solver_log = []
        
        return (optimization_model_vals, optimization_solver_log)
    
    
    def start_solving(self, next_aggregator_timestep_start_time, charge_needs_dict, charge_forecast, D_net_kWh):
        self.aggregator_helper.load_charging_forecast(charge_forecast)
        self.aggregator_helper.load_charging_needs(charge_needs_dict)
        
        obj_fun_constraints = self.aggregator_helper.get_obj_fun_constraints(next_aggregator_timestep_start_time)
        self.canSolve_aka_pev_charging_in_prediction_window = obj_fun_constraints.canSolve_aka_pev_charging_in_prediction_window
        
        if self.canSolve_aka_pev_charging_in_prediction_window:
            self.opt_solver_manager.start_solving_obj_fun(obj_fun_constraints, D_net_kWh)
            
            #------------------------------
            
            key_val = int(next_aggregator_timestep_start_time)
            
            self.optimization_model_vals_dict[key_val] = {}
            
            self.optimization_model_vals_dict[key_val]["E_cumEnergy_ALAP_kWh"] = obj_fun_constraints.E_cumEnergy_ALAP_kWh
            self.optimization_model_vals_dict[key_val]["E_cumEnergy_ASAP_kWh"] = obj_fun_constraints.E_cumEnergy_ASAP_kWh
            self.optimization_model_vals_dict[key_val]["E_energy_ALAP_kWh"] = obj_fun_constraints.E_energy_ALAP_kWh
            self.optimization_model_vals_dict[key_val]["E_energy_ASAP_kWh"] = obj_fun_constraints.E_energy_ASAP_kWh
            self.optimization_model_vals_dict[key_val]["E_step_ALAP"] = obj_fun_constraints.E_step_ALAP
            self.optimization_model_vals_dict[key_val]["D_net_kWh"] = D_net_kWh
            self.optimization_model_vals_dict[key_val]["feeder_step_energy_limit_kWh"] = self.feeder_step_energy_limit_kWh
        
    
    def check_for_solution(self, next_aggregator_timestep_start_time):
        pev_energy = None
        
        if self.canSolve_aka_pev_charging_in_prediction_window:
            E_step_kWh_0 = self.opt_solver_manager.check_for_solution(next_aggregator_timestep_start_time)
            
            if E_step_kWh_0 != None:
                (E_step_kWh_log_, SolverInfo_log_) = self.opt_solver_manager.get_log_data()
                
                key_val = int(next_aggregator_timestep_start_time)
                self.optimization_model_vals_dict[key_val]["E_step_kWh"] = E_step_kWh_log_
                self.optimization_solver_log.extend(SolverInfo_log_)
                
                pev_energy = self.aggregator_helper.allocate_energy_to_PEVs(next_aggregator_timestep_start_time, self.E_step_0_multiplier*E_step_kWh_0)
                self.optimization_model_vals_dict[key_val]["E_residual_kWh"] = self.aggregator_helper.get_E_residual_kWh()
        else:
            X = '{}, {}, '.format(next_aggregator_timestep_start_time, next_aggregator_timestep_start_time/3600)
            X += ', 00_No_PEV_Charging_During_Prediction_Horizon,,,,,,,,,'
            self.optimization_solver_log.append(X)
            
            E_step_kWh_0 = 0
            pev_energy = self.aggregator_helper.allocate_energy_to_PEVs(next_aggregator_timestep_start_time, E_step_kWh_0)
        
        return pev_energy


#=================================================================================
#                    Optimization Solver Manager Class
#=================================================================================
    
class mmap_container:
    pass


class optimization_solver_manager:
    
    def __init__(self, num_agg_time_steps_in_prediction_horizon, feeder_step_energy_limit_kWh, objective_function_, pickle_protocol, cvxopt_show_progress, opt_solver_iteration_values):
        self.feeder_step_energy_limit_kWh = feeder_step_energy_limit_kWh
        self.objective_function_ = objective_function_
        self.pickle_protocol = pickle_protocol
        
        #---------------------------------------------------
        
        self.mmap_size_multiplier_aggProc_to_optSolver = 2.5
        self.cvxopt_show_progress = cvxopt_show_progress
        self.opt_solver_iteration_values = opt_solver_iteration_values
        
        #------------------------------------------
        
        self.iteration_index = None
        self.D_net_kWh = None
        self.obj_fun_constraints = None
        
        self.iteration_start_time = None
        self.iteration_timeout_sec = None
        self.mmap_aggProc_to_optSolver = None
        self.solver_process = None
    
        self.previous_solution_index = 0
        self.previous_solution = [0 for x in range(num_agg_time_steps_in_prediction_horizon)]
    
        self.E_step_kWh_log_vals = []
        self.SolverInfo_log = []
        
    
    def get_log_data(self):
        E_step_kWh_log_ = self.E_step_kWh_log_vals
        SolverInfo_log_ = self.SolverInfo_log
        
        self.E_step_kWh_log_vals = []
        self.SolverInfo_log = []
    
        return (E_step_kWh_log_, SolverInfo_log_)
    
    
    def start_solving_obj_fun(self, obj_fun_constraints, D_net_kWh):
        self.E_step_kWh_log_vals = []
        
        self.iteration_index = 0
        self.obj_fun_constraints = obj_fun_constraints
        self.D_net_kWh = D_net_kWh
        self.__start_new_iteration()
    
    
    def check_for_solution(self, next_aggregator_timestep_start_time):
        # read mmap from optimization_solver_process
        mmap_data = read_and_unpickle_mmap_data_OSP(self.mmap_aggProc_to_optSolver)
        
        iteration_execution_time_sec = time.time() - self.iteration_start_time
        
        if mmap_data != None:
            self.solver_process.join()
            
            (total_opt_solver_execution_time_sec, opt_solver_execution_time_sec, is_valid_solution, solution_status, relative_gap, obj_function_value, E_step_kWh) = mmap_data
            
            if not is_valid_solution:
                self.__add_line_to_SolverInfo_log('03_Solution_NOT_Found', iteration_execution_time_sec, obj_function_value,  solution_status, relative_gap, next_aggregator_timestep_start_time)
                return_val = self.__try_to_start_new_iteration()
            
            else:
                self.previous_solution = E_step_kWh
                self.previous_solution_index = 0
                return_val = E_step_kWh[0]
                
                self.__add_line_to_SolverInfo_log('01_Solved', iteration_execution_time_sec, obj_function_value,  solution_status, relative_gap, next_aggregator_timestep_start_time)
                self.E_step_kWh_log_vals = E_step_kWh
            
        else:
            if self.iteration_timeout_sec < iteration_execution_time_sec:
                self.solver_process.terminate()
                self.solver_process.join()
                
                self.__add_line_to_SolverInfo_log('02_Timed_Out', iteration_execution_time_sec, None, None, None, next_aggregator_timestep_start_time)
                return_val = self.__try_to_start_new_iteration()
            
            else:
                return_val = None
        
        return return_val   # return_val = None  (Solution not ready, keep waiting)
    
    
    def __add_line_to_SolverInfo_log(self, outcome, iteration_execution_time_sec, obj_function_value, solution_status, relative_gap, next_aggregator_timestep_start_time):
        if obj_function_value == None: obj_function_value = ''
        if solution_status == None: solution_status = ''
        if relative_gap == None: relative_gap = ''
        if iteration_execution_time_sec == None: iteration_execution_time_sec = ''
        
        iteration_index = self.iteration_index - 1
                
        tmp_msg = '{}, {}, '.format(next_aggregator_timestep_start_time, next_aggregator_timestep_start_time/3600) #convert_time_to_string(next_aggregator_timestep_start_time))
        tmp_msg += '{}, {}, {}, {}, {}, {}, '.format(iteration_index, outcome, iteration_execution_time_sec, obj_function_value, relative_gap, solution_status) 
                
        (w_LB, w_UB, cvxopt__max_relative_gap, iteration_timeout_sec, optimization_solver_) = self.opt_solver_iteration_values[iteration_index]
            
        if cvxopt__max_relative_gap == None: cvxopt__max_relative_gap = ''
        if optimization_solver_ == ES500_optimization_solver.cvxopt:
            opt_solver = 'cvxopt'
        else:
            opt_solver = 'cplex'
            
        tmp_msg += '{}, {}, {}, {}, {}'.format(opt_solver, iteration_timeout_sec, cvxopt__max_relative_gap, w_LB, w_UB)
        
        self.SolverInfo_log.append(tmp_msg)
        
        
    def __try_to_start_new_iteration(self):
        if self.iteration_index >= len(self.opt_solver_iteration_values):
            self.previous_solution_index += 1
            E_step_kWh = self.previous_solution
            return_val = E_step_kWh[self.previous_solution_index]
        
        else:
            self.__start_new_iteration()
            return_val = None
        
        return return_val
    
    
    def __start_new_iteration(self):
        self.iteration_start_time = time.time()
        
        if self.cvxopt_show_progress:
            print('iteration_index:{} '.format(self.iteration_index))
        
        E_cumEnrgy_ALAP_kWh = self.obj_fun_constraints.E_cumEnergy_ALAP_kWh
        E_cumEnrgy_ASAP_kWh = self.obj_fun_constraints.E_cumEnergy_ASAP_kWh
        E_step_ALAP = self.obj_fun_constraints.E_step_ALAP
        
        (w_LB, w_UB, cvxopt__max_relative_gap, iteration_timeout_sec, optimization_solver_) = self.opt_solver_iteration_values[self.iteration_index]
        
        self.iteration_timeout_sec = iteration_timeout_sec
        self.iteration_index += 1
            
        K = len(E_cumEnrgy_ALAP_kWh)
        E_step_UB_kWh = [0 for k in range(K)]
        E_step_LB_kWh = [0 for k in range(K)]
            
        for k in range(K):
            E_step_UB_kWh[k] = w_UB*E_step_ALAP[k]
            E_step_LB_kWh[k] = w_LB*E_step_ALAP[k]
        
        inputs_array = (self.objective_function_, optimization_solver_, cvxopt__max_relative_gap, self.cvxopt_show_progress)
        constraints_array = (E_step_UB_kWh, E_step_LB_kWh, E_cumEnrgy_ASAP_kWh, E_cumEnrgy_ALAP_kWh, self.D_net_kWh, self.feeder_step_energy_limit_kWh)
        
        solver_obj = solve_objective_function()
        solver_obj.set_inputs(inputs_array, constraints_array)
        
        #-----------------------------------------
        #          Create Memory Map
        #-----------------------------------------
        num_timesteps_in_prediction_horizon = len(E_cumEnrgy_ALAP_kWh)                    
        mmap_size_bytes = self.mmap_size_multiplier_aggProc_to_optSolver*(8 + 8 + 8 + 20 + 8 + 8 + 8*num_timesteps_in_prediction_horizon)
                                                                   
        self.mmap_aggProc_to_optSolver = mmap_container()
        length_cmd = 2 + 4
        self.mmap_aggProc_to_optSolver.fmt_cmd = '=HI'
        self.mmap_aggProc_to_optSolver.length_cmd = length_cmd
        self.mmap_aggProc_to_optSolver.lock = Lock()
        self.mmap_aggProc_to_optSolver.mm = Array('B', int(mmap_size_bytes)) 
        
        #-----------------------------------------
        #         Initialize Memory Map
        #-----------------------------------------
        cmd_byte = 0
        tmp_bytes = struct.pack(self.mmap_aggProc_to_optSolver.fmt_cmd, cmd_byte, 0)

        self.mmap_aggProc_to_optSolver.lock.acquire()
        self.mmap_aggProc_to_optSolver.mm[:len(tmp_bytes)] = tmp_bytes
        self.mmap_aggProc_to_optSolver.lock.release()
        
        #--------------------------------
        
        self.solver_process = Process(target=optimization_solver_process, args=(solver_obj, self.mmap_aggProc_to_optSolver, self.pickle_protocol))
        self.solver_process.start()


#=================================================================================
#                      Optimization Solver Process
#                   Read and Write to/from memory map
#=================================================================================

# Memory Map is only used to pass information from the optimization_solver_process to the optimization_solver_manager
# The cmd byte in the memory map is:
#       1. Initialized to 0 when the optimization_solver_process and memory map is created
#       2. Is changed to 1 when the optimization_solver_process writes information to the memory map
# The optimization_solver_manager polls the cmd byte and reads the contents of the memory map when cmd byte = 1.


def optimization_solver_process(solver_obj, mmap_aggProc_to_optSolver, pickle_protocol):
    data = solver_obj.solve()        
    pickle_and_write_mmap_data_OSP(data, mmap_aggProc_to_optSolver, pickle_protocol)


def read_and_unpickle_mmap_data_OSP(mmap_object):
    fmt_cmd = mmap_object.fmt_cmd
    length_cmd = mmap_object.length_cmd
    lock = mmap_object.lock
    mm = mmap_object.mm
    
    #---------------------
    
    lock.acquire()
    tmp_bytes = bytes(mm[:length_cmd])
    (cmd, pickle_obj_length) = struct.unpack(fmt_cmd, tmp_bytes)
    
    mmap_data = None
    cmd_byte = 1
    if cmd == cmd_byte:
        tmp_bytes = bytes(mm[length_cmd:(length_cmd+pickle_obj_length)])
        mmap_data = pickle.loads(tmp_bytes)
            
    lock.release()                        
    return mmap_data


def pickle_and_write_mmap_data_OSP(data, mmap_object, pickle_protocol):
    fmt_cmd = mmap_object.fmt_cmd
    lock = mmap_object.lock
    mm = mmap_object.mm
    
    #---------------------
    
    pickled_data = pickle.dumps(data, protocol=pickle_protocol)
    pickle_obj_length = len(pickled_data)
    
    cmd_byte = 1
    tmp_bytes = struct.pack(fmt_cmd, cmd_byte, pickle_obj_length)
    
    lock.acquire()
    mm[:(len(tmp_bytes)+pickle_obj_length)] = (tmp_bytes+pickled_data)
    lock.release()


#=================================================================================
#=================================================================================
#                      Solve Objective Functions
#=================================================================================
#=================================================================================

class solve_objective_function:

    def __init__(self):
        pass
                                       
        
    def set_inputs(self, inputs_array, constraints_array):
        self.inputs_array = inputs_array
        self.constraints_array = constraints_array
    
    
    def solve(self):
        start_time = time.time()

        (objective_function_, optimization_solver_, cvxopt__max_relative_gap, cvxopt_show_progress) = self.inputs_array
        (E_step_UB_kWh, E_step_LB_kWh, E_cum_energy_ASAP_kWh, E_cum_energy_ALAP_kWh, D_net_kWh, feeder_step_energy_limit_kWh) = self.constraints_array
        
        #-----------------------------------------------
        
        num_time_steps = len(E_step_UB_kWh)
        
        is_valid_solution = False
        if optimization_solver_ == ES500_optimization_solver.cvxopt:
            solution = self.__solve_objective_function_cvxopt(objective_function_, num_time_steps, E_step_UB_kWh, E_step_LB_kWh, E_cum_energy_ASAP_kWh, E_cum_energy_ALAP_kWh, D_net_kWh, feeder_step_energy_limit_kWh, cvxopt__max_relative_gap, cvxopt_show_progress)
            (is_valid_solution, solution_status, relative_gap, E_step_solution_kWh, opt_solver_execution_time_sec) = solution
        
        elif optimization_solver_ == ES500_optimization_solver.cplex:
            solution = self.__solve_objective_function_cplex(objective_function_, num_time_steps, E_step_UB_kWh, E_step_LB_kWh, E_cum_energy_ASAP_kWh, E_cum_energy_ALAP_kWh, D_net_kWh, feeder_step_energy_limit_kWh)
            (is_valid_solution, solution_status, E_step_solution_kWh, opt_solver_execution_time_sec) = solution
            relative_gap = None
        
        obj_function_value = None
        if is_valid_solution:
            obj_function_value = self.__calculate_objective_function_value(objective_function_, D_net_kWh, E_step_solution_kWh)

        total_opt_solver_execution_time_sec = time.time() - start_time
        return (total_opt_solver_execution_time_sec, opt_solver_execution_time_sec, is_valid_solution, solution_status, relative_gap, obj_function_value, E_step_solution_kWh)
    
    
    def __calculate_objective_function_value(self, objective_function_, D_net_kWh, E_step_kWh):        
        if len(E_step_kWh) == 0:
            value = -1
        else:        
            if objective_function_ == ES500_objective_function.minimize_load:
                value = sum([(E_step_kWh[i]+D_net_kWh[i])**2 for i in range(len(E_step_kWh))])
                
            elif objective_function_ == ES500_objective_function.minimize_delta_load:
                value = sum([(E_step_kWh[i+1]-E_step_kWh[i]+D_net_kWh[i+1]-D_net_kWh[i])**2 for i in range(0,len(E_step_kWh)-1)])
                
            elif objective_function_ == ES500_objective_function.minimize_delta_pev_load:
                value = sum([(E_step_kWh[i+1]-E_step_kWh[i])**2 for i in range(0,len(E_step_kWh)-1)])
            
        return value
    
    
    def __solve_objective_function_cplex(self, objective_function_, num_time_steps, E_step_UB_kWh, E_step_LB_kWh, E_cum_energy_ASAP_kWh, E_cum_energy_ALAP_kWh, D_net_kWh, feeder_step_energy_limit_kWh):
        #mdl = Model(name='two_step_optimization')
        mdl = None
    
        # Format Constraints
        E_step_kWh = mdl.continuous_var_list(num_time_steps, name='E_step_kWh', lb=E_step_LB_kWh, ub=E_step_UB_kWh)
    
        for k in range(num_time_steps):
            mdl.add_constraint(E_step_kWh[k] + D_net_kWh[k] <= feeder_step_energy_limit_kWh)
    
        for k in range(num_time_steps):
            subset = []
            for cum_k in range(k+1):
                subset.append(E_step_kWh[cum_k])
            mdl.add_constraint(mdl.sum(subset) <= E_cum_energy_ASAP_kWh[k])
            mdl.add_constraint(E_cum_energy_ALAP_kWh[k] <= mdl.sum(subset))
        
        # Formate Objective Function
        if objective_function_ == ES500_objective_function.minimize_load:
            obj = mdl.sum((D_net_kWh[k]+E_step_kWh[k])*(D_net_kWh[k]+E_step_kWh[k]) for k in range(num_time_steps))
        
        elif objective_function_ == ES500_objective_function.minimize_delta_load:
            obj = mdl.sum(((D_net_kWh[k+1]+E_step_kWh[k+1])-(D_net_kWh[k]+E_step_kWh[k]))*((D_net_kWh[k+1]+E_step_kWh[k+1])-(D_net_kWh[k]+E_step_kWh[k])) for k in range(num_time_steps-1))
        
        elif objective_function_ == ES500_objective_function.minimize_delta_pev_load:
            obj = mdl.sum((E_step_kWh[k+1]-E_step_kWh[k])*(E_step_kWh[k+1]-E_step_kWh[k]) for k in range(num_time_steps-1))
        
        # Solve Objective Function
        solution_status = None
        E_step_solution_kWh = None
        is_valid_solution = False
        
        mdl.minimize(obj)           
        
        start_time = time.time() 
        msol = mdl.solve()
        opt_solver_execution_time_sec = time.time() - start_time

        E_step_solution_kWh = [] 
        for val in E_step_kWh:
            E_step_solution_kWh.append(msol[val])
            
        is_valid_solution = True        
        
        return (is_valid_solution, solution_status, E_step_solution_kWh, opt_solver_execution_time_sec)
    
    
    def __solve_objective_function_cvxopt(self, objective_function_, num_time_steps, E_step_UB_kWh, E_step_LB_kWh, E_cum_energy_ASAP_kWh, E_cum_energy_ALAP_kWh, D_net_kWh, feeder_step_energy_limit_kWh, cvxopt__max_relative_gap, cvxopt_show_progress):
        (G_cvxopt, h_cvxopt) = self.__format_constraints_for_cvxopt(num_time_steps, E_step_UB_kWh, E_step_LB_kWh, E_cum_energy_ASAP_kWh, E_cum_energy_ALAP_kWh, D_net_kWh, feeder_step_energy_limit_kWh)
        (P_cvxopt, q_cvxopt) = self.__format_obj_fun_cvxopt(objective_function_, num_time_steps, D_net_kWh)
        
        cvx.solvers.options['show_progress'] = cvxopt_show_progress
       
        start_time = time.time() 
        sol = cvx.solvers.qp(P_cvxopt, q_cvxopt, G_cvxopt, h_cvxopt)
        opt_solver_execution_time_sec = time.time() - start_time

        cvxopt_solution_status = sol['status']
        cvxopt_relative_gap = sol['relative gap']
        
        E_step_solution_kWh = None
        is_valid_solution = False
        
        if cvxopt_solution_status == 'optimal':
            is_valid_solution = True
            E_step_solution_kWh = [sol['x'][k] for k in range(num_time_steps)]
            
        elif cvxopt_solution_status in('primal infeasible', 'dual infeasible'):            
            pass
           
        elif cvxopt_solution_status == 'unknown':
            if cvxopt_relative_gap < cvxopt__max_relative_gap:
                is_valid_solution = True
                E_step_solution_kWh = [sol['x'][k] for k in range(num_time_steps)]            
            else:
                pass
        
        return (is_valid_solution, cvxopt_solution_status, cvxopt_relative_gap, E_step_solution_kWh, opt_solver_execution_time_sec)
    
    
    def __format_obj_fun_cvxopt(self, objective_function_, num_time_steps, D_net_kWh):
        K = num_time_steps        
        
        if objective_function_ == ES500_objective_function.minimize_load:
            P = 2*np.identity(K)
            q = 2*np.array([D_net_kWh]).T
            
        elif objective_function_ in(ES500_objective_function.minimize_delta_load, ES500_objective_function.minimize_delta_pev_load):
            singlerow = np.zeros((1,K))
            singlerow[0,0] = -1
            singlerow[0,1] = 1
            M = singlerow
            for i in range(1,K-1):
                singlerow = np.zeros((1,K))
                singlerow[0,i] = -1
                singlerow[0,i+1] = 1
                M = np.vstack((M,singlerow))
                            
            if objective_function_ == ES500_objective_function.minimize_delta_load:
                P = 2*np.matmul((M.T),M)
                q = np.matmul(P.T,np.array([D_net_kWh]).T)
            else:
                stability_multiplier = 100
                P = stability_multiplier*2*np.matmul((M.T),M)
                q = np.zeros((K,1))
        
        P_cvxopt = cvx.matrix(P)
        q_cvxopt = cvx.matrix(q)
        return (P_cvxopt, q_cvxopt)
    
    
    def __format_constraints_for_cvxopt(self, num_time_steps, E_step_UB_kWh, E_step_LB_kWh, E_cum_energy_ASAP_kWh, E_cum_energy_ALAP_kWh, D_net_kWh, feeder_step_energy_limit_kWh):        
        G = self.__create_matrix_G(num_time_steps)
        h = self.__create_vector_h(num_time_steps, E_step_UB_kWh, E_step_LB_kWh, E_cum_energy_ASAP_kWh, E_cum_energy_ALAP_kWh, D_net_kWh, feeder_step_energy_limit_kWh)    
        G_cvxopt = cvx.matrix(G)
        h_cvxopt = cvx.matrix(h)
        return (G_cvxopt, h_cvxopt)
    

    def __create_matrix_G(self, num_time_steps):
        K = num_time_steps
        G_feeder = np.identity(K)
        G_step_upr = np.identity(K)
        G_step_lwr = -1*np.identity(K)
        G_cum_asap = np.tril(np.ones((K,K)),0)
        G_cum_maxdelay = np.tril(-1*np.ones((K,K)),0)
        G = np.vstack((G_feeder, G_step_upr, G_step_lwr, G_cum_asap, G_cum_maxdelay))
        return G
    
    
    def __create_vector_h(self, num_time_steps, E_step_UB_kWh, E_step_LB_kWh, E_cum_energy_ASAP_kWh, E_cum_energy_ALAP_kWh, D_net_kWh, feeder_step_energy_limit_kWh):
        K = num_time_steps
        h_feeder = feeder_step_energy_limit_kWh*np.ones((K,1))-np.array([D_net_kWh]).T
        h_step_upr = np.array([E_step_UB_kWh]).T
        h_step_lwr = -1*np.array([E_step_LB_kWh]).T
        h_cum_asap = np.array([E_cum_energy_ASAP_kWh]).T
        h_cum_maxdelay = -1*np.array([E_cum_energy_ALAP_kWh]).T
        h = np.vstack((h_feeder, h_step_upr, h_step_lwr, h_cum_asap, h_cum_maxdelay ))
        return h

