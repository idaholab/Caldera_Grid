
from load_input_files import load_input_files
from global_aux import input_datasets, charge_event_builder


class load_inputs_aux:

    def __init__(self, io_dir, start_simulation_unix_time):
        self.io_dir = io_dir
        self.start_simulation_unix_time = start_simulation_unix_time
        
        self.SE_CE_data_obj = None
        self.baseLD_data_obj = None
        self.global_parameters = None
        self.control_strategy_parameters_dict = None
        
        
    def load(self):
        inputs_dir = self.io_dir.inputs_dir
    
        load_obj = load_input_files(self.start_simulation_unix_time)
        self.L2_control_strategies_to_include = load_obj.get_L2_control_strategies_to_include()
    
        (is_successful, self.SE_CE_data_obj, self.baseLD_data_obj, self.global_parameters, self.control_strategy_parameters_dict) = load_obj.load(inputs_dir)
        
        if is_successful:
            SEid_to_SE_type = self.SE_CE_data_obj.SEid_to_SE_type
            SEid_to_SE_group = self.SE_CE_data_obj.SEid_to_SE_group
            self.charge_event_builder_obj = charge_event_builder(SEid_to_SE_type, SEid_to_SE_group, self.L2_control_strategies_to_include, self.control_strategy_parameters_dict)
        else:
            self.charge_event_builder_obj = None
            
        #-------------------------
    
        # Load custom inputs here
        # ...
        # ...
            
        return is_successful # If errors detected in input datasets return False otherwise return True
    
    
    def get_input_dataset(self, input_dataset_enum_list):
        return_val = {}
        
        for dataset_enum in input_dataset_enum_list:
            if dataset_enum == input_datasets.SE_CE_data_obj:
                return_val[dataset_enum] = self.SE_CE_data_obj
                
            elif dataset_enum == input_datasets.SE_group_configuration:
                return_val[dataset_enum] = self.SE_CE_data_obj.SE_group_configuration_list
                
            elif dataset_enum == input_datasets.SE_group_charge_event_data:
                return_val[dataset_enum] = self.SE_CE_data_obj.SE_group_charge_events
                
            elif dataset_enum == input_datasets.SEid_to_SE_type:
                return_val[dataset_enum] = self.SE_CE_data_obj.SEid_to_SE_type
              
            elif dataset_enum == input_datasets.SEid_to_SE_group:
                return_val[dataset_enum] = self.SE_CE_data_obj.SEid_to_SE_group
            
            elif dataset_enum == input_datasets.charge_event_builder:
                return_val[dataset_enum] = self.charge_event_builder_obj
            
            elif dataset_enum == input_datasets.Caldera_L2_ES_strategies:
                return_val[dataset_enum] = self.SE_CE_data_obj.ES_strategies
                
            elif dataset_enum == input_datasets.Caldera_L2_VS_strategies:
                return_val[dataset_enum] = self.SE_CE_data_obj.VS_strategies
                
            elif dataset_enum == input_datasets.external_strategies:
                return_val[dataset_enum] = self.SE_CE_data_obj.ext_strategies
            
            elif dataset_enum == input_datasets.all_caldera_node_names:
                return_val[dataset_enum] = self.SE_CE_data_obj.caldera_powerflow_nodes.all_caldera_node_names
                
            elif dataset_enum == input_datasets.HPSE_caldera_node_names:
                return_val[dataset_enum] = self.SE_CE_data_obj.caldera_powerflow_nodes.HPSE_caldera_node_names
                
            elif dataset_enum == input_datasets.baseLD_data_obj:
                return_val[dataset_enum] = self.baseLD_data_obj
                
            elif dataset_enum == input_datasets.Caldera_global_parameters:
                return_val[dataset_enum] = self.global_parameters
                
            elif dataset_enum == input_datasets.Caldera_control_strategy_parameters_dict:
                return_val[dataset_enum] = self.control_strategy_parameters_dict
            
            # Return custom inputs here
            # ...
            # ...
            
            else:
                raise ValueError('Invalid dataset_enum in load_inputs_aux:get_input_dataset.')
        
        return return_val
        