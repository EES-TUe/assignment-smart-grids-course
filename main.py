from typing import List
import numpy as np
import time

#import required .py files
from Simulator import Simulator, StrategyOrder
from DataClasses import PVInstallation, EVInstallation, Heatpump, Battery
import time

AMOUNT_OF_TIME_STEPS_IN_DAY = 96
AMOUNT_OF_DAYS_TO_SIMULATE = 364

def house_strategy(time_step : int, base_data : np.ndarray, pv : PVInstallation, ev : EVInstallation, batt : Battery, hp : Heatpump):
    pv.consumption[time_step] = pv.max 
    ev.consumption[time_step] = ev.max
    hp.consumption[time_step] = hp.min
    house_load = base_data[time_step] + pv.consumption[time_step] + ev.consumption[time_step] + hp.consumption[time_step]
    if house_load <= 0: # if the combined load is negative, charge the battery
        batt.consumption[time_step] = min(-house_load, batt.max)
    else: # always immediately discharge the battery
        batt.consumption[time_step] = max(-house_load, batt.min)

def pv_strategy(time_step : int, pv : PVInstallation):
    # Implement a nice pv strategy here
    pass

def ev_strategy(time_step : int, ev : EVInstallation):
    # Implement a nice ev strategy here
    pass

def hp_strategy(time_step : int, hp : Heatpump):
    # Implement a nice hp strategy here
    pass

def batt_strategy(time_step : int, batt : Battery):
    # Implement a nice battery strategy here
    pass

def neighborhood_strategy(time_step, baseloads, pvs : List[PVInstallation], evs : List[EVInstallation], hps : List[Heatpump], batteries : List[Battery]):
    # Implement a nice neigberhood strategy here
    pass

def main():
    #INITIALIZE SCENARIO
    sim_length = AMOUNT_OF_TIME_STEPS_IN_DAY * AMOUNT_OF_DAYS_TO_SIMULATE #Length of simulation (96 ptu's per day and 7 days)
    number_of_houses = 100
    
    strategy_order = [StrategyOrder.INDIVIDUAL, StrategyOrder.HOUSEHOLD, StrategyOrder.NEIGHBORHOOD]

    simulator = Simulator(control_order=strategy_order,
                          battery_strategy=batt_strategy, 
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
