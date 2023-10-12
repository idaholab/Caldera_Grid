
from numpy.random import Generator, PCG64

from Caldera_globals import L2_control_strategies_enum, L2_control_strategy_parameters
from Caldera_globals import ES100_L2_parameters, ES110_L2_parameters, ES200_L2_parameters 
from Caldera_globals import ES300_L2_parameters, normal_random_error, ES500_L2_parameters
from Caldera_globals import VS100_L2_parameters, VS200_L2_parameters, VS300_L2_parameters
from Caldera_globals import stop_charging_decision_metric
from Caldera_models import EVSE_level


class container_class:
    pass


def build_L2_control_strategy_parameters(L2_control_strategy_parameters_dict):
    CSP_dict = L2_control_strategy_parameters_dict
    return_val = L2_control_strategy_parameters()
    
    #===========================================
    
    enum_val = L2_control_strategies_enum.ES100_A
    X = ES100_L2_parameters()
    
    if enum_val in CSP_dict:
        X.beginning_of_TofU_rate_period__time_from_midnight_hrs = CSP_dict[enum_val]['beginning_of_TofU_rate_period__time_from_midnight_hrs']
        X.end_of_TofU_rate_period__time_from_midnight_hrs = CSP_dict[enum_val]['end_of_TofU_rate_period__time_from_midnight_hrs']
        X.randomization_method = CSP_dict[enum_val]['randomization_method']
        X.M1_delay_period_hrs = CSP_dict[enum_val]['M1_delay_period_hrs']
        X.random_seed = CSP_dict[enum_val]['random_seed']
        
    return_val.ES100_A = X
    
    #------------------------------
    
    enum_val = L2_control_strategies_enum.ES100_B
    X = ES100_L2_parameters()
    
    if enum_val in CSP_dict:
        X.beginning_of_TofU_rate_period__time_from_midnight_hrs = CSP_dict[enum_val]['beginning_of_TofU_rate_period__time_from_midnight_hrs']
        X.end_of_TofU_rate_period__time_from_midnight_hrs = CSP_dict[enum_val]['end_of_TofU_rate_period__time_from_midnight_hrs']
        X.randomization_method = CSP_dict[enum_val]['randomization_method']
        X.M1_delay_period_hrs = CSP_dict[enum_val]['M1_delay_period_hrs']
        X.random_seed = CSP_dict[enum_val]['random_seed']
    
    return_val.ES100_B = X
    
    #------------------------------
    
    enum_val = L2_control_strategies_enum.ES110
    X = ES110_L2_parameters()
    
    if enum_val in CSP_dict:
        X.random_seed = CSP_dict[enum_val]['random_seed']
        
    return_val.ES110 = X
    
    #------------------------------
    
    enum_val = L2_control_strategies_enum.ES200
    X = ES200_L2_parameters()
    
    if enum_val in CSP_dict:
        X.weight_factor_to_calculate_valley_fill_target = CSP_dict[enum_val]['weight_factor_to_calculate_valley_fill_target']
        
    return_val.ES200 = X
    
    #------------------------------
    
    enum_val = L2_control_strategies_enum.ES300
    X = ES300_L2_parameters()
    
    if enum_val in CSP_dict:
        X.weight_factor_to_calculate_valley_fill_target = CSP_dict[enum_val]['weight_factor_to_calculate_valley_fill_target']
        
    return_val.ES300 = X
    
    #------------------------------
    
    enum_val = L2_control_strategies_enum.ES500
    X = ES500_L2_parameters()
    
    if enum_val in CSP_dict:
        X.aggregator_timestep_mins = CSP_dict[enum_val]['aggregator_timestep_mins']
        
        Y = normal_random_error()
        Y.seed = CSP_dict[enum_val]['randomize_pev_lead_time_off_to_on_lead_time_sec']['seed']
        Y.stdev = CSP_dict[enum_val]['randomize_pev_lead_time_off_to_on_lead_time_sec']['stdev']
        Y.stdev_bounds = CSP_dict[enum_val]['randomize_pev_lead_time_off_to_on_lead_time_sec']['stdev_bounds']
        X.off_to_on_lead_time_sec = Y
        
        Y = normal_random_error()
        Y.seed = CSP_dict[enum_val]['randomize_pev_lead_time_default_lead_time_sec']['seed']
        Y.stdev = CSP_dict[enum_val]['randomize_pev_lead_time_default_lead_time_sec']['stdev']
        Y.stdev_bounds = CSP_dict[enum_val]['randomize_pev_lead_time_default_lead_time_sec']['stdev_bounds']
        X.default_lead_time_sec = Y
        
    return_val.ES500 = X
    
    #------------------------------
    
    enum_val = L2_control_strategies_enum.VS100
    X = VS100_L2_parameters()
    
    if enum_val in CSP_dict:
        X.target_P3_reference__percent_of_maxP3 = CSP_dict[enum_val]['target_P3_reference__percent_of_maxP3']
        X.max_delta_kW_per_min = CSP_dict[enum_val]['max_delta_kW_per_min']
        
        #----------
        
        volt_delta_kW_curve_puV = []
        volt_delta_kW_percP = []
        for (puV, percQ) in CSP_dict[enum_val]['volt_delta_kW_curve']:
            volt_delta_kW_curve_puV.append(puV)
            volt_delta_kW_percP.append(percQ)
        
        X.volt_delta_kW_curve_puV = volt_delta_kW_curve_puV
        X.volt_delta_kW_percP = volt_delta_kW_percP
        
        #----------
        
        X.voltage_LPF.is_active = CSP_dict[enum_val]['voltage_LPF']['is_active']
        X.voltage_LPF.seed = CSP_dict[enum_val]['voltage_LPF']['seed']
        X.voltage_LPF.window_size_LB = CSP_dict[enum_val]['voltage_LPF']['window_size_LB']
        X.voltage_LPF.window_size_UB = CSP_dict[enum_val]['voltage_LPF']['window_size_UB']
        X.voltage_LPF.window_type = CSP_dict[enum_val]['voltage_LPF']['window_type']
        
        #----------
    
    return_val.VS100 = X
    
    #------------------------------
    
    enum_val = L2_control_strategies_enum.VS200_A
    X = VS200_L2_parameters()
    
    if enum_val in CSP_dict:
        X.target_P3_reference__percent_of_maxP3 = CSP_dict[enum_val]['target_P3_reference__percent_of_maxP3']
        X.max_delta_kVAR_per_min = CSP_dict[enum_val]['max_delta_kVAR_per_min']
        
        #----------
        
        volt_var_curve_puV = []
        volt_var_curve_percQ = []
        for (puV, percQ) in CSP_dict[enum_val]['volt_var_curve']:
            volt_var_curve_puV.append(puV)
            volt_var_curve_percQ.append(percQ)
        
        X.volt_var_curve_puV = volt_var_curve_puV
        X.volt_var_curve_percQ = volt_var_curve_percQ
        
        #----------
        
        X.voltage_LPF.is_active = CSP_dict[enum_val]['voltage_LPF']['is_active']
        X.voltage_LPF.seed = CSP_dict[enum_val]['voltage_LPF']['seed']
        X.voltage_LPF.window_size_LB = CSP_dict[enum_val]['voltage_LPF']['window_size_LB']
        X.voltage_LPF.window_size_UB = CSP_dict[enum_val]['voltage_LPF']['window_size_UB']
        X.voltage_LPF.window_type = CSP_dict[enum_val]['voltage_LPF']['window_type']
        
        #----------
        
    return_val.VS200_A = X
    
    #------------------------------
    
    enum_val = L2_control_strategies_enum.VS200_B
    X = VS200_L2_parameters()
    
    if enum_val in CSP_dict:
        X.target_P3_reference__percent_of_maxP3 = CSP_dict[enum_val]['target_P3_reference__percent_of_maxP3']
        X.max_delta_kVAR_per_min = CSP_dict[enum_val]['max_delta_kVAR_per_min']
        
        #----------
        
        volt_var_curve_puV = []
        volt_var_curve_percQ = []
        for (puV, percQ) in CSP_dict[enum_val]['volt_var_curve']:
            volt_var_curve_puV.append(puV)
            volt_var_curve_percQ.append(percQ)
        
        X.volt_var_curve_puV = volt_var_curve_puV
        X.volt_var_curve_percQ = volt_var_curve_percQ
        
        #----------
        
        X.voltage_LPF.is_active = CSP_dict[enum_val]['voltage_LPF']['is_active']
        X.voltage_LPF.seed = CSP_dict[enum_val]['voltage_LPF']['seed']
        X.voltage_LPF.window_size_LB = CSP_dict[enum_val]['voltage_LPF']['window_size_LB']
        X.voltage_LPF.window_size_UB = CSP_dict[enum_val]['voltage_LPF']['window_size_UB']
        X.voltage_LPF.window_type = CSP_dict[enum_val]['voltage_LPF']['window_type']
        
        #----------
        
    return_val.VS200_B = X
    
    #------------------------------
    
    enum_val = L2_control_strategies_enum.VS200_C
    X = VS200_L2_parameters()
    
    if enum_val in CSP_dict:
        X.target_P3_reference__percent_of_maxP3 = CSP_dict[enum_val]['target_P3_reference__percent_of_maxP3']
        X.max_delta_kVAR_per_min = CSP_dict[enum_val]['max_delta_kVAR_per_min']
        
        #----------
        
        volt_var_curve_puV = []
        volt_var_curve_percQ = []
        for (puV, percQ) in CSP_dict[enum_val]['volt_var_curve']:
            volt_var_curve_puV.append(puV)
            volt_var_curve_percQ.append(percQ)
        
        X.volt_var_curve_puV = volt_var_curve_puV
        X.volt_var_curve_percQ = volt_var_curve_percQ
        
        #----------
        
        X.voltage_LPF.is_active = CSP_dict[enum_val]['voltage_LPF']['is_active']
        X.voltage_LPF.seed = CSP_dict[enum_val]['voltage_LPF']['seed']
        X.voltage_LPF.window_size_LB = CSP_dict[enum_val]['voltage_LPF']['window_size_LB']
        X.voltage_LPF.window_size_UB = CSP_dict[enum_val]['voltage_LPF']['window_size_UB']
        X.voltage_LPF.window_type = CSP_dict[enum_val]['voltage_LPF']['window_type']
        
        #----------
        
    return_val.VS200_C = X
    
    #------------------------------
    
    enum_val = L2_control_strategies_enum.VS300
    X = VS300_L2_parameters()
    
    if enum_val in CSP_dict:
        X.target_P3_reference__percent_of_maxP3 = CSP_dict[enum_val]['target_P3_reference__percent_of_maxP3']
        X.max_QkVAR_as_percent_of_SkVA = CSP_dict[enum_val]['max_QkVAR_as_percent_of_SkVA']
        X.gamma = CSP_dict[enum_val]['gamma']
        
        #----------
        
        X.voltage_LPF.is_active = CSP_dict[enum_val]['voltage_LPF']['is_active']
        X.voltage_LPF.seed = CSP_dict[enum_val]['voltage_LPF']['seed']
        X.voltage_LPF.window_size_LB = CSP_dict[enum_val]['voltage_LPF']['window_size_LB']
        X.voltage_LPF.window_size_UB = CSP_dict[enum_val]['voltage_LPF']['window_size_UB']
        X.voltage_LPF.window_type = CSP_dict[enum_val]['voltage_LPF']['window_type']
        
        #----------
    
    return_val.VS300 = X
    
    #------------------------------
    
    return return_val


def assign_control_strategies_to_CE(EVSE_inventory, control_strategies, charge_event, SEid_to_SE_type, L2_control_strategy_parameters_dict):
    
    if EVSE_inventory[SEid_to_SE_type[charge_event.SE_id]].get_level() == EVSE_level.L2: #supply_equipment_is_L2(SEid_to_SE_type[charge_event.SE_id]):
        ES_enum = control_strategies.ES_control_strategy
        VS_enum = control_strategies.VS_control_strategy
        NA_enum = L2_control_strategies_enum.NA
        
        if VS_enum != NA_enum and control_strategies.inverter_model_supports_Qsetpoint:
            if L2_control_strategy_parameters_dict[VS_enum]['can_provide_reactive_power_after_battery_full']:
                charge_event.stop_charge.decision_metric = stop_charging_decision_metric.stop_charging_using_depart_time
        
        #----------------
        
        if ES_enum == L2_control_strategies_enum.ES500:
            aggregator_timestep_mins = L2_control_strategy_parameters_dict[ES_enum]['aggregator_timestep_mins']
            park_duration_min = (charge_event.departure_unix_time - charge_event.arrival_unix_time)/60
            
            if park_duration_min < 2*aggregator_timestep_mins:
                control_strategies.ES_control_strategy = NA_enum

    # We should use the default here (whatever happens first)
    #elif is_XFC_charge(charge_event.vehicle_type, SEid_to_SE_type[charge_event.SE_id]):
    #    charge_event.stop_charge.decision_metric = stop_charging_decision_metric.stop_charging_using_target_soc

    charge_event.control_enums = control_strategies


class select_control_strategy:

    def __init__(self, seed, control_strategy_list_):
        self.control_strategy_list = control_strategy_list_
        
        self.cum_vals = []
        cum_perc = 0
        for (ES_enum, VS_enum, perc_val) in self.control_strategy_list:
            cum_perc += perc_val
            self.cum_vals.append(cum_perc)
        
        #----------------------
        
        if seed < 0:
            self.rand_gen = Generator(PCG64())           
        else:
            self.rand_gen = Generator(PCG64(seed))
        
        self.__generate_random_values()
    
    
    def __generate_random_values(self):
        num_random_values = 500
        self.index = 0
        self.random_values = self.rand_gen.uniform(0, 100, num_random_values)
        
        
    def get_next_control_strategy(self):
        self.index += 1
        if self.index >= len(self.random_values):
            self.__generate_random_values()
        
        #----------------------
        
        rand_val = self.random_values[self.index]
        
        i = 0
        for x in self.cum_vals:
            if rand_val < x:
                break
            else:
                i += 1
        
        if i >= len(self.cum_vals):
            return_val = None
        else:
            (ES_enum, VS_enum, perc_val) = self.control_strategy_list[i]
            return_val = (ES_enum, VS_enum)
        
        return return_val


class parameters_file_processor:
    
    def __init__(self, meta_data_info_):
        self.meta_data_info = meta_data_info_
        self.conversion_obj = data_conversion_and_validation()
    
    
    def __validate_key_and_convert_value(self, line, line_number):
        errors = []
        
        fields = line.split(',')                
        if len(fields) not in (2, 3):
            errors.append("{}, Invalid number of fields.".format(line_number))
            return (errors, None, None)
        
        #--------------------------
        
        key = fields[0].strip()
        csv_value = fields[1].strip()
        
        if key in(self.meta_data_info['str']):
            if csv_value == '':
                errors.append("{}, Invalid Value.".format(line_number))
            
            value = csv_value
                
        elif key in(self.meta_data_info['int']): 
            (tmp_errors, value) = self.conversion_obj.cast_integer_value(csv_value, line_number)
            errors += tmp_errors
 
            if len(tmp_errors) == 0:
                range_vals = self.meta_data_info['int'][key]
                (tmp_errors, value) = self.conversion_obj.range_check(value, line_number, range_vals)
                errors += tmp_errors

        elif key in(self.meta_data_info['double']):
            (tmp_errors, value) = self.conversion_obj.cast_double_value(csv_value, line_number)
            errors += tmp_errors
            
            if len(tmp_errors) == 0:
                range_vals = self.meta_data_info['double'][key]
                (tmp_errors, value) = self.conversion_obj.range_check(value, line_number, range_vals)
                errors += tmp_errors
        
        elif key in(self.meta_data_info['bool']):
            (tmp_errors, value) = self.conversion_obj.cast_bool_value(csv_value, line_number)
            errors += tmp_errors

        elif key in(self.meta_data_info['list_of_tuples_dd']):
            value = []
            str_list = csv_value.split(';')

            if len(str_list) == 0:
                errors.append("{}, Invalid Value.".format(line_number))
            else:
                for str in str_list:
                    tuple_vals = str.split('|')     
                    
                    if len(tuple_vals) != 2:
                        errors.append("{}, Invalid Value.".format(line_number))
                    else:
                        (tmp_errors_0, value_0) = self.conversion_obj.cast_double_value(tuple_vals[0], line_number)
                        (tmp_errors_1, value_1) = self.conversion_obj.cast_double_value(tuple_vals[1], line_number)
                        errors += tmp_errors_0
                        errors += tmp_errors_1
                        
                        if len(tmp_errors_0) != 0 or len(tmp_errors_1) != 0:
                            break
                        
                        range_vals_0 = self.meta_data_info['list_of_tuples_dd'][key][0]                        
                        (tmp_errors_0, value_0) = self.conversion_obj.range_check(value_0, line_number, range_vals_0)
                        errors += tmp_errors_0
                        
                        range_vals_1 = self.meta_data_info['list_of_tuples_dd'][key][1]                        
                        (tmp_errors_1, value_1) = self.conversion_obj.range_check(value_1, line_number, range_vals_1)
                        errors += tmp_errors_1
                        
                        if len(tmp_errors_0) == 0 and len(tmp_errors_1) == 0:
                            value.append((value_0, value_1))

        elif key in(self.meta_data_info['dict_of_string_keys_double_vals']):
            value = {}
            str_list = csv_value.split(';')

            if len(str_list) == 0:
                errors.append("{}, Invalid Value.".format(line_number))
            else:
                for str in str_list:
                    key_val_pair = str.split('|')     
                    
                    if len(key_val_pair) != 2:
                        errors.append("{}, Invalid Value.".format(line_number))
                    else:
                        tmp_key = key_val_pair[0].strip()
                        (tmp_errors, tmp_val) = self.conversion_obj.cast_double_value(key_val_pair[1], line_number)
                        errors += tmp_errors
                        
                        if len(tmp_errors) == 0:
                            range_dictionary = self.meta_data_info['dict_of_string_keys_double_vals'][key]
                            
                            if tmp_key not in range_dictionary:
                                errors.append("{}, Invalid Value.".format(line_number))
                            else:
                                range_vals = range_dictionary[tmp_key]
                                (tmp_errors, tmp_val) = self.conversion_obj.range_check(tmp_val, line_number, range_vals)
                                errors += tmp_errors
                        
                                if len(tmp_errors) == 0:
                                    if tmp_key in value:
                                        errors.append("{}, Invalid Value.".format(line_number))
                                        break
                                    else:
                                        value[tmp_key] = tmp_val
                                    
        elif key in(self.meta_data_info['dict_of_string_keys_string_vals']):
            value = {}
            str_list = csv_value.split(';')

            if len(str_list) == 0:
                errors.append("{}, Invalid Value.".format(line_number))
            else:
                for str in str_list:
                    key_val_pair = str.split('|')     
                    
                    if len(key_val_pair) != 2:
                        errors.append("{}, Invalid Value.".format(line_number))
                    else:
                        range_dictionary = self.meta_data_info['dict_of_string_keys_string_vals'][key]
                    
                        tmp_key = key_val_pair[0].strip()
                        tmp_val = key_val_pair[1].strip()
                        
                        if tmp_key not in range_dictionary:
                            errors.append("{}, Invalid Value.".format(line_number))
                        else:
                            if tmp_key == '' or tmp_val == '':
                                errors.append("{}, Invalid Value.".format(line_number))
                            else:
                                if tmp_key in value:
                                    errors.append("{}, Invalid Value.".format(line_number))
                                    break
                                else:
                                    value[tmp_key] = tmp_val
        
        elif key in(self.meta_data_info['list_of_3ples_StrStrStr']):
            value = []
            str_list = csv_value.split(';')

            if len(str_list) == 0:
                errors.append("{}, Invalid Value.".format(line_number))
            else:
                for str in str_list:
                    tuple_vals = str.split('|')     
                    
                    if len(tuple_vals) != 3:
                        errors.append("{}, Invalid Value.".format(line_number))
                    else:
                        val_1 = tuple_vals[0].strip()
                        val_2 = tuple_vals[1].strip()
                        val_3 = tuple_vals[2].strip()
                        
                        if val_1 == '' or val_2 == '' or val_3 == '':
                            errors.append("{}, Invalid Value.".format(line_number))
                        else:
                            value.append((val_1, val_2, val_3))

        else:
            errors.append("{}, Invalid Key.".format(line_number))

        #---------------------------

        if len(errors) != 0:
            value = None
            key = None

        return (errors, key, value)
        
        
    def __check_all_parameters_in_file(self, parameters_dict):        
        valid_parameter_names = []            
        for (type, tmp_dict) in self.meta_data_info.items():
            for parameter_name in tmp_dict:
                valid_parameter_names.append(parameter_name)
        
        errors = []
        missing_parameters = set(valid_parameter_names) - set(parameters_dict.keys())
        
        if len(missing_parameters) != 0:
            msg = ""
            for x in missing_parameters:
                msg += x + ';  '
            
            errors.append('NA, Missing Keys: ({})'.format(msg))
        
        return errors
        
        
    def __check_dictionary_keys(self, parameters_dict, valid_parameter_name_to_line_number_map):
        errors = []
        
        for (parameter_name, meta_data_dict) in self.meta_data_info['dict_of_string_keys_double_vals'].items():
            symetric_difference = set(meta_data_dict.keys()) ^ set(parameters_dict[parameter_name].keys())
            if len(symetric_difference) != 0:
                line_number = valid_parameter_name_to_line_number_map[parameter_name]
                errors.append('{}, Invalid Value.'.format(line_number)) 
        
        for (parameter_name, meta_data_dict) in self.meta_data_info['dict_of_string_keys_string_vals'].items():
            symetric_difference = set(meta_data_dict.keys()) ^ set(parameters_dict[parameter_name].keys())
            if len(symetric_difference) != 0:
                line_number = valid_parameter_name_to_line_number_map[parameter_name]
                errors.append('{}, Invalid Value.'.format(line_number))
            
        return errors
    
    
    def __convert_seed_values_in_dictionaries_from_doubles_to_ints(self, parameters_dict, valid_parameter_name_to_line_number_map):
        errors = []
        
        for (parameter_name, meta_data_dict) in self.meta_data_info['dict_of_string_keys_double_vals'].items():
            if 'seed' in parameters_dict[parameter_name].keys():
                line_number = valid_parameter_name_to_line_number_map[parameter_name]
            
                value = parameters_dict[parameter_name]['seed']
                (tmp_errors, value) = self.conversion_obj.cast_integer_value(value, line_number)
                
                if len(tmp_errors) > 0:
                    errors += tmp_errors
                else:
                    parameters_dict[parameter_name]['seed'] = int(value)
        
        for (parameter_name, meta_data_dict) in self.meta_data_info['dict_of_string_keys_string_vals'].items():
            if 'seed' in parameters_dict[parameter_name].keys():
                line_number = valid_parameter_name_to_line_number_map[parameter_name]
            
                value = parameters_dict[parameter_name]['seed']
                (tmp_errors, value) = self.conversion_obj.cast_integer_value(value, line_number)
                
                if len(tmp_errors) > 0:
                    errors += tmp_errors
                else:
                    parameters_dict[parameter_name]['seed'] = int(value)
        
        return errors
    
    
    def validate(self, config_file_path):
        parameters_dict = {}
        valid_parameter_name_to_line_number_map = {}
        errors = []
        line_number = 1
        
        config_file_handle = open(config_file_path, 'r')

        for line in config_file_handle:
            if line_number == 1:
                line_number += 1
                continue
       
            (tmp_errors, key, value) = self.__validate_key_and_convert_value(line, line_number)
            errors += tmp_errors
            
            if len(tmp_errors) == 0:
                if key in parameters_dict:
                    errors.append('{}, Duplicate Keys.'.format(line_number))
                else:
                    parameters_dict[key] = value
                    valid_parameter_name_to_line_number_map[key] = line_number
            
            line_number += 1 

        if line_number <= 2:
            errors.append('NA, Empty file')
        
        if len(errors) == 0:
            tmp_errors = self.__check_all_parameters_in_file(parameters_dict)
            errors += tmp_errors
        
        if len(errors) == 0:
            tmp_errors = self.__check_dictionary_keys(parameters_dict, valid_parameter_name_to_line_number_map)
            errors += tmp_errors
            
        if len(errors) == 0:
            tmp_errors = self.__convert_seed_values_in_dictionaries_from_doubles_to_ints(parameters_dict, valid_parameter_name_to_line_number_map)
            errors += tmp_errors
        
        #------------------
        
        if len(errors) != 0:
            parameters_dict = None
            valid_parameter_name_to_line_number_map = None

        return (errors, parameters_dict, valid_parameter_name_to_line_number_map)
    
    
    def cast_to_int_and_check_bounds(self, value, line_number, range_vals):
        errors = []
        
        (tmp_errors, value) = self.conversion_obj.cast_integer_value(value, line_number)
                
        if len(tmp_errors) > 0:
            errors += tmp_errors
        else:
            (tmp_errors, value) = self.conversion_obj.range_check(value, line_number, range_vals)
        
            if len(tmp_errors) > 0:
                errors += tmp_errors
            else:
                value = int(value)
        
        if len(errors) > 0:
            value = None
        
        return (errors, value)
        
        
    def cast_to_double_and_check_bounds(self, value, line_number, range_vals):
        errors = []
        
        (tmp_errors, value) = self.conversion_obj.cast_double_value(value, line_number)
                
        if len(tmp_errors) > 0:
            errors += tmp_errors
        else:
            (tmp_errors, value) = self.conversion_obj.range_check(value, line_number, range_vals)
        
            if len(tmp_errors) > 0:
                errors += tmp_errors
        
        if len(errors) > 0:
            value = None
            
        return (errors, value)
    
    
class data_conversion_and_validation:
    
    def range_check(self, value, line_number, range_vals):
        errors = []
        if range_vals != None:
            (min_value, max_value) = range_vals
            if value < min_value or max_value < value:
                errors.append('{}, Value outside the acceptable range.'.format(line_number))
                
        return (errors, value)


    def cast_integer_value(self, value, line_number):
        errors = []
        try:
            if (float(value) % 1) < 0.000000001:
                value = int(round(float(value)))
            else: 
                errors.append("{}, Invalid integer value".format(line_number))
        except (TypeError, ValueError):
            errors.append("{}, Invalid integer value".format(line_number))

        return (errors, value)
    
    
    def cast_double_value(self, value, line_number):
        errors = []
        try:
            value = float(value)
        except (TypeError, ValueError):
            errors.append('{}, Could not convert value to double'.format(line_number))
            
        return (errors, value)
        
        
    def cast_bool_value(self, value, line_number):
        errors = []
                   
        if value.lower().strip() == "true":
            value = True
        elif value.lower().strip() == 'false':
            value = False
        else:
            errors.append('{}, Could not convert value to bool'.format(line_number))
        
        return (errors, value)



