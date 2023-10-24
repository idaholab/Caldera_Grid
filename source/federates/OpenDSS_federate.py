import helics as h
from OpenDSS_aux import open_dss
from Helics_Helper import send, receive, cleanup
import os

def open_dss_federate(io_dir, json_config_file_name, simulation_time_constraints, use_opendss):

    print_communication = False
    #=====================================
    #         Setup Helics
    #=====================================
    config_file_path = os.path.join( io_dir.base_dir, os.path.join(io_dir.inputs_dir,"helics_config"), json_config_file_name )
    fed = h.helicsCreateCombinationFederateFromConfig(config_file_path)
    
    sub_data_loaded = h.helicsFederateGetInputByTarget(fed, 'Load_Input_Files/data_loaded')
    pub_dss_simulation_loaded = h.helicsFederateGetPublication(fed, 'dss_simulation_loaded')

    input_datasets_endpoint_local = h.helicsFederateGetEndpoint(fed, "input_datasets_endpoint")
    input_datasets_endpoint_remote = h.helicsEndpointGetDefaultDestination(input_datasets_endpoint_local)

    ICM_endpoint_local = h.helicsFederateGetEndpoint(fed, "ICM_openDSS_endpoint")
    ICM_endpoint_remote = h.helicsEndpointGetDefaultDestination(ICM_endpoint_local)
    
    typeA_control_endpoint = h.helicsFederateGetEndpoint(fed, "typeA_control_openDSS_endpoint")
    typeB_control_endpoint = h.helicsFederateGetEndpoint(fed, "typeB_control_openDSS_endpoint")
    
    #-------------------------------------
    
    start_simulation_unix_time = simulation_time_constraints.start_simulation_unix_time
    end_simulation_unix_time = simulation_time_constraints.end_simulation_unix_time
    grid_timestep_sec = simulation_time_constraints.grid_timestep_sec
    grid_deltatime_sec = grid_timestep_sec/4

    h.helicsFederateSetTimeProperty(fed, h.helics_property_time_offset, 0)
    h.helicsFederateSetTimeProperty(fed, h.helics_property_time_delta, grid_deltatime_sec)
    
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
    #       Initialize OpenDSS
    #=====================================
    dss_obj = open_dss(io_dir, use_opendss)
    
    #-------------------------------------
    # Get Information from Load Input Files
    #-------------------------------------
    
    # Send request
    input_dataset_enum_list = dss_obj.get_input_dataset_enum_list()
    send(input_dataset_enum_list, input_datasets_endpoint_local, input_datasets_endpoint_remote)


    # Advance 2 delta Timesteps
    federate_time = h.helicsFederateRequestNextStep(fed)
    federate_time = h.helicsFederateRequestNextStep(fed)
    
    # Get Reply
    input_dataset_dict = receive(input_datasets_endpoint_local)
    datasets_dict = input_dataset_dict[input_datasets_endpoint_remote]
    dss_obj.load_input_datasets(datasets_dict)
    
    #-------------------------------------
    #      Load and Check dss file
    #-------------------------------------    
    dss_loaded_successfully = dss_obj.initialize()
    
    h.helicsPublicationPublishBoolean(pub_dss_simulation_loaded, dss_loaded_successfully)
    
    if not dss_loaded_successfully:
        cleanup(fed)   
        return
    
    #-------------------------------------------
    #   Advance to Actual Simulation Start Time
    #-------------------------------------------
    federate_time = h.helicsFederateRequestNextStep(fed)
    
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
            dss_obj.process_control_messages(federate_time, msg_dict)

        #-------------------------------------
        #   Read pev P&Q from Caldera_ICM         
        #-------------------------------------
        msg_obj = receive(ICM_endpoint_local)
        node_pevPQ = msg_obj[ICM_endpoint_remote]
        dss_obj.set_caldera_pev_charging_loads(node_pevPQ)        
        
        #-------------------------------------
        #        Solve OpenDSS
        #-------------------------------------
        dss_obj.solve(federate_time)
        
        #-------------------------------------
        # Send node Voltages to Caldera_ICM
        #-------------------------------------    
        node_puV = dss_obj.get_pu_node_voltages_for_caldera()
        send(node_puV, ICM_endpoint_local, ICM_endpoint_remote)
        
        #=====================================
        #         	Sub Step 2
        #=====================================		
        federate_time = h.helicsFederateRequestNextStep(fed)
        
        #-------------------------------------
        #              Log Data
        #-------------------------------------  
        dss_obj.log_data(federate_time)
        
        #=====================================
        #         	Sub Step 3
        #=====================================		
        federate_time = h.helicsFederateRequestNextStep(fed)
        
        #-------------------------------------
        #   Read & Process TypeB Messages
        #-------------------------------------        
        msg_obj = receive(typeB_control_endpoint)
        for source, msg_dict in msg_obj.items():
            msg_dict = dss_obj.process_control_messages(federate_time, msg_dict)
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
            msg_dict = dss_obj.process_control_messages(federate_time, msg_dict)
            if len(msg_dict) != 0:
                send(msg_dict, typeA_control_endpoint, source)
                
        #=====================================
        #      Advance to Next Time Step
        #=====================================		
        federate_time = h.helicsFederateRequestNextStep(fed)
        
        if abs(federate_time % 3600) < 0.8:
            print("simulation_time_hrs: {}".format(federate_time/3600))
        
        if federate_time >= end_simulation_unix_time:
            break

    dss_obj.post_simulation()

    #=====================================
    #         Terminate Federate
    #=====================================
    cleanup(fed)
    print('{} Federate Terminated.'.format(federate_name))
