from typing import List
import numpy as np
import time

from Simulator import Simulator, StrategyOrder
from DataClasses import PVInstallation, EVInstallation, Heatpump, Battery
import time
import constants

AMOUNT_OF_DAYS_TO_SIMULATE = 2  # 1, ..., 364

def pv_strategy(time_step : int, temperature_data : np.ndarray, renewable_share : np.ndarray, pv : PVInstallation):
    """
    Implement a nice pv strategy here

    Do this by setting a value for pv.consumption[time_step]
    This value should be <= 0
    """

    # Example:
    pv.consumption[time_step] = pv.max

def ev_strategy(time_step : int, temperature_data : np.ndarray, renewable_share : np.ndarray, ev : EVInstallation):
    """
    Implement a nice ev strategy here

    Do this by setting a value for ev.consumption[time_step]
    This value should be >= 0
    """

    # Example:
    ev.consumption[time_step] = ev.max

def hp_strategy(time_step : int, temperature_data : np.ndarray, renewable_share : np.ndarray, hp : Heatpump):
    """
    Implement a nice hp strategy here

    Do this by setting a value for hp.consumption[time_step]
    This value should be >= 0
    """

    # Example:
    hp.consumption[time_step] = hp.min

def batt_strategy(time_step : int, temperature_data : np.ndarray, renewable_share : np.ndarray, batt : Battery):
    """
    Implement a nice battery strategy here

    Do this by setting a value for batt.consumption[time_step]
    This value cam be smaller (discharging) or greater (charging) than 0
    """

    # Example: do nothing, determine the consumption of the battery in the house strategy
    pass

def house_strategy(time_step : int, temperature_data : np.ndarray, renewable_share : np.ndarray, base_data : np.ndarray, pv : PVInstallation, ev : EVInstallation, batt : Battery, hp : Heatpump):
    """
    Implement a nice house strategy here

    Do this by setting one or more of the following values:
    - pv.consumption[time_step]
    - ev.consumption[time_step]
    - hp.consumption[time_step]
    - batt.consumption[time_step]
    """

    # Example: only set batt.consumption[time_step]
    house_load = base_data[time_step] + pv.consumption[time_step] + ev.consumption[time_step] + hp.consumption[time_step]
    if house_load <= 0: # if the combined load is negative, charge the battery
        batt.consumption[time_step] = min(-house_load, batt.max)
    else: # discharge the battery otherwise
        batt.consumption[time_step] = max(-house_load, batt.min)

def neighborhood_strategy(time_step, temperature_data : np.ndarray, renewable_share : np.ndarray, baseloads : np.ndarray,
                          pvs : List[PVInstallation], evs : List[EVInstallation], hps : List[Heatpump], batteries : List[Battery]):
    """
    Implement a nice neighborhood strategy here

    Do this by setting on or more of the following values for the assets in pvs, evs, hps, and batteries
    - pv.consumption[time_step]
    - ev.consumption[time_step]
    - hp.consumption[time_step]
    - batt.consumption[time_step]
    """
    pass

def main():
    """
    Run this function to start a simulation
    """

    # Set up simulation
    sim_length = constants.AMOUNT_OF_TIME_STEPS_IN_DAY * AMOUNT_OF_DAYS_TO_SIMULATE
    number_of_houses = 100

    strategy_order = [StrategyOrder.INDIVIDUAL, StrategyOrder.HOUSEHOLD, StrategyOrder.NEIGHBORHOOD]

    simulator = Simulator(control_order=strategy_order,
                          battery_strategy=batt_strategy, 
                          hp_strategy=hp_strategy, 
                          pv_strategy=pv_strategy, 
                          ev_strategy=ev_strategy, 
                          neighborhood_strategy=neighborhood_strategy, 
                          house_strategy=house_strategy)
    simulator.initialize(sim_length, number_of_houses, "data/data.pkl", "data/reference_load.npy")

    # Run Simulation
    start_time = time.time()
    print("Start simulation")
    simulator.start_simulation()
    print("finished simulation")
    print(f'Duration: {time.time() - start_time} seconds')
    
    # Show Results
    simulator.print_metrics()
    simulator.plot_results()

if __name__ == '__main__':
    exit(main())
