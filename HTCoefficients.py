
def calculate_htc(inputs_data):

    from joblib import load
    import pandas as pd
    import numpy as np
    from joblib import dump

    #gm_d = inputs_data["gm_d"]
    gm_r = inputs_data["gm_r"]
    gm_south = inputs_data["gm_south"]
    gm_side = inputs_data["gm_side"]
    gm_north = inputs_data["gm_north"]

    climate = inputs_data["climate"]

    #crop_co2 = inputs_data["crop_co2"]
    crop = inputs_data["crop"]

    #op_enviro = inputs_data["op_enviro"]
    #op_temp = inputs_data["op_temp"]
    op_temp_sp = inputs_data["op_temp_sp"]
    #op_light = inputs_data["op_light"]
    #op_co2 = inputs_data["op_co2"]

    global_assump = inputs_data["global_assump"]

    climate.index = pd.to_datetime(climate.index, dayfirst=True)
    op_temp_sp.index = pd.to_datetime(op_temp_sp.index, dayfirst=True)
    crop.index = pd.to_datetime(crop.index, dayfirst=True)

    # Heat Transfer Coefficients calculations
    htc = pd.DataFrame(index= climate.index)
    htc["Cover Temp"] = (2/3) * climate["Temperature K"] + (1/3) * op_temp_sp["Temperature K"]
    htc["Prandtl No"] = global_assump.loc["Dynamic Viscosity of Air", "Value"] * global_assump.loc["Specific Heat of Air", "Value"] / global_assump.loc["Thermal Conductivity of Air", "Value"]

    variable = ["re_no", "H_i", "H_o", "U-Value"]
    structure = ["Roof_", "South_Wall", "Side_Wall", "North_Wall"]

    # Roof H/T
    htc["Roof Re No"] = global_assump.loc["Air Density", "Value"] * climate["Wind Speed"] * gm_r.loc["Characteristic Length Surface", "Value"] / global_assump.loc["Dynamic Viscosity of Air", "Value"]

    htc["Roof h_i"] = 1.86 * (np.abs(op_temp_sp["Temperature K"] - htc["Cover Temp"])) ** 0.33

    htc["Roof h_o"] = (global_assump.loc["Thermal Conductivity of Air", "Value"] / gm_r.loc["Characteristic Length Surface", "Value"]) * 0.037 * (htc["Roof Re No"] ** 0.8) * (htc["Prandtl No"] ** 0.33)

    x = (1 / htc["Roof h_i"]) + (gm_r.loc["Number of Layers in Cover", "Value"] * (gm_r.loc["Characteristic Length", "Value"] / gm_r.loc["Material Thermal Conductivity", "Value"]))
    y = (gm_r.loc["Number of Layers in Cover", "Value"] - 1) * (1 / gm_r.loc["Thermal Air Conductance", "Value"])+(1 / htc["Roof h_o"])

    htc["Roof U-Value"] = (x+y) ** -1

    # South wall H/T
    htc["South Wall Re No"] = global_assump.loc["Air Density", "Value"] * climate["Wind Speed"] * gm_south.loc["Characteristic Length Surface", "Value"] / global_assump.loc["Dynamic Viscosity of Air", "Value"]

    htc["South Wall h_i"] = 1.86 * (np.abs(op_temp_sp["Temperature K"] - htc["Cover Temp"])) ** 0.33

    htc["South Wall h_o"] = (global_assump.loc["Thermal Conductivity of Air", "Value"] / gm_south.loc["Characteristic Length Surface", "Value"]) * 0.037 * (htc["South Wall Re No"] ** 0.8) * (htc["Prandtl No"] ** 0.33)

    x = (1 / htc["South Wall h_i"]) + (gm_south.loc["Number of Layers in Cover", "Value"] * (gm_south.loc["Characteristic Length", "Value"] / gm_south.loc["Material Thermal Conductivity", "Value"]))
    y = (gm_south.loc["Number of Layers in Cover", "Value"] - 1) * (1 / gm_south.loc["Thermal Air Conductance", "Value"])+(1 / htc["South Wall h_o"])

    htc["South Wall U-Value"] = (x+y) ** -1

    # Side wall H/T
    htc["Side Wall Re No"] = global_assump.loc["Air Density", "Value"] * climate["Wind Speed"] * gm_side.loc["Characteristic Length Surface", "Value"] / global_assump.loc["Dynamic Viscosity of Air", "Value"]

    htc["Side Wall h_i"] = 1.86 * (np.abs(op_temp_sp["Temperature K"] - htc["Cover Temp"])) ** 0.33

    htc["Side Wall h_o"] = (global_assump.loc["Thermal Conductivity of Air", "Value"] / gm_side.loc["Characteristic Length Surface", "Value"]) * 0.037 * (htc["Side Wall Re No"] ** 0.8) * (htc["Prandtl No"] ** 0.33)

    x = (1 / htc["Side Wall h_i"]) + (gm_side.loc["Number of Layers in Cover", "Value"] * (gm_side.loc["Characteristic Length", "Value"] / gm_side.loc["Material Thermal Conductivity", "Value"]))
    y = (gm_side.loc["Number of Layers in Cover", "Value"] - 1) * (1 / gm_side.loc["Thermal Air Conductance", "Value"])+(1 / htc["Side Wall h_o"])

    htc["Side Wall U-Value"] = (x+y) ** -1

    # North wall H/T
    htc["North Wall Re No"] = global_assump.loc["Air Density", "Value"] * climate["Wind Speed"] * gm_north.loc["Characteristic Length Surface", "Value"] / global_assump.loc["Dynamic Viscosity of Air", "Value"]

    htc["North Wall h_i"] = 1.247 * (np.abs(op_temp_sp["Temperature K"] - htc["Cover Temp"])) ** 0.33

    htc["North Wall h_o"] = (global_assump.loc["Thermal Conductivity of Air", "Value"] / gm_north.loc["Characteristic Length Surface", "Value"]) * 0.037 * (htc["North Wall Re No"] ** 0.8) * (htc["Prandtl No"] ** 0.33)

    gm_north.loc["Characteristic Length", "Value"] = float(gm_north.loc["Characteristic Length", "Value"])
    gm_north.loc["Material 2 Thermal Conductivity", "Value"] = float(gm_north.loc["Material 2 Thermal Conductivity", "Value"])
    gm_north.loc["Number of Layers in Cover", "Value"] = float(gm_north.loc["Number of Layers in Cover", "Value"])
    gm_north.loc["Thermal Air Conductance", "Value"] = float(gm_north.loc["Thermal Air Conductance", "Value"])
    gm_north.loc["Material 1 Thickness", "Value"] = float(gm_north.loc["Material 1 Thickness", "Value"])
    gm_north.loc["Material 1 Thermal Conductivity", "Value"] = float(gm_north.loc["Material 1 Thermal Conductivity", "Value"])
    gm_north.loc["Material 2 Thickness", "Value"] = float(gm_north.loc["Material 2 Thickness", "Value"])
    gm_north.loc["Material 2 Thermal Conductivity", "Value"] = float(gm_north.loc["Material 2 Thermal Conductivity", "Value"])

    x = (1 / htc["North Wall h_i"]) + (gm_north.loc["Material 1 Thickness", "Value"] / gm_north.loc["Material 1 Thermal Conductivity", "Value"])
    y = (gm_north.loc["Material 2 Thickness", "Value"] / gm_north.loc["Material 2 Thermal Conductivity", "Value"]) + (1 / htc["North Wall h_o"])

    htc["North Wall U-Value"] = (x+y) ** -1

    return htc


if __name__ == "__main__":
    from InputCalculations import calculate_inputs

    inputs_data = calculate_inputs()
    htc = calculate_htc(inputs_data)
