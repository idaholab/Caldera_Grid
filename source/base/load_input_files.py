
import pandas as pd
import numpy as np
import time, os, math, fnmatch

from Caldera_global import SE_group_configuration, SE_configuration
from Caldera_global import pev_is_compatible_with_supply_equipment, supply_equipment_is_L2, supply_equipment_is_3phase
from Caldera_global import SE_group_charge_event_data, charge_event_data, stop_charging_criteria
from Caldera_global import get_supply_equipment_enum, get_vehicle_enum, get_LPF_window_enum, LPF_window_enum
from Caldera_global import L2_control_strategies_enum, get_L2_control_strategies_enum, control_strategy_enums, is_L2_ES_control_strategy, is_L2_VS_control_strategy
from Caldera_global import L2_control_strategy_supports_Vrms_using_QkVAR
from Helper import container_class, select_control_strategy, assign_control_strategies_to_CE
from Helper import parameters_file_processor, data_conversion_and_validation


def print_errors_file(input_data_file_path, errors):
    if len(errors) == 0:
        return

    errors_file_path = input_data_file_path[:-4] + '_errors.csv'

    f_out = open(errors_file_path, 'w')
    f_out.write("Line Number, Message" + '\n')
    
    for x in errors:
        f_out.write(x + '\n')

    f_out.close()


def write_error_message_to_console_and_consoleFile(console_error_message, console_message_filepath):
    f_out = open(console_message_filepath, 'w')
    f_out.write(console_error_message)
    f_out.close()
    
    print(console_error_message)


def get_Ext_strategy(Ext_str):
    successfull = True
    inverter_model_supports_Qsetpoint = False
    
    Ext_string = Ext_str.strip()
    
    if len(Ext_string) == 2:
        if Ext_string != 'NA':
            successfull = False
    elif len(Ext_string) not in(7, 8):
        successfull = False
    else:
        header_val = Ext_string[:3]
        num_val = Ext_string[3:7]    
            
        if header_val != 'ext':
            successfull = False
        
        try:
            tmp = int(num_val)
            if tmp < 0: successfull = False
        except ValueError:
            successfull = False
                
        if len(Ext_string) == 8:
            if Ext_string[-1] != 'q':
                successfull = False
            else:
                inverter_model_supports_Qsetpoint = True
    
    return (successfull, inverter_model_supports_Qsetpoint, Ext_string)


def get_control_strategy_enums(ES_str, VS_str, Ext_str, line_number, L2_control_strategies_to_include):
    errors = []
    control_strategies = control_strategy_enums()
    
    #-----------------------

    (ES_conversion_successfull, ES_enum) = get_L2_control_strategies_enum(ES_str)
    (VS_conversion_successfull, VS_enum) = get_L2_control_strategies_enum(VS_str)
    (Ext_successfull, ext_supports_Q, Ext_string) = get_Ext_strategy(Ext_str)
    
    if not ES_conversion_successfull or not VS_conversion_successfull or not Ext_successfull:
        errors.append('{}, Invalid Control Strategy Values.'.format(line_number))
        
    if len(errors) == 0:
        if (ES_enum not in L2_control_strategies_to_include) or (VS_enum not in L2_control_strategies_to_include):
            errors.append('{}, Invalid Control Strategy Values.'.format(line_number))
            
        if is_L2_ES_control_strategy(VS_enum) or is_L2_VS_control_strategy(ES_enum):
            errors.append('{}, Invalid Control Strategy Values.  First strategy should be ES; second should be VS'.format(line_number))
        
        NA_enum = L2_control_strategies_enum.NA
        if Ext_string != 'NA' and ((ES_enum != NA_enum) or (VS_enum != NA_enum)):
            errors.append('{}, Invalid Control Strategy Values.  If Ext_strategy is active; ES_strategy and VS_strategy must be NA.'.format(line_number))
        
    #-----------------------
    
    if len(errors) == 0:
        VS_supportsQ = L2_control_strategy_supports_Vrms_using_QkVAR(VS_enum)
    
        control_strategies.inverter_model_supports_Qsetpoint = ext_supports_Q or VS_supportsQ
        control_strategies.ES_control_strategy = ES_enum
        control_strategies.VS_control_strategy = VS_enum
        control_strategies.ext_control_strategy = Ext_string
    
    #-----------------------
    
    return (errors, control_strategies)


#=============================================================
#=============================================================
#                   Load Input Files
#=============================================================
#=============================================================


class load_input_files:

    class filepaths_class:
        pass

    def __init__(self, start_simulation_unix_time):
        self.start_simulation_unix_time = start_simulation_unix_time
        
        self.L2_control_strategies_to_include = []
        self.L2_control_strategies_to_include.append(L2_control_strategies_enum.NA)
        self.L2_control_strategies_to_include.append(L2_control_strategies_enum.ES100_A)
        self.L2_control_strategies_to_include.append(L2_control_strategies_enum.ES100_B)
        self.L2_control_strategies_to_include.append(L2_control_strategies_enum.ES110)
        #self.L2_control_strategies_to_include.append(L2_control_strategies_enum.ES200)
        #self.L2_control_strategies_to_include.append(L2_control_strategies_enum.ES300)
        self.L2_control_strategies_to_include.append(L2_control_strategies_enum.ES500)
        self.L2_control_strategies_to_include.append(L2_control_strategies_enum.VS100)
        self.L2_control_strategies_to_include.append(L2_control_strategies_enum.VS200_A)
        self.L2_control_strategies_to_include.append(L2_control_strategies_enum.VS200_B)
        self.L2_control_strategies_to_include.append(L2_control_strategies_enum.VS200_C)
        #self.L2_control_strategies_to_include.append(L2_control_strategies_enum.VS300)
    
    
    def get_L2_control_strategies_to_include(self):
        return self.L2_control_strategies_to_include
    
    
    def __get_filepaths_aux(self, dir_path, file_search_name):
        is_successful = False
        file_path = None
        
        for (root, dirs, files) in os.walk(dir_path):
            files_list = fnmatch.filter(files, file_search_name)            
            break
            
        if len(files_list) == 1:
            file_path = dir_path + '/' + files_list[0]
            
            if os.stat(file_path).st_size > 0:
                is_successful = True
            else:
                file_path = None
        
        return (is_successful, file_path)
    
    
    def __get_filepaths(self, input_dir):        
        parameters_dir = input_dir + '/parameters'
        
        X = []
        X.append((input_dir, 'CE*.csv'))
        X.append((input_dir, 'SE*.csv'))
        X.append((input_dir, 'baseLD*.csv'))        
        X.append((input_dir, 'global*.csv'))
        
        if L2_control_strategies_enum.ES100_A in self.L2_control_strategies_to_include: X.append((parameters_dir, 'ES100-A*.csv'))
        if L2_control_strategies_enum.ES100_B in self.L2_control_strategies_to_include: X.append((parameters_dir, 'ES100-B*.csv'))
        if L2_control_strategies_enum.ES110   in self.L2_control_strategies_to_include: X.append((parameters_dir, 'ES110*.csv'))
        if L2_control_strategies_enum.ES200   in self.L2_control_strategies_to_include: X.append((parameters_dir, 'ES200*.csv'))
        if L2_control_strategies_enum.ES300   in self.L2_control_strategies_to_include: X.append((parameters_dir, 'ES300*.csv'))
        if L2_control_strategies_enum.ES500   in self.L2_control_strategies_to_include: X.append((parameters_dir, 'ES500*.csv'))
        if L2_control_strategies_enum.VS100   in self.L2_control_strategies_to_include: X.append((parameters_dir, 'VS100*.csv'))
        if L2_control_strategies_enum.VS200_A in self.L2_control_strategies_to_include: X.append((parameters_dir, 'VS200-A*.csv'))
        if L2_control_strategies_enum.VS200_B in self.L2_control_strategies_to_include: X.append((parameters_dir, 'VS200-B*.csv'))
        if L2_control_strategies_enum.VS200_C in self.L2_control_strategies_to_include: X.append((parameters_dir, 'VS200-C*.csv'))
        if L2_control_strategies_enum.VS300   in self.L2_control_strategies_to_include: X.append((parameters_dir, 'VS300*.csv'))
        
        #-----------------------
        
        Y = []
        file_paths_with_problems = []
        for (dir_path, file_search_name) in X:
            (tmp_is_successful, file_path) = self.__get_filepaths_aux(dir_path, file_search_name)
            
            if tmp_is_successful:
                Y.append(file_path)
            else:
                file_paths_with_problems.append(dir_path + '/' + file_search_name)
        
        #-----------------------
        
        filepaths = self.filepaths_class()
        filepaths.console_messages = input_dir + '/error_messages.txt'
        
        f_out = open(filepaths.console_messages, 'w')
        f_out.write('No Errors.')
        f_out.close()
        
        if len(file_paths_with_problems) == 0:
            i = 0
            filepaths.CE = Y[i]; i += 1
            filepaths.SE = Y[i]; i += 1
            filepaths.baseLD = Y[i]; i += 1
            filepaths.global_ = Y[i]; i += 1
            
            if L2_control_strategies_enum.ES100_A in self.L2_control_strategies_to_include: filepaths.ES100_A = Y[i]; i += 1
            if L2_control_strategies_enum.ES100_B in self.L2_control_strategies_to_include: filepaths.ES100_B = Y[i]; i += 1
            if L2_control_strategies_enum.ES110   in self.L2_control_strategies_to_include: filepaths.ES110   = Y[i]; i += 1
            if L2_control_strategies_enum.ES200   in self.L2_control_strategies_to_include: filepaths.ES200   = Y[i]; i += 1
            if L2_control_strategies_enum.ES300   in self.L2_control_strategies_to_include: filepaths.ES300   = Y[i]; i += 1
            if L2_control_strategies_enum.ES500   in self.L2_control_strategies_to_include: filepaths.ES500   = Y[i]; i += 1
            if L2_control_strategies_enum.VS100   in self.L2_control_strategies_to_include: filepaths.VS100   = Y[i]; i += 1
            if L2_control_strategies_enum.VS200_A in self.L2_control_strategies_to_include: filepaths.VS200_A = Y[i]; i += 1
            if L2_control_strategies_enum.VS200_B in self.L2_control_strategies_to_include: filepaths.VS200_B = Y[i]; i += 1
            if L2_control_strategies_enum.VS200_C in self.L2_control_strategies_to_include: filepaths.VS200_C = Y[i]; i += 1
            if L2_control_strategies_enum.VS300   in self.L2_control_strategies_to_include: filepaths.VS300   = Y[i]; i += 1

        #-----------------------
        
        return (file_paths_with_problems, filepaths)
    
    
    def load(self, base_dir):
        console_error_message = "Caldera:  Not Initialized Check Log Files." + '\n'
    
        #------------------------------
        #       Get File Paths
        #------------------------------
        (file_paths_with_problems, filepaths) = self.__get_filepaths(base_dir)
        
        if len(file_paths_with_problems) != 0:
            console_error_message = '\n' + "Duplicate, Missing or Empty Input Files." + '\n'
            for x in file_paths_with_problems:
                console_error_message += '    ' + x + '\n'
            
            write_error_message_to_console_and_consoleFile(console_error_message, filepaths.console_messages)
            return (False, None, None, None, None)  # (is_successful, SE_CE_data_obj, baseLD_data_obj, global_parameters, control_strategy_parameters_dict)
    
        #------------------------------
        #  Read global Parameters
        #------------------------------
        X = load_global_parameters(filepaths.global_, self.L2_control_strategies_to_include)
        (is_successful, global_parameters) = X.load()
   
        if not is_successful:
            write_error_message_to_console_and_consoleFile(console_error_message, filepaths.console_messages)
            return (False, None, None, None, None)  # (is_successful, SE_CE_data_obj, baseLD_data_obj, global_parameters, control_strategy_parameters_dict)
    
        #------------------------------
        # Read Control Strategy Files
        #------------------------------
        load_parameters = []
        for x_enum in self.L2_control_strategies_to_include:
            if x_enum == L2_control_strategies_enum.NA:
                pass
                
            elif x_enum == L2_control_strategies_enum.ES100_A:
                X = load_ES100_parameters(filepaths.ES100_A)
                load_parameters.append( (x_enum, X) )
                
            elif x_enum == L2_control_strategies_enum.ES100_B:
                X = load_ES100_parameters(filepaths.ES100_B)
                load_parameters.append( (x_enum, X) )
                
            elif x_enum == L2_control_strategies_enum.ES110:
                X = load_ES110_parameters(filepaths.ES110)
                load_parameters.append( (x_enum, X) )
            
            elif x_enum == L2_control_strategies_enum.ES200:
                X = load_ES200_parameters(filepaths.ES200)
                load_parameters.append( (x_enum, X) )
                
            elif x_enum == L2_control_strategies_enum.ES300:
                X = load_ES300_parameters(filepaths.ES300)
                load_parameters.append( (x_enum, X) )
                
            elif x_enum == L2_control_strategies_enum.ES500:
                X = load_ES500_parameters(filepaths.ES500)
                load_parameters.append( (x_enum, X) )
            
            elif x_enum == L2_control_strategies_enum.VS100:
                X = load_VS100_parameters(filepaths.VS100)
                load_parameters.append( (x_enum, X) )
            
            elif x_enum == L2_control_strategies_enum.VS200_A:
                X = load_VS200_parameters(filepaths.VS200_A)
                load_parameters.append( (x_enum, X) )
            
            elif x_enum == L2_control_strategies_enum.VS200_B:
                X = load_VS200_parameters(filepaths.VS200_B)
                load_parameters.append( (x_enum, X) )
            
            elif x_enum == L2_control_strategies_enum.VS200_C:
                X = load_VS200_parameters(filepaths.VS200_C)
                load_parameters.append( (x_enum, X) )
            
            elif x_enum == L2_control_strategies_enum.VS300:
                X = load_VS300_parameters(filepaths.VS300)
                load_parameters.append( (x_enum, X) )
            
            else:
                print('Coding Error in (file: load_input_files.py class: load_input_files, method: load)')
        
        #------------------------
        
        control_strategy_parameters_dict = {}
        is_successful = True
        
        for (x_enum, load_parameters_obj) in load_parameters:
            (is_success, parameters_dict) = load_parameters_obj.load()
        
            if is_success:
                control_strategy_parameters_dict[x_enum] = parameters_dict
            else:
                is_successful = False
        
        if not is_successful:
            write_error_message_to_console_and_consoleFile(console_error_message, filepaths.console_messages)
            return (False, None, None, None, None)  # (is_successful, SE_CE_data_obj, baseLD_data_obj, global_parameters, control_strategy_parameters_dict)
        
        #------------------------------
        #  Read CE_ and SE_ files
        #------------------------------
        X = load_SE_CE_input_files()
        (is_successful, SE_CE_data_obj) = X.load(filepaths.SE, filepaths.CE, global_parameters, self.L2_control_strategies_to_include, control_strategy_parameters_dict)
        
        if not is_successful:
            write_error_message_to_console_and_consoleFile(console_error_message, filepaths.console_messages)
            return (False, None, None, None, None)  # (is_successful, SE_CE_data_obj, baseLD_data_obj, global_parameters, control_strategy_parameters_dict)
        
        #------------------------------
        #      Read baseLD_ file
        #------------------------------
        X = load_non_pev_load(filepaths.baseLD)
        (is_successful, baseLD_data_obj) = X.load(self.start_simulation_unix_time)

        if not is_successful:
            write_error_message_to_console_and_consoleFile(console_error_message, filepaths.console_messages)
            return (False, None, None, None, None)  # (is_successful, SE_CE_data_obj, baseLD_data_obj, global_parameters, control_strategy_parameters_dict)
        
        #---------------------------------------------
        #  Assign Control Strategies to Charge Events
        #---------------------------------------------
        if is_successful and False == global_parameters['use_control_strategy_assignment_in_charge_event_file']:
            control_strategy_list = global_parameters['assign_control_strategies_to_charge_events']['control_strategy_list']
            seed = global_parameters['assign_control_strategies_to_charge_events']['seed']

            if len(control_strategy_list) > 0:
                rand_CS = select_control_strategy(seed, control_strategy_list)
                SEid_to_SE_type = SE_CE_data_obj.SEid_to_SE_type
                
                for X in SE_CE_data_obj.SE_group_charge_events:
                    for charge_event in X.charge_events:
                        CS = rand_CS.get_next_control_strategy()
                        if CS is not None:
                            (ES_enum, VS_enum) = CS
                            Ext_string = 'NA'
                            control_strategies = control_strategy_enums()
                            control_strategies.inverter_model_supports_Qsetpoint = L2_control_strategy_supports_Vrms_using_QkVAR(VS_enum)
                            control_strategies.ES_control_strategy = ES_enum
                            control_strategies.VS_control_strategy = VS_enum
                            control_strategies.ext_control_strategy = Ext_string
                            
                            assign_control_strategies_to_CE(control_strategies, charge_event, SEid_to_SE_type, control_strategy_parameters_dict)
        
        #---------------------------------------------
        #               Return Values
        #---------------------------------------------
        # SE_CE_data_obj:
        #       SE_CE_data_obj.SE_group_configuration_list -> list of SE_group_configuration
        #                       SE_group_configuration -> (SE_group_id, list of SE_configuration)
        #       SE_CE_data_obj.SE_group_charge_events = list of SE_group_charge_event_data
        #               SE_group_charge_event_data -> (SE_group_id, list of charge_event_data)
        #                               charge_event_data(charge_event_id, SE_group_id, SE_id, vehicle_id, vehicle_type, arrival_unix_time, departure_unix_time
        #                                                 arrival_SOC, departure_SOC, stop_charging_criteria, control_strategy_enums)
        #       SE_CE_data_obj.SEid_to_SE_type = {}
        #                      SEid_to_SE_type[SE_id] = SE_enum
        #
        #       SE_CE_data_obj.SEid_to_SE_group = {}
        #                      SEid_to_SE_group[SE_id] = SE_group
        #
        #       SE_CE_data_obj.ES_strategies = set()
        #               All unique ES_strategies in the CE file if (TRUE == use_control_strategy_assignment_in_charge_event_file)
        #
        #       SE_CE_data_obj.VS_strategies = set()
        #               All unique VS_strategies in the CE file if (TRUE == use_control_strategy_assignment_in_charge_event_file)
        #
        #       SE_CE_data_obj.ext_strategies = set()
        #               All unique ext_strategies in the CE file if (TRUE == use_control_strategy_assignment_in_charge_event_file)
        #        
        #       SE_CE_data_obj.caldera_powerflow_nodes = container_class()
        #               caldera_powerflow_nodes.all_caldera_node_names = set()
        #               caldera_powerflow_nodes.HPSE_caldera_node_names = set()
        #
        # baseLD_data_obj:
        #       baseLD_data_obj.actual_load_akW = list of double
        #       baseLD_data_obj.forecast_load_akW = list of double
        #       baseLD_data_obj.data_start_unix_time = double
        #       baseLD_data_obj.data_timestep_sec = double
        #
        # global_parameters:
        #       global_parameters = {}
        #       global_parameters[value_name] = value
        #
        # control_strategy_parameters_dict:
        #       control_strategy_parameters_dict = {}
        #       control_strategy_parameters_dict[L2_control_strategies_enum] = parameters_dict
        #               parameters_dict = {}
        #               parameters_dict[value_name] = value
        
        if is_successful:
            return (is_successful, SE_CE_data_obj, baseLD_data_obj, global_parameters, control_strategy_parameters_dict)
        else:
            write_error_message_to_console_and_consoleFile(console_error_message, filepaths.console_messages)
            return (False, None, None, None, None)       
    
    
#=============================================================
#=============================================================
#                   Load SE CE Input Files
#=============================================================
#=============================================================

class load_SE_CE_input_files:

    def load(self, SE_data_file_path, CE_data_file_path, global_parameters, L2_control_strategies_to_include, control_strategy_parameters_dict):
        self.L2_control_strategies_to_include = L2_control_strategies_to_include
        self.control_strategy_parameters_dict = control_strategy_parameters_dict
        
        (SE_errors, SEid_to_SE_group, SEid_to_SE_type, SEid_to_isInGridSim, SE_group_configuration_list, all_caldera_node_names, HPSE_caldera_node_names) = self.__get_supply_equipment_data(SE_data_file_path)

        CE_errors = []
        if len(SE_errors) == 0:
            use_control_strategy_assignment_in_charge_event_file = global_parameters['use_control_strategy_assignment_in_charge_event_file']
            (CE_errors, SE_group_charge_events, ES_strategies, VS_strategies, ext_strategies) = self.__get_charge_events_data(CE_data_file_path, SEid_to_SE_group, SEid_to_SE_type, SEid_to_isInGridSim, use_control_strategy_assignment_in_charge_event_file)
        
        #-------------------------------------
        
        SE_CE_data_obj = container_class()
        
        if len(SE_errors) == 0 and len(CE_errors) == 0:
            is_successfull = True
            
            caldera_powerflow_nodes = container_class()
            caldera_powerflow_nodes.all_caldera_node_names = all_caldera_node_names
            caldera_powerflow_nodes.HPSE_caldera_node_names = HPSE_caldera_node_names
            
            SE_CE_data_obj.SE_group_configuration_list = SE_group_configuration_list
            SE_CE_data_obj.SE_group_charge_events = SE_group_charge_events
            SE_CE_data_obj.SEid_to_SE_type = SEid_to_SE_type
            SE_CE_data_obj.SEid_to_SE_group = SEid_to_SE_group
            SE_CE_data_obj.caldera_powerflow_nodes = caldera_powerflow_nodes
            SE_CE_data_obj.ES_strategies = ES_strategies
            SE_CE_data_obj.VS_strategies = VS_strategies
            SE_CE_data_obj.ext_strategies = ext_strategies
            
        else:
            is_successfull = False
            SE_CE_data_obj.SE_group_configuration_list = None
            SE_CE_data_obj.SE_group_charge_events = None
            SE_CE_data_obj.SEid_to_SE_type = None
            SE_CE_data_obj.SEid_to_SE_group = None
            SE_CE_data_obj.caldera_powerflow_nodes = None
            SE_CE_data_obj.ES_strategies = None
            SE_CE_data_obj.VS_strategies = None
            SE_CE_data_obj.ext_strategies = None
            
            print_errors_file(SE_data_file_path, SE_errors)
            print_errors_file(CE_data_file_path, CE_errors)
        
        return (is_successfull, SE_CE_data_obj)


    def __get_supply_equipment_data(self, SE_data_file_path):
        number_of_fields = 7
        
        errors = []
        SEid_to_SEgroup = {}
        SEid_to_SE_type = {}
        SEid_to_isInGridSim = {}
        SE_group_configuration_list = []
        
        #------------------------
        
        if os.stat(SE_data_file_path).st_size ==0:
            errors.append("NA, File is empty.")
        
        #------------------------
        
        f_in = open(SE_data_file_path, 'r')
        line = f_in.readline()  # The first line is the header
        f_in.close()
        
        elements = line.split(',')
        if len(elements) != number_of_fields:
            errors.append("NA, Invalid number of fields.")
        
        #------------------------
        
        if len(errors) == 0:
            grid_node_id_col_name = elements[4].strip()
            location_type_col_name = elements[6].strip()
            df = pd.read_csv(SE_data_file_path, sep=',', header=0, dtype={grid_node_id_col_name:str, location_type_col_name:str})
            
            if len(df.columns) != number_of_fields:
                errors.append('NA, There must be {} columns in file.'.format(number_of_fields))
            
            if len(df.index) < 2:
                errors.append("NA, There must be at least 2 Supply Equipment defined.")
            
            if len(errors) == 0:                
                grid_node_id = df.iloc[:,4].astype('str').apply(lambda a: a.strip())
                grid_node_id = grid_node_id.apply(lambda a: 'nan' if a == '' else a)
                df.iloc[:,4] = grid_node_id
                
                location_type = df.iloc[:,6].astype('str').apply(lambda a: a.strip())
                location_type = location_type.apply(lambda a: 'nan' if a == '' else a)
                df.iloc[:,6] = location_type
                
                df.rename(columns = {df.columns[5]:'SE_group'}, inplace=True)
                df.sort_values(by=['SE_group'], ascending=True, inplace=True, na_position='last')
                
                SE_id = df.iloc[:,0].values
                SE_type = df.iloc[:,1].astype('str').values
                lon = df.iloc[:,2].values
                lat = df.iloc[:,3].values            
                grid_node_id = df.iloc[:,4].astype('str').values
                SE_group = df.iloc[:,5].values
                location_type = df.iloc[:,6].astype('str').values
                
                index = df.index.values
                
                #------------------------
                
                if SE_id.dtype != 'int64':
                    errors.append("NA, Invalid value in SE_id column. Values must be integers.")
                    
                if len(np.unique(SE_id)) != len(SE_id):
                    errors.append("NA, Values in SE_id column must be unique.")
                
                #if SE_type.dtype != 'int64':
                #    errors.append("NA, Invalid value in SE_type column. Values must be integers.")

                if lon.dtype != 'float64':
                    errors.append("NA, Invalid value in longitude column. Values must be floats.")

                if lat.dtype != 'float64':
                    errors.append("NA, Invalid value in lattitude column. Values must be floats.")
                
                if SE_group.dtype != 'int64':
                    errors.append("NA, Invalid value in SE_group column. Values must be integers.")
                
                if len(errors) == 0:
                    SE_configuration_list = []
                    SE_group_of_last_loaded_SE = -1
                    
                    for i in range(len(SE_group)):            
                        line_number = index[i] + 2
                        SE_id_val = SE_id[i]
                        is_valid = True
                        
                        #if(np.isnan(SE_id_val) or np.isnan(SE_type[i]) or np.isnan(lon[i]) or np.isnan(lat[i]) or np.isnan(SE_group[i])):
                        if(np.isnan(SE_id_val) or np.isnan(lon[i]) or np.isnan(lat[i]) or np.isnan(SE_group[i])):
                            is_valid = False
                            errors.append("{}, Invalid value type.".format(line_number))

                        if SE_group[i] < 0:
                            is_valid = False
                            errors.append("{}, SE_group must be non-negative.".format(line_number))
                        
                        if not np.isnan(SE_id_val) and SE_id_val in SEid_to_SEgroup:
                            is_valid = False
                            errors.append("{}, Duplicate SE_id in table.".format(line_number))
                        
                        (conversion_successfull, SE_enum) = get_supply_equipment_enum(str(SE_type[i]))
                        if not conversion_successfull:
                            is_valid = False
                            errors.append("{}, Invalid SE_type.".format(line_number))

                        if location_type[i] not in('H', 'W', 'O', 'U'):
                            is_valid = False
                            errors.append("{}, Invalid location_type.  Valid values: (H; W; O; U).".format(line_number))

                        if is_valid:
                            SEid_to_isInGridSim[SE_id_val] = (grid_node_id[i] != 'nan')
                            
                            if SEid_to_isInGridSim[SE_id_val]:
                                if (SE_group_of_last_loaded_SE >= 0) and (SE_group[i] != SE_group_of_last_loaded_SE):
                                    SE_group_configuration_list.append(SE_group_configuration(SE_group_of_last_loaded_SE, SE_configuration_list))
                                    SE_configuration_list = []
                                
                                SE_configuration_list.append(SE_configuration(SE_group[i], SE_id_val, SE_enum, lat[i], lon[i], grid_node_id[i], location_type[i]))
                                SEid_to_SEgroup[SE_id_val] = SE_group[i]
                                SEid_to_SE_type[SE_id_val] = SE_enum
                                SE_group_of_last_loaded_SE = SE_group[i]
                            
                    if i > 0 and len(SE_configuration_list) > 0:
                        SE_group_configuration_list.append(SE_group_configuration(SE_group_of_last_loaded_SE, SE_configuration_list))
                        SE_configuration_list = []
                    
                    #------------------------
                    
                    if len(SEid_to_SE_type) == 0:
                        errors.append("NA, No Supply Equipment has been selected.")
                    
                    #------------------------
                    
                    all_caldera_node_names = set()
                    HPSE_caldera_node_names = set()
        
                    if len(errors) == 0:
                        for i in range(len(grid_node_id)):
                            if SEid_to_isInGridSim[SE_id[i]]:
                                node_id = grid_node_id[i]
                            
                                if node_id not in all_caldera_node_names:
                                    all_caldera_node_names.add(node_id)
                            
                                if SE_id[i] in SEid_to_SE_type:
                                    SE_enum = SEid_to_SE_type[SE_id[i]]
                                
                                    if supply_equipment_is_3phase(SE_enum):
                                        if node_id not in HPSE_caldera_node_names:
                                            HPSE_caldera_node_names.add(node_id)
        
        if 0 < len(errors):
            SEid_to_SE_type = {}
            SEid_to_SEgroup = {}
            SEid_to_isInGridSim = {}
            SE_group_configuration_list = []
            all_caldera_node_names = set()
            HPSE_caldera_node_names = set()

        return (errors, SEid_to_SEgroup, SEid_to_SE_type, SEid_to_isInGridSim, SE_group_configuration_list, all_caldera_node_names, HPSE_caldera_node_names)
  
    #=====================================================

    def __parse_charge_event_line(self, line, line_number, number_of_fields, SEid_to_SE_type, use_control_strategy_assignment_in_charge_event_file):
        errors = []
        elements = line.split(',')
        
        #---------------------
        
        number_of_fields_is_valid = True
        if len(elements) != number_of_fields:
            number_of_fields_is_valid = False        
        
        #---------------------
        
        if not number_of_fields_is_valid:
            errors.append("{}, Invalid number of fields.".format(line_number))
        try:
            charge_event_id = int(elements[0])
            SE_id = int(elements[1])
            vehicle_id = int(elements[2])
            arrival_unix_time = 3600*float(elements[4])
            departure_unix_time = 3600*float(elements[6])
            arrival_SOC = 100*float(elements[8])
            departure_SOC = 100*float(elements[9])
        
        except ValueError:
            errors.append("{}, Invalid value.".format(line_number))
        
        if len(errors) == 0:
            (conversion_successfull, vehicle_type) = get_vehicle_enum(elements[3])
            
            if not conversion_successfull:
                errors.append("{}, Invalid pev_type.".format(line_number))
            
            #---------
            
            if SE_id not in SEid_to_SE_type:
                errors.append("{}, SE_id not in SE table.".format(line_number))
                
            #---------
            
            if departure_unix_time - arrival_unix_time < 1:
                errors.append("{}, Error: Departure time before arrival time.".format(line_number))
                
            if not (0 <= arrival_SOC and arrival_SOC < departure_SOC and departure_SOC <= 100):
                errors.append("{}, Error: Invalid soc values.".format(line_number))
            
            if len(errors) == 0:
                if not pev_is_compatible_with_supply_equipment(vehicle_type, SEid_to_SE_type[SE_id]):
                    errors.append("{}, Error: Incompatible Supply Equipment and PEV types.".format(line_number))
        
        #-------------------------------------
        
        if len(errors) == 0:
            SE_group_id = -1
            charge_event = charge_event_data(charge_event_id, SE_group_id, SE_id, vehicle_id, vehicle_type, arrival_unix_time, departure_unix_time, arrival_SOC, departure_SOC, stop_charging_criteria(), control_strategy_enums())
            
            #---------
            
            if use_control_strategy_assignment_in_charge_event_file:
                ES_str = elements[10].strip()
                VS_str = elements[11].strip()
                Ext_str = elements[12].strip()
                
                (tmp_errors, control_strategies) = get_control_strategy_enums(ES_str, VS_str, Ext_str, line_number, self.L2_control_strategies_to_include)
                
                if len(tmp_errors) > 0:
                    errors += tmp_errors
                else:
                    if not supply_equipment_is_L2(SEid_to_SE_type[SE_id]):
                        ES_enum = control_strategies.ES_control_strategy
                        VS_enum = control_strategies.VS_control_strategy
                        NA_enum = L2_control_strategies_enum.NA
                        if ES_enum != NA_enum or VS_enum != NA_enum:
                            errors.append("{}, Error: L2 control strategy assigned to non L2 charge.".format(line_number))
                    
                    if len(errors) == 0:
                        assign_control_strategies_to_CE(control_strategies, charge_event, SEid_to_SE_type, self.control_strategy_parameters_dict)
        
        #-------------------------------------
        
        if len(errors) > 0:
            charge_event = None
        
        return (errors, charge_event)


    def __get_charge_events_data(self, CE_data_file_path, SEid_to_SEgroup, SEid_to_SE_type, SEid_to_isInGridSim, use_control_strategy_assignment_in_charge_event_file):
        number_of_fields = 13
        errors = []
        
        f_in = open(CE_data_file_path, 'r')
        line = f_in.readline()  # The first line is the header
        
        elements = line.split(',') 
        if len(elements) != number_of_fields:
            errors.append("NA, Invalid number of fields.")
        
        #----------------------------
        
        line = f_in.readline() 
        line_number = 2
        
        SE_group_to_chargeEventsList = {}
        charge_event_id = []
        VS_strategies = set()
        ES_strategies = set()
        ext_strategies = set()
        
        while line:
            (errs, charge_event) = self.__parse_charge_event_line(line, line_number, number_of_fields, SEid_to_SE_type, use_control_strategy_assignment_in_charge_event_file)
            
            if 0 < len(errs):
                errors.extend(errs)
                
            elif SEid_to_isInGridSim[charge_event.SE_id]:
            
                charge_event_id.append(charge_event.charge_event_id)
                
                #------------------
                
                if use_control_strategy_assignment_in_charge_event_file:
                    ES_enum = charge_event.control_enums.ES_control_strategy
                    VS_enum = charge_event.control_enums.VS_control_strategy
                    ext_str = charge_event.control_enums.ext_control_strategy
                    
                    if ES_enum not in ES_strategies:
                        ES_strategies.add(ES_enum)
                
                    if VS_enum not in VS_strategies:
                        VS_strategies.add(VS_enum)
                        
                    if ext_str not in ext_strategies:
                        ext_strategies.add(ext_str)
            
                #------------------                
                
                SE_group = SEid_to_SEgroup[charge_event.SE_id]
                charge_event.SE_group_id = SE_group
                
                if SE_group not in SE_group_to_chargeEventsList:
                    SE_group_to_chargeEventsList[SE_group] = []
                
                SE_group_to_chargeEventsList[SE_group].append(charge_event)
                
                #------------------    
            
            line_number += 1
            line = f_in.readline()
                
        f_in.close()
        
        #------------------  
        
        if 0 < len(charge_event_id):
            X = np.array(charge_event_id)
            if len(np.unique(X)) != len(X):
                errors.append("NA, Values in charge_event_id column must be unique.")
        
        #-------------------------
        
        SE_group_charge_events = []
        
        if len(errors) == 0:
            for (SE_group, charge_events) in SE_group_to_chargeEventsList.items():
                SE_group_charge_events.append(SE_group_charge_event_data(SE_group, charge_events))

        #-------------------------
        
        return (errors, SE_group_charge_events, ES_strategies, VS_strategies, ext_strategies)
    
    
#=============================================================
#=============================================================
#                   Load Non PEV Load
#=============================================================
#=============================================================

class load_non_pev_load:

    def __init__(self, data_file_path):
        self.data_file_path = data_file_path
        
        self.actual_load_akW = []
        self.forecast_load_akW = []
        self.conversion_obj = data_conversion_and_validation()

    def __parse_line(self, line, line_number):
        errors = []
        value_0 = None
        value_1 = None
        
        #----------------
        
        str_data = line.split(',')

        if len(str_data) != 2:
            errors.append("{}, Invalid number of fields".format(line_number))

        if len(errors) == 0:
            first_str = str_data[0].strip()
            second_str = str_data[1].strip()
             
            if line_number == 1:            
                if first_str == "data_start_time_unix_time":
                    value_0 = first_str
                    (tmp_errors, value_1) = self.conversion_obj.cast_integer_value(second_str, line_number)
                else:
                    errors.append("{}, data_start_time_unix_time is expected on this line.".format(line_number))

                errors += tmp_errors                
            elif line_number == 2:            
                if first_str == "time_step_sec":
                    value_0 = first_str
                    (tmp_errors, value_1) = self.conversion_obj.cast_integer_value(second_str, line_number)
                else:
                    errors.append("{}, time_step_sec is expected on this line.".format(line_number))

                errors += tmp_errors
            else: 
                (tmp_errors_0, value_0) = self.conversion_obj.cast_double_value(first_str, line_number)
                (tmp_errors_1, value_1) = self.conversion_obj.cast_double_value(second_str, line_number)
                errors += tmp_errors_0
                errors += tmp_errors_1

        return (errors, value_0, value_1)

    
    def load(self, start_simulation_unix_time):            
        errors = []
        tmp_errors = []
        
        #------------------------------------------
        #         Validate Meta Data
        #------------------------------------------  

        f_in = open(self.data_file_path, 'r') 
        line_number = 1
        
        (tmp_errors, parameter_name, data_start_time_unix_time) = self.__parse_line(f_in.readline(), line_number)
        line_number += 1 
        errors += tmp_errors
        
        (tmp_errors, parameter_name, orig_time_step_sec) = self.__parse_line(f_in.readline(), line_number)
        line_number += 1 
        errors += tmp_errors
        
        if len(errors) == 0:
            if 0.000001 < abs(data_start_time_unix_time % 3600):
                errors.append('1, data_start_time_unix_time must be 0 or a multiple of 3600')
                
            if start_simulation_unix_time < data_start_time_unix_time:
                errors.append('1, data_start_time_unix_time must precede the simulation start time.')

            if orig_time_step_sec not in [1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60]:
                errors.append('2, time_step_sec must be on of the following: (1; 2; 3; 4; 5; 6; 10; 12; 15; 20; 30; 60)')
            
        # skip the header
        f_in.readline()
        line_number += 1
        
        #------------------------------------------
        #         Validate and Convert Data
        #------------------------------------------
        validated_actual_load = []
        validated_forecast_load = []
        
        for line in f_in:
            (tmp_errors, validated_actual_data_item, validated_forecast_data_item) = self.__parse_line(line, line_number)
            validated_actual_load.append(validated_actual_data_item)
            validated_forecast_load.append(validated_forecast_data_item)
            errors += tmp_errors 
            line_number += 1

        f_in.close()
        
        #------------------------------------------
        
        baseLD_data_obj = container_class()
        
        if len(errors) == 0: 
            is_successful = True
            baseLD_data_obj.actual_load_akW = validated_actual_load
            baseLD_data_obj.forecast_load_akW = validated_forecast_load
            baseLD_data_obj.data_start_unix_time = data_start_time_unix_time
            baseLD_data_obj.data_timestep_sec = orig_time_step_sec
        else:
            is_successful = False
            baseLD_data_obj.actual_load_akW = None
            baseLD_data_obj.forecast_load_akW = None
            baseLD_data_obj.data_start_unix_time = None
            baseLD_data_obj.data_timestep_sec = None
            print_errors_file(self.data_file_path, errors)
        
        return (is_successful, baseLD_data_obj)


#=============================================================
#=============================================================
#                   Load Parameter Files
#=============================================================
#=============================================================


#===============================
#    Load Global Parameters
#===============================

class load_global_parameters:

    def __init__(self, file_path_, L2_control_strategies_to_include):
        self.file_path = file_path_
        self.L2_control_strategies_to_include = L2_control_strategies_to_include

        self.meta_data_info = {}
        self.meta_data_info['str'] = {}
        self.meta_data_info['list_of_tuples_dd'] = {}
        self.meta_data_info['dict_of_string_keys_double_vals'] = {}
        self.meta_data_info['dict_of_string_keys_string_vals'] = {}
        self.meta_data_info['int'] = {}
        self.meta_data_info['bool'] = {}
        self.meta_data_info['list_of_3ples_StrStrStr'] = {}
        
        self.meta_data_info['double'] = {
                            'feeder_power_limit_kW' : (100, math.inf),
                            'base_load_forecast_adjust_interval_hrs' : (0.1, 24)
        }
        
        '''
        self.meta_data_info['bool'] = {
                            'use_control_strategy_assignment_in_charge_event_file' : None
        }
        
        self.meta_data_info['list_of_3ples_StrStrStr'] = {
                            'assign_control_strategies_to_charge_events' : None
        }
        '''
        
        self.processor_obj = parameters_file_processor(self.meta_data_info)
    
    
    def __parameter_file_specific_checks(self, parameters_dict, valid_parameter_name_to_line_number_map):
        conversion_obj = data_conversion_and_validation()
        errors = []
        
        #---------------------------------------------
        #  assign_control_strategies_to_charge_events
        #---------------------------------------------
        '''
        line_number = valid_parameter_name_to_line_number_map['assign_control_strategies_to_charge_events']
        tmp_list = parameters_dict['assign_control_strategies_to_charge_events']
        tmp_dict = {}
        tmp_dict['control_strategy_list'] = []
        tmp_dict['seed'] = None
        
        for (ES_str, VS_str, perc_str) in tmp_list:
            if ES_str.strip() == 'seed':
                range_vals = (1, math.inf)
                (tmp_errors, value) = self.processor_obj.cast_to_int_and_check_bounds(VS_str, line_number, range_vals)
                
                if len(tmp_errors) > 0:
                    errors += tmp_errors
                    break
                else:
                    tmp_dict['seed'] = int(value)
            else:
                Ext_str = 'NA'
                (tmp_errors, control_strategies) = get_control_strategy_enums(ES_str, VS_str, Ext_str, line_number, self.L2_control_strategies_to_include)
                ES_enum = control_strategies.control_enums.ES_control_strategy
                VS_enum = control_strategies.control_enums.VS_control_strategy
                
                if len(tmp_errors) > 0:
                    errors += tmp_errors
                    break
                
                if ES_enum == L2_control_strategies_enum.NA and VS_enum == L2_control_strategies_enum.NA:
                    errors.append('{}, Invalid Control Strategy Enum.  Both strategies are NA.'.format(line_number))
                    break
                
                range_vals = (0.01, 100)
                (tmp_errors, perc_val) = self.processor_obj.cast_to_double_and_check_bounds(perc_str, line_number, range_vals)
                
                if len(tmp_errors) > 0:
                    errors += tmp_errors
                    break
                else:
                    tmp_dict['control_strategy_list'].append((ES_enum, VS_enum, perc_val))
        
        if len(errors) == 0:
            if tmp_dict['seed'] == None:
                errors.append('{}, Invalid Value.  No seed present.'.format(line_number))
        
            perc_sum = 0
            for (ES_enum, VS_enum, perc_val) in tmp_dict['control_strategy_list']:
                perc_sum += perc_val
                
            if perc_sum > 100:
                errors.append('{}, Invalid Value.  Sum of percents exceeds 100 percent.'.format(line_number))
        '''
        
        #==============================================
        #              Hardcoded Values
        #==============================================        
        tmp_dict = {}
        tmp_dict['control_strategy_list'] = []  # (ES_enum, VS_enum, perc_val)
        tmp_dict['seed'] = 206
        
        parameters_dict['use_control_strategy_assignment_in_charge_event_file'] = True
        #==============================================
        #==============================================
        
        #-------------------
        
        parameters_dict['assign_control_strategies_to_charge_events'] = tmp_dict
       
        #=====================================
        
        return errors
    
    
    def load(self):
        (errors, parameters_dict, valid_parameter_name_to_line_number_map) = self.processor_obj.validate(self.file_path)
        
        if len(errors) > 0:
            print_errors_file(self.file_path, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #------------------------------------------
        #      Parameter File Specific Checks
        #------------------------------------------
        errors += self.__parameter_file_specific_checks(parameters_dict, valid_parameter_name_to_line_number_map)
            
        if len(errors) > 0:
            print_errors_file(self.file_path, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #========================================
        
        return (True, parameters_dict)   #(is_successful, parameters_dict)
    
    
#===============================
#  Load ES100 Parameters
#===============================

class load_ES100_parameters:

    def __init__(self, file_path_):
        self.file_path = file_path_

        self.meta_data_info = {}        
        self.meta_data_info['bool'] = {}
        self.meta_data_info['list_of_tuples_dd'] = {}
        self.meta_data_info['dict_of_string_keys_double_vals'] = {}
        self.meta_data_info['dict_of_string_keys_string_vals'] = {}
        self.meta_data_info['dict_of_string_keys_double_vals'] = {}
        self.meta_data_info['list_of_3ples_StrStrStr'] = {}
        
        self.meta_data_info['double'] = {
                                    'beginning_of_TofU_rate_period__time_from_midnight_hrs' : (-12, 12),
                                    'end_of_TofU_rate_period__time_from_midnight_hrs' : (-12, 12),
                                    'M1_delay_period_hrs' : (0, 12)
        }
        
        self.meta_data_info['str'] = {
                            'randomization_method' : None
        }
        
        self.meta_data_info['int'] = {
                            'random_seed' : (1, math.inf)
        }
        
        self.processor_obj = parameters_file_processor(self.meta_data_info)
    
    
    def __parameter_file_specific_checks(self, parameters_dict, valid_parameter_name_to_line_number_map):
        conversion_obj = data_conversion_and_validation()
        errors = []
        
        #------------------
        
        if parameters_dict['randomization_method'] not in ('M1','M2','M3'):
            line_number = valid_parameter_name_to_line_number_map['randomization_method']
            errors.append('{}, randomization_method must be one of (M1  M2  M3).'.format(line_number))
        
        TofU_rate_period_duration_hrs = parameters_dict['end_of_TofU_rate_period__time_from_midnight_hrs'] - parameters_dict['beginning_of_TofU_rate_period__time_from_midnight_hrs']
        
        # commented out to allow TOU period within a day. e.g. (8, -6) aka (8, 18)
        #if TofU_rate_period_duration_hrs < 0.5:
        #    errors.append('NA, Invalid time of use rate period.')
        
        return errors
    
    
    def load(self):
        (errors, parameters_dict, valid_parameter_name_to_line_number_map) = self.processor_obj.validate(self.file_path)
        
        if len(errors) > 0:
            print_errors_file(self.file_path, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #------------------------------------------
        #      Parameter File Specific Checks
        #------------------------------------------
        errors += self.__parameter_file_specific_checks(parameters_dict, valid_parameter_name_to_line_number_map)
            
        if len(errors) > 0:
            print_errors_file(self.file_path, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #========================================
        
        return (True, parameters_dict)   #(is_successful, parameters_dict)


#===============================
#  Load ES110 Parameters
#===============================

class load_ES110_parameters:

    def __init__(self, file_path_):
        self.file_path = file_path_

        self.meta_data_info = {}
        self.meta_data_info['str'] = {}
        self.meta_data_info['bool'] = {}
        self.meta_data_info['double'] = {}
        self.meta_data_info['list_of_tuples_dd'] = {}
        self.meta_data_info['dict_of_string_keys_string_vals'] = {}
        self.meta_data_info['list_of_3ples_StrStrStr'] = {}
        self.meta_data_info['dict_of_string_keys_double_vals'] = {}
        
        self.meta_data_info['int'] = {
                                    'random_seed' : (1, math.inf)
        }
        
        self.processor_obj = parameters_file_processor(self.meta_data_info)
    
    
    def __parameter_file_specific_checks(self, parameters_dict, valid_parameter_name_to_line_number_map):
        conversion_obj = data_conversion_and_validation()
        errors = []
        
        #------------------
        
        return errors
    
    
    def load(self):
        (errors, parameters_dict, valid_parameter_name_to_line_number_map) = self.processor_obj.validate(self.file_path)
        
        if len(errors) > 0:
            print_errors_file(self.file_path, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #------------------------------------------
        #      Parameter File Specific Checks
        #------------------------------------------
        errors += self.__parameter_file_specific_checks(parameters_dict, valid_parameter_name_to_line_number_map)
            
        if len(errors) > 0:
            print_errors_file(self.file_path, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #========================================
        
        return (True, parameters_dict)   #(is_successful, parameters_dict)
    

#===============================
#  Load ES200 Parameters
#===============================

class load_ES200_parameters:

    def __init__(self, file_path_):
        self.file_path = file_path_

        self.meta_data_info = {}
        self.meta_data_info['str'] = {}
        self.meta_data_info['bool'] = {}   
        self.meta_data_info['int'] = {}
        self.meta_data_info['list_of_tuples_dd'] = {}
        self.meta_data_info['dict_of_string_keys_double_vals'] = {}
        self.meta_data_info['dict_of_string_keys_string_vals'] = {}
        self.meta_data_info['list_of_3ples_StrStrStr'] = {}                
        
        self.meta_data_info['double'] = {
                                    'weight_factor_to_calculate_valley_fill_target' : (0, 1)
        }
        
        self.processor_obj = parameters_file_processor(self.meta_data_info)
    
    
    def __parameter_file_specific_checks(self, parameters_dict, valid_parameter_name_to_line_number_map):
        conversion_obj = data_conversion_and_validation()
        errors = []
        
        #------------------
        
        return errors
    
    
    def load(self):
        (errors, parameters_dict, valid_parameter_name_to_line_number_map) = self.processor_obj.validate(self.file_path)
        
        if len(errors) > 0:
            print_errors_file(self.file_path, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #------------------------------------------
        #      Parameter File Specific Checks
        #------------------------------------------
        errors += self.__parameter_file_specific_checks(parameters_dict, valid_parameter_name_to_line_number_map)
            
        if len(errors) > 0:
            print_errors_file(self.file_path, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #========================================
        
        return (True, parameters_dict)   #(is_successful, parameters_dict)


#===============================
#  Load ES300 Parameters
#===============================

class load_ES300_parameters:

    def __init__(self, file_path_):
        self.file_path = file_path_

        self.meta_data_info = {}
        self.meta_data_info['str'] = {}
        self.meta_data_info['bool'] = {}   
        self.meta_data_info['int'] = {}
        self.meta_data_info['list_of_tuples_dd'] = {}
        self.meta_data_info['dict_of_string_keys_double_vals'] = {}
        self.meta_data_info['dict_of_string_keys_string_vals'] = {}
        self.meta_data_info['list_of_3ples_StrStrStr'] = {}
        
        self.meta_data_info['double'] = {
                                    'weight_factor_to_calculate_valley_fill_target' : (0, 1)
        }
        
        self.processor_obj = parameters_file_processor(self.meta_data_info)
    
    
    def __parameter_file_specific_checks(self, parameters_dict, valid_parameter_name_to_line_number_map):
        conversion_obj = data_conversion_and_validation()
        errors = []
        
        #------------------
        
        return errors
    
    
    def load(self):
        (errors, parameters_dict, valid_parameter_name_to_line_number_map) = self.processor_obj.validate(self.file_path)
        
        if len(errors) > 0:
            print_errors_file(self.file_path, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #------------------------------------------
        #      Parameter File Specific Checks
        #------------------------------------------
        errors += self.__parameter_file_specific_checks(parameters_dict, valid_parameter_name_to_line_number_map)
            
        if len(errors) > 0:
            print_errors_file(self.file_path, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #========================================
        
        return (True, parameters_dict)   #(is_successful, parameters_dict)


#===============================
#  Load ES500 Parameters
#===============================

class load_ES500_parameters:

    def __init__(self, file_path):
        self.file__ = file_path        

        self.meta_data_info = {}
        self.meta_data_info['dict_of_string_keys_string_vals'] = {}        
        self.meta_data_info['list_of_3ples_StrStrStr'] = {}
        
        self.meta_data_info['str'] = {
                            'objective_function'  : None
        }
        
        self.meta_data_info['int'] = {
                            'charging_needs_lead_time_sec' : (5, 60*30), 
                            'energy_setpoints_lead_time_sec' : (5, 60*30), 
                            'num_pevs_to_start_charging_each_controlled_cycle_iteration' : (1, 100), 
                            'max_number_of_controlled_cycle_iterations' : (20, 5000), 
                            'aggregator_timestep_mins' : None
        }
        self.meta_data_info['double'] = {
                            'charge_flexibility_threshold' : (0.1, 4), 
                            'prediction_horizon_duration_hrs' : (2, 48),
                            'aggregator_poll_time_sec' : (0.001, 0.250), 
                            'E_step_0_multiplier' : (0.2, 2),
                            'calc_obj_fun_constraints_depart_time_adjustment_sec' : (0, 15*60)
        }
        self.meta_data_info['bool'] = {
                            'cvxopt_show_progress'  : None,
                            'log_optimization_values'  : None,
                            'log_pev_energy_setpoints' : None,
                            'log_stop_charge_cycling_decision_parameters' : None
        }
        self.meta_data_info['list_of_tuples_dd'] = {
                            'charge_cycling_control_boundary' : ((0, 1), (0, 1)), 
                            'opt_solver_iteration_values' : ((0.000001, 0.01), (0.1, 10))
        }
        self.meta_data_info['dict_of_string_keys_double_vals'] = {
                            'charge_event_forecast_arrival_time_sec' : {'seed' : (1, math.inf), 'stdev' : (0, 3600), 'stdev_bounds' : (0.5, 3)},
                            'charge_event_forecast_park_duration_sec' : {'seed' : (1, math.inf), 'stdev' : (0, 3600), 'stdev_bounds' : (0.5, 3)}, 
                            'charge_event_forecast_e3_charge_remain_soc' : {'seed' : (1, math.inf), 'stdev' : (0, 25), 'stdev_bounds' : (0.5, 3)},
                            'randomize_pev_lead_time_off_to_on_lead_time_sec' : {'seed' : (1, math.inf), 'stdev' : (0, 6*60), 'stdev_bounds' : (0.5, 3)},
                            'randomize_pev_lead_time_default_lead_time_sec' : {'seed' : (1, math.inf), 'stdev' : (0, 6*60), 'stdev_bounds' : (0.5, 3)}
        }
        
        self.processor_obj = parameters_file_processor(self.meta_data_info)


    def __miscellaneous_relational_checks(self, parameters_dict, valid_parameter_name_to_line_number_map):
        charging_needs_lead_time_sec = parameters_dict['charging_needs_lead_time_sec']
        energy_setpoints_lead_time_sec = parameters_dict['energy_setpoints_lead_time_sec']
        aggregator_timestep_mins = parameters_dict['aggregator_timestep_mins']
        
        #---------------------
        
        randomize_lead_time_dict = parameters_dict['randomize_pev_lead_time_off_to_on_lead_time_sec']
        X1_sec = randomize_lead_time_dict['stdev'] * randomize_lead_time_dict['stdev_bounds']
        
        randomize_lead_time_dict = parameters_dict['randomize_pev_lead_time_default_lead_time_sec']
        X2_sec = randomize_lead_time_dict['stdev'] * randomize_lead_time_dict['stdev_bounds']
        
        max_randomize_lead_time_sec = max(X1_sec, X2_sec)
        
        #---------------------
        
        errors = []
        
        if aggregator_timestep_mins not in [1,2,3,4,5,6,10,12,15,20,30,60]:
            line_number = valid_parameter_name_to_line_number_map['aggregator_timestep_mins']
            errors.append('{}, aggregator_timestep_mins must be one of the following: (1; 2; 3; 4; 5; 6; 10; 12; 15; 20; 30; 60).'.format(line_number))
        
        #-------
        
        if not(max_randomize_lead_time_sec + 10 < energy_setpoints_lead_time_sec):
            errors.append('NA, energy_setpoints_lead_time_sec must be greater than max_randomize_lead_time_sec.')
        
        if not(energy_setpoints_lead_time_sec + 10 < charging_needs_lead_time_sec):
            errors.append('NA, charging_needs_lead_time_sec must be greater than energy_setpoints_lead_time_sec.')
        
        if not(charging_needs_lead_time_sec + 10 < (60*aggregator_timestep_mins - max_randomize_lead_time_sec)):
            errors.append('NA, charging_needs_lead_time_sec must be less than (60*aggregator_timestep_mins - max_randomize_lead_time_sec).')
        
        #---------------------
        
        objective_function = parameters_dict['objective_function']
        
        if objective_function not in('minimize_load', 'minimize_delta_load', 'minimize_delta_pev_load'):
            line_number = valid_parameter_name_to_line_number_map['objective_function']
            errors.append('{}, objective_function must be one of the following: (minimize_load; minimize_delta_load; minimize_delta_pev_load).'.format(line_number))
        
        return errors


    def load(self):
        (errors, parameters_dict, valid_parameter_name_to_line_number_map) = self.processor_obj.validate(self.file__)

        if len(errors) > 0:
            print_errors_file(self.file__, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #------------------------------------------
        #    Miscellaneous Relational Checks
        #------------------------------------------
        errors += self.__miscellaneous_relational_checks(parameters_dict, valid_parameter_name_to_line_number_map)
            
        if len(errors) > 0:
            print_errors_file(self.file__, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #========================================
        
        return (True, parameters_dict)   #(is_successful, parameters_dict)
    

#===============================
#  Load VS100 Parameters
#===============================

class load_VS100_parameters:

    def __init__(self, file_path_):
        self.file_path = file_path_

        self.meta_data_info = {}
        self.meta_data_info['str'] = {}
        self.meta_data_info['bool'] = {}   
        self.meta_data_info['int'] = {}
        self.meta_data_info['dict_of_string_keys_double_vals'] = {}
        self.meta_data_info['list_of_3ples_StrStrStr'] = {}                
        
        self.meta_data_info['double'] = {
                                    'target_P3_reference__percent_of_maxP3' : (50, 100),
                                    'max_delta_kW_per_min' : (0.01, 1000)
        }
        
        self.meta_data_info['list_of_tuples_dd'] = {
                            'volt_delta_kW_curve' : ((0.8, 1.2), (-100, 100))
        }
        
        self.meta_data_info['dict_of_string_keys_string_vals'] = {
                            'voltage_LPF' :  {'is_active':None, 'seed':None, 'window_size_LB':None, 'window_size_UB':None, 'window_type':None}
        }
        
        self.processor_obj = parameters_file_processor(self.meta_data_info)
    
    
    def __parameter_file_specific_checks(self, parameters_dict, valid_parameter_name_to_line_number_map):
        conversion_obj = data_conversion_and_validation()
        errors = []
        
        #=================================
        
        line_number = valid_parameter_name_to_line_number_map['voltage_LPF']
        tmp_dict = parameters_dict['voltage_LPF']
        tmp_errors = convert_and_validate__voltage_LPF(tmp_dict, line_number, self.processor_obj)
        parameters_dict['voltage_LPF'] = tmp_dict
        
        if len(tmp_errors) > 0:
            errors += tmp_errors
        
        #=================================
        
        line_number = valid_parameter_name_to_line_number_map['volt_delta_kW_curve']
        volt_delta_kW_curve = parameters_dict['volt_delta_kW_curve']
        
        if len(volt_delta_kW_curve) < 2:
            errors.append('{}, Volt_delta_kW_curve must have at least 2 points.'.format(line_number))
        
        if len(errors) == 0:
            for i in range(0, len(volt_delta_kW_curve) - 1):
                puV_cur = volt_delta_kW_curve[i][0]
                percP_cur = volt_delta_kW_curve[i][1]
                puV_next = volt_delta_kW_curve[i+1][0]
                percP_next = volt_delta_kW_curve[i+1][1]
                
                if not (puV_cur < puV_next):
                    errors.append('{}, Per unit voltage values must be increasing in volt_delta_kW_curve.'.format(line_number))
                    break
                    
                if not (percP_cur <= percP_next):
                    errors.append('{}, Percent real power must be non-decreasing in volt_delta_kW_curve.'.format(line_number))
                    break
        
        #------------------
        
        return errors
    
    
    def load(self):
        (errors, parameters_dict, valid_parameter_name_to_line_number_map) = self.processor_obj.validate(self.file_path)
        
        if len(errors) > 0:
            print_errors_file(self.file_path, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #------------------------------------------
        #      Parameter File Specific Checks
        #------------------------------------------
        errors += self.__parameter_file_specific_checks(parameters_dict, valid_parameter_name_to_line_number_map)
            
        if len(errors) > 0:
            print_errors_file(self.file_path, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #========================================
        
        return (True, parameters_dict)   #(is_successful, parameters_dict)

#===============================
#  Load VS200 Parameters
#===============================

class load_VS200_parameters:

    def __init__(self, file_path_):
        self.file_path = file_path_

        self.meta_data_info = {}
        self.meta_data_info['str'] = {}           
        self.meta_data_info['int'] = {}
        self.meta_data_info['dict_of_string_keys_double_vals'] = {}
        self.meta_data_info['list_of_3ples_StrStrStr'] = {}                
        
        self.meta_data_info['bool'] = {
                                    'can_provide_reactive_power_after_battery_full' : None
        }
        
        self.meta_data_info['double'] = {
                                    'target_P3_reference__percent_of_maxP3' : (50, 100),
                                    'max_delta_kVAR_per_min' : (0.01, 1000)
        }
        
        self.meta_data_info['list_of_tuples_dd'] = {
                            'volt_var_curve' : ((0.8, 1.2), (-100, 100))
        }
        
        self.meta_data_info['dict_of_string_keys_string_vals'] = {
                            'voltage_LPF' :  {'is_active':None, 'seed':None, 'window_size_LB':None, 'window_size_UB':None, 'window_type':None}
        }
        
        self.processor_obj = parameters_file_processor(self.meta_data_info)
    
    
    def __parameter_file_specific_checks(self, parameters_dict, valid_parameter_name_to_line_number_map):
        conversion_obj = data_conversion_and_validation()
        errors = []
        
        #=================================
        
        line_number = valid_parameter_name_to_line_number_map['voltage_LPF']
        
        #-----------------------------
        tmp_dict = parameters_dict['voltage_LPF']
        
        #tmp_dict_1 = parameters_dict['voltage_LPF']
        #tmp_dict = {}
        #tmp_dict['is_active'] = tmp_dict_1['is_active']
        #tmp_dict['seed'] = tmp_dict_1['seed']
        #tmp_dict['window_size_LB'] = tmp_dict_1['window_size']
        #tmp_dict['window_size_UB'] = tmp_dict_1['window_size']
        #tmp_dict['window_type'] = tmp_dict_1['window_type']
        #-----------------------------
        
        tmp_errors = convert_and_validate__voltage_LPF(tmp_dict, line_number, self.processor_obj)
        parameters_dict['voltage_LPF'] = tmp_dict
        
        if len(tmp_errors) > 0:
            errors += tmp_errors
        
        #=================================
        
        line_number = valid_parameter_name_to_line_number_map['volt_var_curve']
        volt_var_curve = parameters_dict['volt_var_curve']
        
        if len(volt_var_curve) < 2:
            errors.append('{}, Volt_var_curve must have at least 2 points.'.format(line_number))
        
        if len(errors) == 0:
            for i in range(0, len(volt_var_curve) - 1):
                puV_cur = volt_var_curve[i][0]
                percQ_cur = volt_var_curve[i][1]
                puV_next = volt_var_curve[i+1][0]
                percQ_next = volt_var_curve[i+1][1]
                
                if not (puV_cur < puV_next):
                    errors.append('{}, Per unit voltage values must be increasing in volt_var_curve.'.format(line_number))
                    break
                    
                if not (percQ_cur <= percQ_next):
                    errors.append('{}, Percent reactive power must be non-decreasing in volt_var_curve.'.format(line_number))
                    break
        
        #------------------
        
        return errors
    
    
    def load(self):
        (errors, parameters_dict, valid_parameter_name_to_line_number_map) = self.processor_obj.validate(self.file_path)
        
        if len(errors) > 0:
            print_errors_file(self.file_path, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #------------------------------------------
        #      Parameter File Specific Checks
        #------------------------------------------
        errors += self.__parameter_file_specific_checks(parameters_dict, valid_parameter_name_to_line_number_map)
            
        if len(errors) > 0:
            print_errors_file(self.file_path, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #========================================
        
        return (True, parameters_dict)   #(is_successful, parameters_dict)


#===============================
#  Load VS300 Parameters
#===============================

class load_VS300_parameters:

    def __init__(self, file_path_):
        self.file_path = file_path_

        self.meta_data_info = {}
        self.meta_data_info['str'] = {}          
        self.meta_data_info['int'] = {}
        self.meta_data_info['list_of_tuples_dd'] = {}
        self.meta_data_info['dict_of_string_keys_double_vals'] = {}
        self.meta_data_info['list_of_3ples_StrStrStr'] = {}                
        
        self.meta_data_info['bool'] = {
                                    'can_provide_reactive_power_after_battery_full' : None
        }
        
        self.meta_data_info['double'] = {
                                    'target_P3_reference__percent_of_maxP3' : (50, 100),
                                    'max_QkVAR_as_percent_of_SkVA' : (0, 100),
                                    'gamma' : (0.00001, 0.2)
        }
        
        self.meta_data_info['dict_of_string_keys_string_vals'] = {
                            'voltage_LPF' :  {'is_active':None, 'seed':None, 'window_size_LB':None, 'window_size_UB':None, 'window_type':None}
        }
        
        self.processor_obj = parameters_file_processor(self.meta_data_info)
    
    
    def __parameter_file_specific_checks(self, parameters_dict, valid_parameter_name_to_line_number_map):
        conversion_obj = data_conversion_and_validation()
        errors = []
        
        #=================================
        
        line_number = valid_parameter_name_to_line_number_map['voltage_LPF']
        tmp_dict = parameters_dict['voltage_LPF']
        tmp_errors = convert_and_validate__voltage_LPF(tmp_dict, line_number, self.processor_obj)
        parameters_dict['voltage_LPF'] = tmp_dict
        
        if len(tmp_errors) > 0:
            errors += tmp_errors
            
        #=================================
        
        return errors
    
    
    def load(self):
        (errors, parameters_dict, valid_parameter_name_to_line_number_map) = self.processor_obj.validate(self.file_path)
        
        if len(errors) > 0:
            print_errors_file(self.file_path, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #------------------------------------------
        #      Parameter File Specific Checks
        #------------------------------------------
        errors += self.__parameter_file_specific_checks(parameters_dict, valid_parameter_name_to_line_number_map)
            
        if len(errors) > 0:
            print_errors_file(self.file_path, errors)
            return (False, None)  #(is_successful, parameters_dict)
        
        #========================================
        
        return (True, parameters_dict)   #(is_successful, parameters_dict)


#===============================
#       Helper Functions
#===============================

def convert_and_validate__voltage_LPF(voltage_LPF_dict, line_number, processor_obj):
    errors = []
    conversion_obj = data_conversion_and_validation()
    
    #-------------------
    
    # 'seed' has already been converted and validated in the processor_obj
    
    #-------------------
    
    value = voltage_LPF_dict['is_active']
    (tmp_errors, value) = conversion_obj.cast_bool_value(value, line_number)
    
    if len(tmp_errors) > 0:
        errors += tmp_errors
    else:
        voltage_LPF_dict['is_active'] = value
    
    #-------------------
    
    value = voltage_LPF_dict['window_type']
    (conversion_successfull, window_type_enum) = get_LPF_window_enum(value)
    
    if conversion_successfull:
        voltage_LPF_dict['window_type'] = window_type_enum
    else:
        errors.append('{}, Invalid window_type.'.format(line_number))
    
    #-------------------
    
    value = voltage_LPF_dict['window_size_LB']
    range_vals = (1, 10000)
    (tmp_errors, value) = processor_obj.cast_to_int_and_check_bounds(value, line_number, range_vals)
    
    if len(tmp_errors) > 0:
        errors += tmp_errors
    else:
        voltage_LPF_dict['window_size_LB'] = int(value)
    
    #-------------------
    
    value = voltage_LPF_dict['window_size_UB']
    range_vals = (1, 10000)
    (tmp_errors, value) = processor_obj.cast_to_int_and_check_bounds(value, line_number, range_vals)
    
    if len(tmp_errors) > 0:
        errors += tmp_errors
    else:
        voltage_LPF_dict['window_size_UB'] = int(value)
    
    #-------------------
    
    if len(errors) == 0:
        if voltage_LPF_dict['window_size_UB'] < voltage_LPF_dict['window_size_LB']:
            errors.append('{}, window_size_UB can not be less than window_size_LB.'.format(line_number))

        if voltage_LPF_dict['window_type'] != LPF_window_enum.Rectangular:
            if voltage_LPF_dict['window_size_LB'] == 1:
                errors.append('{}, If the window_type is Hanning or Blackman; the window_size must be greater than 1.'.format(line_number))

    return errors


#===========================================================================================================
#===========================================================================================================
#===========================================================================================================
#===========================================================================================================


#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#     Do we need to add SE_CE_data_obj.Ext_strategies = set()
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

if __name__ == '__main__':
    start_simulation_unix_time = 10
    load_obj = load_input_files(start_simulation_unix_time)
    
    base_dir = os.getcwd()
    
    (is_successful, SE_CE_data_obj, baseLD_data_obj, global_parameters, L2_control_strategy_parameters_dict) = load_obj.load(base_dir)
    
    #==========================================
    
    if not is_successful:
        print('Houston we have a problem!')
    else:
        print('Global Parameters')
        for (key, value) in global_parameters.items():
            print('{}           {}'.format(key, value))
        
        print('\n')
        
        for (enum_val, params_dict) in L2_control_strategy_parameters_dict.items():
            print(enum_val)
            for (key, value) in params_dict.items():
                print('{}           {}'.format(key, value))
            
            print('\n')
            
        print('\n')
        
        if True:
            SE_group_charge_events = SE_CE_data_obj.SE_group_charge_events
            
            print('SE_id, ES_strategy, VS_strategy, Ext_Strategy')
            for X in SE_group_charge_events:
                for charge_event in X.charge_events:
                    print("{}, {}, {}, {}".format(charge_event.SE_id, charge_event.control_enums.ES_control_strategy, charge_event.control_enums.VS_control_strategy, charge_event.control_enums.ext_control_strategy))
    
            for Y in SE_CE_data_obj.SE_group_configuration_list:
                print('\n')
                print('SE_group: {}'.format(Y.SE_group_id))
                print('SE_id, SE_group, SE_type, lat, long, grid_node, location_type')
                for X in Y.SEs:
                    print('{}, {}, {}, {}, {}, {}, {}'.format(X.SE_id, X.SE_group_id, X.supply_equipment_type, X.lattitude, X.longitude, X.grid_node_id, X.location_type))
            
            print('\n')
            print('SE_id, SE_type')
            for (SE_id, SE_type) in SE_CE_data_obj.SEid_to_SE_type.items():
                print('{}, {}'.format(SE_id, SE_type))
                
            print('\n')
            print('ES_strategies')
            print(SE_CE_data_obj.ES_strategies)
            
            print('\n')
            print('VS_strategies')
            print(SE_CE_data_obj.VS_strategies)
            
            print('\n')
            print('all_caldera_node_names')
            print(SE_CE_data_obj.caldera_powerflow_nodes.all_caldera_node_names)
            
            print('\n')
            print('HPSE_caldera_node_names')
            print(SE_CE_data_obj.caldera_powerflow_nodes.HPSE_caldera_node_names)
            
    print('Finished')
    

