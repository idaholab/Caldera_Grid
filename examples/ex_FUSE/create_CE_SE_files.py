import pandas as pd
import random

df = pd.read_csv("./TE_profiles/CE_ICM_work_dominant_original.csv", keep_default_na=False)

n_samples = 10000

home_df = df[(df["charge_event_id"] >= 100000000)  & (df["charge_event_id"] < 200000000)]
home_df_with_fixed_CEs = home_df.sample(n=n_samples)
home_df_with_fixed_CEs["Ext_strategy"] = "ext0001"

home_df_with_fixed_CEs.to_csv("inputs/home/CE_home.csv", index = False)

work_df = df[(df["charge_event_id"] >= 200000000)  & (df["charge_event_id"] < 300000000)]
work_df_with_fixed_CEs = work_df.sample(n=n_samples)
work_df_with_fixed_CEs["Ext_strategy"] = "ext0001"

work_df_with_fixed_CEs.to_csv("inputs/work/CE_work.csv", index = False)


SE_df = pd.read_csv("./TE_profiles/SE_ICM_work_dominant_original.csv")

SE_df_home = SE_df[SE_df["SE_id"].isin(home_df_with_fixed_CEs["SE_id"])]
SE_df_work = SE_df[SE_df["SE_id"].isin(work_df_with_fixed_CEs["SE_id"])]

SE_df_home.to_csv("inputs/home/SE_home.csv", index = False)
SE_df_work.to_csv("inputs/work/SE_work.csv", index = False)