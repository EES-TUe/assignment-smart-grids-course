from enum import Enum
import os.path
import pickle
from typing import List
import numpy as np
import matplotlib.pyplot as plt

import constants
from DataClasses import House

class StrategyOrder(Enum):
    INDIVIDUAL = 1
    HOUSEHOLD = 2
    NEIGHBORHOOD = 3

class Simulator:
    """
    This class does several things:
    - Builds the neighborhood to simulate (.initialize)
    - Loops over all the time steps in the simulation and executes the control strategies (.control_strategy, ...)
    - Plots the results (.plot_results)
    - Calculates some metrics (.print_metrics)
    
    Please don't touch the parts related to the first two functionalities!
    """
    
    def __init__(self, control_order, battery_strategy, hp_strategy, pv_strategy, ev_strategy, neighborhood_strategy, house_strategy):
        self.list_of_houses : List[House] = []
        self.ren_share : np.ndarray = np.array([])
        self.temperature_data : np.ndarray = np.array([])
        self.batt_strategy = battery_strategy
        self.hp_strategy = hp_strategy
        self.pv_strategy = pv_strategy
        self.ev_strategy = ev_strategy
        self.house_strategy = house_strategy
        self.neighborhood_strategy = neighborhood_strategy
        self.total_load : np.ndarray = np.array([])
        self.control_order : List[StrategyOrder] = control_order

    def limit_ders(self, time_step : int):
        for house in self.list_of_houses:
            house.pv.limit(time_step)
            house.ev.limit(time_step)
            house.batt.limit(time_step)
            house.hp.limit(time_step)

    def initialize(self, sim_length : int, number_of_houses : int, path_to_pkl_data : str, path_to_reference_data : str):
        #Scenario Parameters
        np.random.seed(42) 
        self.total_load = np.zeros(sim_length)
    
        #Load pre-configured data
        if os.path.isfile(path_to_pkl_data): 
            self.sim_length = sim_length
            f = open(path_to_pkl_data, 'rb')
            scenario_data = pickle.load(f)
            baseloads = scenario_data['baseloaddata']

            if number_of_houses > len(baseloads) or sim_length > baseloads[0].size:
                raise ValueError(f"number_of_houses <= {len(baseloads)} and sim_length <= {baseloads[0].size}")

            pv_data = scenario_data['irrdata']
            ev_data = scenario_data["ev_data"]
            hp_data = scenario_data['hp_data']
            temperature_data = hp_data["ambient_temp"]
            ren_share = scenario_data['ren_share']
            #determine distribution of data
            distribution = np.arange(number_of_houses)
            np.random.shuffle(distribution)
        
            #create a list containing all the household data and parameters
            list_of_houses = []
            for nmb in range(number_of_houses):
                list_of_houses.append(House(sim_length=sim_length,
                                            id=nmb, 
                                            baseload=baseloads[distribution[nmb]], 
                                            pv_data=pv_data[distribution[nmb]], 
                                            ev_data=ev_data[distribution[nmb]], 
                                            hp_data=hp_data, 
                                            temperature_data=temperature_data,
                                            house_strategy=self.house_strategy,
                                            pv_strategy=self.pv_strategy,
                                            ev_strategy=self.ev_strategy,
                                            batt_strategy=self.batt_strategy,
                                            hp_strategy=self.hp_strategy))

            self.list_of_houses : List[House] = list_of_houses
            self.ren_share = ren_share
            self.temperature_data = temperature_data
            self.hps = [house.hp for house in self.list_of_houses]
            self.evs = [house.ev for house in self.list_of_houses]
            self.pvs = [house.pv for house in self.list_of_houses]
            self.batteries = [house.batt for house in self.list_of_houses]
            self.ev_data = ev_data
            self.base_loads = [house.base_data for house in self.list_of_houses]
        else:
            print(f"Path to pickle data is invalid {path_to_pkl_data}")

        if os.path.isfile(path_to_reference_data):
            self.reference_load = np.load(path_to_reference_data)
        else:
            print(f"Path to reference data is invalid {path_to_reference_data}")

    def individual_strategy(self, time_step : int):
        for house in self.list_of_houses:
            house.pv.simulate_individual_entity(time_step, self.ren_share, self.temperature_data)
            house.ev.simulate_individual_entity(time_step, self.ren_share, self.temperature_data)
            house.hp.simulate_individual_entity(time_step, self.ren_share, self.temperature_data)
            house.batt.simulate_individual_entity(time_step, self.ren_share, self.temperature_data)

    def household_strategy(self, time_step : int):
        for house in self.list_of_houses:
            house.simulate_individual_entity(time_step, self.ren_share, self.temperature_data)

    def group_strategy(self, time_step : int):
        self.neighborhood_strategy(time_step, self.temperature_data, self.ren_share, self.base_loads, self.pvs, self.evs, self.hps, self.batteries)

    def control_strategy(self, time_step : int):
        for control_strategy_order in self.control_order:
            if control_strategy_order == StrategyOrder.HOUSEHOLD:
                self.household_strategy(time_step)
            if control_strategy_order == StrategyOrder.INDIVIDUAL:
                self.individual_strategy(time_step)
            if control_strategy_order == StrategyOrder.NEIGHBORHOOD:
                self.group_strategy(time_step)

    def response(self, time_step : int) -> float:
        total_load = 0
        for house in self.list_of_houses:
            house.ev.response(time_step)
            house.hp.response(time_step)
            house.batt.response(time_step)
            house_load = (house.base_data[time_step] + house.pv.consumption[time_step] + house.ev.consumption[time_step] + house.batt.consumption[time_step] + house.hp.consumption[time_step])
            total_load += house_load
        return total_load

    def do_time_step(self, time_step : int):
        self.limit_ders(time_step)
        self.control_strategy(time_step)
        self.total_load[time_step] = self.response(time_step)

    def start_simulation(self):
        for time_step in range(0, self.sim_length):
            self.do_time_step(time_step)

            # print progress
            if time_step % int(self.sim_length // 100) == 0:
                print(f"Progress: {time_step / self.sim_length:.1%}")

    def plot_results(self):
        """
        Creates two plots:
        - The total load of the neighborhood over time, compared with a reference
        - The normalized daily profile of the neighborhood, compared with a reference

        Feel free to include more plots if you want
        """

        # Plot total calculated load and the reference load
        reference_load = self.reference_load[0:self.sim_length]
        plt.title("Total Load Neighborhood")
        plt.plot(reference_load, label="Reference")
        plt.plot(self.total_load, label="Simulation")
        plt.xlabel('PTU [-]')
        plt.ylabel('Kilowatt [kW]')
        plt.legend()
        plt.grid(True)
        plt.show()

        # Calculate average daily profile
        amount_of_time_steps_in_day = constants.AMOUNT_OF_TIME_STEPS_IN_DAY
        time_step_seconds = constants.TIME_STEP_SECONDS

        power_split = np.split(self.total_load, self.sim_length / amount_of_time_steps_in_day)
        reference_split = np.split(reference_load, self.sim_length / amount_of_time_steps_in_day)
        power_split = sum(power_split)
        reference_split = sum(reference_split)
        max_val = max(max(power_split),max(reference_split))
        power_split /= max_val
        reference_split /= max_val
    
        # Plot the average daily profiles
        plt.title("Normalized Daily Power Profile")
        plt.plot(np.arange(1, amount_of_time_steps_in_day + 1) * time_step_seconds / 3600, power_split, label = 'Simulation')
        plt.plot(np.arange(1, amount_of_time_steps_in_day + 1) * time_step_seconds / 3600, reference_split, label = "Reference")
        plt.xlabel('Hour [-]')
        plt.ylabel('Relative Power [-]')
        plt.legend()
        plt.grid(True)
        plt.show()

    def print_metrics(self):
        """
        Calculates 3 metrics:
        - Total energy exported to the grid
        - Total energy imported from the grid
        - Percentage of imported energy to be from renewables

        Feel free to include more metrics if you want
        """

        time_step_seconds = constants.TIME_STEP_SECONDS
        ren_share = self.ren_share[0: self.sim_length]

        # Calculate metrics
        energy_export = abs(sum(self.total_load[self.total_load < 0] * time_step_seconds/ 3600))
        energy_import = sum(self.total_load[self.total_load>0] * time_step_seconds/ 3600)
        renewable_import = sum(self.total_load[self.total_load > 0] * ren_share[self.total_load > 0]) * time_step_seconds/ 3600
        renewable_percentage = renewable_import/energy_import * 100

        print("METRICS:")
        print("---------------------------------------")
        print(f"Energy Exported: {energy_export} kWh")
        print(f"Energy Imported: {energy_import} kWh")
        print(f"Share Renewable Energy Imported: {renewable_percentage} %")
