
import opendssdirect as dss
import os, math
import pandas as pd

from global_aux import OpenDSS_message_types, input_datasets, non_pev_feeder_load


class open_dss:

    # NOTE: The 'open_dss' class does two things: Use OpenDSS, and do logging.
    # if the boolean 'use_opendss' is false, then this class will just do the logging.
    # TODO: Separate the logging into a separate federate.
    def __init__(self, io_dir, use_opendss):

        if use_opendss == True:
            self.helper = open_dss_helper(io_dir)
        else:
            self.helper = logger_helper(io_dir)

        # The dictionararies save current and voltage every timestep
        self.voltage_profile = {}
        self.current_profile = {}
        


    def get_input_dataset_enum_list(self):
        return self.helper.get_request_list()


    def load_input_datasets(self, datasets_dict):
        self.datasets_dict = datasets_dict
        self.helper.load_input_datasets(datasets_dict)


    def initialize(self):

        # Intializing RL helper class
        self.RL_helper = RL_helper(self.datasets_dict[input_datasets.all_caldera_node_names], self.datasets_dict[input_datasets.HPSE_caldera_node_names])
        return self.helper.initialize()
    

    def process_control_messages(self, simulation_unix_time, message_dict):

        return_val = self.helper.process_control_messages(simulation_unix_time, message_dict)

        # Convert OpenDSS Voltages to Dataframe format and send the info to External Control Federate 
        key = OpenDSS_message_types.get_node_voltage_profiles
        if key in return_val:
            v_df = pd.DataFrame()        
            for key, value in self.voltage_profile.items():
                v_df[key] = value
            
            return_val[OpenDSS_message_types.get_node_voltage_profiles] = v_df
        
        # Convert OpenDSS Currents to Dataframe format and send the info to External Control Federate
        key = OpenDSS_message_types.get_line_current_profiles
        if key in return_val:

            i_df = pd.DataFrame()
            for key, value in self.current_profile.items():
                if key == "time":
                    i_df["time"] = value
                else:
                    separated_lists = zip(*value)
                    separated_lists = [list(t) for t in separated_lists]
                    for (i, t) in enumerate(separated_lists):
                        i_df["col_{}".format(i)] = list(t)
            
            return_val[OpenDSS_message_types.get_line_current_profiles] = i_df

        return return_val

    
    def set_caldera_pev_charging_loads(self, node_pevPQ):
        self.helper.set_caldera_pev_charging_loads(node_pevPQ)
    
    
    def get_pu_node_voltages_for_caldera(self):
        return self.helper.get_pu_node_voltages_for_caldera()
    
    
    def solve(self, simulation_unix_time):
        
        self.helper.solve(simulation_unix_time)        
        

        # Collect voltage data for RL
        if "time" not in self.voltage_profile:
            self.voltage_profile["time"] = []
        self.voltage_profile["time"].append(simulation_unix_time)

        # Collect voltages and append to the data structure
        node_voltages = self.RL_helper.get_voltages_for_RL()
        for (node, V) in node_voltages.items():
            if node not in self.voltage_profile:
                self.voltage_profile[node] = []
            self.voltage_profile[node].append(V)

        # Collect current data for RL
        if "time" not in self.current_profile:
            self.current_profile["time"] = []
        self.current_profile["time"].append(simulation_unix_time)

        # Collect currents and append to the data structure
        line_currents = self.RL_helper.get_currents_for_RL()
        for (line, currents) in line_currents.items():
            if line not in self.current_profile:
                self.current_profile[line] = []
            self.current_profile[line].append(currents)

    def log_data(self, simulation_unix_time):
        self.helper.log_data(simulation_unix_time)

    def post_simulation(self):
        self.helper.post_simulation()

# An helper class to collect voltage and currents data for RL
class RL_helper:
    def __init__(self, all_caldera_node_names, HPSE_caldera_node_names):
        self.all_caldera_node_names = all_caldera_node_names
        self.HPSE_caldera_node_names = HPSE_caldera_node_names
        self.line_currents_to_log=['L1(800-802)','L13(824-828)']
            
    def get_voltages_for_RL(self):
        return_dict = {}
        
        #---------------
        # Single Phase
        #---------------
        all_V = dss.Circuit.AllBusMagPu()
        all_node_names = dss.Circuit.AllNodeNames()
        
        for i in range(len(all_V)):
            if all_node_names[i] in self.all_caldera_node_names:
                return_dict[all_node_names[i]] = all_V[i]
        
        #---------------
        # Avg 3 Phase
        #---------------
        for bus_name in self.HPSE_caldera_node_names:    
            dss.Circuit.SetActiveBus(bus_name)
            V_complex_pu = dss.Bus.PuVoltage()
            num_nodes = int(round(len(V_complex_pu)/2))
            pu_V = 0
            
            for i in range(num_nodes):
                pu_V += dss.CmathLib.cabs(V_complex_pu[2*i], V_complex_pu[2*i+1])
            
            return_dict[bus_name] = pu_V / num_nodes
        
        return return_dict

    def get_currents_for_RL(self):
        
        return_dict = {}        
        
        for node_id in self.line_currents_to_log:
            if node_id =='L1(800-802)':
                #print("####Line between 800 - 802 nodes####")
                dss.Lines.Name('L1')
                current_rating = dss.Lines.NormAmps()
                #print(f'Line L1 rated for {current_rating} amps of current')

                dss.Circuit.SetActiveElement('Line.L1')
                line_currents = dss.CktElement.CurrentsMagAng()[::2] # just the magnitudes
                #print('Three-phase line currents:', line_currents)  # six because there's six terminals to a three-phase line

                max_current = max(line_currents)
                line_loading_L1 = max_current / current_rating
                #print(f'the line is {100*line_loading_L1:.2f}% loaded')

                #tmp_str = '{}, {}, {}, {}, {}, {}, {}, {}'.format(simulation_time_hrs,line_currents[0],line_currents[1], line_currents[2],#line_currents[3],line_currents[4],line_currents[5],line_loading_L1)
                #f_node.write(tmp_str + '\n')
            
            return_dict[node_id] = (line_currents[0],line_currents[1], line_currents[2],line_currents[3],line_currents[4],line_currents[5],line_loading_L1)
        
        return return_dict

class open_dss_helper:

    def __init__(self, io_dir):
        self.io_dir = io_dir
        self.dss_file_name = 'ieee34.dss'

    def get_request_list(self):
        return [input_datasets.baseLD_data_obj, input_datasets.all_caldera_node_names, input_datasets.HPSE_caldera_node_names]

    def load_input_datasets(self, datasets_dict):
        # datasets_dict is a dictionary with input_datasets as keys.
        self.datasets_dict = datasets_dict

    def initialize(self):

        baseLD_data_obj = self.datasets_dict[input_datasets.baseLD_data_obj]
        all_caldera_node_names = self.datasets_dict[input_datasets.all_caldera_node_names]
        HPSE_caldera_node_names = self.datasets_dict[input_datasets.HPSE_caldera_node_names]
        
        self.dss_core = open_dss_core(self.io_dir, self.dss_file_name, baseLD_data_obj)
        self.dss_Caldera = open_dss_Caldera(self.io_dir, all_caldera_node_names, HPSE_caldera_node_names)
        self.dss_external_control = open_dss_external_control()
        
        #-------------------------------------------
        #         Load and Check .dss file
        #-------------------------------------------
        is_successful = self.dss_core.load_dss_file()
    
        if is_successful:
            is_successful = self.dss_Caldera.check_caldera_node_names()
        
        #----------------------------------------------------
        #  Create logger object:   
        #----------------------------------------------------
        self.dss_logger = None
        if(is_successful):
            self.dss_logger = open_dss_logger_A(self.io_dir, all_caldera_node_names, HPSE_caldera_node_names)

        return is_successful

    def process_control_messages(self, simulation_unix_time, message_dict):        
        return self.dss_external_control.process_control_messages(simulation_unix_time, message_dict)
    
    def set_caldera_pev_charging_loads(self, node_pevPQ):
        self.node_pevPQ = node_pevPQ
        self.dss_Caldera.set_caldera_pev_charging_loads(node_pevPQ) 

    def get_pu_node_voltages_for_caldera(self):    
        return self.dss_Caldera.get_pu_node_voltages_for_caldera()

    def solve(self, simulation_unix_time):
        self.dss_core.solve(simulation_unix_time)

    def log_data(self, simulation_unix_time):
        self.dss_logger.log_data(simulation_unix_time, self.node_pevPQ)
    
    def post_simulation(self):
        pass

class logger_helper:

    def __init__(self, io_dir):
        self.io_dir = io_dir


    def get_request_list(self):
        return [input_datasets.baseLD_data_obj, input_datasets.all_caldera_node_names]

    def load_input_datasets(self, datasets_dict):
        # datasets_dict is a dictionary with input_datasets as keys.
        self.datasets_dict = datasets_dict

    def initialize(self):

        self.baseLD_data_obj = self.datasets_dict[input_datasets.baseLD_data_obj]
        self.all_caldera_node_names = self.datasets_dict[input_datasets.all_caldera_node_names]
                
        self.logger_obj = logger(self.io_dir, self.baseLD_data_obj, self.all_caldera_node_names)

        is_successful = True
        return is_successful
    
    def process_control_messages(self, simulation_unix_time, message_dict): 

        return_dict = {}
        
        for (msg_enum, parameters) in message_dict.items():
            if msg_enum == OpenDSS_message_types.get_all_node_voltages:
                return_dict[msg_enum] = self.get_pu_node_voltages_for_caldera()
            else:
                raise ValueError('Invalid message in caldera_ICM_aux::process_message.')
        
        # The return value (return_dict) must be a dictionary with OpenDSS_message_types as keys.
        # If there is nothing to return, return an empty dictionary.
        return return_dict

    
    def set_caldera_pev_charging_loads(self, node_pevPQ):
        self.node_pevPQ = node_pevPQ

    def get_pu_node_voltages_for_caldera(self):
        return_dict = {}
        for node_name in self.all_caldera_node_names:
            return_dict[node_name] = 1.0
        
        return return_dict
    
    def solve(self, simulation_unix_time):
        self.logger_obj.compute_total_load_profiles(self.node_pevPQ, simulation_unix_time)
        
    def log_data(self, simulation_unix_time):
        return None

    def post_simulation(self):
        self.logger_obj.write_data_to_disk()


class open_dss_external_control:

    def __get_all_node_voltages(self):
        return_dict = {}
        
        all_V = dss.Circuit.AllBusMagPu()
        all_node_names = dss.Circuit.AllNodeNames()
        
        for i in range(len(all_V)):            
            return_dict[all_node_names[i]] = all_V[i]
        
        return return_dict

    
    def process_control_messages(self, simulation_unix_time, msg_dict):
        # msg_dict is a dictionary with OpenDSS_message_types as keys.
        
        return_dict = {}
        
        for (msg_enum, parameters) in msg_dict.items():
            if msg_enum == OpenDSS_message_types.get_all_node_voltages:
                return_dict[msg_enum] = self.__get_all_node_voltages()

            elif msg_enum == OpenDSS_message_types.get_node_voltage_profiles:
                return_dict[msg_enum] = None

            elif msg_enum == OpenDSS_message_types.get_line_current_profiles:
                return_dict[msg_enum] = None

            else:
                raise ValueError('Invalid message in caldera_ICM_aux::process_message.')
        
        # The return value (return_dict) must be a dictionary with OpenDSS_message_types as keys.
        # If there is nothing to return, return an empty dictionary.
        return return_dict

    def get_pu_node_voltages_hourly(self):
        pass


class open_dss_core:
    

    def __init__(self, io_dir, dss_file_name, baseLD_data_obj):
        self.io_dir = io_dir
        self.output_path = self.io_dir.outputs_dir
        self.dss_file_name = dss_file_name
        self.feeder_load = non_pev_feeder_load(baseLD_data_obj)
        self.ref_feeder_kW = 1
    
    
    def __configuring_dss(self):
        #dss.run_command('set controlMode=TIME') 
        dss.Solution.ControlMode(2) # 0->STATIC, 1->EVENT, 2->TIME
        dss.Solution.SolveSnap()
        (ref_feeder_kW, ref_feeder_kVAR) = dss.Circuit.TotalPower()
        self.ref_feeder_kW = abs(ref_feeder_kW)
    
    
    def load_dss_file(self):
        is_successful = True
        
        dss_filepath = os.path.join( self.io_dir.base_dir, 'opendss', self.dss_file_name )
        opendss_input_file_exists = os.path.isfile(dss_filepath)
        
        #-----------------------
        
        if not opendss_input_file_exists or not dss.Basic.Start(0):
            is_successful = False
        
            if not opendss_input_file_exists:
                print('OpenDSS input file does not exist.  Path to file: {}'.format(dss_filepath))
            else:
                print('OpenDSS not started!')
        
        #-----------------------
        
        if is_successful:        
            dss.Basic.ClearAll()
            dss.Basic.DataPath(self.output_path)
            opendss_load_status = dss.run_command('Compile ['+ dss_filepath + ']')
            
            if opendss_load_status != '':
                is_successful = False
                print('Unable to Compile OpenDSS input file. Error message: {}'.format(opendss_load_status))
        
        #-----------------------
        
        if is_successful:
            self.__configuring_dss()
        
        return is_successful
    
    
    def solve(self, simulation_unix_time):
        # Scaling the non-pev feeder load
        feeder_load_akW = self.feeder_load.get_non_pev_feeder_load_akW(simulation_unix_time)
        load_multiplier =  feeder_load_akW / self.ref_feeder_kW
        dss.Solution.LoadMult(load_multiplier)
        
        # Solving Powerflow
        hours = math.floor(simulation_unix_time/3600)
        seconds = simulation_unix_time - hours*3600
        dss.Solution.Hour(hours)
        dss.Solution.Seconds(seconds)
        dss.Solution.SolveSnap()

        converged = dss.Solution.Converged()
        if not converged:
            print('OpenDSS simulation did NOT converge at simulation time: {} hours.'.format(simulation_unix_time/3600))


class open_dss_Caldera:
    
    def __init__(self, io_dir, all_caldera_node_names, HPSE_caldera_node_names):
        self.io_dir = io_dir
        self.all_caldera_node_names = all_caldera_node_names
        self.HPSE_caldera_node_names = HPSE_caldera_node_names
        
    
    def check_caldera_node_names(self):
        errors = []
        
        all_node_names = dss.Circuit.AllNodeNames()
        all_bus_names = dss.Circuit.AllBusNames()
        all_load_names = dss.Loads.AllNames()
        
        for node_name in self.all_caldera_node_names:
            if node_name in self.HPSE_caldera_node_names:
                if node_name not in all_bus_names:
                    errors.append('Error: The Caldera node_id: ({}) for fast charging does not correspond to a bus in Open-DSS.'.format(node_name))
                
                load_name = 'pev3p_' + node_name
                if load_name not in all_load_names:
                    errors.append('Error: The fast charging loads on Caldera node_id: ({}) does not have a corresponing Open-DSS load object.  The Open-DSS load object should be named ({}).'.format(node_name, load_name))
            else:
                if node_name not in all_node_names:
                    errors.append('Error: The Caldera node_id: ({}) for L1 and L2 charging does not correspond to a node in Open-DSS.'.format(node_name))
                
                load_name = 'pev1p_' + node_name
                if load_name not in all_load_names:
                    errors.append('Error: The L1 & L2 loads on Caldera node_id: ({}) does not have a corresponing Open-DSS load object.  The Open-DSS load object should be named ({}).'.format(node_name, load_name))
        
        #-----------------------
        
        is_successful = True
        f_invalid_nodes = open( os.path.join( self.io_dir.inputs_dir, 'error_invalid_node_in_SE_file.txt' ), 'w')
        
        if len(errors) > 0:
            is_successful = False
            print('Invalid OpenDSS nodes in Caldera SE file.')
            
            for msg in errors:
                f_invalid_nodes.write(msg + '\n')
        
        f_invalid_nodes.close()
        
        #-----------------------
        
        return is_successful
    
    
    def get_pu_node_voltages_for_caldera(self):
        return_dict = {}
        
        #---------------
        # Single Phase
        #---------------
        all_V = dss.Circuit.AllBusMagPu()
        all_node_names = dss.Circuit.AllNodeNames()
        
        for i in range(len(all_V)):
            if all_node_names[i] in self.all_caldera_node_names:
                return_dict[all_node_names[i]] = all_V[i]
        
        #---------------
        # Avg 3 Phase
        #---------------
        for bus_name in self.HPSE_caldera_node_names:    
            dss.Circuit.SetActiveBus(bus_name)
            V_complex_pu = dss.Bus.PuVoltage()
            num_nodes = int(round(len(V_complex_pu)/2))
            pu_V = 0
            
            for i in range(num_nodes):
                pu_V += dss.CmathLib.cabs(V_complex_pu[2*i], V_complex_pu[2*i+1])
            
            return_dict[bus_name] = pu_V / num_nodes
        
        return return_dict


    def set_caldera_pev_charging_loads(self, node_pevPQ): 
        for (node_id, (P_kW, Q_kVAR)) in node_pevPQ.items(): 
            if node_id in self.HPSE_caldera_node_names:
                dss.Loads.Name('pev3p_' + node_id)
                dss.Loads.kW(P_kW)
                dss.Loads.kvar(Q_kVAR)
            else:
                dss.Loads.Name('pev1p_' + node_id)
                dss.Loads.kW(P_kW)
                dss.Loads.kvar(Q_kVAR)



class open_dss_logger_A:

    def __init__(self, io_dir, all_caldera_node_names, HPSE_caldera_node_names):
        
        node_voltages_to_log = ['810.2', '822.1', '826.2', '856.2', '864.1', '848.1', '848.2', '848.3', '840.1', '840.2', '840.3', '838.2', '890.1', '890.2', '890.3']
        #node_pev_charging_to_log = ['810.2', '826.2', '856.2', '838.2']
        node_pev_charging_to_log = ['848', '854']
        
        #------------------------------
        
        self.io_dir = io_dir
        self.all_caldera_node_names = all_caldera_node_names
        self.HPSE_caldera_node_names = HPSE_caldera_node_names
        
        openDSS_node_names = set()
        X = dss.Circuit.AllNodeNames()
        for x in X:
            openDSS_node_names.add(x)
        
        output_path = self.io_dir.outputs_dir
        
        #--------------------------------------
        #           feeder_PQ.csv
        #--------------------------------------
        self.f_feeder = open(output_path + '/feeder_PQ.csv', 'w')
        self.f_feeder.write('simulation_time_hrs, feeder_kW, pev_kW, feeder_kVAR, pev_kVAR' + '\n')
        
        #--------------------------------------
        #     Selected_Node_Voltages.csv
        #--------------------------------------
        self.node_voltages_to_log = []
        
        header = 'simulation_time_hrs'
        for node_id in node_voltages_to_log:
            if node_id in openDSS_node_names:
                self.node_voltages_to_log.append(node_id)
                header += ', _' + node_id 
        
        self.f_V = open(output_path + '/Selected_Node_Voltages.csv', 'w')
        self.f_V.write(header + '\n')
        
        #--------------------------------------
        #       node_pev_charging_to_log
        #--------------------------------------
        self.f_node_pev_charging = {}
        for x in node_pev_charging_to_log:
            if x in self.all_caldera_node_names:
                self.f_node_pev_charging[x] = open(output_path + '/' + x + '.csv', 'w')
                self.f_node_pev_charging[x].write('simulation_time_hrs, pu_Vrms, pev_kVAR, pev_kW' + '\n')
    
    
    def __del__(self):
        self.f_feeder.close()
        self.f_V.close()
        
        for (node_id, f_node) in self.f_node_pev_charging.items():
            f_node.close()
    
    
    def log_data(self, simulation_unix_time, node_pevPQ):
        simulation_time_hrs = simulation_unix_time/3600
    
        (feeder_kW, feeder_kVAR) = dss.Circuit.TotalPower()
        feeder_kW = -feeder_kW
        feeder_kVAR = -feeder_kVAR
        
        pev_kW = 0
        pev_kVAR = 0        
        for (node_id, (P_kW, Q_kVAR)) in node_pevPQ.items():
            pev_kW += P_kW
            pev_kVAR += Q_kVAR
        
        node_puV = {}
        all_V = dss.Circuit.AllBusMagPu()
        all_node_names = dss.Circuit.AllNodeNames()
        
        for i in range(len(all_V)):
            node_puV[all_node_names[i]] = all_V[i]
        
        #--------------------------------------
        #           feeder_PQ.csv
        #--------------------------------------
        tmp_str = '{}, {}, {}, {}, {}'.format(simulation_time_hrs, feeder_kW, pev_kW, feeder_kVAR, pev_kVAR)
        self.f_feeder.write(tmp_str + '\n')
        
        #--------------------------------------
        #     Selected_Node_Voltages.csv
        #--------------------------------------
        node_voltage_str = '{}'.format(simulation_time_hrs)
        for node_id in self.node_voltages_to_log:
            node_voltage_str += ', {}'.format(node_puV[node_id])
        
        self.f_V.write(node_voltage_str + '\n')
    
        #--------------------------------------
        #       node_pev_charging_to_log
        #--------------------------------------
        for (node_id, f_node) in self.f_node_pev_charging.items():   
            (pevP_kW, pevQ_kVAR) = node_pevPQ[node_id]
            
            if node_id in node_puV:
                node_V = node_puV[node_id]
            else:
                node_V = 0.0
                dss.Circuit.SetActiveBus(node_id)
                X = dss.Bus.Nodes()
                for x in X:
                    node_name = node_id + "." + str(x)
                    node_V += node_puV[node_name]

                node_V = node_V/len(X)
            
            tmp_str = '{}, {}, {}, {}'.format(simulation_time_hrs, node_V, pevQ_kVAR, pevP_kW)
            f_node.write(tmp_str + '\n')

class logger:

    def __init__(self, io_dir, baseLD_data_obj, all_caldera_node_names):

        self.io_dir = io_dir
        self.all_caldera_node_names = all_caldera_node_names
        self.baseLD_data_obj = baseLD_data_obj
        #print("all_caldera_node_names : {}".format(all_caldera_node_names))
        
        self.real_power_profiles = {}
        self.reactive_power_profiles = {}
        self.real_power_profiles["simulation_time_hrs"] = []
        self.real_power_profiles["base_load_kW"] = []
        self.real_power_profiles["total_demand_kW"] = []
        
        self.reactive_power_profiles["simulation_time_hrs"] = []
        self.reactive_power_profiles["base_load_kW"] = []
        self.reactive_power_profiles["total_demand_kW"] = []

        for node_name in all_caldera_node_names:
            self.real_power_profiles[node_name] = []
            self.reactive_power_profiles[node_name] = []


    def compute_total_load_profiles(self, node_pevPQ, simulation_unix_time):
  
        simulation_time_hrs = simulation_unix_time/3600.0

        index = math.floor((simulation_unix_time - self.baseLD_data_obj.data_start_unix_time) / self.baseLD_data_obj.data_timestep_sec)

        if (index < 0) or (index >= len(self.baseLD_data_obj.actual_load_akW)):
            print("Error : base_LD index computed not in data range")
            exit()

        base_LD_kW = self.baseLD_data_obj.actual_load_akW[index]
        self.real_power_profiles["simulation_time_hrs"].append(simulation_time_hrs)
        self.real_power_profiles["base_load_kW"].append(base_LD_kW)

        self.reactive_power_profiles["simulation_time_hrs"].append(simulation_time_hrs)
        self.reactive_power_profiles["base_load_kW"].append(base_LD_kW)

        total_P_kW = 0.0
        total_Q_kVAR = 0.0
        for (node_name, (P_kW, Q_kVAR)) in node_pevPQ.items():
            self.real_power_profiles[node_name].append(P_kW)
            self.reactive_power_profiles[node_name].append(Q_kVAR)
            total_P_kW += P_kW
            total_Q_kVAR += Q_kVAR
    
        self.real_power_profiles["total_demand_kW"].append(total_P_kW)
        self.reactive_power_profiles["total_demand_kW"].append(total_Q_kVAR)

    def write_data_to_disk(self):
        output_dir = self.io_dir.outputs_dir

        df = pd.DataFrame(self.real_power_profiles)
        df.to_csv( os.path.join( output_dir, "real_power_profiles.csv" ), index=False)

        df = pd.DataFrame(self.reactive_power_profiles)
        df.to_csv( os.path.join( output_dir, "reactive_power_profiles.csv" ), index=False)

    def get_pu_node_voltages_for_caldera(self):

        return_dict = {}
        for node_name in self.all_caldera_node_names:
            return_dict[node_name] = 1.0
        
        return return_dict