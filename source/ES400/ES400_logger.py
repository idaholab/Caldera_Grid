import os


class ES400_logger():

    def __init__(self, log_path, headers):
        
        self.log_path = log_path
        self.data_str = ''

        self.log(headers)

        
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
       