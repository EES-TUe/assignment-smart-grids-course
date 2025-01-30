import os.path
import pickle
import numpy as np

from data_initialization import batt, ev, house, hp, pv

class Simulator:
    def initialize(sim_length,number_of_houses,path_to_data):

        #Scenario Parameters
        np.random.seed(42) # LvS Any particular reason for this?
    
        #Load pre-configured data
        if os.path.isfile(path_to_data): 
            f = open(path_to_data, 'rb')
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
                list_of_houses.append(house(sim_length,nmb,baseloads[distribution[nmb]],pv_data[distribution[nmb]],ev_data[distribution[nmb]],hp_data))

            return [list_of_houses,ren_share,temperature_data]
        else:
            print(f"Path to data is invalid {path_to_data}")

    def house_strategy(self, time_step : int, pv : pv, ev : ev, batt : batt, hp : hp):
        pv.consumption[time_step] = pv.minmax[1] #The PV wil always generate maximum power
        ev.consumption[time_step] = ev.minmax[1] #The EV will, if connected, always charge with maximum power
        hp.consumption[time_step] = hp.minmax[0] #The HP will keep the household temperature constant
        house_load = base_data[time_step] + pv.consumption[time_step] + ev.consumption[time_step] + hp.consumption[time_step]
        if house_load <= 0: #if the combined load is negative, charge the battery
            batt.consumption[time_step] = min(-house_load, batt.minmax[1])
        else: #always immediately discharge the battery
            batt.consumption[time_step] = max(-house_load, batt.minmax[0])