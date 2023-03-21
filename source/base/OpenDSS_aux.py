
import opendssdirect as dss
import os, math
import pandas as pd

from global_aux import OpenDSS_message_types, input_datasets, non_pev_feeder_load


class open_dss:

    def __init__(self, base_dir, use_opendss):

        if use_opendss == True:
            self.helper = open_dss_helper(base_dir)
        else:
            self.helper = logger_helper(base_dir)


    def get_input_dataset_enum_list(self):
        return self.helper.get_request_list()


    def load_input_datasets(self, datasets_dict):
        self.helper.load_input_datasets(datasets_dict)


    def initialize(self):       
        return self.helper.initialize()
    

    def process_control_messages(self, simulation_unix_time, message_dict):        
        return self.helper.process_control_messages(simulation_unix_time, message_dict)

    
    def set_caldera_pev_charging_loads(self, node_pevPQ):
        self.helper.set_caldera_pev_charging_loads(node_pevPQ)
    
    
    def get_pu_node_voltages_for_caldera(self):
        return self.helper.get_pu_node_voltages_for_caldera()
    
    
    def solve(self, simulation_unix_time):
        self.helper.solve(simulation_unix_time)        
    

    def log_data(self, simulation_unix_time):
        self.helper.log_data(simulation_unix_time)


    def post_simulation(self):
        self.helper.post_simulation()


class open_dss_helper:

    def __init__(self, base_dir):
        self.base_dir = base_dir
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
        
        self.dss_core = open_dss_core(self.base_dir, self.dss_file_name, baseLD_data_obj)
        self.dss_Caldera = open_dss_Caldera(self.base_dir, all_caldera_node_names, HPSE_caldera_node_names)
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
            self.dss_logger = open_dss_logger_A(self.base_dir, all_caldera_node_names, HPSE_caldera_node_names)

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

    def __init__(self, base_dir):
        self.base_dir = base_dir

    def get_request_list(self):
        return [input_datasets.baseLD_data_obj, input_datasets.all_caldera_node_names]

    def load_input_datasets(self, datasets_dict):
        # datasets_dict is a dictionary with input_datasets as keys.
        self.datasets_dict = datasets_dict

    def initialize(self):

        self.baseLD_data_obj = self.datasets_dict[input_datasets.baseLD_data_obj]
        self.all_caldera_node_names = self.datasets_dict[input_datasets.all_caldera_node_names]
                
        self.logger_obj = logger(self.base_dir, self.baseLD_data_obj, self.all_caldera_node_names)

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
                
            else:
                raise ValueError('Invalid message in caldera_ICM_aux::process_message.')
        
        # The return value (return_dict) must be a dictionary with OpenDSS_message_types as keys.
        # If there is nothing to return, return an empty dictionary.
        return return_dict



class open_dss_core:
    

    def __init__(self, base_dir, dss_file_name, baseLD_data_obj):
        self.base_dir = base_dir
        self.output_path = self.base_dir + '/outputs'
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
        
        dss_filepath = self.base_dir + '/opendss/' + self.dss_file_name
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
    
    def __init__(self, base_dir, all_caldera_node_names, HPSE_caldera_node_names):
        self.base_dir = base_dir
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
        f_invalid_nodes = open(self.base_dir + '/inputs/error_invalid_node_in_SE_file.txt', 'w')
        
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

    def __init__(self, base_dir, all_caldera_node_names, HPSE_caldera_node_names):
        
        node_voltages_to_log = ['810.2', '822.1', '826.2', '856.2', '864.1', '848.1', '848.2', '848.3', '840.1', '840.2', '840.3', '838.2', '890.1', '890.2', '890.3']
        #node_pev_charging_to_log = ['810.2', '826.2', '856.2', '838.2']
        node_pev_charging_to_log = ['806.1','806', '854']
        
        #------------------------------
        
        self.base_dir = base_dir
        self.all_caldera_node_names = all_caldera_node_names
        self.HPSE_caldera_node_names = HPSE_caldera_node_names
        
        openDSS_node_names = set()
        X = dss.Circuit.AllNodeNames()
        for x in X:
            openDSS_node_names.add(x)
        
        output_path = self.base_dir + '/outputs'
        
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

    def __init__(self, base_dir, baseLD_data_obj, all_caldera_node_names):

        self.base_dir = base_dir
        self.all_caldera_node_names = all_caldera_node_names
        self.baseLD_data_obj = baseLD_data_obj
        #print("all_caldera_node_names : {}".format(all_caldera_node_names))
        
        self.real_power_profiles = {}
        self.reactive_power_profiles = {}
        self.real_power_profiles["simulation_time_hrs"] = []
        self.real_power_profiles["base_load_kW"] = []
        self.reactive_power_profiles["simulation_time_hrs"] = []
        self.reactive_power_profiles["base_load_kW"] = []

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

        for (node_name, (P_kW, Q_kVAR)) in node_pevPQ.items():
            self.real_power_profiles[node_name].append(P_kW)
            self.reactive_power_profiles[node_name].append(Q_kVAR)

    def write_data_to_disk(self):
        Output_dir = self.base_dir + "/outputs/"

        df = pd.DataFrame(self.real_power_profiles)
        df.to_csv(Output_dir + "real_power_profiles.csv", index=False)

        df = pd.DataFrame(self.reactive_power_profiles)
        df.to_csv(Output_dir + "reactive_power_profiles.csv", index=False)

    def get_pu_node_voltages_for_caldera(self):

        return_dict = {}
        for node_name in self.all_caldera_node_names:
            return_dict[node_name] = 1.0
        
        return return_dict