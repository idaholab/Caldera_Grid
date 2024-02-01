import matplotlib.pyplot as plt

time_at_start_of_bin =  [0*3600, 7*3600, 10*3600, 12*3600, 13*3600, 15*3600, 17*3600, 20*3600]
bin_value =             [0.2,    0.26,   0.16,    0.1,     0.28,    0.18,    0.3,     0.2]

timestep = 15*60
starttime = 0
endtime = 24*3600

data = []
time_index = 0
for cur_time in range(starttime, endtime, timestep):
    
    if(time_index + 1 < len(time_at_start_of_bin) and cur_time == time_at_start_of_bin[time_index+1]):
        time_index += 1
    
    data.append(bin_value[time_index])

plt.plot(data)      


f = open("TE_cost.csv", "w")

f.write("data_starttime_secs,{}\n".format(starttime))
f.write("data_timestep_secs,{}\n".format(timestep))
f.write("data,\n")
for val in data:
    f.write("{},\n".format(val))

f.close()

