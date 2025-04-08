def calculate_lightdemand(inputs_dataframe, htc, heat_demand):

    from joblib import load
    import pandas as pd
    import matplotlib.pyplot as plt
    import numpy as np
    from json import dump

    gm_d = inputs_dataframe["gm_d"]
    gm_r = inputs_dataframe["gm_r"]
    gm_south = inputs_dataframe["gm_south"]
    gm_side = inputs_dataframe["gm_side"]
    gm_north = inputs_dataframe["gm_north"]

    climate = inputs_dataframe["climate"]

    crop_data = inputs_dataframe["crop_data"]
    crop = inputs_dataframe["crop"]

    op_enviro = inputs_dataframe["op_enviro"]
    op_temp = inputs_dataframe["op_temp"]
    op_temp_sp = inputs_dataframe["op_temp_sp"]
    op_light = inputs_dataframe["op_light"]
    op_co2 = inputs_dataframe["op_co2"]

    global_assump = inputs_dataframe["global_assump"]

    climate.index = pd.to_datetime(climate.index, dayfirst=True)
    op_temp_sp.index = pd.to_datetime(op_temp_sp.index, dayfirst=True)
    crop.index = pd.to_datetime(crop.index, dayfirst=True)
    htc.index = pd.to_datetime(htc.index, dayfirst=True)

    light_demand = pd.DataFrame(index=climate.index)

    # Lighting Demand MJ
    light_demand["MJ"] = np.where(
        (climate.index.hour > op_light.loc["Time lighting is switched on", "Value"]) & (climate.index.hour <= op_light.loc["Time lighting is switched off", "Value"]) &
        (crop["Solar Radiation in Greenhouse"].values < op_light.loc["Switch off if solar radiation is greater than:", "Value"]),
        (op_light.loc["Installed Power of lamp", "Value"] * gm_d.loc["Floor Area", "Value"]) * 3600 / 1e6,
        0
    )

    # Lighting Demand MWh
    light_demand["MWh"] = light_demand["MJ"] / 3600

    light_demand.to_json("light_demand.json")

    return light_demand


if __name__ == "__main__":
    from InputCalculations import calculate_inputs
    from HTCoefficients import calculate_htc
    from HeatDemand import calculate_heatdemand

    inputs = calculate_inputs()
    htc = calculate_htc(inputs)
    heatdemand = calculate_heatdemand(inputs, htc)
    lightdemand = calculate_lightdemand(inputs, htc, heatdemand)