import pandas as pd
import numpy as np
from joblib import dump, load
import Lib.EnergyDemand


class Source:
    """Base class for energy sources."""

    def __init__(self, capital_cost, base_capex, operational_cost, fuel_cost, power, energy_output, fuel_requirement, cc_power,
                 lifetime, loan_term, co2_emissions):

        self.base_capex = base_capex
        self.capital_cost = capital_cost  # CAPEX per MW installed capacity (greenspec.co.uk, £900/kW)
        self.operational_cost = operational_cost  # Opex per MWh
        self.fuel_cost = fuel_cost  # Cost of fuel per MWh or cost of electricity per kWh
        self.power = power  # kW
        self.energy_output = energy_output  # MWh
        self.fuel_requirement = fuel_requirement  # MWh
        self.cc_power = cc_power  # Percentage of power used for Carbon Capture
        self.construction_time = 1  # years
        self.decommission_time = 1  # years
        self.lifetime = lifetime  # years of useful life
        self.discount_rate = 0.05
        self.loan_rate = 0.035
        self.loan_term = loan_term
        self.co2_emissions = co2_emissions
        self.co2_tax = 0.056  # €/kg
        self.evaluation_period = 50  # years


    def constant_cost(self):
        """
        Calculate the constant costs of the energy source over its lifetime. This includes CAPEX and OPEX.
        Applicable to all energy sources.
        """
        # Create a DataFrame with years as index
        years = range(0, self.evaluation_period)
        costs_df = pd.DataFrame(index=years, columns=['CAPEX', 'OPEX', 'Fuel', 'CO2 Tax', 'Total Cost'])

        # Calculate CAPEX
        capex = self.power * self.capital_cost

        # Calculate Annual Opex
        # OPEX (Euro) = Operational cost (Euro/MWh) * Energy output (MWh)
        opex = self.operational_cost * self.energy_output

        # Calculate fuel cost per year
        fuel = self.fuel_requirement * self.fuel_cost

        # CO2 Tax
        co2_tax = self.co2_emissions * self.co2_tax

        capex_eac = capex * (self.discount_rate / (1 - (1 + self.discount_rate) ** -self.lifetime))

        eac = capex * (self.discount_rate / (1 - (1 + self.discount_rate) ** -self.lifetime)) + opex + fuel + co2_tax

        lifetime_cost = eac

        costs_df['CAPEX'] = capex_eac
        costs_df['OPEX'] = opex
        costs_df['Fuel'] = fuel
        costs_df['CO2 Tax'] = co2_tax
        costs_df['Total Cost'] = costs_df['CAPEX'] + costs_df['OPEX'] + costs_df['Fuel'] + costs_df['CO2 Tax']

        return capex_eac, opex, fuel, co2_tax, lifetime_cost, costs_df, eac


class CHP(Source):
    """Class for Combined Heat and Power (CHP) systems."""

    pass  # Inherits everything from EnergySource


class GSHP(Source):
    """Class for Ground Source Heat Pump (GSHP) systems."""

    pass  # Inherits everything from EnergySource


class Geothermal(Source):
    """Class for Geothermal energy systems."""

    pass  # Inherits everything from EnergySource


class Grid(Source):
    """Class for Grid Electricity."""
    pass  # Inherits everything from EnergySource


class WasteHeat(Source):
    """Class for Waste Heat systems."""
    pass  # Inherits everything from EnergySource


class SolarPV(Source):
    """Class for Solar Photovoltaic systems."""
    pass  # Inherits everything from EnergySource


class Boiler(Source):
    """Class for Boilers"""

    pass  # Inherits everything from EnergySource


class CO2Import(Source):
    """Class for importing CO2"""

    pass  # Inherits


# Example usage:
if __name__ == "__main__":

    heat_demand = pd.read_json("heat_demand.json")
    light_demand = pd.read_json("light_demand.json")
    co2_demand = pd.read_json("co2_demand.json")

    # co2_demand = calculate_co2demand(inputs, htc, heat_demand, light_demand)

    chp_demand, chp_max_power = Lib.EnergyDemand.CHP(heat_demand, light_demand, co2_demand).calculate_max_supply()
    chp_supply = Lib.EnergyDemand.CHP(heat_demand, light_demand, co2_demand).calculate_supply(chp_max_power, chp_max_power, chp_demand)
    chp_fuel = chp_supply["Fuel Requirement"].sum()
    energy_output = chp_supply["Yearly Electricity Output"].sum()
    co2_emissions = chp_supply["Direct CO2 Emissions"].sum()

    print("\nCreating CHP instance...")
    chp = CHP(capital_cost=1.2e6*chp_max_power**-0.4,
              operational_cost=9.3,
              fuel_cost=90.1,
              base_capex=0,
              lifetime=25,
              power=chp_max_power,
              energy_output=energy_output,
              fuel_requirement=chp_fuel,
              cc_power=0.16,
              loan_term=20,
              co2_emissions=co2_emissions)

    print("\nCalculating CHP cost...")
    chp_capex_npv, chp_opex_npv, chp_fuel_npv, chp_co2_tax, chp_lifetime_cost, chp_yearly_costs, chp_lcoe = chp.constant_cost()

    geothermal_demand, geo_max_power = Lib.EnergyDemand.Geothermal(heat_demand, light_demand, co2_demand).calculate_max_supply()
    geo_supply = Lib.EnergyDemand.Geothermal(heat_demand, light_demand, co2_demand).calculate_supply(geo_max_power, geo_max_power)
    geothermal_electricity = geo_supply["Electricity for Heat"].sum()
    geo_energy_output = geo_supply["Yearly Heat Output"].sum()
    co2_emissions = geo_supply["Direct CO2 Emissions"].sum()

    geothermal = Geothermal(capital_cost=2.89e6*geo_max_power**-0.45+2.1e6,
                            operational_cost=11000*geo_max_power/geo_energy_output,
                            fuel_cost=228.1,
                            lifetime=30,
                            power=geo_max_power,
                            energy_output=geo_energy_output,
                            base_capex=0, fuel_requirement=geothermal_electricity,
                            cc_power=0,
                            loan_term=20,
                            co2_emissions=co2_emissions)

    (geo_capex_npv, geo_opex_npv, geo_fuel_npv, geo_co2_tax, geo_lifetime_cost, geo_yearly_costs,
     geo_lcoe) = geothermal.constant_cost()

    gshp_demand, gshp_max_power = Lib.EnergyDemand.GSHP(heat_demand, light_demand, co2_demand).calculate_max_supply()
    gshp_supply = Lib.EnergyDemand.GSHP(heat_demand, light_demand, co2_demand).calculate_supply(gshp_max_power, gshp_max_power)
    gshp_fuel = gshp_supply["Electricity for Heat"].sum()
    gshp_energy_output = gshp_supply["Yearly Heat Output"].sum()
    co2_emissions = gshp_supply["Direct CO2 Emissions"].sum()

    gshp = GSHP(capital_cost=1297000*gshp_max_power**-0.21557,
                operational_cost=8000*gshp_max_power/gshp_energy_output,
                fuel_cost=228.1,
                lifetime=25,
                power=gshp_max_power,
                energy_output=gshp_energy_output,
                fuel_requirement=gshp_fuel,
                base_capex=0,
                cc_power=0,
                loan_term=20,
                co2_emissions=co2_emissions)

    (gshp_capex_npv, gshp_opex_npv, gshp_fuel_npv, gshp_co2_tax, gshp_lifetime_cost, gshp_yearly_costs,
     gshp_lcoe) = gshp.constant_cost()

    grid_demand, grid_max_power = Lib.EnergyDemand.Grid(heat_demand, light_demand, co2_demand).calculate_max_supply()
    grid_supply = Lib.EnergyDemand.Grid(heat_demand, light_demand, co2_demand).calculate_supply(grid_max_power, grid_max_power)
    grid_fuel = grid_supply["Electricity for Light"].sum()
    grid_energy_output = grid_supply["Yearly Electricity Output"].sum()
    co2_emissions = grid_supply["Direct CO2 Emissions"].sum()

    grid = Grid(capital_cost=0,
                operational_cost=0,
                fuel_cost=228.1,
                lifetime=50,
                power=grid_max_power,
                energy_output=grid_energy_output,
                fuel_requirement=grid_fuel,
                base_capex=0,
                cc_power=0,
                loan_term=20,
                co2_emissions=co2_emissions)

    grid_capex_npv, grid_opex_npv, grid_fuel_npv, grid_co2_tax, grid_lifetime_cost, grid_yearly_costs, grid_lcoe = grid.constant_cost()

    wasteheat_demand, wasteheat_max_power = Lib.EnergyDemand.WasteHeat(heat_demand, light_demand, co2_demand).calculate_max_supply()
    wasteheat_supply = Lib.EnergyDemand.WasteHeat(heat_demand, light_demand, co2_demand).calculate_supply(wasteheat_max_power, wasteheat_max_power)
    waseteheat_fuel = wasteheat_supply["Steam Required"].sum()
    waste_energy_output = wasteheat_supply["Yearly Heat Output"].sum()
    co2_emissions = wasteheat_supply["Direct CO2 Emissions"].sum()

    wasteheat = WasteHeat(capital_cost=0,
                          operational_cost=0,
                          fuel_cost=90.1*0.9,
                          lifetime=50,
                          power=wasteheat_max_power,
                          energy_output=waste_energy_output,
                          fuel_requirement=waseteheat_fuel,
                          base_capex=0,
                          cc_power=0,
                          loan_term=20,
                          co2_emissions=co2_emissions)

    (wasteheat_capex_npv, wasteheat_opex_npv, wasteheat_fuel_npv, wasteheat_co2_tax, wasteheat_lifetime_cost, wasteheat_yearly_costs,
     wasteheat_lcoe) = wasteheat.constant_cost()

    solar_demand, solar_max_power = Lib.EnergyDemand.SolarPV(heat_demand, light_demand, co2_demand).calculate_max_supply()
    solar_supply = Lib.EnergyDemand.SolarPV(heat_demand, light_demand, co2_demand).calculate_supply(solar_max_power, solar_max_power)
    solar_energy_output = solar_supply["Yearly Electricity Output"].sum()
    co2_emissions = solar_supply["Direct CO2 Emissions"].sum()

    solar = SolarPV(capital_cost=1.572e6*solar_max_power**-0.15-1.5e5,
                    operational_cost=12000*solar_max_power/solar_energy_output,
                    fuel_cost=0,
                    lifetime=30,
                    power=solar_max_power,
                    energy_output=solar_energy_output,
                    fuel_requirement=0,
                    base_capex=0,
                    cc_power=0,
                    loan_term=20,
                    co2_emissions=co2_emissions)

    (solar_capex_npv, solar_opex_npv, solar_fuel_npv, solar_co2_tax, solar_lifetime_cost, solar_yearly_costs,
     solar_lcoe) = solar.constant_cost()

    boiler_demand, boiler_max_power = Lib.EnergyDemand.Boiler(heat_demand, light_demand, co2_demand).calculate_max_supply()
    boiler_supply = Lib.EnergyDemand.Boiler(heat_demand, light_demand, co2_demand).calculate_supply(boiler_max_power, boiler_max_power, boiler_demand)
    boiler_fuel = boiler_supply["Fuel Requirement"].sum()
    boiler_energy_output = boiler_supply["Yearly Heat Output"].sum()
    co2_emissions = boiler_supply["Direct CO2 Emissions"].sum()

    boilers = Boiler(capital_cost=103000*boiler_max_power**-0.17,
                     operational_cost=3900*boiler_max_power/boiler_energy_output,
                     fuel_cost=90.1,
                     lifetime=25,
                     power=boiler_max_power,
                     energy_output=boiler_energy_output,
                     fuel_requirement=boiler_fuel,
                     base_capex=0,
                     cc_power=0.16,
                     loan_term=20,
                     co2_emissions=co2_emissions)

    (boiler_capex_npv, boiler_opex_npv, boiler_fuel_npv, boiler_co2_tax, boiler_lifetime_cost, boiler_yearly_costs,
     boiler_lcoe) = boilers.constant_cost()

    co2_max_demand, co2_max_power = Lib.EnergyDemand.CO2Import(heat_demand, light_demand, co2_demand).calculate_max_supply()
    co2_supply = Lib.EnergyDemand.CO2Import(heat_demand, light_demand, co2_demand).calculate_supply(co2_max_power, co2_max_power)
    co2_fuel = co2_supply["CO2 Requirement"].sum()
    co2_emissions = co2_supply["Direct CO2 Emissions"].sum()

    co2 = CO2Import(capital_cost=0,
                    operational_cost=0,
                    fuel_cost=0.14678,
                    lifetime=50,
                    power=co2_max_power,
                    energy_output=co2_fuel,
                    fuel_requirement=co2_fuel,
                    base_capex=0,
                    cc_power=0,
                    loan_term=20,
                    co2_emissions=co2_emissions)

    co2_capex_npv, co2_opex_npv, co2_fuel_npv, co2_c02_tax, co2_lifetime_cost, co2_yearly_costs, co2_lcoe = co2.constant_cost()

    cheapest = min(chp_lifetime_cost, geo_lifetime_cost, gshp_lifetime_cost, grid_lifetime_cost, wasteheat_lifetime_cost, solar_lifetime_cost)
    print("\nCheapest energy source: ", cheapest)

    costsDF = pd.DataFrame({
        'Energy Source': ['CHP', 'Geothermal', 'GSHP', 'Grid', 'Waste Heat', 'Solar PV', 'Boiler', 'CO2 Import'],
        'CAPEX': [chp_capex_npv, geo_capex_npv, gshp_capex_npv, grid_capex_npv, wasteheat_capex_npv, solar_capex_npv, boiler_capex_npv, co2_capex_npv],
        'OPEX': [chp_opex_npv, geo_opex_npv, gshp_opex_npv, grid_opex_npv, wasteheat_opex_npv, solar_opex_npv, boiler_opex_npv, co2_opex_npv],
        'Fuel Cost': [chp_fuel_npv, geo_fuel_npv, gshp_fuel_npv, grid_fuel_npv, wasteheat_fuel_npv, solar_fuel_npv, boiler_fuel_npv, co2_fuel_npv],
        'CO2 Tax': [chp_co2_tax, geo_co2_tax, gshp_co2_tax, grid_co2_tax, wasteheat_co2_tax, solar_co2_tax, boiler_co2_tax, co2_c02_tax],
        'Total Cost': [chp_lifetime_cost, geo_lifetime_cost, gshp_lifetime_cost, grid_lifetime_cost,
                       wasteheat_lifetime_cost, solar_lifetime_cost, boiler_lifetime_cost,
                       co2_lifetime_cost]
    })

    costsDF.to_json("costsDF_case2.json", orient="records", lines=True)
