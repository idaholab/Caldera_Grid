import helics as h
from Helics_Helper import send, receive, cleanup
import os

def typeB_control_federate(io_dir, json_config_file_name, simulation_time_constraints, control_obj):

    print_communication = False
    #=====================================
    #         Setup Helics
    #=====================================
    config_file_path = os.path.join( io_dir.base_dir, "inputs/helics_config/", json_config_file_name )
    fed = h.helicsCreateCombinationFederateFromConfig(config_file_path)
    
    sub_data_loaded = h.helicsFederateGetInputByTarget(fed, 'Load_Input_Files/data_loaded')
    sub_dss_simulation_loaded = h.helicsFederateGetInputByTarget(fed, 'OpenDSS/dss_simulation_loaded')

    input_datasets_endpoint_local = h.helicsFederateGetEndpoint(fed, "input_datasets_endpoint")
    input_datasets_endpoint_remote = h.helicsEndpointGetDefaultDestination(input_datasets_endpoint_local)
    
    ICM_endpoint_local = h.helicsFederateGetEndpoint(fed, "typeB_control_ICM_endpoint")
    ICM_endpoint_remote = h.helicsEndpointGetDefaultDestination(ICM_endpoint_local)
    
    OpenDSS_endpoint_local = h.helicsFederateGetEndpoint(fed, "typeB_control_openDSS_endpoint")
    OpenDSS_endpoint_remote = h.helicsEndpointGetDefaultDestination(OpenDSS_endpoint_local)
    
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
    federate_time = h.helicsFederateRequestNextStep(fed) 
    
    data_loaded = h.helicsInputGetBoolean(sub_data_loaded)
    if not data_loaded:
        cleanup(fed)  
        return
    
    #=========================================
    #    Load and Initialize Control Object
    #=========================================
    
    #-------------------------------------
    # Get Information from Load Input Files
    #-------------------------------------
    # Send request
    input_dataset_enum_list = control_obj.get_input_dataset_enum_list()
    send(input_dataset_enum_list, input_datasets_endpoint_local, input_datasets_endpoint_remote)
    
    # Advance 2 delta Timesteps
    federate_time = h.helicsFederateRequestNextStep(fed)
    federate_time = h.helicsFederateRequestNextStep(fed)
    
    # Get Reply
    input_dataset_dict = receive(input_datasets_endpoint_local)
    datasets_dict = input_dataset_dict[input_datasets_endpoint_remote]
    control_obj.load_input_datasets(datasets_dict)
    
    #--------------------------------------------------
    #  Decide if this Federate is needed in Simulation
    #--------------------------------------------------
    if control_obj.terminate_this_federate():
        cleanup(fed)
        return
        
    #--------------------------------------------------
    #            Initialize Control Object
    #--------------------------------------------------
    control_obj.initialize()
    
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

    is_first_iteration = True
    while True:

        #=====================================
        #           Sub Step 1 
        #=====================================

        if is_first_iteration:
            is_first_iteration = False
        else:
            control_obj.log_data()
        
        #=====================================
        #           Sub Step 2 
        #=====================================
        federate_time = h.helicsFederateRequestNextStep(fed)

        #----------------------------------------
        #  Get State Info from Caldera & OpenDSS
        #----------------------------------------
        # Send Request to Caldera    
        msg_dict = control_obj.get_messages_to_request_state_info_from_Caldera(federate_time)
        if len(msg_dict) != 0:
            send(msg_dict, ICM_endpoint_local, ICM_endpoint_remote)
            
        # Send Request to OpenDSS 
        msg_dict = control_obj.get_messages_to_request_state_info_from_OpenDSS(federate_time)
        if len(msg_dict) != 0:
            send(msg_dict, OpenDSS_endpoint_local, OpenDSS_endpoint_remote)

        #=====================================
        #           Sub Step 3 
        #=====================================
        federate_time = h.helicsFederateRequestNextStep(fed)

        # Do Nothing in Sub step 3

        #=====================================
        #           Sub Step 4 
        #=====================================
        federate_time = h.helicsFederateRequestNextStep(fed)

        #---------------------------------------------
        # Read response from OpenDSS and Caldera ICM
        #---------------------------------------------
        Caldera_state_info_dict = {}
        if h.helicsEndpointHasMessage(ICM_endpoint_local):
            msg_dict = receive(ICM_endpoint_local)       
            Caldera_state_info_dict = msg_dict[ICM_endpoint_remote]

        DSS_state_info_dict = {}
        if h.helicsEndpointHasMessage(OpenDSS_endpoint_local):
            msg_dict = receive(OpenDSS_endpoint_local)
            DSS_state_info_dict = msg_dict[OpenDSS_endpoint_remote] 

        #-------------------------------------
        #     Solve Optimization Problem
        #-------------------------------------
        
        (Caldera_control_info_dict, DSS_control_info_dict) = control_obj.solve(federate_time, Caldera_state_info_dict, DSS_state_info_dict)
        
        #-------------------------------------------
        #  Send Control Info to Caldera and OpenDSS
        #-------------------------------------------
        if len(Caldera_control_info_dict) != 0:
            send(Caldera_control_info_dict, ICM_endpoint_local, ICM_endpoint_remote)

        if len(DSS_control_info_dict) != 0:
            send(DSS_control_info_dict, OpenDSS_endpoint_local, OpenDSS_endpoint_remote)
            
        #=====================================
        #     Break at end of Simulation
        #=====================================
        if federate_time >= end_simulation_unix_time-grid_timestep_sec:
            break
        else:
            federate_time = h.helicsFederateRequestNextStep(fed)

    
    #=====================================
    #         Terminate Federate
    #=====================================
    cleanup(fed)
    print('{} Federate Terminated.'.format(federate_name))
