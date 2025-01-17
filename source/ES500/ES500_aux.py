
import time
import os
import sys

from ES500_Aggregator import ES500_aggregator_parameters__general, ES500_aggregator_parameters__solve_optimization_model, ES500_aggregator_parameters__allocate_energy_to_PEVs
from ES500_Aggregator import ES500_aggregator, ES500_objective_function, ES500_optimization_solver
from ES500_Aggregator_Aid import ES500_Aggregator_charging_needs_forecast
from Caldera_ICM_Aux import get_baseLD_forecast
from Caldera_globals import L2_control_strategies_enum
from global_aux import Caldera_message_types, OpenDSS_message_types, input_datasets, container_class
from control_templates import typeA_control

import pandas as pd

file_dir = os.path.dirname(os.path.abspath(__file__))
index = 1
sys.path.insert( index+0, os.path.join( file_dir, "..", "ES400" ) )

from cost_forecaster import TE_cost_forecaster_v3
import numpy as np


class ES500_aux(typeA_control):

    def __init__(self, io_dir, simulation_time_constraints):        
        super().__init__(io_dir, simulation_time_constraints)
        
        self.io_dir = io_dir
    
    def get_input_dataset_enum_list(self):
        return [input_datasets.SE_CE_data_obj, input_datasets.baseLD_data_obj, input_datasets.Caldera_L2_ES_strategies, input_datasets.Caldera_global_parameters, input_datasets.Caldera_control_strategy_parameters_dict]


    def load_input_datasets(self, datasets_dict):
        # datasets_dict is a dictionary with input_datasets as keys.
        self.datasets_dict = datasets_dict
    
    
    def terminate_this_federate(self):
        return L2_control_strategies_enum.ES500 not in self.datasets_dict[input_datasets.Caldera_L2_ES_strategies]
    
    
    def initialize(self):
        
        # For measuring time between calls to "solve"
        self.between_solves_time = time.time()
        
        SE_CE_data_obj = self.datasets_dict[input_datasets.SE_CE_data_obj]
        baseLD_data_obj = self.datasets_dict[input_datasets.baseLD_data_obj]
        global_parameters = self.datasets_dict[input_datasets.Caldera_global_parameters]
        L2_control_strategy_parameters_dict = self.datasets_dict[input_datasets.Caldera_control_strategy_parameters_dict]
        ES500_params = L2_control_strategy_parameters_dict[L2_control_strategies_enum.ES500]
        
        aggregator_timestep_mins = ES500_params['aggregator_timestep_mins']
        self.aggregator_poll_time_sec = ES500_params['aggregator_poll_time_sec']
        
        #-------------------------------------
        #    Calculate Timing Parameters
        #-------------------------------------        
        X = container_class()
        X.control_timestep_min = aggregator_timestep_mins
        X.send_control_info_lead_time_min = ES500_params['energy_setpoints_lead_time_sec']/60
        X.request_state_lead_time_min = ES500_params['charging_needs_lead_time_sec']/60
        self._calculate_timing_parameters(X, self.__class__.__name__)
        
        #------------------------------
        # Initialize Aggregator Object
        #------------------------------
        general_params = ES500_aggregator_parameters__general()
        general_params.data_lead_time_secs = ES500_params['charging_needs_lead_time_sec']
        general_params.prediction_horizon_duration_hrs = ES500_params['prediction_horizon_duration_hrs']
        general_params.feeder_step_energy_limit_kWh = global_parameters['feeder_power_limit_kW'] * aggregator_timestep_mins/60
        
        #--------------------------------------
        
        allocate_energy_to_PEVs_params = ES500_aggregator_parameters__allocate_energy_to_PEVs()
        allocate_energy_to_PEVs_params.charge_flexibility_threshold = ES500_params['charge_flexibility_threshold']
        allocate_energy_to_PEVs_params.num_pevs_to_start_charging_each_controlled_cycle_iteration = ES500_params['num_pevs_to_start_charging_each_controlled_cycle_iteration']
        allocate_energy_to_PEVs_params.max_number_of_controlled_cycle_iterations = ES500_params['max_number_of_controlled_cycle_iterations']
        allocate_energy_to_PEVs_params.charge_cycling_control_boundary = ES500_params['charge_cycling_control_boundary']
        allocate_energy_to_PEVs_params.E_step_0_multiplier = ES500_params['E_step_0_multiplier']
        
        #--------------------------------------
        
        solve_optimization_model_params = ES500_aggregator_parameters__solve_optimization_model()
        solve_optimization_model_params.cvxopt_show_progress = ES500_params['cvxopt_show_progress']
        solve_optimization_model_params.calc_obj_fun_constraints_depart_time_adjustment_sec = ES500_params['calc_obj_fun_constraints_depart_time_adjustment_sec']
        
        if ES500_params['objective_function'] == 'minimize_delta_load':
            self.objective_function = ES500_objective_function.minimize_delta_load
        
        elif ES500_params['objective_function'] == 'minimize_load':
            self.objective_function = ES500_objective_function.minimize_load
            
        elif ES500_params['objective_function'] == 'minimize_delta_pev_load':
            self.objective_function = ES500_objective_function.minimize_delta_pev_load
        
        elif ES500_params['objective_function'] == 'maximize_renewables':
            self.objective_function = ES500_objective_function.maximize_renewables
            
        else:
            self.objective_function = ES500_objective_function.minimize_load
        
        solve_optimization_model_params.ES500_objective_function = self.objective_function
        
        opt_solver_iteration_values = []
        for (cvxopt__max_relative_gap, iteration_timeout_sec) in ES500_params['opt_solver_iteration_values']:
            opt_solver_iteration_values.append([0, 1, cvxopt__max_relative_gap, iteration_timeout_sec, ES500_optimization_solver.cvxopt])
        solve_optimization_model_params.opt_solver_iteration_values = opt_solver_iteration_values
        
        #--------------------------------------
        
        self.aggregator_obj = ES500_aggregator(aggregator_timestep_mins, general_params, allocate_energy_to_PEVs_params, solve_optimization_model_params)

        #------------------------------
        #     Create CE Forecaster 
        #------------------------------
        self.CE_forecaster = ES500_Aggregator_charging_needs_forecast(SE_CE_data_obj.SE_group_charge_events, SE_CE_data_obj.SEid_to_SE_type, ES500_params)
        
        #------------------------------
        #     Create cost/generation Forecaster 
        #------------------------------
        self.cost_forecaster = TE_cost_forecaster_v3(os.path.join(self.io_dir.inputs_dir, 'TE_inputs'), ".", False)

        #------------------------------
        #   Create baseLD Forecaster
        #------------------------------
        data_start_unix_time = baseLD_data_obj.data_start_unix_time
        data_timestep_sec = baseLD_data_obj.data_timestep_sec
        actual_load_akW = baseLD_data_obj.actual_load_akW
        forecast_load_akW = baseLD_data_obj.forecast_load_akW
        adjustment_interval_hrs = global_parameters['base_load_forecast_adjust_interval_hrs']
        
        self.baseLD_forecaster = get_baseLD_forecast(data_start_unix_time, data_timestep_sec, actual_load_akW, forecast_load_akW, adjustment_interval_hrs)
            
        self.forecast_duration_hrs = ES500_params['prediction_horizon_duration_hrs']
        self.forecast_timestep_mins = aggregator_timestep_mins
        self.forecast_timestep_hrs = self.forecast_timestep_mins/60
    
        #------------------------------
        #      Initialize Logger
        #------------------------------
        log_optimization_values = ES500_params['log_optimization_values']
        log_pev_energy_setpoints = ES500_params['log_pev_energy_setpoints']
        log_stop_charge_cycling_decision_parameters = ES500_params['log_stop_charge_cycling_decision_parameters']
        
        self.log_files = ES500_Aggregator_log_files(self.base_dir, log_optimization_values, log_pev_energy_setpoints, log_stop_charge_cycling_decision_parameters)
        

    def log_data(self):
        (optimization_model_vals, optimization_solver_log) = self.aggregator_obj.get_log_data()
        stop_charge_cycling_decision_params = self.aggregator_obj.get_stop_charge_cycling_decision_params()
        self.log_files.log_data(optimization_solver_log, optimization_model_vals, self.pev_energy, stop_charge_cycling_decision_params)
    
    
    def get_messages_to_request_state_info_from_Caldera(self, next_control_timestep_start_unix_time):
        return_dict = {}
        return_dict[Caldera_message_types.ES500_get_charging_needs] = next_control_timestep_start_unix_time
        
        # The return value (return_dict) must be a dictionary with Caldera_message_types as keys.
        # If there is nothing to return, return an empty dictionary.
        return return_dict
    
    
    def get_messages_to_request_state_info_from_OpenDSS(self, next_control_timestep_start_unix_time):
        return_dict = {}
        
        # The return value (return_dict) must be a dictionary with OpenDSS_message_types as keys.
        # If there is nothing to return, return an empty dictionary.
        return return_dict
    
    
    def solve(self, next_control_timestep_start_unix_time, Caldera_state_info_dict, DSS_state_info_dict):
        # Caldera_state_info_dict is a dictionary with Caldera_message_types as keys.
        # DSS_state_info_dict is a dictionary with OpenDSS_message_types as keys. 
        
        time_since_last_call = time.time() - self.between_solves_time
        
        #---------------------
        #    Get Forecasts
        #---------------------
        time00 = time.time()
        next_aggregator_start_unix_time = next_control_timestep_start_unix_time
        base_D_akW = self.baseLD_forecaster.get_forecast_akW(next_aggregator_start_unix_time, self.forecast_timestep_mins, self.forecast_duration_hrs)
        
        if self.objective_function == ES500_objective_function.maximize_renewables:

            if os.environ['SIM_SCALE'] == "full":
                multiplier = 1000
            elif os.environ['SIM_SCALE'] == "small":
                multiplier = 1
            else:
                multiplier = 1000    # Run full simulation by default
            
            print("ES500:", os.environ['SIM_SCALE'])
            # data_id, current_time_sec, start_time_sec, end_time_sec, timestep_sec, debug
            solar_kW = self.cost_forecaster.get_raw_data_for_time_range( "solar", "actual", next_aggregator_start_unix_time, next_aggregator_start_unix_time, next_aggregator_start_unix_time + self.forecast_duration_hrs * 3600, self.forecast_timestep_mins * 60, False ) * multiplier
            wind_kW = self.cost_forecaster.get_raw_data_for_time_range( "wind", "actual", next_aggregator_start_unix_time, next_aggregator_start_unix_time, next_aggregator_start_unix_time + self.forecast_duration_hrs * 3600, self.forecast_timestep_mins * 60, False ) * multiplier
            nuclear_kW = self.cost_forecaster.get_raw_data_for_time_range( "nuclear", "actual", next_aggregator_start_unix_time, next_aggregator_start_unix_time, next_aggregator_start_unix_time + self.forecast_duration_hrs * 3600, self.forecast_timestep_mins * 60, False ) * multiplier
            
            D_net_kW = nuclear_kW + solar_kW + wind_kW - base_D_akW

        else:
            
            D_net_kW = base_D_akW
        
        D_net_kWh =  np.array([self.forecast_timestep_hrs*akW for akW in D_net_kW])
        
        CE_forecast = self.CE_forecaster.get_forecast(next_aggregator_start_unix_time)
        time01 = time.time()
        
        #-----------------------------
        # Calculate Optimal Solution
        #-----------------------------
        time02 = time.time()
        process_id = '1'
        tmp_Caldera_state_info = {}
        tmp_Caldera_state_info[process_id] = Caldera_state_info_dict[Caldera_message_types.ES500_get_charging_needs]
        time03 = time.time()
        
        '''
        print("ES500 fed: starting solve")
        self.aggregator_obj.start_solving(next_aggregator_start_unix_time, tmp_Caldera_state_info, CE_forecast, D_net_kWh)
        
        tmp_Caldera_control_info = None
        while True:
            tmp_Caldera_control_info = self.aggregator_obj.check_for_solution(next_aggregator_start_unix_time)
            
            if tmp_Caldera_control_info == None:
                time.sleep(self.aggregator_poll_time_sec)
            else:
                break
        '''
        
        #-----------------------------
        
        time04 = time.time()
        self.pev_energy = self.aggregator_obj.start_solving_v2(next_aggregator_start_unix_time, tmp_Caldera_state_info, CE_forecast, D_net_kWh)  # Needed to log data
        Caldera_control_info_dict = {}
        Caldera_control_info_dict[Caldera_message_types.ES500_set_energy_setpoints] = self.pev_energy[process_id]
        
        DSS_control_info_dict = {}
        time05 = time.time()

        '''
        print("flag1")
        print("   time_since_last_call: ",time_since_last_call)
        print("   time00: ",time00 )
        print("   time01: ",time01 )
        print("   time02: ",time02 )
        print("   time03: ",time03 )
        print("   time04: ",time04 )
        print("   time05: ",time05 )
        print("   time01-time00: ", time01-time00 )
        print("   time03-time02: ", time03-time02 )
        print("   time05-time04: ", time05-time04 )
        print("   time05-time00: ", time05-time00 )
        '''

        # Start measuring time to the next call of this function.
        self.between_solves_time = time.time()

        # Caldera_control_info_dict must be a dictionary with Caldera_message_types as keys.
        # DSS_control_info_dict must be a dictionary with OpenDSS_message_types as keys.
        # If either value has nothing to return, return an empty dictionary.
        return (Caldera_control_info_dict, DSS_control_info_dict)


    def cleanup_this_federate(self):
        print("In cleanup_this_federate")

        dem_gen_df = pd.DataFrame()
        debug = True
        dem_gen_df['time'] = np.arange(self.start_simulation_unix_time, self.end_simulation_unix_time, self.forecast_timestep_mins * 60)/3600.0
        for data_id in ['demand', 'nuclear', 'solar', 'wind']:
            dem_gen_df[data_id] = np.array(self.cost_forecaster.get_raw_data_for_time_range( data_id, 'actual', self.start_simulation_unix_time, self.start_simulation_unix_time, self.end_simulation_unix_time, self.forecast_timestep_mins * 60, debug).data)
        
        dem_gen_df["net_renewables"] = dem_gen_df['nuclear'] + dem_gen_df['solar'] + dem_gen_df['wind'] - dem_gen_df['demand']
        
        dem_gen_df.to_csv(os.path.join(self.io_dir.outputs_dir, 'ES500_demand_generation.csv'), index = False)

        print("Done writing")


class ES500_Aggregator_log_files:

    def __init__(self, io_dir, log_optimization_values, log_pev_energy_setpoints, log_stop_charge_cycling_decision_parameters):
        self.log_optimization_values = log_optimization_values
        self.log_pev_energy_setpoints = log_pev_energy_setpoints
        self.log_stop_charge_cycling_decision_parameters = log_stop_charge_cycling_decision_parameters
        
        #=============================
        
        self.f_stop_CC = None
        if self.log_stop_charge_cycling_decision_parameters:
            self.f_stop_CC = open( os.path.join( io_dir.outputs_dir, 'ES500_Stop_Charge_Cycling_Parameters.csv' ), 'w')
            line = 'next_aggregator_timestep_start_time, next_aggregator_timestep_start_time'
            line += ', iteration, is_last_iteration, off_to_on_nrg_kWh, on_to_off_nrg_kWh, total_on_nrg_kWh'
            line += ', cycling_vs_ramping, cycling_magnitude, delta_energy_kWh'
            self.f_stop_CC.write(line + '\n')
        
        #=============================
        
        self.f_OSS = open( os.path.join( io_dir.outputs_dir, 'ES500_Optimization_Solver_Status.csv' ), 'w')
        line = 'next_aggregator_timestep_start_time, next_aggregator_timestep_start_time'
        line += ', iteration_index, outcome, iteration_execution_time_sec, obj_function_value, relative_gap, solution_status'
        line += ', opt_solver, iteration_timeout_sec, cvxopt__max_relative_gap, w_LB, w_UB'
        self.f_OSS.write(line + '\n')
        
        #=============================
        
        self.f_OMV = None
        self.f_E_residual = None
        if self.log_optimization_values:
            if self.log_optimization_values:
                self.f_OMV = open( os.path.join( io_dir.outputs_dir, 'ES500_Optimization_Model_Values.csv' ), 'w')
                self.f_OMV.write('next_aggregator_timestep_start_time, next_aggregator_timestep_start_time, index, E_cumEnergy_ALAP_kWh, E_cumEnergy_ASAP_kWh, E_energy_ALAP_kWh, E_energy_ASAP_kWh, E_step_ALAP, E_step_kWh, D_net_kWh, feeder_step_energy_limit_kWh  \n') 
            
                self.f_E_residual = open( os.path.join( io_dir.outputs_dir, 'ES500_Residual_Energy.csv' ), 'w')
                self.f_E_residual.write('next_aggregator_timestep_start_time, next_aggregator_timestep_start_time, E_residual_kWh' + '\n')
        
        #=============================
        
        self.f_e_step = None
        if self.log_pev_energy_setpoints:
            if self.log_pev_energy_setpoints:
                self.f_e_step = open( os.path.join( io_dir.outputs_dir, 'ES500_PEV_Energy_Setpoints.csv' ), 'w')
                self.f_e_step.write('next_aggregator_timestep_start_time, next_aggregator_timestep_start_time, process_id, SE_id, e3_step_kWh, charge_progression' + '\n')
    
    
    def __del__(self):
        self.f_OSS.close()
        
        if self.log_stop_charge_cycling_decision_parameters:
            self.f_stop_CC.close()
        
        if self.log_optimization_values:
            self.f_OMV.close()
            self.f_E_residual.close()
        
        if self.log_pev_energy_setpoints:
            self.f_e_step.close()

    
    def log_data(self, optimization_solver_log, optimization_model_vals, pev_energy, stop_charge_cycling_decision_params):
        for x in optimization_solver_log:
            self.f_OSS.write(x + '\n')
        
        #------------------------
        
        if self.log_stop_charge_cycling_decision_parameters:
            for x in stop_charge_cycling_decision_params:
                line = '{}, {}'.format(x.next_aggregator_timestep_start_time, x.next_aggregator_timestep_start_time/3600)
                line += ', {}, {}'.format(x.iteration, x.is_last_iteration)
                line += ', {}, {}, {}'.format(x.off_to_on_nrg_kWh, x.on_to_off_nrg_kWh, x.total_on_nrg_kWh)
                line += ', {}, {}, {}'.format(x.cycling_vs_ramping, x.cycling_magnitude, x.delta_energy_kWh)
                self.f_stop_CC.write(line + '\n')
        
        #------------------------
        
        if self.log_optimization_values:
            for next_aggregator_start_unix_time, tmp_dict in optimization_model_vals.items():
                E_residual_kWh = tmp_dict["E_residual_kWh"]
                self.f_E_residual.write("{}, {}, {} \n".format(next_aggregator_start_unix_time, next_aggregator_start_unix_time/3600, E_residual_kWh))
            
                #----------------
                
                E_cumEnergy_ALAP_kWh = tmp_dict['E_cumEnergy_ALAP_kWh']
                E_cumEnergy_ASAP_kWh = tmp_dict['E_cumEnergy_ASAP_kWh']
                E_energy_ALAP_kWh = tmp_dict['E_energy_ALAP_kWh']
                E_energy_ASAP_kWh = tmp_dict['E_energy_ASAP_kWh']
                E_step_ALAP = tmp_dict['E_step_ALAP']
                E_step_kWh = tmp_dict['E_step_kWh']
                D_net_kWh = tmp_dict['D_net_kWh']
                feeder_step_energy_limit_kWh = tmp_dict['feeder_step_energy_limit_kWh']
                
                for i in range(len(E_cumEnergy_ALAP_kWh)):
                    line = "{}, {}, {}, {}, {}".format(next_aggregator_start_unix_time, next_aggregator_start_unix_time/3600, i, E_cumEnergy_ALAP_kWh[i], E_cumEnergy_ASAP_kWh[i])
                    line += ", {}, {}, {}, {}, {}".format(E_energy_ALAP_kWh[i], E_energy_ASAP_kWh[i], E_step_ALAP[i], E_step_kWh[i], D_net_kWh[i], feeder_step_energy_limit_kWh)
                    self.f_OMV.write(line + '\n')
        
        #------------------------

        if self.log_pev_energy_setpoints:
            for (process_id, X) in pev_energy.items():
                start_time = X.next_aggregator_timestep_start_time
                SE_id = X.SE_id
                e3_step_kWh = X.e3_step_kWh
                charge_progression = X.charge_progression
            
                for i in range(len(SE_id)):
                    line = "{}, {}, {}, {}, {}, {}".format(start_time, start_time/3600, process_id, SE_id[i], e3_step_kWh[i], charge_progression[i])
                    self.f_e_step.write(line + '\n')      
 