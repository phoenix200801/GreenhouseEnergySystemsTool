import numpy as np
import pandas as pd
from scipy.optimize import dual_annealing
from joblib import load
import EnergyDemand
import Cost
import time
from datetime import timedelta, datetime


class OptimizeEnergySources:
    def __init__(self, heat_demand, light_demand, co2_demand):
        self.heat_demand = heat_demand
        self.light_demand = light_demand
        self.co2_demand = co2_demand

        # Store demand calculations and max powers
        self.chp = EnergyDemand.CHP(heat_demand, light_demand, co2_demand)
        self.chp_demand, self.chp_max_power = self.chp.calculate_max_supply()
        self.chp_max_supply = self.chp.calculate_supply(self.chp_max_power, self.chp_max_power, self.chp_demand)
        self.chp_co2_power = self.chp_demand["Fuel for CO2"].max()*EnergyDemand.CHP.fuel_to_electric_efficiency

        self.geo = EnergyDemand.Geothermal(heat_demand, light_demand, co2_demand)
        self.geo_demand, self.geo_max_power = self.geo.calculate_max_supply()
        self.geo_max_supply = self.geo.calculate_supply(self.geo_max_power, self.geo_max_power)

        self.gshp = EnergyDemand.GSHP(heat_demand, light_demand, co2_demand)
        self.gshp_demand, self.gshp_max_power = self.gshp.calculate_max_supply()
        self.gshp_max_supply = self.gshp.calculate_supply(self.gshp_max_power, self.gshp_max_power)

        self.solar = EnergyDemand.SolarPV(heat_demand, light_demand, co2_demand)
        self.solar_demand, self.solar_max_power = self.solar.calculate_max_supply()
        self.solar_max_supply = self.solar.calculate_supply(self.solar_max_power, self.solar_max_power)

        self.wasteheat = EnergyDemand.WasteHeat(heat_demand, light_demand, co2_demand)
        self.wasteheat_demand, self.wasteheat_max_power = self.wasteheat.calculate_max_supply()
        self.wasteheat_max_supply = self.wasteheat.calculate_supply(self.wasteheat_max_power, self.wasteheat_max_power)

        self.grid = EnergyDemand.Grid(heat_demand, light_demand, co2_demand)
        self.grid_demand, self.grid_max_power = self.grid.calculate_max_supply()
        self.grid_max_supply = self.grid.calculate_supply(self.grid_max_power, self.grid_max_power)

        self.boiler = EnergyDemand.Boiler(heat_demand, light_demand, co2_demand)
        self.boiler_demand, self.boiler_max_power = self.boiler.calculate_max_supply()
        self.boiler_max_supply = self.boiler.calculate_supply(self.boiler_max_power, self.boiler_max_power, self.boiler_demand)

        self.co2 = EnergyDemand.CO2Import(heat_demand, light_demand, co2_demand)
        self.co2_max_demand, self.co2_max_power = self.co2.calculate_max_supply()
        self.co2_max_supply = self.co2.calculate_supply(self.co2_max_power, self.co2_max_power)

        # Store maximum demands
        self.max_heat = heat_demand["QnetMWh"].max()
        self.max_light = light_demand["MWh"].max()
        self.max_co2 = co2_demand["Total CO2 Demand"].max()
        self.best_solution = None
        self.best_cost = float('inf')

        print(f"\nMaximum demands:")
        print(f"Heat: {self.max_heat:.4f} MW")
        print(f"Light: {self.max_light:.4f} MW")
        print(f"CO2: {self.max_co2:.4f} kg/h")

        print(f"\nMaximum technology powers:")
        print(f"CHP: {self.chp_max_power:.4f} MW")
        print(f"Geothermal: {self.geo_max_power:.4f} MW")
        print(f"GSHP: {self.gshp_max_power:.4f} MW")
        print(f"Solar: {self.solar_max_power:.4f} MW")
        print(f"Waste Heat: {self.wasteheat_max_power:.4f} MW")
        print(f"Grid: {self.grid_max_power:.4f} MW")
        print(f"Boiler: {self.boiler_max_power:.4f} MW")
        print(f"CO2: {self.co2_max_power:.4f} kg/h")

        self.iteration_data = []
        self.current_minimum = float('inf')
        self.local_minima = []
        self.iteration_count = 0
        self.convergence_window = 100  # Number of iterations to check for improvement
        self.improvement_threshold = 0.0001  # 0.5% improvement threshold
        self.converged = False
        self.current_cost_breakdown = {}

        self.best_cost_components = {
            'CHP': {'capex': 0, 'opex': 0, 'fuel': 0, 'co2_tax': 0},
            'BOILER': {'capex': 0, 'opex': 0, 'fuel': 0, 'co2_tax': 0}
        }

        self.best_cost_components = {
            'CHP': {'capex': 0, 'opex': 0, 'fuel': 0},
            'Geothermal': {'capex': 0, 'opex': 0, 'fuel': 0},
            'GSHP': {'capex': 0, 'opex': 0, 'fuel': 0},
            'Solar': {'capex': 0, 'opex': 0, 'fuel': 0},
            'WasteHeat': {'capex': 0, 'opex': 0, 'fuel': 0},
            'Grid': {'capex': 0, 'opex': 0, 'fuel': 0},
            'Boiler': {'capex': 0, 'opex': 0, 'fuel': 0},
            'CO2': {'capex': 0, 'opex': 0, 'fuel': 0}
        }

    def calculate_supplies(self, x):
        """Calculate supply of heat, light, and CO2 from given capacities"""
        chp, geo, gshp, solar, waste, grid, boiler, co2 = x

        # Calculate heat supply
        heat_supply = (
                chp * self.chp.heat_to_electric_ratio +  # These need to be double checked <<<<<<<<<<
                geo +
                gshp +
                waste * EnergyDemand.WasteHeat.exchanger_efficiency +
                boiler
        )

        # Calculate light supply
        light_supply = (
                chp * (1 - self.chp.cc_power) +
                solar * self.solar.capacity_factor +
                grid
        )

        # Calculate CO2 capture
        co2_supply = (
                chp / self.chp.fuel_to_electric_efficiency * self.chp.gas_co2_per_Mwh * self.chp.cc_efficiency +
                boiler * self.boiler.gas_co2_per_Mwh * self.boiler.fuel_to_heat_efficiency +
                co2
        )

        return heat_supply, light_supply, co2_supply

    def calculate_total_cost(self, x):
        """Calculate total annual cost for all technologies"""
        chp, geo, gshp, solar, waste, grid, boiler, co2 = x
        total_cost = 0

        current_cost_components = dict(self.best_cost_components)

        min_size = 0

        try:
            # CHP costs
            if chp > min_size:
                chp_instance = EnergyDemand.CHP(self.heat_demand, self.light_demand, self.co2_demand)
                self.chp_supply = chp_instance.calculate_supply(chp, self.chp_max_power, self.chp_demand)
                chp_cost = Cost.CHP(
                    capital_cost=1.2e6 * chp ** -0.4,
                    base_capex=0,
                    operational_cost=9.3,
                    fuel_cost=90.1,
                    power=chp,
                    energy_output=self.chp_supply["Yearly Electricity Output"].sum(),
                    fuel_requirement=self.chp_supply["Fuel Requirement"].sum(),
                    cc_power=0.16,
                    lifetime=25,
                    loan_term=20,
                    co2_emissions=self.chp_supply["Direct CO2 Emissions"].sum()
                )
                capex, opex, fuel, co2_tax, lifetime_cost, _, _ = chp_cost.constant_cost()
                current_cost_components['CHP'] = {'capex': capex, 'opex': opex, 'fuel': fuel, 'co2_tax': co2_tax}
                total_cost += lifetime_cost

            # Geothermal costs
            if geo > min_size:
                geo_instance = EnergyDemand.Geothermal(self.heat_demand, self.light_demand, self.co2_demand)
                self.geo_supply = geo_instance.calculate_supply(geo, self.geo_max_power)
                geo_cost = Cost.Geothermal(
                    capital_cost=2890000 * geo ** -0.45 + 1.2e6,
                    base_capex=0,
                    operational_cost=11000 * geo /
                                     self.geo_supply["Yearly Heat Output"].sum(),
                    fuel_cost=228.1,
                    power=geo,
                    energy_output=self.geo_supply["Yearly Heat Output"].sum(),
                    fuel_requirement=self.geo_supply["Electricity for Heat"].sum(),
                    cc_power=0,
                    lifetime=30,
                    loan_term=20,
                    co2_emissions=self.geo_supply["Direct CO2 Emissions"].sum()
                )
                capex, opex, fuel, co2_tax, lifetime_cost, _, _ = geo_cost.constant_cost()
                current_cost_components['Geothermal'] = {'capex': capex, 'opex': opex, 'fuel': fuel, 'co2_tax': co2_tax}
                total_cost += lifetime_cost

            # GSHP costs
            if gshp > min_size:
                gshp_instance = EnergyDemand.GSHP(self.heat_demand, self.light_demand, self.co2_demand)
                self.gshp_supply = gshp_instance.calculate_supply(gshp, self.gshp_max_power)
                gshp_cost = Cost.GSHP(
                    capital_cost=1297000 * gshp ** -0.21557,
                    base_capex=0,
                    operational_cost=8000 * gshp / self.gshp_supply["Yearly Heat Output"].sum(),
                    fuel_cost=228.1,
                    power=gshp,
                    energy_output=self.gshp_supply["Yearly Heat Output"].sum(),
                    fuel_requirement=self.gshp_supply["Electricity for Heat"].sum(),
                    cc_power=0,
                    lifetime=25,
                    loan_term=20,
                    co2_emissions=self.gshp_supply["Direct CO2 Emissions"].sum()
                )
                capex, opex, fuel, co2_tax, lifetime_cost, _, _ = gshp_cost.constant_cost()
                current_cost_components['GSHP'] = {'capex': capex, 'opex': opex, 'fuel': fuel, 'co2_tax': co2_tax}
                total_cost += lifetime_cost

            # Solar costs
            if solar > min_size:
                solar_instance = EnergyDemand.SolarPV(self.heat_demand, self.light_demand, self.co2_demand)
                self.solar_supply = solar_instance.calculate_supply(solar, self.solar_max_power)
                solar_cost = Cost.SolarPV(
                    capital_cost=1.572e6 * solar ** -0.15 - 1.5e5,
                    base_capex=0,
                    operational_cost=12000 * solar / self.solar_supply["Yearly Electricity Output"].sum(),
                    fuel_cost=0,
                    power=solar,
                    energy_output=self.solar_supply["Yearly Electricity Output"].sum(),
                    fuel_requirement=0,
                    cc_power=0,
                    lifetime=30,
                    loan_term=20,
                    co2_emissions=self.solar_supply["Direct CO2 Emissions"].sum()
                )
                capex, opex, fuel, co2_tax, lifetime_cost, _, _ = solar_cost.constant_cost()
                current_cost_components['Solar'] = {'capex': capex, 'opex': opex, 'fuel': fuel, 'co2_tax': co2_tax}
                total_cost += lifetime_cost

            # Waste Heat costs
            if waste > min_size:
                waste_instance = EnergyDemand.WasteHeat(self.heat_demand, self.light_demand, self.co2_demand)
                self.wasteheat_supply = waste_instance.calculate_supply(waste, self.wasteheat_max_power)
                waste_cost = Cost.WasteHeat(
                    capital_cost=0,
                    base_capex=0,
                    operational_cost=0,
                    fuel_cost=90.1*0.9,
                    power=waste,
                    energy_output=self.wasteheat_supply["Yearly Heat Output"].sum(),
                    fuel_requirement=self.wasteheat_supply["Steam Required"].sum(),
                    cc_power=0,
                    lifetime=50,
                    loan_term=20,
                    co2_emissions=self.wasteheat_supply["Direct CO2 Emissions"].sum()
                )
                capex, opex, fuel, co2_tax, lifetime_cost, _, _ = waste_cost.constant_cost()
                current_cost_components['WasteHeat'] = {'capex': capex, 'opex': opex, 'fuel': fuel, 'co2_tax': co2_tax}
                total_cost += lifetime_cost

            # Grid costs
            if grid > min_size:
                grid_instance = EnergyDemand.Grid(self.heat_demand, self.light_demand, self.co2_demand)
                self.grid_supply = grid_instance.calculate_supply(grid, self.grid_max_power)
                grid_cost = Cost.Grid(
                    capital_cost=0,
                    base_capex=0,
                    operational_cost=0,
                    fuel_cost=228.1,
                    power=grid,
                    energy_output=self.grid_supply["Yearly Electricity Output"].sum(),
                    fuel_requirement=self.grid_supply["Electricity for Light"].sum(),
                    cc_power=0,
                    lifetime=50,
                    loan_term=20,
                    co2_emissions=self.grid_supply["Direct CO2 Emissions"].sum()
                )
                capex, opex, fuel, co2_tax, lifetime_cost, _, _ = grid_cost.constant_cost()
                current_cost_components['Grid'] = {'capex': capex, 'opex': opex, 'fuel': fuel, 'co2_tax': co2_tax}
                total_cost += lifetime_cost

            if boiler > min_size:
                boiler_instance = EnergyDemand.Boiler(self.heat_demand, self.light_demand, self.co2_demand)
                self.boiler_supply = boiler_instance.calculate_supply(boiler, self.boiler_max_power, self.boiler_demand)
                boiler_cost = Cost.Boiler(
                    capital_cost=103000 * boiler ** -0.17,
                    base_capex=0,
                    operational_cost=3900 * boiler / self.boiler_supply["Yearly Heat Output"].sum(),
                    fuel_cost=90.1,
                    power=boiler,
                    energy_output=self.boiler_supply["Yearly Heat Output"].sum(),
                    fuel_requirement=self.boiler_supply["Fuel Requirement"].sum(),
                    cc_power=0,
                    lifetime=25,
                    loan_term=20,
                    co2_emissions=self.boiler_supply["Direct CO2 Emissions"].sum()
                )
                capex, opex, fuel, co2_tax, lifetime_cost, _, _ = boiler_cost.constant_cost()
                current_cost_components['Boiler'] = {'capex': capex, 'opex': opex, 'fuel': fuel, 'co2_tax': co2_tax}
                total_cost += lifetime_cost

            if co2 > min_size:
                co2_instance = EnergyDemand.CO2Import(self.heat_demand, self.light_demand, self.co2_demand)
                self.co2_supply = co2_instance.calculate_supply(co2, self.co2_max_power)
                co2_cost = Cost.CO2Import(
                    capital_cost=0,
                    base_capex=0,
                    operational_cost=0,
                    fuel_cost=0.14678,
                    power=co2,
                    energy_output=self.co2_supply["CO2 Requirement"].sum(),
                    fuel_requirement=self.co2_supply["CO2 Requirement"].sum(),
                    cc_power=0,
                    lifetime=50,
                    loan_term=20,
                    co2_emissions=self.co2_supply["Direct CO2 Emissions"].sum()
                )
                capex, opex, fuel, co2_tax, lifetime_cost, _, _ = co2_cost.constant_cost()
                current_cost_components['CO2'] = {'capex': capex, 'opex': opex, 'fuel': fuel, 'co2_tax': co2_tax}
                total_cost += lifetime_cost

            if total_cost < self.best_cost:
                self.best_cost_components = current_cost_components

            chp_costs = current_cost_components['CHP']
            boiler_costs = current_cost_components['Boiler']
            return total_cost, chp_costs, boiler_costs
        except Exception as e:
            print(f"Error in calculate_total_cost: {e}")
            return 1e10  # Return high cost instead of None

    def check_convergence(self):
        """Check if optimization has converged based on improvements between discovered minima"""
        if len(self.local_minima) < self.convergence_window:
            return False

        # Look at the most recent X minima discoveries, where X is the convergence window
        recent_minima = self.local_minima[-self.convergence_window:]

        # Calculate the best cost from the start of this window and the best cost now
        best_cost_start = recent_minima[0]['cost']
        best_cost_now = recent_minima[-1]['cost']

        # Calculate relative improvement from best discovered solution at window start to now
        relative_improvement = (best_cost_start - best_cost_now) / best_cost_start

        if relative_improvement < self.improvement_threshold:
            print(f"\nConvergence detected:")
            print(
                f"Best solution improved by only {relative_improvement:.4%} over last {self.convergence_window} discovered minima")
            print(f"Below threshold of {self.improvement_threshold:.1%}")
            self.converged = True
            # Set the current minimum to the best cost when convergence is detected
            self.current_minimum = self.best_cost
            return True

        return False

    def objective(self, x):
        """Modified objective function that tracks local minima"""
        chp, geo, gshp, solar, waste, grid, boiler, co2 = x

        if self.converged:
            return self.current_minimum

        cost = self._calculate_objective(x)  # This contains the original objective function logic

        # Update best solution if this is better
        if cost < self.best_cost:
            self.best_cost = cost
            self.best_solution = x.copy()  # Store a copy of the best solution

            # Print only significant improvements (e.g., more than 1% better)
            if len(self.local_minima) == 0 or cost < self.local_minima[-1]['cost'] * 0.99:
                print(f"\nNew better solution found: £{cost:,.2f}")
                techs = ['CHP', 'Geothermal', 'GSHP', 'Solar', 'Waste Heat', 'Grid', 'Boiler', 'CO2']
                for tech, cap in zip(techs, x):
                    if cap > 0.0001:
                        unit = "kg/h" if tech == "CO2" else "MW"
                        print(f"{tech}: {cap:.4f} {unit}")

            self.local_minima.append({
                'iteration': self.iteration_count,
                'cost': cost,
                'capacities': list(x)
            })

            # Add this line to check for convergence after updating local_minima
            self.check_convergence()

        self.iteration_count += 1
        return cost

    def _calculate_objective(self, x):
        """Objective function with cost breakdown tracking"""
        chp, geo, gshp, solar, waste, grid, boiler, co2 = x
        try:
            heat_supply, light_supply, co2_supply = self.calculate_supplies(x)
            try:
                cost_result = self.calculate_total_cost(x)
                if isinstance(cost_result, tuple):
                    base_cost, chp_costs, boiler_costs = cost_result
                else:
                    base_cost = cost_result
                    chp_costs = {'capex': 0, 'opex': 0, 'fuel': 0, 'co2_tax': 0}
                    boiler_costs = {'capex': 0, 'opex': 0, 'fuel': 0, 'co2_tax': 0}
            except Exception as e:
                print(f"Error processing cost results: {e}")
                base_cost = 1e10  # Use high cost value for errors
                chp_costs = {'capex': 0, 'opex': 0, 'fuel': 0, 'co2_tax': 0}
                boiler_costs = {'capex': 0, 'opex': 0, 'fuel': 0, 'co2_tax': 0}

            # Calculate violations
            heat_undersupply = max(0, self.max_heat - heat_supply)
            light_undersupply = max(0, self.max_light - light_supply)
            co2_undersupply = max(0, self.max_co2 - co2_supply)

            # Calculate undersupply penalties
            heat_undersupply_penalty = 1e12 * heat_undersupply ** 2
            light_undersupply_penalty = 1e12 * light_undersupply ** 2
            co2_undersupply_penalty = 1e10 * co2_undersupply ** 2
            undersupply_penalty = heat_undersupply_penalty + light_undersupply_penalty + co2_undersupply_penalty

            tolerance = 0.05
            # heat_oversupply = max(0, heat_supply - self.max_heat * (1 + tolerance))
            # light_oversupply = max(0, light_supply - self.max_light * (1 + tolerance))
            # co2_oversupply = (
            #         self.chp_supply["Fuel Requirement"].sum() * self.chp.gas_co2_per_Mwh * self.chp.cc_efficiency * (
            #         chp / self.chp_max_power) +
            #         self.boiler_supply[
            #             "Fuel Requirement"].sum() * self.boiler.gas_co2_per_Mwh * self.boiler.cc_efficiency * (
            #                 boiler / self.boiler_max_power) +
            #         self.co2_supply["CO2 Requirement"].sum() * (co2 / self.co2_max_power) -
            #         self.co2_supply["CO2 Requirement"].sum()
            # )

            # Calculate oversupply penalties
            # co2_oversupply_penalty = co2_oversupply * 0.056  # £56 per tonne of CO2
            # oversupply_penalty = co2_oversupply_penalty

            total_cost = base_cost + undersupply_penalty

            # Store the iteration data
            self.iteration_data.append({
                'CHP': chp,
                'Geothermal': geo,
                'GSHP': gshp,
                'Solar': solar,
                'Waste Heat': waste,
                'Grid': grid,
                'Boiler': boiler,
                'CO2': co2,
                'undersupply_breakdown': {
                    'heat': heat_undersupply_penalty,
                    'light': light_undersupply_penalty,
                    'co2': co2_undersupply_penalty
                },
                'CHP_costs': chp_costs,
                'Boiler_costs': boiler_costs,
                'total_cost': total_cost
            })

            # Store cost breakdown for this iteration
            self.current_cost_breakdown = {
                'total_cost': total_cost,
                'base_cost': base_cost,
                'CHP': chp,
                'Geothermal': geo,
                'GSHP': gshp,
                'Solar': solar,
                'Waste Heat': waste,
                'Grid': grid,
                'Boiler': boiler,
                'CO2': co2,
                'undersupply_breakdown': {
                    'heat': heat_undersupply_penalty,
                    'light': light_undersupply_penalty,
                    'co2': co2_undersupply_penalty
                },
            }

            # Detailed debugging output
            if undersupply_penalty > 0:
                print(f"\nCost Breakdown at CHP = {x[0]:.4f} MW:"
                      f"\nGeothermal = {x[1]:.4f} MW "
                      f"\nGSHP = {x[2]:.4f} MW "
                      f"\nSolar = {x[3]:.4f} MW"
                      f"\nWaste Heat = {x[4]:.4f} MW"
                      f"\nGrid = {x[5]:.4f} MW"
                      f"\nBoiler = {x[6]:.4f} MW"
                      f"\nCO2 = {x[7]:.4f} kg/h")
                print(f"Base Cost: £{base_cost:,.2f}")
                print(f"Undersupply Penalty: £{undersupply_penalty:,.2f}")
                print(f"  Heat: £{heat_undersupply_penalty:,.2f}")
                print(f"  Light: £{light_undersupply_penalty:,.2f}")
                print(f"  CO2: £{co2_undersupply_penalty:,.2f}")
                print(f"Total Cost: £{total_cost:,.2f}")

            return float(total_cost)

        except Exception as e:
            print(f"Error in objective function: {e}")
            return 1e10

    def optimize(self):
        """Run optimization using dual annealing with convergence tracking"""
        print("\nStarting dual annealing optimization...")

        self.best_solution = None
        self.best_cost = float('inf')
        self.local_minima = []
        self.iteration_count = 0

        bounds = [
            (0, self.chp_max_power),
            (0, self.geo_max_power),
            (0, self.gshp_max_power),
            (0, self.solar_max_power),
            (0, self.wasteheat_max_power),
            (0, self.grid_max_power),
            (0, self.boiler_max_power),
            (0, self.co2_max_power)
        ]

        # Calculate minimum CHP capacity needed for constraints
        min_chp_heat = self.max_heat / self.chp.heat_to_electric_ratio
        min_chp_light = self.max_light / (self.chp.fuel_to_electric_efficiency * (1 - self.chp.cc_power))
        min_chp_co2 = self.max_co2 / (self.chp.gas_co2_per_Mwh * self.chp.cc_efficiency)

        min_chp = self.chp_max_power

        print(f"\nMinimum CHP requirements:")
        print(f"For heat: {min_chp_heat:.4f} MW")
        print(f"For light: {min_chp_light:.4f} MW")
        print(f"For CO2: {min_chp_co2:.4f} MW")
        print(f"Overall minimum: {min_chp:.4f} MW")

        results = []

        initial_points = [
            [self.chp_co2_power, self.geo_max_power, 0, 0, self.grid_max_power, 0, 0, 0],
            [self.chp_co2_power, 0, self.gshp_max_power, 0, self.grid_max_power, 0, 0, 0],
            [0.057, 0, 0.122, 0, 0.0319, 0, 0, 0],
            [self.chp_co2_power, self.geo_max_power, 0, self.solar_max_power, 0, 0, 0, 0],
            [self.chp_co2_power, 0, self.gshp_max_power, self.solar_max_power, 0, 0, 0, 0],
            [self.chp_co2_power, 0, 0, self.solar_max_power, self.wasteheat_max_power, 0, 0, 0],
            [self.chp_co2_power, 0, 0, 0, self.wasteheat_max_power, self.grid_max_power, 0, 0],
            [self.chp_co2_power, 0, 0, self.solar_max_power*0.45, self.wasteheat_max_power, 0, 0, 0],
            #[0.057, 0, 0.121, 0, 0, 0.0319, 0, 0],
            [self.chp_max_power, 0, 0, 0, 0, 0, 0, 0],
            [0,self.geo_max_power, 0, 0, 0, self.grid_max_power, 0, self.co2_max_power],
            [0, self.geo_max_power, 0, self.solar_max_power, 0, 0, 0, self.co2_max_power],
            [0,0, self.gshp_max_power,self.solar_max_power, 0, 0, 0, self.co2_max_power],
            [0,0, self.gshp_max_power, 0, 0, self.grid_max_power, 0, self.co2_max_power],
            [0, 0, 0, self.solar_max_power, self.wasteheat_max_power, 0, 0, self.co2_max_power],
            [0, 0, 0, 0, self.wasteheat_max_power, self.grid_max_power, 0, self.co2_max_power],

        ]

        for i, x0 in enumerate(initial_points):
            print(f"\nStarting optimization run {i + 1} with initial CHP power: {x0[0]:.2f} MW")

            result = dual_annealing(
                self.objective,
                bounds=bounds,  # Search space limit for each variable
                x0=x0,  # Starting point in the search space
                initial_temp=500,  # High initial temperature for exploration, 5230 is the default, 1310.121
                maxiter=50,  # Max number of global iterations, 1000 is the default, 132
                visit=1.01,
                # Controls the relative weighting of the global (Cauchy) and local (Gaussian) search components, range is 1 to 3, 2.62 is the default
                accept=-5,
                # Negative with larger absolute values means less likely to accept solutions tending away from the objective, -5.0 is the default
                no_local_search=True,  # No local search is traditional generalised simulated annealing
                seed=42 + i,  # Random seed for reproducibility
            )

            results.append(result)

        best_result = min(results, key=lambda r: r.fun)

        # Override the result with our best found solution
        if self.best_solution is not None and self.best_cost < best_result.fun:
            best_result.x = self.best_solution
            best_result.fun = self.best_cost

        minima_df = pd.DataFrame(self.local_minima)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"optimization_minima_{timestamp}.csv"
        minima_df.to_csv(filename, index=False)

        iterations_df = pd.DataFrame(self.iteration_data)
        evaluations_filename = f"optimization_evaluations_{timestamp}.csv"
        iterations_df.to_csv(evaluations_filename, index=False)

        if self.converged:
            print("\nOptimization stopped early due to convergence")
        print(f"\nLocal minima history saved to {filename}")
        print(f"Best solution found: £{self.best_cost:,.2f}")

        return best_result


def main():
    # Start timing
    start_time = time.time()

    print("Loading demand data...")
    heat_demand = pd.read_json("heat_demand.json")
    light_demand = pd.read_json("light_demand.json")
    co2_demand = pd.read_json("co2_demand.json")

    # Time for data loading
    data_load_time = time.time()
    print(f"Data loading time: {timedelta(seconds=data_load_time - start_time)}")

    # Initialize optimizer
    optimizer = OptimizeEnergySources(heat_demand, light_demand, co2_demand)

    # Time for initialization
    init_time = time.time()
    print(f"Initialization time: {timedelta(seconds=init_time - data_load_time)}")

    # Run optimization
    print("\nStarting optimization...")
    opt_start_time = time.time()
    result = optimizer.optimize()
    opt_end_time = time.time()

    # Calculate optimization time
    opt_duration = opt_end_time - opt_start_time
    print(f"\nOptimization time: {timedelta(seconds=opt_duration)}")

    if result.success:
        print("\nOptimization successful!")
        print("\nOptimal capacities (MW):")
        technologies = ['CHP', 'Geothermal', 'GSHP', 'Solar PV', 'Waste Heat', 'Grid', 'Boiler', 'CO2 Import']
        for tech, capacity in zip(technologies, result.x):
            print(f"{tech}: {capacity:.4f}")

        print(f"\nMinimum annual cost: £{result.fun:,.2f}")

        # Verify constraints are met
        heat_supply, light_supply, co2_supply = optimizer.calculate_supplies(result.x)

        print("\nConstraint Verification:")
        print(f"Heat Supply:")
        print(f"Required: {optimizer.max_heat:.4f} MW")
        print(f"Supplied: {heat_supply:.4f} MW")

        print(f"\nLight Supply:")
        print(f"Required: {optimizer.max_light:.4f} MW")
        print(f"Supplied: {light_supply:.4f} MW")

        print(f"\nCO2 Supply:")
        print(f"Required: {optimizer.max_co2:.4f} kg/h")
        print(f"Supplied: {co2_supply:.4f} kg/h")

        # Print optimization statistics
        print("\nOptimization Statistics:")
        print(f"Number of iterations: {result.nit}")
        print(f"Number of function evaluations: {result.nfev}")
        print(f"Average time per iteration: {timedelta(seconds=opt_duration / result.nit)}")

        # Get final cost breakdown
        optimizer.objective(result.x)  # This will update the cost breakdown
        cost_breakdown = optimizer.current_cost_breakdown

        print("\nFinal Cost Breakdown:")
        print(f"Base Cost: £{cost_breakdown['base_cost']:,.2f}")
        print("\nUndersupply Penalties:")
        print(f"  Heat: £{cost_breakdown['undersupply_breakdown']['heat']:,.2f}")
        print(f"  Light: £{cost_breakdown['undersupply_breakdown']['light']:,.2f}")
        print(f"  CO2: £{cost_breakdown['undersupply_breakdown']['co2']:,.2f}")
        print(f"\nTotal Cost: £{cost_breakdown['total_cost']:,.2f}")

    else:
        print("\nOptimization failed:", result.message)

    # Total runtime
    end_time = time.time()
    total_duration = end_time - start_time

    # Detailed timing breakdown
    print("\nTiming Breakdown:")
    print(f"Total:          {timedelta(seconds=total_duration)}")


if __name__ == "__main__":
    main()
