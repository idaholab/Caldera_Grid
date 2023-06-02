
directxfc_to_emosaic_pevs_map = {
    "bev250_ld2_300kW":  "hd_300kWh",
    "bev200_ld4_150kW":  "md_200kWh",
    "bev275_ld1_150kW":  "ld_100kWh",
    "bev250_ld1_75kW":   "ld_100kWh",
    "bev150_ld1_50kW":   "ld_50kWh",
    "phev_SUV":          "ld_50kWh",
    "phev50":            "ld_50kWh",
    "phev20":            "ld_50kWh",
    "bev250_400kW":      "hd_400kWh",
    "bev300_575kW":      "hd_600kWh",
    "bev300_400kW":      "hd_400kWh",
    "bev250_350kW":      "hd_300kWh",
    "bev300_300kW":      "hd_300kWh",
    "bev150_150kW":      "md_200kWh",
}

# Using readlines()
file1 = open('CE_inputs.csv', 'r')
lines = file1.readlines()

file2 = open('CE_inputs_new.csv','w')

for line in lines:
    nline = line
    for xfc_str in directxfc_to_emosaic_pevs_map:
        emos_str = directxfc_to_emosaic_pevs_map[xfc_str]
        nline = nline.replace(xfc_str,emos_str)
    file2.write(nline)
