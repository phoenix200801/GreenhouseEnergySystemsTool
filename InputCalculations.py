def calculate_inputs():

    import pandas as pd
    import math
    import numpy as np
    from joblib import dump
    import os

    def read_csv(file_name):
        # Get the base directory (Lib folder)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, r"Lib\\CSV Inputs", os.path.basename(file_name))

        x = pd.read_csv(full_path, index_col=0, skip_blank_lines=True)
        return x.dropna(how="all")

    def read_csv_climate(file_name):
        # Get the base directory (Lib folder)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, r"Lib\\CSV Inputs", os.path.basename(file_name))

        x = pd.read_csv(full_path, index_col=False, skip_blank_lines=True, skiprows=23, engine='python')
        return x.dropna(how="all")

    def read_csv_sr(file_name):
        # Get the base directory (Lib folder)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, r"Lib\\CSV Inputs", os.path.basename(file_name))

        x = pd.read_csv(full_path, index_col=False, skipfooter=12, skiprows=8, engine='python')
        return x.dropna(how="all")


    def rad(x):
        z = math.radians(x)
        return z


    # Reading in all CSV files
    gm_d = read_csv("CSV Inputs/GreenhouseModel_Dimensions.csv")
    gm_r = read_csv("CSV Inputs/GreenhouseModel_Roof.csv")
    gm_south = read_csv("CSV Inputs/GreenhouseModel_SouthWall.csv")
    gm_side = read_csv("CSV Inputs/GreenhouseModel_SideWall.csv")
    gm_north = read_csv("CSV Inputs/GreenhouseModel_NorthWall.csv")

    # Climate Calculations
    climate_data = read_csv_climate("CSV Inputs/ClimateData.csv")

    #
    start_date = pd.Timestamp('1945-01-01 00:00:00')
    climate_data.index = pd.date_range(start=start_date, periods=len(climate_data), freq='h')
    climate_data = climate_data[(climate_data.index.year >= 2023) & (climate_data.index.year <= 2023)]

    climate = pd.DataFrame(index=climate_data.index)
    climate["Temperature C"] = climate_data["temp"]
    climate["Temperature K"] = climate["Temperature C"] + 273.15

    climate["TDP"] = pd.to_numeric(climate_data["dewpt"])
    climate["Wind Speed"] = pd.to_numeric(climate_data["wdsp"]) * 0.514444  # Convert from knots to m/s
    climate["Relative Humidity"] = pd.to_numeric(climate_data["rhum"])
    climate["CF"] = pd.to_numeric(climate_data["clamt"], errors='coerce')
    climate["cf"] = climate["CF"].fillna(0)

    climate.to_csv("climateTEST.csv")

    solar_radiation_nr = read_csv_sr("CSV Inputs/SolarRadiationNR.csv")
    solar_radiation_sr = read_csv_sr("CSV Inputs/SolarRadiationSR.csv")
    solar_radiation_nw = read_csv_sr("CSV Inputs/SolarRadiationNW.csv")
    solar_radiation_ew = read_csv_sr("CSV Inputs/SolarRadiationEW.csv")
    solar_radiation_sw = read_csv_sr("CSV Inputs/SolarRadiationSW.csv")
    solar_radiation_ww = read_csv_sr("CSV Inputs/SolarRadiationWW.csv")



    # Make sure the solar radiation DataFrames have the same length as climate_data
    if len(solar_radiation_nr) == len(climate_data):
        # Copy the datetime index from climate_data to the solar radiation DataFrames
        solar_radiation_nr.index = climate_data.index.copy()
        solar_radiation_sr.index = climate_data.index.copy()
        solar_radiation_nw.index = climate_data.index.copy()
        solar_radiation_ew.index = climate_data.index.copy()
        solar_radiation_sw.index = climate_data.index.copy()
        solar_radiation_ww.index = climate_data.index.copy()
    else:
        print(
            f"Warning: Index length mismatch. Climate data has {len(climate_data)} entries, but solar radiation has {len(solar_radiation_nr)} entries.")

    solar_radiation_sw.to_csv("climateSR_test.csv")

    climate["Solar Radiation (North Roof)"] = solar_radiation_nr["Gb(i)"] + solar_radiation_nr["Gd(i)"] + solar_radiation_nr["Gr(i)"]
    climate["Solar Radiation (South Roof)"] = solar_radiation_sr["Gb(i)"] + solar_radiation_sr["Gd(i)"] + solar_radiation_sr["Gr(i)"]
    climate["Solar Radiation (North Wall)"] = solar_radiation_nw["Gb(i)"] + solar_radiation_nw["Gd(i)"] + solar_radiation_nw["Gr(i)"]
    climate["Solar Radiation (South Wall)"] = solar_radiation_sw["Gb(i)"] + solar_radiation_sw["Gd(i)"] + solar_radiation_sw["Gr(i)"]
    climate["Solar Radiation (East Wall)"] = solar_radiation_ew["Gb(i)"] + solar_radiation_ew["Gd(i)"] + solar_radiation_ew["Gr(i)"]
    climate["Solar Radiation (West Wall)"] = solar_radiation_ww["Gb(i)"] + solar_radiation_ww["Gd(i)"] + solar_radiation_ww["Gr(i)"]

    climate["Clear Sky Emissivity"] = 0.787+0.7641*np.log((climate["TDP"]+273.15)/273)
    climate["Cloud Sky Emissivity"] = (1 + (0.0224**climate["CF"]) - (0.0035 * (climate["CF"]**2)) +
                                        (0.00028 * (climate["CF"]**3)))*climate["Clear Sky Emissivity"]
    climate["Tsky"] = climate["Temperature K"] * (climate["Cloud Sky Emissivity"]**0.25)

    #climate = read_csv("CSV Inputs/Climate.csv")
    climate.to_csv("climateDF.csv")
    climate.to_json("climateDF.json")

    crop_data = read_csv("CSV Inputs/Crop_Data.csv")
    # crop_data.loc["Extinction Coefficient", "Value"] = 0.7
    # crop_data.loc["Leaf Transmission Coefficient", "Value"] = 0.1
    # crop_data.loc["a", "Value"] = 8.95e-5
    # crop_data.loc["b", "Value"] = 0.021
    # crop_data.loc["Leaf PAR use efficiency", "Value"] = 2.11e-5
    # crop_data.loc["CO2 Density stp", "Value"] = 1.87
    # crop_data.loc["Dark Respiration Rate", "Value"] = 4e-8
    # crop_data.loc["Stem Density", "Value"] = 2.5
    crop_data.loc["Leaf Area Index", "Value"] = crop_data.loc["Stem Density", "Value"] * 0.91

    op_enviro = read_csv("CSV Inputs/Operation_Enviromental.csv")
    op_temp = read_csv("CSV Inputs/Operation_Temperature.csv")
    op_light = read_csv("CSV Inputs/Operation_Lighting.csv")
    op_co2 = read_csv("CSV Inputs/Operation_CO2.csv")

    #global_assump = read_csv("CSV Inputs/GlobalAssumptions.csv")

    # Greenhouse Model inter dependant calcs
    gm_d.loc["Max Height", "Value"] = (gm_d.loc["Wall height", "Value"] + (gm_d.loc["Width", "Value"] / 2) *
                                       math.tan(rad(gm_d.loc["Roof angle", "Value"])))

    gm_d.loc["Floor Area", "Value"] = gm_d.loc["Length", "Value"] * gm_d.loc["Width", "Value"]

    gm_d.loc["South Wall Area", "Value"] = gm_d.loc["Length", "Value"] * gm_d.loc["Wall height", "Value"]
    gm_d.loc["North Wall Area", "Value"] = gm_d.loc["Length", "Value"] * gm_d.loc["Wall height", "Value"]

    gm_d.loc["East Wall Area", "Value"] = (gm_d.loc["Width", "Value"] * gm_d.loc["Wall height", "Value"] +
                                           ((gm_d.loc["Width", "Value"] / 2) * (gm_d.loc["Max Height", "Value"] -
                                                                                gm_d.loc["Wall height", "Value"])))

    gm_d.loc["West Wall Area", "Value"] = (gm_d.loc["Width", "Value"] * gm_d.loc["Wall height", "Value"] +
                                             ((gm_d.loc["Width", "Value"] / 2) * (gm_d.loc["Max Height", "Value"] -
                                              gm_d.loc["Wall height", "Value"])))

    gm_d.loc["South Roof Area", "Value"] = gm_d.loc["Length", "Value"] * ((gm_d.loc["Width", "Value"] / 2) /
                                                                          math.cos(rad(gm_d.loc["Roof angle", "Value"])))

    gm_d.loc["North Roof Area", "Value"] = gm_d.loc["Length", "Value"] * ((gm_d.loc["Width", "Value"] / 2) /
                                                                          math.cos(rad(gm_d.loc["Roof angle", "Value"])))

    gm_d.loc["Total Area of Glass", "Value"] = (gm_d.loc["South Roof Area", "Value"] +
                                                gm_d.loc["North Roof Area", "Value"] +
                                                gm_d.loc["South Wall Area", "Value"] +
                                                gm_d.loc["North Wall Area", "Value"] +
                                                gm_d.loc["East Wall Area", "Value"] +
                                                gm_d.loc["West Wall Area", "Value"])

    gm_d.loc["Greenhouse Volume", "Value"] = (gm_d.loc["Floor Area", "Value"] * gm_d.loc["Max Height", "Value"] -
                                              (gm_d.loc["Width", "Value"] / 4) *
                                              (gm_d.loc["Max Height", "Value"] - gm_d.loc["Wall height", "Value"]) *
                                              gm_d.loc["Length", "Value"])

    gm_d.loc["Total Roof Area", "Value"] = gm_d.loc["South Roof Area", "Value"] + gm_d.loc["North Roof Area", "Value"]

    gm_d.loc["Total Wall Area", "Value"] = (gm_d.loc["South Wall Area", "Value"] + gm_d.loc["North Wall Area", "Value"]
                                            + gm_d.loc["East Wall Area", "Value"] + gm_d.loc["West Wall Area", "Value"])

    gm_d.loc["Greenhouse Perimeter", "Value"] = 2 * gm_d.loc["Width", "Value"] + 2 * gm_d.loc["Length", "Value"]

    gm_r.loc["Characteristic Length Surface", "Value"] = gm_d.loc["South Roof Area", "Value"] / (
                2 * ((gm_d.loc["Width", "Value"] / 2) / math.cos(rad(gm_d.loc["Roof angle", "Value"]))) + 2 * gm_d.loc[
            "Length", "Value"])

    gm_r.loc["Characteristic Length", "Value"] = gm_r.loc["Material Thickness", "Value"]

    gm_r.loc["View Factor", "Value"] = (1 + math.cos(rad(gm_d.loc["Roof angle", "Value"]))) / 2

    gm_south.loc["View Factor", "Value"] = (1 + math.cos(rad(90))) / 2

    gm_side.loc["View Factor", "Value"] = (1 + math.cos(rad(90))) / 2

    gm_south.loc["Characteristic Length Surface", "Value"] = gm_d.loc["South Wall Area", "Value"] / (
                2 * gm_d.loc["Length", "Value"] + 2 * gm_d.loc["Wall height", "Value"])

    gm_south.loc["Characteristic Length", "Value"] = gm_south.loc["Material Thickness", "Value"]

    gm_side.loc["Characteristic Length Surface", "Value"] = gm_d.loc["East Wall Area", "Value"] / (
                2 * ((gm_d.loc["Width", "Value"] / 2) / math.cos(rad(gm_d.loc["Roof angle", "Value"]))) + (
                    2 * gm_d.loc["Wall height", "Value"]) + gm_d.loc["Width", "Value"])

    gm_side.loc["Characteristic Length", "Value"] = gm_side.loc["Material Thickness", "Value"]

    gm_north.loc["Characteristic Length Surface", "Value"] = gm_d.loc["South Wall Area", "Value"] / (
                2 * gm_d.loc["Length", "Value"] + 2 * gm_d.loc["Wall height", "Value"])

    gm_north.loc["Characteristic Length", "Value"] = gm_north.loc["Total Material Thickness", "Value"]

    #Operational Temperature inter dependant calcs
    op_temp_sp= pd.DataFrame(index=climate.index)
    op_temp_sp["Temperature C"] = np.where(
        (op_temp_sp.index.hour >= op_temp.loc["Daytime Start Hour", "Value"]) &
        (op_temp_sp.index.hour < op_temp.loc["Nighttime Start Hour", "Value"]),
        op_temp.loc["Set-point Daytime Temperature", "Value"],
        op_temp.loc["Set-point Nighttime Temperature", "Value"]
    )
    op_temp_sp["Temperature K"] = op_temp_sp["Temperature C"] + 273.15

    # Global Assumptions inter dependant calcs
    global_assump = pd.DataFrame(index=range(1))
    global_assump.loc["Thermal Conductivity of Air", "Value"] = 0.0255
    global_assump.loc["Stefan-Boltzmann Constant", "Value"] = 5.67e-8
    global_assump.loc["Sky View Factor", "Value"] = 1
    global_assump.loc["Emissivity of plants", "Value"] = 0.9
    global_assump.loc["Acceleration due to gravity", "Value"] = 9.81
    global_assump.loc["Dynamic Viscosity of Air", "Value"] = 1.825e-5
    global_assump.loc["Specific Heat of Air", "Value"] = 1005
    global_assump.loc["Air Density", "Value"] = 1.225

    x = (gm_d.loc["South Roof Area", "Value"] + gm_d.loc["North Roof Area", "Value"]) * gm_r.loc[
        "Long-wave Transmissivity", "Value"]
    y = gm_d.loc["South Wall Area", "Value"] * gm_south.loc["Long-wave Transmissivity", "Value"]
    z = (gm_d.loc["East Wall Area", "Value"] + gm_d.loc["West Wall Area", "Value"]) * gm_side.loc[
        "Long-wave Transmissivity", "Value"]
    a = gm_d.loc["South Wall Area", "Value"] + gm_d.loc["East Wall Area", "Value"] + gm_d.loc[
        "West Wall Area", "Value"] + gm_d.loc["South Roof Area", "Value"] + gm_d.loc["North Roof Area", "Value"]
    global_assump.loc["Avg Transmissivity LW Radiation", "Value"] = (x + y + z) / a

    global_assump.loc["Atmospheric Pressure", "Value"] = 101325
    global_assump.loc["CO2 Density", "Value"] = 1.87
    global_assump.loc["Latent Heat of Water Vaporisation", "Value"] = 2.26e6
    global_assump.loc["Discount Factor", "Value"] = 0.05

    # Crop inter dependant calcs
    crop = pd.DataFrame(index=climate.index)
    crop["Solar Radiation in Greenhouse"] = (climate["Solar Radiation (South Roof)"] + climate["Solar Radiation (North Roof)"])  # Different to the Excel formula
    crop["Photosynthetically Active Solar Radiation"] = crop["Solar Radiation in Greenhouse"]*0.5*0.7/2
    avg_list = []

    for i in range(len(crop)):
        if i < 167:
            avg = crop["Photosynthetically Active Solar Radiation"][:167].mean()
        else:
            avg = crop["Photosynthetically Active Solar Radiation"][i-167:i].mean()

        avg_list.append(avg)

    crop["I StomCond"] = avg_list
    crop["Saturation Temperature of Water Vapour"] = 0.61078*(np.exp((17.27*op_temp_sp["Temperature C"])/(op_temp_sp["Temperature C"]+237.3)))*1000
    crop["Partial Pressure of Water Vapour"] = crop["Saturation Temperature of Water Vapour"]*(climate["Relative Humidity"]/100)
    crop["Plant Surface Area"] = crop_data.loc["Leaf Area Index", "Value"]*gm_d.loc["Floor Area", "Value"]
    crop["Saturated Humidity Ratio"] = 0.6219*(crop["Saturation Temperature of Water Vapour"]/(global_assump.loc["Atmospheric Pressure", "Value"]-crop["Saturation Temperature of Water Vapour"]))
    crop["Humidity Ratio"] = 0.6219*(crop["Partial Pressure of Water Vapour"]/(global_assump.loc["Atmospheric Pressure", "Value"]-crop["Partial Pressure of Water Vapour"]))
    crop["Aerodynamic Resistance"] = 220*((crop_data.loc["Characteristic Length of Leaf", "Value"]**0.2)/(op_enviro.loc["Indoor air Velocity", "Value"]**0.8))

    t = gm_r.loc["Solar Transmissivity", "Value"]
    i = (climate["Solar Radiation (South Roof)"] + climate["Solar Radiation (North Roof)"])/2
    crop["Stomatal Resistance"] = 200*(1+(1/np.exp(0.05*(t*i-50))))
    crop["Moisture Transfer Rate"] = crop["Plant Surface Area"]*global_assump.loc["Air Density", "Value"]*((crop["Saturated Humidity Ratio"]-crop["Humidity Ratio"])/(crop["Aerodynamic Resistance"]+crop["Stomatal Resistance"]))

    crop.to_json("cropDF.json")

    # Operational Controls inter dependant
    start_hour = op_temp.loc["Daytime Start Hour", "Value"]
    end_hour = op_temp.loc["Nighttime Start Hour", "Value"]
    value_if_true = op_temp.loc["Set-point Daytime Temperature", "Value"]
    value_if_false = op_temp.loc["Set-point Nighttime Temperature", "Value"]

    op_temp_sp.index = pd.to_datetime(op_temp_sp.index, dayfirst =True)
    op_temp_sp["Temperature C"] = np.where(
        (op_temp_sp.index.hour > start_hour) & (op_temp_sp.index.hour < end_hour),
        value_if_true,
        value_if_false
    )
    op_temp_sp["Temperature K"] = op_temp_sp["Temperature C"] + 273.15

    # Saving dataframes for use in other files
    inputs_dataframe = {
        "gm_d": gm_d,
        "gm_r": gm_r,
        "gm_south": gm_south,
        "gm_side": gm_side,
        "gm_north": gm_north,
        "climate": climate,
        "crop": crop,
        "crop_data": crop_data,
        "op_enviro": op_enviro,
        "op_temp": op_temp,
        "op_temp_sp": op_temp_sp,
        "op_light": op_light,
        "op_co2": op_co2,
        "global_assump": global_assump,
    }

    return inputs_dataframe

if __name__ == "__main__":
    inputs_data = calculate_inputs()

