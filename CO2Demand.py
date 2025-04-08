def calculate_co2demand(inputs_dataframe, htc, heat_demand, light_demand):
    from joblib import load
    import pandas as pd
    import matplotlib.pyplot as plt
    import numpy as np

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
    heat_demand.index = pd.to_datetime(heat_demand.index, dayfirst=True)
    light_demand.index = pd.to_datetime(light_demand.index, dayfirst=True)

    CO2_demand = pd.DataFrame(index=climate.index)

    # Desired CO2 Level
    CO2_demand["Desired CO2 Level"] = np.where(
        (CO2_demand.index.hour > op_co2.loc["Daytime CO2 Level On", "Value"]) &
        (CO2_demand.index.hour <= op_co2.loc["Daytime CO2 Level Off", "Value"]),
        op_co2.loc["Daytime CO2 Level", "Value"],
        op_co2.loc["Nighttime CO2 Level", "Value"]
    )

    # CO2 Change
    # First row calculation
    first_change = (
                           global_assump.loc["CO2 Density", "Value"]
                           * gm_d.loc["Greenhouse Volume", "Value"]
                           * (CO2_demand["Desired CO2 Level"].iloc[0] - op_co2.loc["Ambient Levels", "Value"])
                   ) / 1e6

    # Rest of the rows calculation
    rest_change = (
                          global_assump.loc["CO2 Density", "Value"]
                          * gm_d.loc["Greenhouse Volume", "Value"]
                          * (CO2_demand["Desired CO2 Level"].iloc[1:] - CO2_demand["Desired CO2 Level"].iloc[
                                                                        :-1].values)
                  ) / 1e6

    # Combine first row with the rest
    CO2_demand["CO2 Change"] = pd.Series(
        [first_change] + rest_change.tolist(),
        index=CO2_demand.index
    )

    # Set negative changes to 0
    CO2_demand["CO2 Change"] = CO2_demand["CO2 Change"].clip(lower=0)
    CO2_demand["CO2 Change"] = CO2_demand["CO2 Change"].fillna(0)

    # CO2 Loss Rate (Kg/h)
    CO2_demand["CO2 Loss Rate"] = global_assump.loc["CO2 Density", "Value"] * gm_d.loc["Greenhouse Volume", "Value"] * (
            CO2_demand["Desired CO2 Level"] - op_co2.loc["Ambient Levels", "Value"]) / 1e6

    # Lighting Photosynthetically Active Radiation (PAR) (W/m2)
    CO2_demand["Lighting PAR"] = np.where(
        crop["Solar Radiation in Greenhouse"] > op_light.loc["Switch off if solar radiation is greater than:", "Value"],
        0,
        np.where(
            (CO2_demand.index.hour > op_light.loc["Time lighting is switched on", "Value"]) &
            (CO2_demand.index.hour <= op_light.loc["Time lighting is switched off", "Value"]),
            op_light.loc["Installed Power of lamp", "Value"] * op_light.loc[
                "Fraction of Lighting Input Converted to PAR", "Value"],
            0
        )
    )

    # Total PAR (W/m2)
    CO2_demand["Total PAR"] = crop["Photosynthetically Active Solar Radiation"] + CO2_demand["Lighting PAR"]

    # PAR Use Efficiency
    CO2_demand["PAR Efficiency"] = crop_data.loc["Leaf PAR use efficiency", "Value"] * (1 - (
            (np.exp(
                -1 * crop_data.loc["Extinction Coefficient", "Value"] * crop_data.loc["Leaf Area Index", "Value"])) / (
                    1 - crop_data.loc["Leaf Transmission Coefficient", "Value"])))

    # Stomatal Conductance
    CO2_demand["Stomatal Conductance"] = (
            (crop_data.loc["a", "Value"] /
             (crop_data.loc["b", "Value"] * crop_data.loc["Extinction Coefficient", "Value"])) *
            np.log(
                (
                        (crop_data.loc["b", "Value"] * crop["I StomCond"] * crop_data.loc[
                            "Extinction Coefficient", "Value"]) +
                        (1 - crop_data.loc["Leaf Transmission Coefficient", "Value"])
                ) /
                (
                        (crop_data.loc["b", "Value"] * crop["I StomCond"] *
                         np.exp(-1 * crop_data.loc["Extinction Coefficient", "Value"] *
                                crop_data.loc["Leaf Area Index", "Value"])) +
                        (1 - crop_data.loc["Leaf Transmission Coefficient", "Value"])
                )
            )
    )

    # Hourly Gross Photosynthesis Rate (kg_CO2 / m2 h
    CO2_demand["Gross Photosynthesis Rate"] = np.where(
        CO2_demand["Total PAR"] == 0,
        0,
        ((CO2_demand["Total PAR"] * CO2_demand["PAR Efficiency"] * CO2_demand["Stomatal Conductance"] *
          global_assump.loc["CO2 Density", "Value"] * CO2_demand["Desired CO2 Level"])
         / ((CO2_demand["Total PAR"] *
             CO2_demand["PAR Efficiency"]) + (CO2_demand["Stomatal Conductance"] *
                                              global_assump.loc["CO2 Density", "Value"] *
                                              CO2_demand["Desired CO2 Level"]))) * 3600
    )

    # Hourly Net Photosynthesis Rate (kg_CO2 / m2 h)
    CO2_demand["Net Photosynthesis Rate"] = np.where(
        CO2_demand["Gross Photosynthesis Rate"] <= crop_data.loc["Dark Respiration Rate", "Value"] * 3600 *
        crop_data.loc["Leaf Area Index", "Value"],
        0,
        CO2_demand["Gross Photosynthesis Rate"] - (crop_data.loc["Dark Respiration Rate", "Value"] * 3600 *
                                                   crop_data.loc["Leaf Area Index", "Value"])
    )

    # Hourly Net Photosynthesis (kg_CO2 / h)
    CO2_demand["Net Photosynthesis"] = CO2_demand["Net Photosynthesis Rate"] * gm_d.loc["Floor Area", "Value"]

    # Total CO2 Demand (kg)
    CO2_demand["Total CO2 Demand"] = (CO2_demand["Net Photosynthesis"] + CO2_demand["CO2 Change"] +
                                      CO2_demand["CO2 Loss Rate"])

    CO2_demand.to_json("co2_demand.json")

    return CO2_demand


if __name__ == "__main__":
    from InputCalculations import calculate_inputs
    from HTCoefficients import calculate_htc
    from HeatDemand import calculate_heatdemand
    from LightDemand import calculate_lightdemand
    from joblib import load, dump

    inputs = calculate_inputs()
    htc = calculate_htc(inputs)
    heatdemand = calculate_heatdemand(inputs, htc)
    lightdemand = calculate_lightdemand(inputs, htc, heatdemand)
    co2_demand = calculate_co2demand(inputs, htc, heatdemand, lightdemand)

    dump(co2_demand, "co2_demand.joblib")
