import os


class ES400_logger():

    def __init__(self, log_path):
        
        self.log_path = log_path
        
        self.data_str = ''
        self.headers = ["step", "num_events", "time_per_solve_s", "time_total_solve_s", "time_total_inc_comm_s"]

        self.log(self.headers)

        
    def log(self, data_arr):

        for data in data_arr:
            self.data_str += str(data) + ','

        self.data_str += '\n'
        
        
    def write_log(self):
        filename = "ES400_performance.csv"

        # file handle
        fh = open(os.path.join(self.log_path, filename), 'w')
        fh.write(self.data_str)
        fh.close()
       