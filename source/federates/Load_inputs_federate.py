import helics as h
from Load_inputs_aux import load_inputs_aux
from Helics_Helper import send, receive, cleanup

def load_inputs_federate(io_dir, json_config_file_name, simulation_time_constraints):

    #=====================================
    #         Setup Helics
    #=====================================
    config_file_path = io_dir.base_dir + "/source/helics_config/" + json_config_file_name
    fed = h.helicsCreateCombinationFederateFromConfig(config_file_path)
    
    pub_data_loaded = h.helicsFederateGetPublication(fed, 'data_loaded')
	
    input_datasets_endpoint = h.helicsFederateGetEndpoint(fed, "input_datasets_endpoint")
    
    #-------------------------------------
    
    start_simulation_unix_time = simulation_time_constraints.start_simulation_unix_time
    end_simulation_unix_time = simulation_time_constraints.end_simulation_unix_time
    grid_timestep_sec = simulation_time_constraints.grid_timestep_sec
    grid_deltatime_sec = grid_timestep_sec/4

    h.helicsFederateSetTimeProperty(fed, h.helics_property_time_delta, grid_deltatime_sec)
    h.helicsFederateSetTimeProperty(fed, h.helics_property_time_offset, 0)

    time_period = h.helicsFederateGetTimeProperty(fed, h.helics_property_time_period)
    time_delta = h.helicsFederateGetTimeProperty(fed, h.helics_property_time_delta)
    time_offset = h.helicsFederateGetTimeProperty(fed, h.helics_property_time_offset)

    #============================================
    # Forward time to start_simulation_unix_time
    #============================================
    h.helicsFederateEnterExecutingMode(fed)

    federate_time = -1
    start_time = start_simulation_unix_time - 4*grid_deltatime_sec
    while abs(federate_time - start_time) > 0.0001:
        federate_time = h.helicsFederateRequestTime(fed, start_time)
	
    #=====================================
    #       Load Input Files
    #=====================================    
    
    load_obj = load_inputs_aux(io_dir, federate_time)
    is_successful = load_obj.load()    
    
    h.helicsPublicationPublishBoolean(pub_data_loaded, is_successful)
    
    if not is_successful:
        cleanup(fed)    
        return
    
    #=====================================
    #      Respond to Data Requests
    #=====================================
    
    federate_name = h.helicsFederateGetName(fed)
    print('{} Federate Started.'.format(federate_name))
    while True:	
        federate_time = h.helicsFederateRequestTime(fed, end_simulation_unix_time+time_delta)
        
        input_dataset_dict = receive(input_datasets_endpoint)
        
        for source, input_dataset_enum_list in input_dataset_dict.items():
        
            dataset = load_obj.get_input_dataset(input_dataset_enum_list)
            send(dataset, input_datasets_endpoint, source)

        if federate_time >= end_simulation_unix_time:
            break
    
    #=====================================
    #         Terminate Federate
    #=====================================
    cleanup(fed)
    print('{} Federate Terminated.'.format(federate_name))
  