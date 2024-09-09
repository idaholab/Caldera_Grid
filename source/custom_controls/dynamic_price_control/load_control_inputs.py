import os
#import modin.pandas as pd
import pandas as pd

class load_demand_gen_files():
    
    def __init__(self, input_folder : str) -> None:
        
        self.input_folder = input_folder
        self.file_extension = ".csv"
        self.demand_files = ["demand", "EV"]
        self.generation_files = ["nuclear", "solar", "wind", "fossil_fuel"]
        self.current_file_being_read = ""
        
    def load(self):
        
        demand_dict = {}
        generation_dict = {}
        
        for file in self.demand_files:                                          # load demand files
             demand_dict[file] = self.load_file(
                 os.path.join(self.input_folder, file + self.file_extension))
           
        for file in self.generation_files:                                      # load generation files
             generation_dict[file] = self.load_file(
                 os.path.join(self.input_folder, file + self.file_extension))
        
        #self.perform_multifile_error_checks()
        
        cost_dict = {}
        for (gen_type, value) in  generation_dict.items():
            metadata_dict = generation_dict[gen_type][0]
            local_cost_dict = {}
            local_cost_dict["gen_min"] = metadata_dict["gen_min"]
            local_cost_dict["cost_min"] = metadata_dict["cost_min"]
            local_cost_dict["gen_max"] = metadata_dict["gen_max"]
            local_cost_dict["cost_max"] = metadata_dict["cost_max"]
            local_cost_dict["cost_function"] = metadata_dict["cost_function"]
            cost_dict[gen_type] = local_cost_dict
        
        return (demand_dict, generation_dict, cost_dict)
    
    # This is incomplete
    def perform_multifile_error_checks(self, demand_dict, generation_dict):
        
        # Get these info
        #1. actual_ts_s
        #2. forecast_ts_s
        #3. forcast_of_s
        #4. forecast_l_s
        
        all_files = self.demand_files + self.generation_files
        for (i, (file, value))in eval(dict(demand_dict, **generation_dict).items()):
            (metadata_dict, forecast_metadata_dict, data_dict) = value
            
            if i == 0:    
                for (forecast_id, data_tup) in forecast_metadata_dict.items():
                    (release_time_sec, start_time_sec, end_time_sec, time_step_sec, offset_sec) = data_tup
                    forecast_ts_s = time_step_sec
                    forcast_of_s = start_time_sec - release_time_sec
                    forecast_l_s = (end_time_sec - start_time_sec)/time_step_sec
        pass
    
    def load_file(self, file_name : str):
        
        self.current_file_being_read = file_name                                # Update file being read
        
        df_full = pd.read_csv(file_name)                                        # Read the full csv file
        df_full = self.perform_df_format_checks(df_full)                        # Ensure file formatting is right
            
        metadata_dict = self.extract_metadata_dict(df_full)                     # Extract metadata dictionary
        forecast_metadata_dict = self.extract_forecast_metadata_dict(df_full)   # Extract forecast metadata dictionary
        data_dict = self.extract_data_dict(df_full, forecast_metadata_dict)     # Extract data dictionary
        
        return_val = self.perform_error_checks(                                 # Perform error checks and return updated data
            metadata_dict, forecast_metadata_dict, data_dict)
        
        return return_val
    
    def perform_df_format_checks(self, df_full):
        
        self.check_column_headers(df_full)                                      # Check column headers
        df_full.columns = self.extract_header_without_units(df_full.columns)    # Remove units from column headers
        
        return df_full
        
    def perform_error_checks(
            self, metadata_dict, forecast_metadata_dict, data_dict):
        
        # Ensure metadata contains gen_min, cost_min, gen_max, cost_max

        required_keys = set()
        required_keys.add(("cost_min", "$/MWh"))
        required_keys.add(("cost_max", "$/MWh"))
        required_keys.add(("gen_min", "MW"))
        required_keys.add(("gen_max", "MW"))
        required_keys.add(("cost_function", "str"))
        
        updated_metadata_dict = dict()
        metadata_keys = set()
        for (key, value) in metadata_dict.items():
            
            key_split = key.split("|")
            assert len(key_split) == 2, \
                "{}: in metadata column, {} does not contain key and value seperated by |"\
                    .format(self.current_file_being_read, key)
                    
            key_id = key_split[0].strip()
            key_unit = key_split[1].strip()
            
            metadata_keys.add((key_id, key_unit))
            
            if key_unit == "$/MWh" : value = float(value)
            elif key_unit == "MW" : value = float(value)
            elif key_unit == "str" : value = str(value)
            else : value = str(value)
            
            updated_metadata_dict[key_id] = value

        for req_key in required_keys:
            
            assert req_key in metadata_keys, \
                "{}: metadata does not contain key: {} | {}"\
                    .format(self.current_file_being_read, req_key[0], req_key[1])
        
        for (data_id, timeseries_df) in data_dict.items():
            
            if len(timeseries_df) > 0:
                # Check data is within the bounds of Gen min and Gen max 
                assert timeseries_df[data_id].min() >= updated_metadata_dict["gen_min"], \
                    "{}: in {} column, the min data:{} is less than gen_min: {}" \
                        .format(self.current_file_being_read, data_id, timeseries_df[data_id].min(), updated_metadata_dict["gen_min"])
                        
                # Check data is within the bounds of Gen min and Gen max 
                assert timeseries_df[data_id].max() <= updated_metadata_dict["gen_max"], \
                    "{}: in {} column, the max data:{} is greater than gen_max: {}" \
                        .format(self.current_file_being_read, data_id, timeseries_df[data_id].max(), updated_metadata_dict["gen_max"])
            
                # Check df doesn't have any missing data
                assert not timeseries_df.isnull().values.any(), \
                    "{}: in {} column, there is missing data" \
                        .format(self.current_file_being_read, data_id)
            
        return (updated_metadata_dict, forecast_metadata_dict, data_dict)
    
    def extract_data_dict(self, df_full, forecast_metadata_dict) -> dict:
    
        data_dict = {}
        
        all_keys = set()
        all_keys.add("actual")
        all_keys.update(forecast_metadata_dict.keys())
    
        for key in all_keys:
        
            columns_to_read = [key + "_time", key]
            
            data_df = df_full[columns_to_read]
            data_df = data_df.dropna(how = 'all')
            data_df[key + "_time"] = data_df[key + "_time"] * 3600.0
            data_dict[key] = data_df
    
        return data_dict

    def extract_header_without_units(self, columns):
        return [column.split('|')[0].strip() for column in columns]
        
    def extract_forecast_metadata_dict(self, df_full):
        
        forecast_metadata_dict = {}     # return_val
       
        forecast_metadata_columns = ["forecast_id", "forecast_release_time"]
        df_forecast_metadata = df_full[forecast_metadata_columns]
        df_forecast_metadata = df_forecast_metadata.dropna(how = 'all')
        
        forecast_id_to_release_time_dict = dict(
            zip(df_forecast_metadata.forecast_id, df_forecast_metadata.forecast_release_time))
        
        for forecast_id in forecast_id_to_release_time_dict.keys():
            
            release_time_sec = forecast_id_to_release_time_dict[forecast_id]
            
            df_forecast_time = df_full[forecast_id + "_time"].dropna(how = 'all')
            
            start_time_sec = df_forecast_time.iloc[0] * 3600
            time_step_sec = (df_forecast_time.iloc[1] - df_forecast_time.iloc[0] ) * 3600
            end_time_sec = start_time_sec + len(df_forecast_time)*time_step_sec
            offset_sec = start_time_sec - release_time_sec
            
            forecast_metadata_dict[forecast_id] = (release_time_sec, start_time_sec, end_time_sec, time_step_sec, offset_sec)            
        
        return forecast_metadata_dict
    
    def extract_metadata_dict(self, df_full) -> dict:
        metadata_cols=["metadata_key", "metadata_value"]
        
        metadata_df = df_full[metadata_cols]
        metadata_df = metadata_df.dropna(how = 'all')
        metadata_dict = dict(zip(metadata_df.metadata_key, metadata_df.metadata_value))
        return metadata_dict
        
    
    def check_column_headers(self, df_full):
        
        column_headers = df_full.columns.tolist()

        # Note : Please use atleast python 3.7. dictionary is ordered in python 3.7 and above
        import sys
        assert sys.version_info >= (3, 7)

        column_name_unit_dict = {}
        column_name_unit_dict["metadata_key"] = "str"
        column_name_unit_dict["metadata_value"] = "any"
        column_name_unit_dict["forecast_id"] = "str"
        column_name_unit_dict["forecast_release_time"] = "hrs"
        column_name_unit_dict["actual_time"] = "hrs"
        column_name_unit_dict["actual"] = "MW"
        column_name_unit_dict["forecast_time"] = "hrs"
        column_name_unit_dict["forecast_val"] = "MW"

        # Check for first 6 columns that's defined        
        for i in range(6):
    
            column_name = column_headers[i].split("|")[0].strip()
            column_unit = column_headers[i].split("|")[1].strip()
    
            assert column_name == list(column_name_unit_dict.keys())[i], \
                "{}: column {} name should be {}"\
                    .format(self.current_file_being_read, i, list(column_name_unit_dict.keys())[i])
            assert column_unit == column_name_unit_dict[column_name], \
                "{}: columns {} unit should be {}"\
                    .format(self.current_file_being_read, i, column_name_unit_dict[column_name])

        forecast_id_columns_df = df_full["forecast_id | str"]

        # Check remaining column names and units in the file
        for i in range(6, len(column_headers)):
    
            forecast_id_idx = int(i/2) - 3
            forecast_id = forecast_id_columns_df.iloc[forecast_id_idx]
        
            column_name = column_headers[i].split("|")[0].strip()
            column_unit = column_headers[i].split("|")[1].strip()
    
            if i%2 == 0:    # Time column
                assert column_name == forecast_id + "_time", \
                    "{}: column {} name should be {}"\
                        .format(self.current_file_being_read, i, forecast_id + "_time")
                assert column_unit == "hrs" or column_unit == "sec", \
                    "{}: column {} unit should be {}"\
                        .format(self.current_file_being_read, i, "hrs or sec")
                
                if column_unit == "sec":
                    df_full["{} | {}".format(column_name, column_unit)] = df_full["{} | {}".format(column_name, column_unit)]/3600.0
                    
                    print("column adjusted for {} | {}. Max : {}".format(column_name, column_unit, df_full["{} | {}".format(column_name, column_unit)].max()))
    
            else:           # Value column
                assert column_name == forecast_id, \
                    "{}: column {} name should be {}"\
                        .format(self.current_file_being_read, i, forecast_id)
                assert column_unit == "MW" or column_unit == "kW", \
                    "{}: column {} unit should be {}"\
                        .format(self.current_file_being_read, i, "MW or kW")
                        
                if column_unit == "kW":
                    df_full["{} | {}".format(column_name, column_unit)] = df_full["{} | {}".format(column_name, column_unit)]/1000.0
                    print("column adjusted for {} | {}. Max : {}".format(column_name, column_unit, df_full["{} | {}".format(column_name, column_unit)].max()))
