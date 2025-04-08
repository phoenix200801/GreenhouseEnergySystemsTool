import matplotlib.pyplot as plt
import pandas as pd
from joblib import dump, load
import json

from InputCalculations import calculate_inputs
from HTCoefficients import calculate_htc
from HeatDemand import calculate_heatdemand
from LightDemand import calculate_lightdemand
from CO2Demand import calculate_co2demand
import EnergyDemand
from Optimise_dual_anealling import OptimizeEnergySources
import Cost


def run_demand_calculations():
    """Run initial demand calculations and display plots"""
    print("Running demand calculations...")

    # Load or calculate demands
    inputs_data = calculate_inputs()
    htc = calculate_htc(inputs_data)
    heat_demand = calculate_heatdemand(inputs_data, htc)
    light_demand = calculate_lightdemand(inputs_data, htc, heat_demand)
    co2_demand = calculate_co2demand(inputs_data, htc, heat_demand, light_demand)

    # Save results
    # Save results - convert DataFrames to serializable format
    # heat_demand.to_json('heat_demand.json')
    # light_demand.to_json('light_demand.json')
    # co2_demand.to_json('co2_demand.json')
    # with open('heat_demand.json', 'w') as f:
    #     json.dump(heat_demand.to_dict(orient='records'), f)
    # with open('light_demand.json', 'w') as f:
    #     json.dump(light_demand.to_dict(orient='records'), f)
    # with open('co2_demand.json', 'w') as f:
    #     json.dump(co2_demand.to_dict(orient='records'), f)

    return heat_demand, light_demand, co2_demand


def configure_energy_sources():
    """Allow user to configure available energy sources"""

    print("\n"
          "Please visit Met Eireann website for climate data:"
          "\n https://www.met.ie/climate/available-data/historical-data"
          "\n 1. Click Hourly Data, and select the station closest to your location"
          "\n 2. Click \"Download the full data series\" highlighted in blue"
          "\n 3. Save the file as 'ClimateData.csv' in the CSV inputs folder"
          "\n\n Next visit The European Commission's PVGIS website for solar radiation data:"
          "\n https://re.jrc.ec.europa.eu/pvg_tools/en/"
          "\n 1. Select the location of your greenhouse"
          "\n 2. Click Hourly Data"
          "\n 3. Change the Start Year to 2023 and the end year to 2023"
          "\n 4. Tick the box next to 'Radiation components'"
          "\n 5. Data will need to downloaded for each face of the greenhouse separately"
          "\n to do this entering the following inputs for 'Slope' and 'Azimuth':"
          "\n     Slope: 30, Azimuth: 0 (North Facing Roof)"
          "\n     Slope: 30, Azimuth: 180 (South Facing Roof)"
          "\n     Slope: 90, Azimuth: 0 (North Facing Wall)"
          "\n     Slope: 90, Azimuth: 90 (East Facing Wall)"
          "\n     Slope: 90, Azimuth: 180 (South Facing Wall)"
          "\n     Slope: 90, Azimuth: -90 (West Facing Wall)"
          "\n 6. Click Download CSV for each of the above configurations"
          "\n 7. Save the files as: \n    'SolarDataNR.csv' for North Roof\n    'SolarDataSR.csv' for South Roof"
          "\n    'SolarDataNW.csv' for North Wall\n    'SolarDataEW.csv' for East Wall\n    'SolarDataSW.csv' for "
          "South Wall"
          "\n    'SolarDataWW.csv' for West Wall\n    Save each file in the CSV inputs folder")

    input("\nPress Enter when you have downloaded and saved the files...")

    sources = {
        'CHP': True,
        'Geothermal': True,
        'GSHP': True,
        'Solar': True,
        'WasteHeat': True,
        'Grid': True,
        'Boiler': True,
        'CO2': True
    }

    print("\n    Energy Source Configuration: \n    Choose the energy sources available for your greenhouse.")
    print("    Enter 'y' to enable or 'n' to disable each source:")

    for source in sources:
        while True:
            response = input(f"    {source} available? (y/n): ").lower()
            if response in ['y', 'n']:
                sources[source] = (response == 'y')
                break
            print("Please enter 'y' or 'n'")

    return sources


def run_optimization(heat_demand, light_demand, co2_demand, source_config):
    """Run optimization with configured energy sources"""
    print("\nRunning optimization with selected energy sources...")

    # Create optimizer instance
    optimizer = OptimizeEnergySources(heat_demand, light_demand, co2_demand)

    # Store original max powers
    original_max_powers = {
        'chp_max_power': optimizer.chp_max_power,
        'geo_max_power': optimizer.geo_max_power,
        'gshp_max_power': optimizer.gshp_max_power,
        'solar_max_power': optimizer.solar_max_power,
        'wasteheat_max_power': optimizer.wasteheat_max_power,
        'grid_max_power': optimizer.grid_max_power,
        'boiler_max_power': optimizer.boiler_max_power,
        'co2_max_power': optimizer.co2_max_power
    }

    # Modify the optimizer's max_power attributes based on source configuration
    if not source_config['CHP']:
        optimizer.chp_max_power = 0.000001
    if not source_config['Geothermal']:
        optimizer.geo_max_power = 0.000001
    if not source_config['GSHP']:
        optimizer.gshp_max_power = 0.000001
    if not source_config['Solar']:
        optimizer.solar_max_power = 0.000001
    if not source_config['WasteHeat']:
        optimizer.wasteheat_max_power = 0.000001
    if not source_config['Grid']:
        optimizer.grid_max_power = 0.000001
    if not source_config['Boiler']:
        optimizer.boiler_max_power = 0.000001
    if not source_config['CO2']:
        optimizer.co2_max_power = 0.000001

    # Run optimization
    result = optimizer.optimize()

    return result, optimizer, original_max_powers


def main():
    # Step 1: Run demand calculations and show plots
    heat_demand, light_demand, co2_demand = run_demand_calculations()

    # Step 2: Configure energy sources
    source_config = configure_energy_sources()

    # Step 3: Run optimization
    print("\nRunning optimization with selected energy sources...")
    result, optimizer, original_max_powers = run_optimization(heat_demand, light_demand, co2_demand, source_config)

    # Get the best solution's breakdown
    best_capacities = {
        'CHP': float(result.x[0]),
        'Geothermal': float(result.x[1]),
        'GSHP': float(result.x[2]),
        'Solar': float(result.x[3]),
        'WasteHeat': float(result.x[4]),
        'Grid': float(result.x[5]),
        'Boiler': float(result.x[6]),
        'CO2': float(result.x[7])
    }

    print("\nOptimal Solution Breakdown:")
    print(f"Capacities:")
    for source, capacity in best_capacities.items():
        if capacity > 0.0001:  # Only show non-zero capacities
            unit = "kg/h" if source == "CO2" else "MW"
            print(f"{source}: {capacity:.4f} {unit}")

    # Calculate optimized costs for used technologies
    optimized_cost_components = {}

    # Initialize with zeros for every component to ensure the JSON structure is consistent
    for source in best_capacities.keys():
        optimized_cost_components[source] = {'capex': 0, 'opex': 0, 'fuel': 0, 'total': 0}

    # Calculate actual costs for enabled sources
    if best_capacities['CHP'] > 0:
        chp_cost = Cost.CHP(
            capital_cost=1.2e6 * best_capacities['CHP'] ** -0.4,
            base_capex=0,
            operational_cost=9.3,
            fuel_cost=90.1,
            power=best_capacities['CHP'],
            energy_output=optimizer.chp_supply["Yearly Electricity Output"].sum(),
            fuel_requirement=optimizer.chp_supply["Fuel Requirement"].sum(),
            cc_power=0.16,
            lifetime=25,
            loan_term=20,
            co2_emissions=optimizer.chp_supply["Direct CO2 Emissions"].sum()
        )
        capex, opex, fuel, co2_tax, total, _, _ = chp_cost.constant_cost()
        optimized_cost_components['CHP'] = {'capex': capex, 'opex': opex, 'fuel': fuel, 'co2_tax': co2_tax,
                                            'total': total}

    if best_capacities['Geothermal'] > 0:
        geo_cost = Cost.Geothermal(
            capital_cost=2890000 * best_capacities["Geothermal"] ** -0.45 + 1.2e6,
            base_capex=0,
            operational_cost=11000 * best_capacities["Geothermal"] /
                             optimizer.geo_supply["Yearly Heat Output"].sum(),
            fuel_cost=228.1,
            power=best_capacities['Geothermal'],
            energy_output=optimizer.geo_supply["Yearly Heat Output"].sum(),
            fuel_requirement=optimizer.geo_supply["Electricity for Heat"].sum(),
            cc_power=0,
            lifetime=30,
            loan_term=20,
            co2_emissions=optimizer.geo_supply["Direct CO2 Emissions"].sum()
        )
        capex, opex, fuel, co2_tax, total, _, _ = geo_cost.constant_cost()
        optimized_cost_components['Geothermal'] = {'capex': capex, 'opex': opex, 'fuel': fuel, 'co2_tax': co2_tax,
                                                   'total': total}

    # Continue with similar blocks for other technologies
    # GSHP, Solar, WasteHeat, Grid, Boiler, CO2

    if best_capacities['GSHP'] > 0:
        gshp_cost = Cost.GSHP(
            capital_cost=1297000 * best_capacities["GSHP"] ** -0.21557,
            base_capex=0,
            operational_cost=8000 * best_capacities["GSHP"] /
                             optimizer.gshp_supply["Yearly Heat Output"].sum(),
            fuel_cost=228.1,
            power=best_capacities['GSHP'],
            energy_output=optimizer.gshp_supply["Yearly Heat Output"].sum(),
            fuel_requirement=optimizer.gshp_supply["Electricity for Heat"].sum(),
            cc_power=0,
            lifetime=25,
            loan_term=20,
            co2_emissions=optimizer.gshp_supply["Direct CO2 Emissions"].sum()
        )
        capex, opex, fuel, co2_tax, total, _, _ = gshp_cost.constant_cost()
        optimized_cost_components['GSHP'] = {'capex': capex, 'opex': opex, 'fuel': fuel, 'co2_tax': co2_tax,
                                             'total': total}

    if best_capacities['Solar'] > 0:
        solar_cost = Cost.SolarPV(
            capital_cost=1.572e6 * best_capacities["Solar"] ** -0.15 - 1.5e6,
            base_capex=0,
            operational_cost=12000 * best_capacities["Solar"] /
                             optimizer.solar_supply["Yearly Electricity Output"].sum(),
            fuel_cost=0,
            power=best_capacities['Solar'],
            energy_output=optimizer.solar_supply["Yearly Electricity Output"].sum(),
            fuel_requirement=0,
            cc_power=0,
            lifetime=30,
            loan_term=20,
            co2_emissions=optimizer.solar_supply["Direct CO2 Emissions"].sum()
        )
        capex, opex, fuel, co2_tax, total, _, _ = solar_cost.constant_cost()
        optimized_cost_components['Solar'] = {'capex': capex, 'opex': opex, 'fuel': fuel, 'co2_tax': co2_tax,
                                              'total': total}

    if best_capacities['WasteHeat'] > 0:
        waste_cost = Cost.WasteHeat(
            capital_cost=0,
            base_capex=0,
            operational_cost=0,
            fuel_cost=90.1*0.9,
            power=best_capacities['WasteHeat'],
            energy_output=optimizer.wasteheat_supply["Yearly Heat Output"].sum(),
            fuel_requirement=optimizer.wasteheat_supply["Steam Required"].sum(),
            cc_power=0,
            lifetime=50,
            loan_term=20,
            co2_emissions=optimizer.wasteheat_supply["Direct CO2 Emissions"].sum()
        )
        capex, opex, fuel, co2_tax, total, _, _ = waste_cost.constant_cost()
        optimized_cost_components['WasteHeat'] = {'capex': capex, 'opex': opex, 'fuel': fuel, 'co2_tax': co2_tax,
                                                  'total': total}

    if best_capacities['Grid'] > 0:
        grid_cost = Cost.Grid(
            capital_cost=0,
            base_capex=0,
            operational_cost=0,
            fuel_cost=228.1,
            power=best_capacities['Grid'],
            energy_output=optimizer.grid_supply["Yearly Electricity Output"].sum(),
            fuel_requirement=optimizer.grid_supply["Electricity for Light"].sum(),
            cc_power=0,
            lifetime=50,
            loan_term=20,
            co2_emissions=optimizer.grid_supply["Direct CO2 Emissions"].sum()
        )
        capex, opex, fuel, co2_tax, total, _, _ = grid_cost.constant_cost()
        optimized_cost_components['Grid'] = {'capex': capex, 'opex': opex, 'fuel': fuel, 'co2_tax': co2_tax,
                                             'total': total}

    if best_capacities['Boiler'] > 0:
        boiler_cost = Cost.Boiler(
            capital_cost=1.03e5 * best_capacities["Boiler"] ** -0.17,
            base_capex=0,
            operational_cost=3900 * best_capacities["Boiler"] /
                             optimizer.boiler_supply["Yearly Heat Output"].sum(),
            fuel_cost=90.1,
            power=best_capacities['Boiler'],
            energy_output=optimizer.boiler_supply["Yearly Heat Output"].sum(),
            fuel_requirement=optimizer.boiler_supply["Fuel Requirement"].sum(),
            cc_power=0,
            lifetime=25,
            loan_term=20,
            co2_emissions=optimizer.boiler_supply["Direct CO2 Emissions"].sum()
        )
        capex, opex, fuel, co2_tax, total, _, _ = boiler_cost.constant_cost()
        optimized_cost_components['Boiler'] = {'capex': capex, 'opex': opex, 'fuel': fuel, 'co2_tax': co2_tax,
                                               'total': total}

    if best_capacities['CO2'] > 0:
        co2_cost = Cost.CO2Import(
            capital_cost=0,
            base_capex=0,
            operational_cost=0,
            fuel_cost=0.14678,
            power=best_capacities['CO2'],
            energy_output=optimizer.co2_supply["CO2 Requirement"].sum(),
            fuel_requirement=optimizer.co2_supply["CO2 Requirement"].sum(),
            cc_power=0,
            lifetime=50,
            loan_term=20,
            co2_emissions=optimizer.co2_supply["Direct CO2 Emissions"].sum()
        )
        capex, opex, fuel, co2_tax, total, _, _ = co2_cost.constant_cost()
        optimized_cost_components['CO2'] = {'capex': capex, 'opex': opex, 'fuel': fuel, 'co2_tax': co2_tax,
                                            'total': total}

    print("co2 require", optimizer.co2_supply["CO2 Requirement"].sum())
    # Save optimization results
    optimization_data = {
        'capacities': best_capacities,
        'max_capacities': {
            'CHP': float(original_max_powers['chp_max_power']),
            'Geothermal': float(original_max_powers['geo_max_power']),
            'GSHP': float(original_max_powers['gshp_max_power']),
            'Solar': float(original_max_powers['solar_max_power']),
            'WasteHeat': float(original_max_powers['wasteheat_max_power']),
            'Grid': float(original_max_powers['grid_max_power']),
            'Boiler': float(original_max_powers['boiler_max_power']),
            'CO2': float(original_max_powers['co2_max_power'])
        },
        'enabled_sources': source_config,
        'total_cost': float(result.fun),
        'cost_components': optimizer.best_cost_components,
        'optimised_cost_components': optimized_cost_components,
    }

    with open('optimization_results.json', 'w') as f:
        json.dump(optimization_data, f, indent=4)

    print(f"\nOptimal annual cost: £{result.fun:,.2f}")

    print("\nOptimization complete!")
    print("Results saved to 'optimization_results.json'")


if __name__ == "__main__":
    main()
