import pandas as pd
import numpy as np
from joblib import dump, load

class EnergySource:
    """
    Base class for different energy sources.
    """
    grid_emissions = 332  # kgCO₂ per MWh of electricity

    def __init__(self, heat_demand, light_demand, co2_demand):
        self._heat_demand = heat_demand["QnetMWh"].astype(float)  # Heat demand in MWh
        self._light_demand = light_demand["MWh"].astype(float)  # Light demand in MWh
        self._co2_demand = co2_demand["Total CO2 Demand"].astype(float)   # CO2 demand in kg
        self._co2_absorbed = co2_demand["Net Photosynthesis"].astype(float)  # CO2 absorbed by plants in kg

    def calculate_max_supply(self):
        raise NotImplementedError("Subclasses must implement demand calculations")

    def calculate_demand(self, x):
        raise NotImplementedError("Subclasses must implement demand calculations")


class CHP(EnergySource):
    gas_co2_per_Mwh = 184  # kgCO₂ per MWh of natural gas
    heat_to_electric_ratio = 1.51  # Heat to electric output ratio of CHP system from SEAI
    fuel_to_electric_efficiency = 0.333  # Efficiency of fuel to electricity conversion
    fuel_to_heat_efficiency = heat_to_electric_ratio / (1 / fuel_to_electric_efficiency) # Efficiency of fuel to heat conversion
    cc_power = 0.16  # Percentage of CHP power used for carbon capture
    cc_efficiency = 0.96  # Efficiency of CO2 capture
    capacity_factor = 0.9  # Capacity factor of CHP system

    def calculate_max_supply(self):
        df = pd.DataFrame(index=self._heat_demand.index)
        df["Fuel for Light"] = (self._safe_divide(self._light_demand, self.fuel_to_electric_efficiency)
                                * (1+self.cc_power))  # Fuel required for light
        df["Fuel for Heat"] = self._safe_divide(self._heat_demand, self.fuel_to_heat_efficiency)  # Fuel required for heat
        df["Fuel for CO2"] = self._safe_divide(self._co2_demand, self.gas_co2_per_Mwh) / self.cc_efficiency # Fuel required for CO2 capture
        df["Max Fuel Requirement"] = df.max(axis=1)  # Finds the driver for fuel requirement for each hour
        df["Primary Driver"] = df[["Fuel for Light", "Fuel for Heat", "Fuel for CO2"]].idxmax(axis=1)  # IDs the driver for fuel requirement

        # Rated power of CHP system for peak demand + CC power + 10% safety margin
        # Max power is calculated as the maximum fuel requirement * efficiency * safety margin
        chp_max_power = max(df["Fuel for Heat"].max() * self.fuel_to_electric_efficiency,
                            max(df["Fuel for Light"].max() * self.fuel_to_electric_efficiency,
                            df["Fuel for CO2"].max() * self.fuel_to_electric_efficiency))
        #chp_max_power = df["Max Fuel Requirement"].max() * self.fuel_to_heat_efficiency

        return df, chp_max_power

    def calculate_supply(self, x, chp_max_power, chp_df):
        df = pd.DataFrame(index=self._heat_demand.index)
        df["Fuel Requirement"] = chp_df["Max Fuel Requirement"] * x / chp_max_power

        df["Direct CO2 Emissions"] = df["Fuel Requirement"] * self.gas_co2_per_Mwh  # CO2 emissions from CHP system
        df["Related CO2 Emissions"] = 0
        df["Net CO2 Emissions"] = df["Direct CO2 Emissions"] + df["Related CO2 Emissions"] - self._co2_absorbed  # Net CO2 emissions from CHP system

        # Total yearly electricity output from CHP system in MWh
        df["Yearly Electricity Output"] = df["Fuel Requirement"] * self.fuel_to_electric_efficiency

        return df

    @staticmethod
    def _safe_divide(numerator, denominator):
        """
        This is used for dividing two arrays element-wise, with a check for division by zero.
        If there is a division by zero, the result is set to zero so that Nan values are not returned  .
        """
        numerator, denominator = np.broadcast_arrays(numerator, denominator)
        result = np.zeros_like(numerator, dtype=float)
        mask = denominator != 0
        result[mask] = numerator[mask] / denominator[mask]
        return result


class Geothermal(EnergySource):
    cop = 5.5  # Coefficient of performance of geothermal system (Taken from Excel)

    def calculate_max_supply(self):
        df = pd.DataFrame(index=self._heat_demand.index)

        # Rated power of geothermal system for peak demand + 10% safety margin
        geo_max_power = self._heat_demand.max()



        return df, geo_max_power

    def calculate_supply(self, x, geo_max_power):
        df = pd.DataFrame(index=self._heat_demand.index)
        df["Electricity for Heat"] = self._heat_demand / self.cop * x / geo_max_power  # Electricity required for heat
        df["Direct CO2 Emissions"] = 0  # No CO2 emissions as it is geothermal
        df["Related CO2 Emissions"] = self.grid_emissions * df[
            "Electricity for Heat"]  # CO2 emissions from geothermal system
        df["Net CO2 Emissions"] = df["Direct CO2 Emissions"] + df["Related CO2 Emissions"]  # Net CO2 emissions from geothermal system
        # Total yearly heat energy output from geothermal system in MWh
        df["Yearly Heat Output"] = self._heat_demand * x / geo_max_power

        return df


class GSHP(EnergySource):
    cop = 3.5  # Coefficient of performance of GSHP system (Taken from Excel)

    def calculate_max_supply(self):
        df = pd.DataFrame(index=self._heat_demand.index)

        # Rated power of GSHP system for peak demand + 10% safety margin
        gshp_max_power = self._heat_demand.max()

        return df, gshp_max_power

    def calculate_supply(self, x, gshp_max_power):
        df = pd.DataFrame(index=self._heat_demand.index)

        df["Electricity for Heat"] = self._heat_demand / self.cop * x / gshp_max_power  # Electricity required for heat
        df["Direct CO2 Emissions"] = 0
        df["Related CO2 Emissions"] = self.grid_emissions * df["Electricity for Heat"]  # CO2 emissions from GSHP system
        df["Net CO2 Emissions"] = df["Direct CO2 Emissions"] + df["Related CO2 Emissions"]  # Net CO2 emissions from GSHP system
        # Total yearly heat energy output from GSHP system in MWh
        df["Yearly Heat Output"] = self._heat_demand * x / gshp_max_power

        return df


class WasteHeat(EnergySource):
    exchanger_efficiency = 0.93  # SEAI Steam Systems

    def calculate_max_supply(self):
        df = pd.DataFrame(index=self._heat_demand.index)

        # Rated power of waste heat system for peak demand + 10% safety margin
        wasteheat_max_power = self._heat_demand.max() / self.exchanger_efficiency

        return df, wasteheat_max_power

    def calculate_supply(self, x, wasteheat_max_power):
        df = pd.DataFrame(index=self._heat_demand.index)
        df["Steam Required"] = self._heat_demand / self.exchanger_efficiency * x / wasteheat_max_power  # Heat from steam required to meet demand
        df["Direct CO2 Emissions"] = 0  # No CO2 emissions as it is waste heat
        df["Related CO2 Emissions"] = ((df["Steam Required"] / 0.37) / 2.78) * 425   # (heat demand / W-T_H Efficiency) * LHV/tonne of waste * kgCO2/tonne of waste
        df["Net CO2 Emissions"] = df["Direct CO2 Emissions"] + df["Related CO2 Emissions"]  # Net CO2 emissions from waste heat system
        # Total yearly heat energy output from waste heat system in MWh
        df["Yearly Heat Output"] = self._heat_demand * x / wasteheat_max_power

        return df


class SolarPV(EnergySource):
    capacity_factor = 0.127  # Capacity factor of solar (Taken from Renewables.ninja for North Dublin)

    def calculate_max_supply(self):
        df = pd.DataFrame(index=self._heat_demand.index)
        df["Electricity for Light"] = self._light_demand  # No conversion required for solar
        df["CO2 Emissions"] = 0  # Zero CO2 emissions from solar

        # Rated power of solar system for peak demand + 10% safety margin
        # This could be improved using battery storage and yearly profile of solar capacity factor
        solar_max_power = self._light_demand.max() / self.capacity_factor

        return df, solar_max_power

    def calculate_supply(self, x, solar_max_power):
        df = pd.DataFrame(index=self._heat_demand.index)

        df["Direct CO2 Emissions"] = 0  # Zero CO2 emissions from solar
        df["Related CO2 Emissions"] = 0
        df["Net CO2 Emissions"] = df["Direct CO2 Emissions"] + df["Related CO2 Emissions"]  # Net CO2 emissions from solar system
        # Total yearly electricity output from solar system in MWh
        df["Yearly Electricity Output"] = self._light_demand * x / solar_max_power

        return df


class Grid(EnergySource):
    def calculate_max_supply(self):
        df = pd.DataFrame(index=self._heat_demand.index)

        # Rated power of grid system for peak demand, no need for safety margin
        grid_max_power = self._light_demand.max()

        return df, grid_max_power

    def calculate_supply(self, x, grid_max_power):
        df = pd.DataFrame(index=self._heat_demand.index)

        df["Electricity for Light"] = self._light_demand * x/grid_max_power  # Electricity required for light
        df["Direct CO2 Emissions"] = 0  # Zero CO2 emissions from grid
        df["Related CO2 Emissions"] = self.grid_emissions * df["Electricity for Light"]
        df["Net CO2 Emissions"] = df["Direct CO2 Emissions"] + df["Related CO2 Emissions"]  # Net CO2 emissions from grid system
        # Total yearly electricity output from grid system in MWh
        df["Yearly Electricity Output"] = self._light_demand * x/grid_max_power

        return df


class Boiler(EnergySource):
    gas_co2_per_Mwh = 184  # kgCO₂ per MWh of natural gas
    fuel_to_heat_efficiency = 0.775  # Efficiency of fuel to heat conversion
    cc_efficiency = 0.96  # Efficiency of CO2 capture

    def calculate_max_supply(self):
        df = pd.DataFrame(index=self._heat_demand.index)
        df["Fuel for Heat"] = self._safe_divide(self._heat_demand,
                                                self.fuel_to_heat_efficiency)  # Fuel required for heat
        df["Fuel for CO2"] = self._safe_divide(self._co2_demand, self.gas_co2_per_Mwh) / self.cc_efficiency  # Fuel required for CO2 capture
        df["Max Fuel Requirement"] = df.max(axis=1)  # Finds the driver for fuel requirement for each hour
        df["Primary Driver"] = df[["Fuel for Heat", "Fuel for CO2"]].idxmax(axis=1)  # IDs the driver for fuel requirement

        # Rated power of CHP system for peak demand + CC power + 10% safety margin
        # Max power is calculated as the maximum fuel requirement * efficiency * safety margin
        boiler_max_power = max(df["Fuel for Heat"].max() * self.fuel_to_heat_efficiency,
                               df["Fuel for CO2"].max() * self.fuel_to_heat_efficiency)

        return df, boiler_max_power

    def calculate_supply(self, x, boiler_max_power, boiler_df):
        df = pd.DataFrame(index=self._heat_demand.index)
        df["Fuel Requirement"] = boiler_df["Max Fuel Requirement"] * x/boiler_max_power
        df["Direct CO2 Emissions"] = df["Fuel Requirement"] * self.gas_co2_per_Mwh  # CO2 emissions from CHP system
        df["Related CO2 Emissions"] = 0
        df["Net CO2 Emissions"] = df["Direct CO2 Emissions"] + df["Related CO2 Emissions"] - self._co2_absorbed  # Net CO2 emissions from CHP system
        # Total yearly electricity output from CHP system in MWh
        df["Yearly Heat Output"] = df["Fuel Requirement"] * self.fuel_to_heat_efficiency

        return df

    @staticmethod
    def _safe_divide(numerator, denominator):
        """
        This is used for dividing two arrays element-wise, with a check for division by zero.
        If there is a division by zero, the result is set to zero.
        """
        numerator, denominator = np.broadcast_arrays(numerator, denominator)
        result = np.zeros_like(numerator, dtype=float)
        mask = denominator != 0
        result[mask] = numerator[mask] / denominator[mask]
        return result


class CO2Import(EnergySource):

    def calculate_max_supply(self):
        df = pd.DataFrame(index=self._heat_demand.index)

        co2_max_power = self._co2_demand.max()

        return df, co2_max_power

    def calculate_supply(self, x, co2_max_power):
        df = pd.DataFrame(index=self._heat_demand.index)
        df["CO2 Requirement"] = self._co2_demand * x / co2_max_power  # CO2 emissions from CO2 import
        df["Direct CO2 Emissions"] = 0  # Zero CO2 emissions from CO2 import
        df["Related CO2 Emissions"] = df["CO2 Requirement"] * x / co2_max_power  # CO2 emissions from CO2 import
        df["Net CO2 Emissions"] = df["Direct CO2 Emissions"] + df["Related CO2 Emissions"] - self._co2_absorbed # Net CO2 emissions from CO2 import

        return df


if __name__ == "__main__":
    heat_demand = pd.read_json("heat_demand.json")
    light_demand = pd.read_json("light_demand.json")
    co2_demand = pd.read_json("co2_demand.json")

    max_heat = heat_demand["QnetMWh"].max()

    chp_max_supply, chp_max_power = CHP(heat_demand, light_demand, co2_demand).calculate_max_supply()
    chp_supply = CHP(heat_demand, light_demand, co2_demand).calculate_supply(chp_max_power, chp_max_power, chp_max_supply)

    chp_co2_power = chp_max_supply["Fuel for CO2"].max() * CHP.fuel_to_electric_efficiency
    chp_light_power = chp_max_supply["Fuel for Light"].max() * CHP.fuel_to_electric_efficiency

    chp2_max_supply, chp2_max_power = CHP(heat_demand, light_demand, co2_demand).calculate_max_supply()
    chp2_supply = CHP(heat_demand, light_demand, co2_demand).calculate_supply(0.057, chp2_max_power, chp2_max_supply)
    max_co2 = co2_demand["Total CO2 Demand"].max()
    max_co2_supply = 0.057 / 0.333 * 184 * 0.96

    geothermal_demand, geo_max_power = Geothermal(heat_demand, light_demand, co2_demand).calculate_max_supply()
    geothermal_supply = Geothermal(heat_demand, light_demand, co2_demand).calculate_supply(geo_max_power, geo_max_power)

    gshp_demand, gshp_max_power = GSHP(heat_demand, light_demand, co2_demand).calculate_max_supply()
    gshp_supply = GSHP(heat_demand, light_demand, co2_demand).calculate_supply(0.121, gshp_max_power)

    wasteheat_demand, wasteheat_max_power = WasteHeat(heat_demand, light_demand, co2_demand).calculate_max_supply()
    wasteheat_supply = WasteHeat(heat_demand, light_demand, co2_demand).calculate_supply(wasteheat_max_power, wasteheat_max_power)

    solar_demand, solar_max_power = SolarPV(heat_demand, light_demand, co2_demand).calculate_max_supply()
    solar_supply = SolarPV(heat_demand, light_demand, co2_demand).calculate_supply(solar_max_power, solar_max_power)

    grid_demand, grid_max_power = Grid(heat_demand, light_demand, co2_demand).calculate_max_supply()
    grid_supply = Grid(heat_demand, light_demand, co2_demand).calculate_supply(0.032, grid_max_power)

    boiler_demand, boiler_max_power = Boiler(heat_demand, light_demand, co2_demand).calculate_max_supply()
    boiler_supply = Boiler(heat_demand, light_demand, co2_demand).calculate_supply(boiler_max_power, boiler_max_power, boiler_demand)
    boiler_max_power2 = max(boiler_demand["Fuel for Heat"].max() * Boiler.fuel_to_heat_efficiency,
                            boiler_demand["Fuel for CO2"].max() / (Boiler.gas_co2_per_Mwh / Boiler.cc_efficiency))

    boiler_co2_demand = boiler_demand["Fuel for CO2"].max() * Boiler.fuel_to_heat_efficiency

    co2_import_demand, co2_max_power = CO2Import(heat_demand, light_demand, co2_demand).calculate_max_supply()
    co2_import_supply = CO2Import(heat_demand, light_demand, co2_demand).calculate_supply(co2_max_power, co2_max_power)

    total_emissions = chp_supply["Net CO2 Emissions"].sum()
