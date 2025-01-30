from typing import List
import numpy as np
import time

#import required .py files
from Simulator import Simulator
from data_initialization import pv, ev, hp, batt
import time

def house_strategy(time_step : int, base_data : np.ndarray, pv : pv, ev : ev, batt : batt, hp : hp):
    pv.consumption[time_step] = pv.max 
    ev.consumption[time_step] = ev.max
    hp.consumption[time_step] = hp.min
    house_load = base_data[time_step] + pv.consumption[time_step] + ev.consumption[time_step] + hp.consumption[time_step]
    if house_load <= 0: # if the combined load is negative, charge the battery
        batt.consumption[time_step] = min(-house_load, batt.max)
    else: # always immediately discharge the battery
        batt.consumption[time_step] = max(-house_load, batt.min)

def pv_strategy(time_step : int, pv : pv):
    # Implement a nice pv strategy here
    pass

def ev_strategy(time_step : int, ev : ev):
    # Implement a nice ev strategy here
    pass

def hp_strategy(time_step : int, hp : hp):
    # Implement a nice hp strategy here
    pass

def batt_strategy(time_step : int, batt : batt):
    # Implement a nice battery strategy here
    pass

def neighborhood_strategy(time_step, baseloads, pvs : List[pv], evs : List[ev], hps : List[hp], batteries : List[batt]):
    # Implement a nice neigberhood strategy here
    pvs[0].consumption[time_step] # pv data of first house with time_step
    evs[0].consumption[time_step] # ev data of first house with time_step
    hps[0].consumption[time_step] # hp data of first house with time_step
    baseloads[0][time_step] # base_load data of first house with time_step
    batteries[0].consumption[time_step] # battery data of first house with time_step

def main():
    #INITIALIZE SCENARIO
    sim_length = 96*1*52 #Length of simulation (96 ptu's per day and 7 days)
    number_of_houses = 100
    simulator = Simulator(battery_strategy=batt_strategy, 
                          hp_strategy=hp_strategy, 
                          pv_strategy=pv_strategy, 
                          ev_strategy=ev_strategy, 
                          neighborhood_strategy=neighborhood_strategy, 
                          house_strategy=house_strategy)
    simulator.initialize(sim_length, number_of_houses, "data.pkl", "reference_load.npy")

    start_time = time.time()
    print("Start simulation")
    simulator.start_simulation()
    print("finished simulation")
    print(f'Duration: {time.time() - start_time} seconds')
    simulator.show_results()

if __name__ == '__main__':
    exit(main())
