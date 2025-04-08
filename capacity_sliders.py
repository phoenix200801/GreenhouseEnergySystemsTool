import json
import pandas as pd
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np

from . import ids
import Lib.Cost
import Lib.EnergyDemand


def load_optimization_data():
    """Load optimization results data"""
    try:
        # Use the correct file path
        file_path = r"C:\Users\phoen\OneDrive - National University of Ireland, Galway\Masters\Thesis\Python Framework\Lib\optimization_results.json"
        print(f"Attempting to load optimization data from: {file_path}")

        with open(file_path, 'r') as f:
            data = json.load(f)
            print("Successfully loaded capacities:", data['capacities'])
            return data

    except FileNotFoundError as e:
        print(f"Error: Could not find file at {file_path}: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file: {str(e)}")
        raise
    except Exception as e:
        print(f"Unexpected error loading optimization data: {str(e)}")
        raise


def get_demand_data():
    """Generate demand data directly by running the calculation functions"""
    try:
        import sys
        import os
        # Add the Lib directory to the path so we can import modules
        lib_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if lib_dir not in sys.path:
            sys.path.append(lib_dir)

        # Import the demand calculation functions
        from Lib.InputCalculations import calculate_inputs
        from Lib.HTCoefficients import calculate_htc
        from Lib.HeatDemand import calculate_heatdemand
        from Lib.LightDemand import calculate_lightdemand
        from Lib.CO2Demand import calculate_co2demand

        # Calculate demand data directly
        # inputs_data = calculate_inputs()
        # htc = calculate_htc(inputs_data)
        # heat_demand = calculate_heatdemand(inputs_data, htc)
        # light_demand = calculate_lightdemand(inputs_data, htc, heat_demand)
        # co2_demand = calculate_co2demand(inputs_data, htc, heat_demand, light_demand)
        heat_demand = pd.read_json("heat_demand.json")
        light_demand = pd.read_json("light_demand.json")
        co2_demand = pd.read_json("co2_demand.json")

        return heat_demand, light_demand, co2_demand
    except Exception as e:
        # If there's an error, print it and return empty DataFrames with sample data
        print(f"Error generating demand data: {e}")
        # Create minimal sample data to avoid division by zero errors
        heat_df = pd.DataFrame({'QnetMWh': [10] * 8760},
                               index=pd.date_range(start='2023-01-01', periods=8760, freq='H'))
        light_df = pd.DataFrame({'MWh': [5] * 8760}, index=pd.date_range(start='2023-01-01', periods=8760, freq='H'))
        co2_df = pd.DataFrame({'Total CO2 Demand': [100] * 8760},
                              index=pd.date_range(start='2023-01-01', periods=8760, freq='H'))
        return heat_df, light_df, co2_df


def get_max_powers():
    """Calculate the maximum power for each energy source"""
    try:
        # Get demand data
        heat_demand, light_demand, co2_demand = get_demand_data()

        # Calculate maximum power for each energy source
        chp = Lib.EnergyDemand.CHP(heat_demand, light_demand, co2_demand)
        _, chp_max_power = chp.calculate_demand()

        geo = Lib.EnergyDemand.Geothermal(heat_demand, light_demand, co2_demand)
        _, geo_max_power = geo.calculate_demand()

        gshp = Lib.EnergyDemand.GSHP(heat_demand, light_demand, co2_demand)
        _, gshp_max_power = gshp.calculate_demand()

        solar = Lib.EnergyDemand.SolarPV(heat_demand, light_demand, co2_demand)
        _, solar_max_power = solar.calculate_demand()

        wasteheat = Lib.EnergyDemand.WasteHeat(heat_demand, light_demand, co2_demand)
        _, wasteheat_max_power = wasteheat.calculate_demand()

        grid = Lib.EnergyDemand.Grid(heat_demand, light_demand, co2_demand)
        _, grid_max_power = grid.calculate_demand()

        boiler = Lib.EnergyDemand.Boiler(heat_demand, light_demand, co2_demand)
        _, boiler_max_power = boiler.calculate_demand()

        co2_import = Lib.EnergyDemand.CO2Import(heat_demand, light_demand, co2_demand)
        _, co2_max_power = co2_import.calculate_demand()

        # Return dictionary of max powers
        return {
            'CHP': float(chp_max_power),
            'Geothermal': float(geo_max_power),
            'GSHP': float(gshp_max_power),
            'Solar': float(solar_max_power),
            'WasteHeat': float(wasteheat_max_power),
            'Grid': float(grid_max_power),
            'Boiler': float(boiler_max_power),
            ' ': float(co2_max_power)
        }
    except Exception as e:
        print(f"Error calculating max powers: {e}")
        # Return default values
        return {
            'CHP': 100,
            'Geothermal': 100,
            'GSHP': 100,
            'Solar': 100,
            'WasteHeat': 100,
            'Grid': 100,
            'Boiler': 100,
            'CO2': 1000
        }


def render(app: Dash) -> html.Div:
    """Create the capacity sliders component"""
    # Load optimization data
    opt_data = load_optimization_data()

    # Extract capacities from optimization data
    capacities = opt_data['capacities']

    # Get actual max powers from energy demand calculations
    max_capacities = opt_data['max_capacities']

    # If optimization data has max capacities, use those as fallback
    if not all(max_capacities.values()):
        opt_max_capacities = opt_data.get('max_capacities', {})
        for source in max_capacities:
            if max_capacities[source] == 0 and source in opt_max_capacities:
                max_capacities[source] = opt_max_capacities[source]

    # Create list of energy sources
    sources = ['CHP', 'Geothermal', 'GSHP', 'Solar', 'WasteHeat', 'Grid', 'Boiler', 'CO2']

    # Create sliders for each energy source
    sliders = []
    for source in sources:
        current_value = capacities.get(source, 0)
        max_value = max_capacities.get(source, 100)

        # Make sure max_value is greater than zero to avoid slider errors
        max_value = max_value

        # For sources with very small max values, adjust step size
        step = max_value / 5000

        # Unit label (kg/h for CO2, MW for others)
        unit = "kg/h" if source == "CO2" else "MW"

        # Create slider component
        slider = html.Div([
            html.Label(f"{source} Capacity ({unit}):",
                       style={"fontWeight": "bold", "marginTop": "10px"}),
            html.Div([
                dcc.Slider(
                    id=f"slider-{source.lower()}",
                    min=0,
                    max=max_value,
                    step=step,
                    value=current_value,
                    marks={
                        0: {'label': '0'},
                        max_value / 2: {'label': f'{max_value / 2:.2f}'},
                        max_value: {'label': f'{max_value:.2f}'}
                    },
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
            ], style={"padding": "10px 0px 20px 0px"}),
        ])
        sliders.append(slider)

    # Add demand warnings container below sliders
    demand_warnings = html.Div([
        html.Div(id=ids.DEMAND_WARNINGS_CONTAINER, style={"marginTop": "10px", "marginBottom": "20px"})
    ])
    sliders.append(demand_warnings)

    # Create cost and emissions display section
    analysis_display = html.Div([
        html.H3("Cost Breakdown", style={"marginTop": "20px"}),
        html.Div(id="total-cost-display",
                 style={"fontSize": "1.5rem", "fontWeight": "bold", "marginBottom": "10px"}),
        html.Div(id="cost-breakdown-table"),
        dcc.Graph(id="updated-cost-chart"),

        # New emissions chart section
        html.H3("CO2 Emissions Breakdown", style={"marginTop": "30px"}),
        dcc.Graph(id=ids.EMISSIONS_COMPARISON_CHART),
    ])

    # Combine sliders and analysis display
    component = html.Div([
        html.H2("Interactive Capacity Explorer"),
        html.P("Adjust sliders to see how different capacity configurations affect total cost and emissions"),

        # Reset button
        html.Button(
            "Reset to Optimal Values",
            id="reset-sliders-button",
            className="btn btn-outline-primary",
            style={"marginBottom": "20px"}
        ),

        # Container for sliders and analysis display
        html.Div([
            # Sliders column
            html.Div(
                sliders,
                style={"flex": "1", "minWidth": "300px"}
            ),

            # Analysis display column
            html.Div(
                analysis_display,
                style={"flex": "1", "minWidth": "500px"}
            ),
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "30px"})
    ])

    # Register callbacks for interactive components
    register_callbacks(app)

    return component


def register_callbacks(app: Dash):
    # Create input list for all sliders
    slider_inputs = [
        Input(f"slider-{source.lower()}", "value")
        for source in ['chp', 'geothermal', 'gshp', 'solar', 'wasteheat', 'grid', 'boiler', 'co2']
    ]

    @app.callback(
        [Output("total-cost-display", "children"),
         Output("cost-breakdown-table", "children"),
         Output("updated-cost-chart", "figure"),
         Output(ids.EMISSIONS_COMPARISON_CHART, "figure"),
         Output(ids.DEMAND_WARNINGS_CONTAINER, "children")],  # Added output for demand warnings
        slider_inputs
    )
    def update_cost_display(chp, geothermal, gshp, solar, wasteheat, grid, boiler, co2):
        """Calculate new costs and emissions based on slider values"""
        try:
            # Get demand data directly instead of loading from joblib files
            heat_demand, light_demand, co2_demand = get_demand_data()

            # Get the CO2 absorbed value directly from the demand data
            co2_absorbed = co2_demand["Net Photosynthesis"].sum() if "Net Photosynthesis" in co2_demand.columns else 0

            # Calculate costs for each technology
            cost_components = {}
            total_cost = 0

            # Dictionary to store emissions data
            emissions_data = {
                'source': [],
                'direct_emissions': [],
                'related_emissions': [],
                'net_emissions': []
            }

            # Calculate CHP cost if capacity > 0
            if chp > 0.0001:
                chp_demand, chp_max_power = Lib.EnergyDemand.CHP(heat_demand, light_demand,
                                                                 co2_demand).calculate_max_supply()
                # Fixed code:
                chp_instance = Lib.EnergyDemand.CHP(heat_demand, light_demand, co2_demand)
                chp_supply = chp_instance.calculate_supply(chp, chp_max_power, chp_demand)
                chp_obj = Lib.Cost.CHP(
                    capital_cost=1.2e6 * chp ** -0.4,
                    base_capex=0,
                    operational_cost=9.3,
                    fuel_cost=90.1,
                    power=chp,
                    energy_output=chp_supply["Yearly Electricity Output"].sum(),
                    fuel_requirement=chp_supply["Fuel Requirement"].sum(),
                    cc_power=0.16,
                    lifetime=25,
                    loan_term=20,
                    co2_emissions=chp_supply["Direct CO2 Emissions"].sum()
                )
                capex, opex, fuel, co2_tax, cost, cost_df, _ = chp_obj.constant_cost()
                cost_components['CHP'] = {'capex': cost_df.loc[0, 'CAPEX'], 'opex': cost_df.loc[0, 'OPEX'],
                                          'fuel': cost_df.loc[0, 'Fuel'], 'co2_tax': cost_df.loc[0, 'CO2 Tax'],
                                          'total': cost_df.loc[0, 'Total Cost']}
                total_cost += cost_df.loc[0, 'Total Cost']

                # Add CHP emissions data
                emissions_data['source'].append('CHP')
                emissions_data['direct_emissions'].append(chp_supply["Direct CO2 Emissions"].sum())
                emissions_data['related_emissions'].append(chp_supply["Related CO2 Emissions"].sum())
                emissions_data['net_emissions'].append(chp_supply["Net CO2 Emissions"].sum())
            else:
                cost_components['CHP'] = {'capex': 0, 'opex': 0, 'fuel': 0, 'co2_tax': 0, 'total': 0}

            # Calculate Geothermal cost if capacity > 0
            if geothermal > 0.0001:
                geo_demand, geo_max_power = Lib.EnergyDemand.Geothermal(heat_demand, light_demand,
                                                                        co2_demand).calculate_max_supply()
                geo_instance = Lib.EnergyDemand.Geothermal(heat_demand, light_demand, co2_demand)
                geo_supply = geo_instance.calculate_supply(geothermal, geo_max_power)
                geo_obj = Lib.Cost.Geothermal(
                    capital_cost=2890000 * geothermal ** -0.45 + 1.2e6,
                    base_capex=0,
                    operational_cost=11000 * geothermal /
                                     geo_supply["Yearly Heat Output"].sum(),
                    fuel_cost=228.1,
                    power=geothermal,
                    energy_output=geo_supply["Yearly Heat Output"].sum(),
                    fuel_requirement=geo_supply["Electricity for Heat"].sum(),
                    cc_power=0,
                    lifetime=30,
                    loan_term=20,
                    co2_emissions=geo_supply["Direct CO2 Emissions"].sum()
                )
                capex, opex, fuel, co2_tax, cost, cost_df, _ = geo_obj.constant_cost()
                cost_components['Geothermal'] = {'capex': cost_df.loc[0, 'CAPEX'], 'opex': cost_df.loc[0, 'OPEX'],
                                                 'fuel': cost_df.loc[0, 'Fuel'],
                                                 'co2_tax': cost_df.loc[0, 'CO2 Tax'],
                                                 'total': cost_df.loc[0, 'Total Cost']}
                total_cost += cost_df.loc[0, 'Total Cost']

                # Add Geothermal emissions data
                emissions_data['source'].append('Geothermal')
                emissions_data['direct_emissions'].append(geo_supply["Direct CO2 Emissions"].sum())
                emissions_data['related_emissions'].append(geo_supply["Related CO2 Emissions"].sum())
                emissions_data['net_emissions'].append(geo_supply["Net CO2 Emissions"].sum())
            else:
                cost_components['Geothermal'] = {'capex': 0, 'opex': 0, 'fuel': 0, 'co2_tax': 0, 'total': 0}

            # Calculate GSHP cost if capacity > 0
            if gshp > 0.0001:
                gshp_demand, gshp_max_power = Lib.EnergyDemand.GSHP(heat_demand, light_demand,
                                                                    co2_demand).calculate_max_supply()
                gshp_instance = Lib.EnergyDemand.GSHP(heat_demand, light_demand, co2_demand)
                gshp_supply = gshp_instance.calculate_supply(gshp, gshp_max_power)
                gshp_obj = Lib.Cost.GSHP(
                    capital_cost=1297000 * gshp ** -0.21557,
                    base_capex=0,
                    operational_cost=8000 * gshp / gshp_supply["Yearly Heat Output"].sum(),
                    fuel_cost=228.1,
                    power=gshp,
                    energy_output=gshp_supply["Yearly Heat Output"].sum(),
                    fuel_requirement=gshp_supply["Electricity for Heat"].sum(),
                    cc_power=0,
                    lifetime=25,
                    loan_term=20,
                    co2_emissions=gshp_supply["Direct CO2 Emissions"].sum()
                )
                capex, opex, fuel, co2_tax, cost, cost_df, _ = gshp_obj.constant_cost()
                cost_components['GSHP'] = {'capex': cost_df.loc[0, 'CAPEX'], 'opex': cost_df.loc[0, 'OPEX'],
                                           'fuel': cost_df.loc[0, 'Fuel'], 'co2_tax': cost_df.loc[0, 'CO2 Tax'],
                                           'total': cost_df.loc[0, 'Total Cost']}
                total_cost += cost_df.loc[0, 'Total Cost']

                # Add GSHP emissions data
                emissions_data['source'].append('GSHP')
                emissions_data['direct_emissions'].append(gshp_supply["Direct CO2 Emissions"].sum())
                emissions_data['related_emissions'].append(gshp_supply["Related CO2 Emissions"].sum())
                emissions_data['net_emissions'].append(gshp_supply["Net CO2 Emissions"].sum())
            else:
                cost_components['GSHP'] = {'capex': 0, 'opex': 0, 'fuel': 0, 'co2_tax': 0, 'total': 0}

            # Calculate Solar cost if capacity > 0
            if solar > 0.0001:
                solar_demand, solar_max_power = Lib.EnergyDemand.SolarPV(heat_demand, light_demand,
                                                                         co2_demand).calculate_max_supply()
                solar_instance = Lib.EnergyDemand.SolarPV(heat_demand, light_demand, co2_demand)
                solar_supply = solar_instance.calculate_supply(solar, solar_max_power)
                solar_obj = Lib.Cost.SolarPV(
                    capital_cost=1.572e6 * solar ** -0.15 - 1.5e5,
                    base_capex=0,
                    operational_cost=12000 * solar / solar_supply["Yearly Electricity Output"].sum(),
                    fuel_cost=0,
                    power=solar,
                    energy_output=solar_supply["Yearly Electricity Output"].sum(),
                    fuel_requirement=0,
                    cc_power=0,
                    lifetime=30,
                    loan_term=20,
                    co2_emissions=solar_supply["Direct CO2 Emissions"].sum()
                )
                capex, opex, fuel, co2_tax, cost, cost_df, _ = solar_obj.constant_cost()
                cost_components['Solar'] = {'capex': cost_df.loc[0, 'CAPEX'], 'opex': cost_df.loc[0, 'OPEX'],
                                            'fuel': cost_df.loc[0, 'Fuel'], 'co2_tax': cost_df.loc[0, 'CO2 Tax'],
                                            'total': cost_df.loc[0, 'Total Cost']}
                total_cost += cost_df.loc[0, 'Total Cost']

                # Add Solar emissions data
                emissions_data['source'].append('Solar')
                emissions_data['direct_emissions'].append(solar_supply["Direct CO2 Emissions"].sum())
                emissions_data['related_emissions'].append(solar_supply["Related CO2 Emissions"].sum())
                emissions_data['net_emissions'].append(solar_supply["Net CO2 Emissions"].sum())
            else:
                cost_components['Solar'] = {'capex': 0, 'opex': 0, 'fuel': 0, 'co2_tax': 0, 'total': 0}

            # Calculate WasteHeat cost if capacity > 0
            if wasteheat > 0.0001:
                waste_demand, waste_max_power = Lib.EnergyDemand.WasteHeat(heat_demand, light_demand,
                                                                           co2_demand).calculate_max_supply()
                wasteheat_instance = Lib.EnergyDemand.WasteHeat(heat_demand, light_demand, co2_demand)
                wasteheat_supply = wasteheat_instance.calculate_supply(wasteheat, waste_max_power)
                waste_obj = Lib.Cost.WasteHeat(
                    capital_cost=0,
                    base_capex=0,
                    operational_cost=0,
                    fuel_cost=90.1*0.9,
                    power=wasteheat,
                    energy_output=wasteheat_supply["Yearly Heat Output"].sum(),
                    fuel_requirement=wasteheat_supply["Steam Required"].sum(),
                    cc_power=0,
                    lifetime=50,
                    loan_term=20,
                    co2_emissions=wasteheat_supply["Direct CO2 Emissions"].sum()
                )
                capex, opex, fuel, co2_tax, cost, cost_df, _ = waste_obj.constant_cost()
                cost_components['WasteHeat'] = {'capex': cost_df.loc[0, 'CAPEX'], 'opex': cost_df.loc[0, 'OPEX'],
                                                'fuel': cost_df.loc[0, 'Fuel'],
                                                'co2_tax': cost_df.loc[0, 'CO2 Tax'],
                                                'total': cost_df.loc[0, 'Total Cost']}
                total_cost += cost_df.loc[0, 'Total Cost']

                # Add WasteHeat emissions data
                emissions_data['source'].append('WasteHeat')
                emissions_data['direct_emissions'].append(wasteheat_supply["Direct CO2 Emissions"].sum())
                emissions_data['related_emissions'].append(wasteheat_supply["Related CO2 Emissions"].sum())
                emissions_data['net_emissions'].append(wasteheat_supply["Net CO2 Emissions"].sum())
            else:
                cost_components['WasteHeat'] = {'capex': 0, 'opex': 0, 'fuel': 0, 'co2_tax': 0, 'total': 0}

            # Calculate Grid cost if capacity > 0
            if grid > 0.0001:
                grid_demand, grid_max_power = Lib.EnergyDemand.Grid(heat_demand, light_demand,
                                                                    co2_demand).calculate_max_supply()
                grid_instance = Lib.EnergyDemand.Grid(heat_demand, light_demand, co2_demand)
                grid_supply = grid_instance.calculate_supply(grid, grid_max_power)
                grid_obj = Lib.Cost.Grid(
                    capital_cost=0,
                    base_capex=0,
                    operational_cost=0,
                    fuel_cost=228.1,
                    power=grid,
                    energy_output=grid_supply["Yearly Electricity Output"].sum(),
                    fuel_requirement=grid_supply["Electricity for Light"].sum(),
                    cc_power=0,
                    lifetime=50,
                    loan_term=20,
                    co2_emissions=grid_supply["Direct CO2 Emissions"].sum()
                )
                capex, opex, fuel, co2_tax, cost, cost_df, _ = grid_obj.constant_cost()
                cost_components['Grid'] = {'capex': cost_df.loc[0, 'CAPEX'], 'opex': cost_df.loc[0, 'OPEX'],
                                           'fuel': cost_df.loc[0, 'Fuel'], 'co2_tax': cost_df.loc[0, 'CO2 Tax'],
                                           'total': cost_df.loc[0, 'Total Cost']}
                total_cost += cost_df.loc[0, 'Total Cost']

                # Add Grid emissions data
                emissions_data['source'].append('Grid')
                emissions_data['direct_emissions'].append(grid_supply["Direct CO2 Emissions"].sum())
                emissions_data['related_emissions'].append(grid_supply["Related CO2 Emissions"].sum())
                emissions_data['net_emissions'].append(grid_supply["Net CO2 Emissions"].sum())
            else:
                cost_components['Grid'] = {'capex': 0, 'opex': 0, 'fuel': 0, 'co2_tax': 0, 'total': 0}

            # Calculate Boiler cost if capacity > 0
            if boiler > 0.0001:
                boiler_demand, boiler_max_power = Lib.EnergyDemand.Boiler(heat_demand, light_demand,
                                                                          co2_demand).calculate_max_supply()
                boiler_instance = Lib.EnergyDemand.Boiler(heat_demand, light_demand, co2_demand)
                boiler_supply = boiler_instance.calculate_supply(boiler, boiler_max_power, boiler_demand)
                boiler_obj = Lib.Cost.Boiler(
                    capital_cost=103000 * boiler ** -0.17,
                    base_capex=0,
                    operational_cost=3900 * boiler / boiler_supply["Yearly Heat Output"].sum(),
                    fuel_cost=90.1,
                    power=boiler,
                    energy_output=boiler_supply["Yearly Heat Output"].sum(),
                    fuel_requirement=boiler_supply["Fuel Requirement"].sum(),
                    cc_power=0.16,
                    lifetime=25,
                    loan_term=20,
                    co2_emissions=boiler_supply["Direct CO2 Emissions"].sum()
                )
                capex, opex, fuel, co2_tax, cost, cost_df, _ = boiler_obj.constant_cost()
                cost_components['Boiler'] = {'capex': cost_df.loc[0, 'CAPEX'], 'opex': cost_df.loc[0, 'OPEX'],
                                             'fuel': cost_df.loc[0, 'Fuel'], 'co2_tax': cost_df.loc[0, 'CO2 Tax'],
                                             'total': cost_df.loc[0, 'Total Cost']}
                total_cost += cost_df.loc[0, 'Total Cost']

                # Add Boiler emissions data
                emissions_data['source'].append('Boiler')
                emissions_data['direct_emissions'].append(boiler_supply["Direct CO2 Emissions"].sum())
                emissions_data['related_emissions'].append(boiler_supply["Related CO2 Emissions"].sum())
                emissions_data['net_emissions'].append(boiler_supply["Net CO2 Emissions"].sum())
            else:
                cost_components['Boiler'] = {'capex': 0, 'opex': 0, 'fuel': 0, 'co2_tax': 0, 'total': 0}

            # Calculate CO2 Import cost if capacity > 0
            if co2 > 0.0001:
                co2_import_demand, co2_max_power = Lib.EnergyDemand.CO2Import(heat_demand, light_demand,
                                                                              co2_demand).calculate_max_supply()
                co2_instance = Lib.EnergyDemand.CO2Import(heat_demand, light_demand, co2_demand)
                co2_supply = co2_instance.calculate_supply(co2, co2_max_power)
                co2_obj = Lib.Cost.CO2Import(
                    capital_cost=0,
                    base_capex=0,
                    operational_cost=0,
                    fuel_cost=0.14678,
                    power=co2,
                    energy_output=co2_supply["CO2 Requirement"].sum(),
                    fuel_requirement=co2_supply["CO2 Requirement"].sum(),
                    cc_power=0,
                    lifetime=50,
                    loan_term=20,
                    co2_emissions=co2_supply["Direct CO2 Emissions"].sum()
                )
                capex, opex, fuel, co2_tax, cost, cost_df, _ = co2_obj.constant_cost()
                cost_components['CO2'] = {'capex': cost_df.loc[0, 'CAPEX'], 'opex': cost_df.loc[0, 'OPEX'],
                                          'fuel': cost_df.loc[0, 'Fuel'], 'co2_tax': cost_df.loc[0, 'CO2 Tax'],
                                          'total': cost_df.loc[0, 'Total Cost']}
                total_cost += cost_df.loc[0, 'Total Cost']

                # Add CO2 Import emissions data
                emissions_data['source'].append('CO2')
                emissions_data['direct_emissions'].append(co2_supply["Direct CO2 Emissions"].sum())
                emissions_data['related_emissions'].append(co2_supply["Related CO2 Emissions"].sum())
                emissions_data['net_emissions'].append(co2_supply["Net CO2 Emissions"].sum())
            else:
                cost_components['CO2'] = {'capex': 0, 'opex': 0, 'fuel': 0, 'co2_tax': 0, 'total': 0}

            # Calculate supplies and demand shortfalls
            # Similar to the calculation in the optimize_dual_annealing.py file

            # Get maximum demands
            max_heat = heat_demand["QnetMWh"].max()
            max_light = light_demand["MWh"].max()
            max_co2 = co2_demand["Total CO2 Demand"].max()

            # Calculate supplies
            # For heat supply
            heat_supply = (
                    chp * 1.51 +  # Electric Power * heat to electric ratio
                    geothermal +
                    gshp +
                    wasteheat * 0.93 +
                    boiler
            )

            # For light supply
            light_supply = (
                    chp * (1 - 0.16) +  # Using 1 - cc_power (0.16) for CHP
                    solar * 0.127 +  # Using capacity factor of 0.15 for solar
                    grid
            )

            # For CO2 supply
            co2_supply = (
                    chp * (
                        1 / 0.33) * 184 * 0.96 +  # Power * electric to fuel ratio * CO2 emissions factor * cc_efficiency
                    boiler * (1 / 0.6) * 184 +  # Power * heat to fuel ratio * CO2 emissions factor
                    co2
            )

            # Calculate shortfalls
            heat_shortfall = max(0, max_heat - heat_supply)
            light_shortfall = max(0, max_light - light_supply)
            co2_shortfall = max(0, max_co2 - co2_supply)

            # Calculate shortfall percentages
            heat_shortfall_pct = (heat_shortfall / max_heat * 100) if max_heat > 0 else 0
            light_shortfall_pct = (light_shortfall / max_light * 100) if max_light > 0 else 0
            co2_shortfall_pct = (co2_shortfall / max_co2 * 100) if max_co2 > 0 else 0

            # Create warnings based on shortfalls
            warnings = []

            if heat_shortfall_pct > 0.0001:
                warnings.append(
                    dbc.Alert(
                        [
                            html.I(className="fas fa-exclamation-triangle me-2"),
                            f"Heat Demand Shortfall: {heat_shortfall:.2f} MW ({heat_shortfall_pct:.1f}% of maximum demand)"
                        ],
                        color="danger",
                        className="mb-2"
                    )
                )

            if light_shortfall_pct > 0.0001:
                warnings.append(
                    dbc.Alert(
                        [
                            html.I(className="fas fa-exclamation-triangle me-2"),
                            f"Light Demand Shortfall: {light_shortfall:.2f} MW ({light_shortfall_pct:.1f}% of maximum demand)"
                        ],
                        color="danger",
                        className="mb-2"
                    )
                )

            if co2_shortfall_pct > 0.0001:
                warnings.append(
                    dbc.Alert(
                        [
                            html.I(className="fas fa-exclamation-triangle me-2"),
                            f"CO2 Demand Shortfall: {co2_shortfall:.2f} kg/h ({co2_shortfall_pct:.1f}% of maximum demand)"
                        ],
                        color="danger",
                        className="mb-2"
                    )
                )

            # If no warnings, show a success message
            if not warnings:
                warnings.append(
                    dbc.Alert(
                        [
                            html.I(className="fas fa-check-circle me-2"),
                            "All demands are satisfied with current capacities"
                        ],
                        color="success"
                    )
                )

            # Create demand summary for debugging
            demand_summary = {
                'Heat': {
                    'Max Demand': max_heat,
                    'Supply': heat_supply,
                    'Shortfall': heat_shortfall,
                    'Shortfall %': heat_shortfall_pct
                },
                'Light': {
                    'Max Demand': max_light,
                    'Supply': light_supply,
                    'Shortfall': light_shortfall,
                    'Shortfall %': light_shortfall_pct
                },
                'CO2': {
                    'Max Demand': max_co2,
                    'Supply': co2_supply,
                    'Shortfall': co2_shortfall,
                    'Shortfall %': co2_shortfall_pct
                }
            }
            print("Demand Summary:", demand_summary)

            # Create total cost display
            total_cost_display = f"Total Annual Cost: €{total_cost:,.2f}"

            # Create cost breakdown table
            # Only show sources with non-zero costs
            active_sources = [s for s in cost_components if cost_components[s]['total'] > 0]

            table_header = [
                html.Thead(html.Tr([
                    html.Th("Energy Source"),
                    html.Th("Capital (€)"),
                    html.Th("Operational (€)"),
                    html.Th("Fuel (€)"),
                    html.Th("Carbon Tax (€)"),
                    html.Th("Total (€)")
                ]))
            ]

            rows = []
            for source in active_sources:
                comp = cost_components[source]
                row = html.Tr([
                    html.Td(source),
                    html.Td(f"€{comp['capex']:,.0f}"),
                    html.Td(f"€{comp['opex']:,.0f}"),
                    html.Td(f"€{comp['fuel']:,.0f}"),
                    html.Td(f"€{comp['co2_tax']:,.0f}"),
                    html.Td(f"€{comp['total']:,.0f}", style={"fontWeight": "bold"})
                ])
                rows.append(row)

            # Add total row
            total_capex = sum(cost_components[s]['capex'] for s in cost_components)
            total_opex = sum(cost_components[s]['opex'] for s in cost_components)
            total_fuel = sum(cost_components[s]['fuel'] for s in cost_components)
            total_co2_tax = sum(cost_components[s]['co2_tax'] for s in cost_components)

            total_row = html.Tr([
                html.Td("TOTAL", style={"fontWeight": "bold"}),
                html.Td(f"€{total_capex:,.0f}", style={"fontWeight": "bold"}),
                html.Td(f"€{total_opex:,.0f}", style={"fontWeight": "bold"}),
                html.Td(f"€{total_fuel:,.0f}", style={"fontWeight": "bold"}),
                html.Td(f"€{total_co2_tax:,.0f}", style={"fontWeight": "bold"}),
                html.Td(f"€{total_cost:,.0f}", style={"fontWeight": "bold"})
            ], style={"backgroundColor": "#f8f9fa"})

            rows.append(total_row)
            table_body = [html.Tbody(rows)]

            table = dbc.Table(
                table_header + table_body,
                bordered=True,
                hover=True,
                responsive=True,
                striped=True,
                size="sm"
            )

            # Create updated cost chart
            cost_data = []

            # Prepare data for stacked bar chart
            sources_with_cost = [s for s in cost_components if cost_components[s]['total'] > 0]

            # Data for capex, opex, and Fuels
            capex_values = [cost_components[s]['capex'] for s in sources_with_cost]
            opex_values = [cost_components[s]['opex'] for s in sources_with_cost]
            fuel_values = [cost_components[s]['fuel'] for s in sources_with_cost]
            co2_values = [cost_components[s]['co2_tax'] for s in sources_with_cost]

            # Create stacked bar chart
            cost_fig = go.Figure()

            cost_fig.add_trace(go.Bar(
                x=sources_with_cost,
                y=capex_values,
                name='Capital Cost',
                marker_color='#4285F4'
            ))

            cost_fig.add_trace(go.Bar(
                x=sources_with_cost,
                y=opex_values,
                name='Operational Cost',
                marker_color='#34A853'
            ))

            cost_fig.add_trace(go.Bar(
                x=sources_with_cost,
                y=fuel_values,
                name='Fuel Cost',
                marker_color='#FBBC05'
            ))

            cost_fig.add_trace(go.Bar(
                x=sources_with_cost,
                y=co2_values,
                name='Carbon Tax',
                marker_color='#FF0000'
            ))

            # Update layout
            cost_fig.update_layout(
                title='Cost Breakdown by Energy Source',
                xaxis_title='Energy Source',
                yaxis_title='Annual Cost (€)',
                barmode='stack',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                margin=dict(l=50, r=50, t=80, b=50),
                height=500
            )

            # Create emissions comparison chart
            emissions_fig = go.Figure()

            # Only include sources with non-zero emissions
            if emissions_data['source']:
                # Create a trace for stacked gross emissions (direct + related)
                emissions_fig.add_trace(go.Bar(
                    x=emissions_data['source'],
                    y=emissions_data['direct_emissions'],
                    name='Direct Emissions',
                    marker_color='#E57373',  # Light red
                    offsetgroup=0
                ))

                emissions_fig.add_trace(go.Bar(
                    x=emissions_data['source'],
                    y=emissions_data['related_emissions'],
                    name='Related Emissions',
                    marker_color='#81C784',  # Light green
                    offsetgroup=0
                ))

                # Create a separate trace for net emissions
                emissions_fig.add_trace(go.Bar(
                    x=emissions_data['source'],
                    y=emissions_data['net_emissions'],
                    name='Net Emissions',
                    marker_color='#5C6BC0',  # Indigo
                    offsetgroup=1
                ))

                # Update layout
                emissions_fig.update_layout(
                    title='CO2 Emissions by Energy Source',
                    xaxis_title='Energy Source',
                    yaxis_title='Annual CO2 Emissions (kg)',
                    barmode='stack',
                    bargroupgap=0.2,  # Gap between the two bar groups
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    margin=dict(l=50, r=50, t=80, b=0),
                    height=500
                )
            else:
                # Empty chart with message if no emissions data
                emissions_fig.add_annotation(
                    x=0.5,
                    y=0.5,
                    text="No emissions data available",
                    showarrow=False,
                    font=dict(size=16)
                )

                emissions_fig.update_layout(
                    title='CO2 Emissions by Energy Source',
                    xaxis_title='Energy Source',
                    yaxis_title='CO2 Emissions (kg per year)',
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    margin=dict(l=50, r=50, t=80, b=50),
                    height=500
                )

            return total_cost_display, table, cost_fig, emissions_fig, warnings

        except Exception as e:
            # Return error message if calculation fails
            error_message = f"Error calculating costs and emissions: {str(e)}"
            return error_message, html.Div(), {}, {}

    # Callback for reset button
    @app.callback(
        [Output(f"slider-{source.lower()}", "value") for source in
         ['chp', 'geothermal', 'gshp', 'solar', 'wasteheat', 'grid', 'boiler', 'co2']],
        Input("reset-sliders-button", "n_clicks"),
        prevent_initial_call=True
    )
    def reset_sliders(n_clicks):
        """Reset sliders to optimal values"""
        opt_data = load_optimization_data()
        capacities = opt_data['capacities']

        # Get values for each source
        values = []
        for source in ['CHP', 'Geothermal', 'GSHP', 'Solar', 'WasteHeat', 'Grid', 'Boiler', 'CO2']:
            values.append(capacities.get(source, 0))

        return values
