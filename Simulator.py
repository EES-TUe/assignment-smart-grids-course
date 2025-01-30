import os.path
import pickle
from typing import List
import numpy as np
import matplotlib.pyplot as plt

from data_initialization import house

class Simulator:

    def __init__(self, battery_strategy, hp_strategy, pv_strategy, ev_strategy, neighborhood_strategy, house_strategy):
        self.list_of_houses : List[house] = []
        self.ren_share : np.ndarray = np.array([])
        self.temperature_data : np.ndarray = np.array([])
        self.batt_strategy = battery_strategy
        self.hp_strategy = hp_strategy
        self.pv_strategy = pv_strategy
        self.ev_strategy = ev_strategy
        self.house_strategy = house_strategy
        self.neighborhood_strategy = neighborhood_strategy
        self.total_load : np.ndarray = np.array([])

    def limit_ders(self,time_step):
        for house in self.list_of_houses:
            house.pv.limit(time_step)
            house.ev.limit(time_step)
            house.batt.limit(time_step)
            house.hp.limit(time_step)

    def initialize(self, sim_length,number_of_houses,path_to_pkl_data, path_to_reference_data):

        #Scenario Parameters
        np.random.seed(42) 
        self.total_load = np.zeros(sim_length)
    
        #Load pre-configured data
        if os.path.isfile(path_to_pkl_data): 
            self.sim_length = sim_length
            f = open(path_to_pkl_data, 'rb')
            scenario_data = pickle.load(f)
            baseloads = scenario_data['baseloaddata']
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
                list_of_houses.append(house(sim_length=sim_length, 
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

            self.list_of_houses : List[house] = list_of_houses
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
            self.reference_load = np.load("reference_load.npy")
        else:
            print(f"Path to reference data is invalid {path_to_reference_data}")

    def individual_strategy(self, time_step):
        for house in self.list_of_houses:
            house.pv.simulate_individual_entity(time_step)
            house.ev.simulate_individual_entity(time_step)
            house.hp.simulate_individual_entity(time_step)
            house.batt.simulate_individual_entity(time_step)

    def household_strategy(self, time_step):
        for house in self.list_of_houses:
            house.simulate_individual_entity(time_step)

    def group_strategy(self, time_step):
        self.neighborhood_strategy(time_step, self.base_loads, self.pvs, self.evs, self.hps, self.batteries)

    def control_strategy(self, time_step):
        self.individual_strategy(time_step)
        self.household_strategy(time_step)
        self.group_strategy(time_step)

    def response(self, time_step) -> float:
        total_load = 0
        for house in self.list_of_houses:
            house.ev.response(time_step)
            house.hp.response(time_step)
            house.batt.response(time_step)
            house_load = (house.base_data[time_step] + house.pv.consumption[time_step] + house.ev.consumption[time_step] + house.batt.consumption[time_step] + house.hp.consumption[time_step])
            total_load += house_load

        print(f"Total load on time step {time_step}: {total_load}")
        return total_load

    def do_time_step(self, time_step):
        self.limit_ders(time_step)
        self.control_strategy(time_step)
        self.total_load[time_step] = self.response(time_step)

    def start_simulation(self):
        for time_step in range(0, self.sim_length):
            self.do_time_step(time_step)
    
    def show_results(self):
        self.plot_grid()
        self.renewables()

    def plot_grid(self):

        plt.title("Total Load Neighborhood")
        plt.plot(self.reference_load, label="Reference")
        plt.plot(self.total_load, label="Simulation")
        plt.xlabel('PTU [-]')
        plt.ylabel('Kilowatt [kW]')
        plt.legend()
        plt.grid(True)
        plt.show()
    
        plt.figure()
        power_split = np.split(self.total_load, self.sim_length / 96)
        reference_split = np.split(self.reference_load, self.sim_length / 96)
        power_split = sum(power_split)
        reference_split = sum(reference_split)
        max_val = max(max(power_split),max(reference_split))
        power_split /= max_val
        reference_split /= max_val
    
        plt.title("Normalized Daily Power Profile")
        plt.plot(np.arange(1, 97) / 4, power_split, label = 'Simulation')
        plt.plot(np.arange(1, 97) / 4, reference_split, label = "Reference")
        plt.xlabel('Hour [-]')
        plt.ylabel('Relative Power [-]')
        plt.legend()
        plt.grid(True)
        plt.show()

    def renewables(self):
    
        energy_export = abs(sum(self.total_load[self.total_load<0]/4))
        energy_import = sum(self.total_load[self.total_load>0]/4)
        renewable_import = sum(self.total_load[self.total_load > 0] * self.ren_share[self.total_load > 0])/4
        renewable_percentage = renewable_import/energy_import*100
    
        print("Energy Exported: ", energy_export)
        print("Energy Imported: ", energy_import)
        print("Renewable Share:", renewable_percentage)
