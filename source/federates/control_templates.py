from global_aux import container_class


class typeA_control:

    def __init__(self, base_dir, simulation_time_constraints):
        self.base_dir = base_dir
        self.end_simulation_unix_time = simulation_time_constraints.end_simulation_unix_time
        self.start_simulation_unix_time = simulation_time_constraints.start_simulation_unix_time
        self.grid_timestep_sec = simulation_time_constraints.grid_timestep_sec
    
    
    def _calculate_timing_parameters(self, control_time_parameters, control_strategy_name):
        X = control_time_parameters
        
        A1 = X.send_control_info_lead_time_min < X.request_state_lead_time_min
        A2 = X.request_state_lead_time_min < X.control_timestep_min
        if not A1 or not A2:
            raise ValueError('In control strategy {}, invalid control_time_parameters. The following inequality must hold: (send_control_info_lead_time_min < request_state_lead_time_min < control_timestep_min).'.format(control_strategy_name))
                
        if not self.grid_timestep_sec < 60*X.send_control_info_lead_time_min:
            raise ValueError('In control strategy {}, invalid send_control_info_lead_time_min. The following inequality must hold: (grid_timestep_sec < 60*X.send_control_info_lead_time_min).'.format(control_strategy_name))
        
        if not 2*self.grid_timestep_sec < 60*X.request_state_lead_time_min:
            raise ValueError('In control strategy {}, invalid request_state_lead_time_min. The following inequality must hold: (2*self.grid_timestep_sec < 60*X.request_state_lead_time_min).'.format(control_strategy_name))
        
        #==============================
        
        control_timestep_sec = 60*X.control_timestep_min
        
        Y = container_class()
        
        prev_control_timestep_start_unix_time = round(self.start_simulation_unix_time - (self.start_simulation_unix_time % control_timestep_sec))
        Y.next_control_timestep_start_unix_time = 2*control_timestep_sec + prev_control_timestep_start_unix_time
        Y.next_request_state_unix_time = Y.next_control_timestep_start_unix_time - 60*X.request_state_lead_time_min
        Y.next_send_control_info_unix_time = Y.next_control_timestep_start_unix_time - 60*X.send_control_info_lead_time_min
        Y.control_timestep_sec = control_timestep_sec
    
        self.initial_control_time_parameters = Y
    
    
    def get_initial_control_time_parameters(self):
        return self.initial_control_time_parameters

    def get_input_dataset_enum_list(self):
        raise NotImplementedError('A child class of typeA_control has not implemented: get_input_dataset_enum_list()')
    
    def load_input_datasets(self, datasets_dict):
        raise NotImplementedError('A child class of typeA_control has not implemented: load_datasets()')
        
    def terminate_this_federate(self):
        raise NotImplementedError('A child class of typeA_control has not implemented: terminate_this_federate()')

    def initialize(self):
        raise NotImplementedError('A child class of typeA_control has not implemented: initialize()')

    def log_data(self):
        pass
    
    def get_messages_to_request_state_info_from_Caldera(self, next_control_timestep_start_unix_time):
        raise NotImplementedError('A child class of typeA_control has not implemented: get_messages_to_request_state_info_from_Caldera()')
    
    def get_messages_to_request_state_info_from_OpenDSS(self, next_control_timestep_start_unix_time):
        raise NotImplementedError('A child class of typeA_control has not implemented: get_messages_to_request_state_info_from_OpenDSS()')
   
    def solve(self, next_control_timestep_start_unix_time, Caldera_state_info, DSS_state_info):
        raise NotImplementedError('A child class of typeA_control has not implemented: solve()')


class typeB_control:

    def __init__(self, base_dir, simulation_time_constraints):
        self.base_dir = base_dir
        self.end_simulation_unix_time = simulation_time_constraints.end_simulation_unix_time
        self.start_simulation_unix_time = simulation_time_constraints.start_simulation_unix_time
        self.grid_timestep_sec = simulation_time_constraints.grid_timestep_sec
    
    def get_input_dataset_enum_list(self):
        raise NotImplementedError('A child class of typeB_control has not implemented: get_input_dataset_enum_list()')
    
    def load_input_datasets(self, datasets_dict):
        raise NotImplementedError('A child class of typeB_control has not implemented: load_datasets()')
        
    def terminate_this_federate(self):
        raise NotImplementedError('A child class of typeB_control has not implemented: terminate_this_federate()')

    def initialize(self):
        raise NotImplementedError('A child class of typeB_control has not implemented: initialize()')

    def log_data(self):
        pass
    
    def get_messages_to_request_state_info_from_Caldera(self, current_simulation_unix_time):
        raise NotImplementedError('A child class of typeB_control has not implemented: get_messages_to_request_state_info_from_Caldera()')
    
    def get_messages_to_request_state_info_from_OpenDSS(self, current_simulation_unix_time):
        raise NotImplementedError('A child class of typeB_control has not implemented: get_messages_to_request_state_info_from_OpenDSS()')
   
    def solve(self, current_simulation_unix_time, Caldera_state_info, DSS_state_info):
        raise NotImplementedError('A child class of typeB_control has not implemented: solve()')