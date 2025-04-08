
def calculate_heatdemand(inputs_data, htc):

    from joblib import load
    import pandas as pd
    import numpy as np
    from joblib import dump
    from json import dump


    gm_d = inputs_data["gm_d"]
    gm_r = inputs_data["gm_r"]
    gm_south = inputs_data["gm_south"]
    gm_side = inputs_data["gm_side"]
    gm_north = inputs_data["gm_north"]

    climate = inputs_data["climate"]

    crop_data = inputs_data["crop_data"]
    crop = inputs_data["crop"]

    op_enviro = inputs_data["op_enviro"]
    op_temp = inputs_data["op_temp"]
    op_temp_sp = inputs_data["op_temp_sp"]
    op_light = inputs_data["op_light"]
    op_co2 = inputs_data["op_co2"]

    global_assump = inputs_data["global_assump"]

    climate.index = pd.to_datetime(climate.index, dayfirst=True)
    op_temp_sp.index = pd.to_datetime(op_temp_sp.index, dayfirst=True)
    crop.index = pd.to_datetime(crop.index, dayfirst=True)
    htc.index = pd.to_datetime(htc.index, dayfirst=True)

    heat_demand = pd.DataFrame(index=climate.index)

    # Solar heat gain (Q_s)
    a = gm_r.loc["Solar Heat Gain Coefficient", "Value"] * ((gm_r.loc["Solar Transmissivity", "Value"] * gm_d.loc[
        "South Roof Area", "Value"] * climate["Solar Radiation (South Roof)"]) + (
                                                                        gm_r.loc["Solar Transmissivity", "Value"] *
                                                                        gm_d.loc["North Roof Area", "Value"] * climate[
                                                                            "Solar Radiation (North Roof)"]))
    b = gm_south.loc["Solar Heat Gain Coefficient", "Value"] * gm_south.loc["Solar Transmissivity", "Value"] * gm_d.loc[
        "South Wall Area", "Value"] * climate["Solar Radiation (South Wall)"]
    c = gm_side.loc["Solar Heat Gain Coefficient", "Value"] * ((gm_side.loc["Solar Transmissivity", "Value"] * gm_d.loc[
        "East Wall Area", "Value"] * climate["Solar Radiation (East Wall)"]) + (
                                                                           gm_side.loc["Solar Transmissivity", "Value"] *
                                                                           gm_d.loc["West Wall Area", "Value"] * climate[
                                                                               "Solar Radiation (West Wall)"]))

    gm_north.loc["Solar Heat Gain Coefficient", "Value"] = float(gm_north.loc["Solar Heat Gain Coefficient", "Value"])
    gm_north.loc["Solar Transmissivity", "Value"] = float(gm_north.loc["Solar Transmissivity", "Value"])
    d = gm_north.loc["Solar Heat Gain Coefficient", "Value"] * gm_north.loc["Solar Transmissivity", "Value"] * gm_d.loc[
        "North Wall Area", "Value"] * climate["Solar Radiation (North Wall)"]

    heat_demand["Q_s"] = a + b + c + d

    # Lighting Heat Gain (Q_sl)
    is_lighting_on = (
            (crop["Solar Radiation in Greenhouse"] < op_light.loc[
                "Switch off if solar radiation is greater than:", "Value"])
            & (climate.index.hour > op_light.loc["Time lighting is switched on", "Value"])
            & (climate.index.hour <= op_light.loc["Time lighting is switched off", "Value"])
    )

    heat_demand["Q_sl"] = np.where(
        is_lighting_on,
        op_light.loc["Installed Power of lamp", "Value"]
        * op_light.loc["Lighting Heat Conversion Factor", "Value"]
        * op_light.loc["Lighting Allowance Factor", "Value"]
        * gm_d.loc["Floor Area", "Value"],
        0,
    )

    # Motors Heat Gain (Q_m)
    heat_demand["Q_m"] = op_enviro.loc["No. of Air Recirculation Fans", "Value"] * (
                op_enviro.loc["Motor Power Rating", "Value"] / op_enviro.loc["Recirculation Motor Efficiency", "Value"]) * \
                         op_enviro.loc["Recirculation Motor Load Factor", "Value"] * op_enviro.loc[
                             "Recirculation Motor Use Factor", "Value"]

    # CO2 Heat Gain (Q_CO2)
    heat_demand["Q_co2"] = 0  # Assumed zero in excel

    # Total Heat Sources
    heat_demand["Sources"] = heat_demand["Q_m"] + heat_demand["Q_s"] + heat_demand["Q_sl"] + heat_demand["Q_co2"]

    # Conduction/Convection Heat Loss (Q_t), Air Exchange Heat Loss (Q_i), Perimeter Heat Loss (Q_p)
    temp_diff = op_temp_sp["Temperature C"] - climate["Temperature C"]
    temp_diff_positive = temp_diff.clip(lower=0)

    heat_demand["Q_t"] = np.where(
        temp_diff_positive > 0,
        (
                htc["Roof U-Value"] * (gm_d.loc["North Roof Area", "Value"] + gm_d.loc["South Roof Area", "Value"])
                + htc["North Wall U-Value"] * gm_d.loc["North Wall Area", "Value"]
                + htc["South Wall U-Value"] * gm_d.loc["South Wall Area", "Value"]
                + htc["Side Wall U-Value"]
                * (gm_d.loc["East Wall Area", "Value"] + gm_d.loc["West Wall Area", "Value"])
        )
        * temp_diff_positive,
        0,
    )

    heat_demand["Q_i"] = np.where(
        temp_diff_positive > 0,
        0.33
        * op_enviro.loc["Number of Air Exchanges per hour", "Value"]
        * gm_d.loc["Greenhouse Volume", "Value"]
        * temp_diff_positive,
        0,
    )

    heat_demand["Q_p"] = np.where(
        temp_diff_positive > 0,
        gm_south.loc["Perimeter Heat Loss Factor", "Value"]
        * gm_d.loc["Greenhouse Perimeter", "Value"]
        * temp_diff_positive,
        0,
    )

    # radiative heat loss (Q_r)

    is_lighting_hours = (
            (climate.index.hour > op_light.loc["Time lighting is switched on", "Value"])
            & (climate.index.hour <= op_light.loc["Time lighting is switched off", "Value"])
    )

    sigma = global_assump.loc["Stefan-Boltzmann Constant", "Value"]

    heat_demand["Q_r,sr"] = np.where(
        (temp_diff_positive > 0) & is_lighting_hours,
        sigma
        * gm_r.loc["Emissivity", "Value"]
        * gm_d.loc["South Roof Area", "Value"]
        * gm_r.loc["View Factor", "Value"]
        * (
                np.power(op_temp_sp["Temperature K"], 4)
                - np.power(htc["Cover Temp"], 4)
        ),
        0,
    )

    heat_demand["Q_r,nr"] = np.where(
        (temp_diff_positive > 0) & is_lighting_hours,
        sigma
        * gm_r.loc["Emissivity", "Value"]
        * gm_d.loc["North Roof Area", "Value"]
        * gm_r.loc["View Factor", "Value"]
        * (
                np.power(op_temp_sp["Temperature K"], 4)
                - np.power(htc["Cover Temp"], 4)
        ),
        0,
    )

    heat_demand["Q_r,sw"] = np.where(
        (temp_diff_positive > 0) & is_lighting_hours,
        sigma
        * gm_south.loc["Emissivity", "Value"]
        * gm_d.loc["South Wall Area", "Value"]
        * gm_south.loc["View Factor", "Value"]
        * (
                np.power(op_temp_sp["Temperature K"], 4)
                - np.power(htc["Cover Temp"], 4)
        ),
        0,
    )

    heat_demand["Q_r,ew"] = np.where(
        (temp_diff_positive > 0) & is_lighting_hours,
        sigma
        * gm_side.loc["Emissivity", "Value"]
        * gm_d.loc["East Wall Area", "Value"]
        * gm_side.loc["View Factor", "Value"]
        * (
                np.power(op_temp_sp["Temperature K"], 4)
                - np.power(htc["Cover Temp"], 4)
        ),
        0,
    )

    heat_demand["Q_r,ww"] = np.where(
        (temp_diff_positive > 0) & is_lighting_hours,
        sigma
        * gm_side.loc["Emissivity", "Value"]
        * gm_d.loc["West Wall Area", "Value"]
        * gm_side.loc["View Factor", "Value"]
        * (
                np.power(op_temp_sp["Temperature K"], 4)
                - np.power(htc["Cover Temp"], 4)
        ),
        0,
    )

    heat_demand["Q_r,i"] = np.where(
        (temp_diff_positive > 0) & is_lighting_hours,
        sigma
        * global_assump.loc["Emissivity of plants", "Value"]
        * global_assump.loc["Avg Transmissivity LW Radiation", "Value"]
        * global_assump.loc["Sky View Factor", "Value"]
        * gm_d.loc["Floor Area", "Value"]
        * (
                np.power(op_temp_sp["Temperature K"], 4)
                - np.power(climate["Tsky"], 4)
        ),
        0,
    )

    # Ground Heat Loss (Q_g) ??not sure about this from excel??
    heat_demand["Q_g"] = 0

    # Total Radiative Heat Loss
    heat_demand["Q_r,total"] = heat_demand["Q_r,sr"] + heat_demand["Q_r,nr"] + heat_demand["Q_r,sw"] + heat_demand[
        "Q_r,ew"] + heat_demand["Q_r,ww"] + heat_demand["Q_r,i"] + heat_demand["Q_g"]

    # Evaporative Heat Loss (Q_e)
    heat_demand["Q_e"] = crop["Moisture Transfer Rate"] * global_assump.loc["Latent Heat of Water Vaporisation", "Value"]

    # Total Heat "Sinks
    heat_demand["Sinks"] = heat_demand["Q_t"] + heat_demand["Q_i"] + heat_demand["Q_p"] + heat_demand["Q_r,total"] + \
                           heat_demand["Q_e"]

    # Net Heat Requirement (Q_net,W) W
    heat_demand["Q_net,W"] = np.where(
        (heat_demand["Sinks"].values - heat_demand["Sources"].values) > 0,
        heat_demand["Sinks"].values - heat_demand["Sources"].values,
        0,
    )

    # Net Heat Requirement (Q_net) MJ
    heat_demand["Q_net,MJ"] = heat_demand["Q_net,W"] * 3600 / 1e6

    # Net Heat Requirement (Q_net) kWh
    heat_demand["QnetMWh"] = heat_demand["Q_net,MJ"] / 3600

    heat_demand["Q_net,MJ"] = heat_demand["Q_net,W"] * 3600 / 1e6

    # Net Heat Requirement (Q_net) MWh
    column_name = "QnetMWh"  # Define the exact column name we want
    heat_demand[column_name] = heat_demand["Q_net,MJ"] / 3600

    heat_demand.to_json("heat_demand.json")

    return heat_demand


if __name__ == "__main__":
    from InputCalculations import calculate_inputs
    from HTCoefficients import calculate_htc

    inputs = calculate_inputs()
    htc = calculate_htc(inputs)
    heat_demand = calculate_heatdemand(inputs, htc)
    total_heat_demand = heat_demand["QnetMWh"].sum()




