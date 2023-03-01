import helics as h
from ICM_aux import ICM_aux
from global_aux import input_datasets
from Helics_Helper import send, receive, cleanup

def caldera_ICM_federate(base_dir, json_config_file_name, simulation_time_constraints, customized_pev_ramping, create_charge_profile_library, ensure_pev_charge_needs_met_for_ext_control_strategy, CE_queuing_inputs):

    print_communication = False
    #=====================================
    #         Setup Helics
    #=====================================
    config_file_path = base_dir + "/source/helics_config/" + json_config_file_name
    fed = h.helicsCreateCombinationFederateFromConfig(config_file_path)
    
    sub_data_loaded = h.helicsFederateGetInputByTarget(fed, 'Load_Input_Files/data_loaded')
    sub_dss_simulation_loaded = h.helicsFederateGetInputByTarget(fed, 'OpenDSS/dss_simulation_loaded')

    input_datasets_endpoint_local = h.helicsFederateGetEndpoint(fed, "input_datasets_endpoint")
    input_datasets_endpoint_remote = h.helicsEndpointGetDefaultDestination(input_datasets_endpoint_local)
   
    openDSS_endpoint_local = h.helicsFederateGetEndpoint(fed, "ICM_openDSS_endpoint")
    openDSS_endpoint_remote = h.helicsEndpointGetDefaultDestination(openDSS_endpoint_local)
    
    typeA_control_endpoint = h.helicsFederateGetEndpoint(fed, "typeA_control_ICM_endpoint")
    typeB_control_endpoint = h.helicsFederateGetEndpoint(fed, "typeB_control_ICM_endpoint")
    
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
    #     Ensure Input Files Loaded 
    #=====================================
    federate_time = h.helicsFederateRequestNextStep(fed) # Input Files being loaded by load_inputs during first delta time.
    
    data_loaded = h.helicsInputGetBoolean(sub_data_loaded)
    if not data_loaded:
        cleanup(fed)   
        return
        
    #=====================================
    #       Initialize Caldera ICM
    #=====================================

    #-------------------------------------
    # Get Information from Load Input Files
    #-------------------------------------
    
    # Send request
    input_dataset_enum_list = [input_datasets.SE_CE_data_obj, input_datasets.baseLD_data_obj, input_datasets.Caldera_global_parameters, input_datasets.Caldera_control_strategy_parameters_dict]
    send(input_dataset_enum_list, input_datasets_endpoint_local, input_datasets_endpoint_remote)

    # Advance 2 delta Timesteps
    federate_time = h.helicsFederateRequestNextStep(fed)
    federate_time = h.helicsFederateRequestNextStep(fed)
    
    # Get Reply
    input_dataset_dict = receive(input_datasets_endpoint_local)
    datasets_dict = input_dataset_dict[input_datasets_endpoint_remote]

    #-------------------------------------
    #    Create ICM_aux Object
    #-------------------------------------
    SE_CE_data_obj = datasets_dict[input_datasets.SE_CE_data_obj]
    baseLD_data_obj = datasets_dict[input_datasets.baseLD_data_obj]
    global_parameters = datasets_dict[input_datasets.Caldera_global_parameters]
    L2_control_strategy_parameters_dict = datasets_dict[input_datasets.Caldera_control_strategy_parameters_dict]
    
    grid_timestep_sec = 4*time_delta    
    ICM_obj = ICM_aux(SE_CE_data_obj, baseLD_data_obj, global_parameters, L2_control_strategy_parameters_dict, grid_timestep_sec, customized_pev_ramping, create_charge_profile_library, CE_queuing_inputs)
    
    ICM_obj.set_ensure_pev_charge_needs_met_for_ext_control_strategy(ensure_pev_charge_needs_met_for_ext_control_strategy)
    
    #=====================================
    # Send pev P=0 and Q=0 to OpenDSS
    #=====================================
    pev_PQ = {}
    for node_name in SE_CE_data_obj.caldera_powerflow_nodes.all_caldera_node_names:
        pev_PQ[node_name] = (0,0)
    
    send(pev_PQ, openDSS_endpoint_local, openDSS_endpoint_remote)
    
    #===========================================
    #   Advance to Actual Simulation Start Time
    #===========================================
    federate_time = h.helicsFederateRequestNextStep(fed)
    
    #=====================================
    #   Ensure OpenDSS Simulation loaded
    #=====================================    
    dss_simulation_loaded = h.helicsInputGetBoolean(sub_dss_simulation_loaded)
    if not dss_simulation_loaded:
        cleanup(fed)   
        return
    
    #=====================================
    #         Start Simulation
    #=====================================
    
    federate_name = h.helicsFederateGetName(fed)
    print('{} Federate Started.'.format(federate_name))
    while True:
        #=====================================
        #         	Sub Step 1 
        #=====================================
        
        #-------------------------------------
        #     Process TypeB Control-Info
        #-------------------------------------
        msg_obj = receive(typeB_control_endpoint)     
        
        for source, msg_dict in msg_obj.items():
            ICM_obj.process_control_messages(federate_time, msg_dict)
            
        #=====================================
        #         	Sub Step 2        
        #=====================================        
        federate_time = h.helicsFederateRequestNextStep(fed)
        
        #-------------------------------------
        # Read node voltages from OpenDSS
        #-------------------------------------
        msg_obj = receive(openDSS_endpoint_local)
        node_puV = msg_obj[openDSS_endpoint_remote]
        
        #-------------------------------------
        # Calculate pev P and Q
        #-------------------------------------
        node_pevPQ = ICM_obj.get_charging_power(federate_time, node_puV)
        
        #-------------------------------------
        # Send pev P and Q to OpenDSS
        #-------------------------------------
        send(node_pevPQ, openDSS_endpoint_local, openDSS_endpoint_remote)
        
        #=====================================
        #         	Sub Step 3
        #=====================================		
        federate_time = h.helicsFederateRequestNextStep(fed)
        
        #-------------------------------------
        #   Read & Process TypeB Messages
        #-------------------------------------
        msg_obj = receive(typeB_control_endpoint)
        for source, msg_dict in msg_obj.items():
            msg_dict = ICM_obj.process_control_messages(federate_time, msg_dict)
            if len(msg_dict) != 0:
                send(msg_dict, typeB_control_endpoint, source)

        #=====================================
        #         	Sub Step 4
        #=====================================
        federate_time = h.helicsFederateRequestNextStep(fed)
        
        #-------------------------------------
        #   Read & Process TypeA Messages
        #-------------------------------------
        msg_obj = receive(typeA_control_endpoint)
        for source, msg_dict in msg_obj.items():
            msg_dict = ICM_obj.process_control_messages(federate_time, msg_dict)
            if len(msg_dict) != 0:
                send(msg_dict, typeA_control_endpoint, source)

        #=====================================
        #      Advance to Next Time Step
        #=====================================
        federate_time = h.helicsFederateRequestNextStep(fed)

        if federate_time >= end_simulation_unix_time:
            break

    #=====================================
    #         Terminate Federate
    #=====================================
    cleanup(fed)
    print('{} Federate Terminated.'.format(federate_name))

