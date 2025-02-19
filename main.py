from typing import List
import numpy as np
import time

from Simulator import Simulator, StrategyOrder
from ModelClasses import PVInstallation, EVInstallation, Heatpump, Battery
import time
from Vizualizer import Vizualizer
import constants

TIME_STEP_SECONDS = constants.TIME_STEP_SECONDS

def pv_strategy(time_step : int, temperature_data : np.ndarray, renewable_share : np.ndarray, pv : PVInstallation):
    """
    Implement a nice pv strategy here

    Do this by setting a value for pv.consumption[time_step]
    This value should be <= 0
    """

    # Example 1: fully curtail the PV
    # pv.consumption[time_step] = 0.0

    # Example 2: no curtailment, generate the max power
    pv.consumption[time_step] = pv.max_power[time_step]

def ev_strategy(time_step : int, temperature_data : np.ndarray, renewable_share : np.ndarray, ev : EVInstallation):
    """
    Implement a nice ev strategy here!

    Do this by setting a value for ev.consumption[time_step]
    This value should be >= 0
    """

    # Example 1: charge as fast as technically possible
    # ev.consumption[time_step] = ev.min
    ev.consumption[time_step] = ev.max

    # Example 2: try to reach max state of charge during the session. Divide the load over the available time
    """
    session_nr = int(ev.session[time_step])
    required_energy = ev.size  # always charge to 100% SoC
    energy_to_charge = max(0, required_energy - ev.energy)  # in kWh
    time_to_charge = (ev.session_leave[session_nr] - time_step) * TIME_STEP_SECONDS / 3600  # in hours
    ev.consumption[time_step] = min(ev.power_max, energy_to_charge / time_to_charge)
    """

def hp_strategy(time_step : int, temperature_data : np.ndarray, renewable_share : np.ndarray, hp : Heatpump):
    """
    Implement a nice hp strategy here!

    Do this by setting a value for hp.consumption[time_step]
    This value should be >= 0
    """
    # Example 1: Consume power such that the house temperature is kept at the set point and such that the tank
    # is heated as much as possible
    """
    hp.consumption[time_step] = hp.max  # convert to kW
    """

    # Example 2 : Consume power such that the house temperature is kept at the set point and such that the tank
    # temperature does not reach below its set point
    # All these calculations are in SI units, that is: Kelvin, Joule, and seconds
    
    # XEM PHẦN limit_hp
    # T_ambient = temperature_data[time_step]

    # # Calculate the amount of heat needed to keep the house temperature constant at the set point
    # heat_demand_house = hp.calculate_heat_demand_house(time_step, hp.T_set)

    # # Calculate whether the tank temperature will reach below its set point if the house is heated
    # tank_T_difference_no_hp = heat_demand_house / (hp.tank_mass * hp.heat_capacity_water)
    # tank_T_no_hp = hp.tank_T - tank_T_difference_no_hp

    # if tank_T_no_hp > hp.tank_T_set:
    #     heat_power_to_tank = 0.0  # No heat needed for the tank
    # else:
    #     # supply up to set point if possible
    #     heat_to_tank = hp.tank_mass * hp.heat_capacity_water * (hp.tank_T_set - tank_T_no_hp) + heat_demand_house
    #     heat_power_to_tank = min(hp.nominal_power, heat_to_tank / TIME_STEP_SECONDS)
    #     # TIME_STEP_SECONDS = 900, chuyển về power nên chia cho time T, norminal power k * với 900 nữa

    # # Convert the heating power to electrical power using the Coefficient of Performance
    # power = heat_power_to_tank / hp.cop(hp.tank_T_set, T_ambient)
    # hp.consumption[time_step] = power / 1000.0  # convert to kW
    # Nếu k có strategy thì dùng min_max?
    hp.consumption[time_step] = hp.min

    # HP không xét min, max nữa mà dùng T_set cùng với heat_demand_house nếu nhiệt độ tank chưa có hp nhỏ hơn Tset. 
    # Lúc trước min thì k tính đến heat demand house, max thì dùng t_max_limit cùng với heat demand house.

def batt_strategy(time_step : int, temperature_data : np.ndarray, renewable_share : np.ndarray, batt : Battery):
    """
    Implement a nice battery strategy here

    Do this by setting a value for batt.consumption[time_step]
    This value cam be smaller (discharging) or greater (charging) than 0
    """
    # batt.consumption[time_step] = 0

    # Example: do nothing, determine the consumption of the battery in the house strategy
    pass

def house_strategy(time_step : int, temperature_data : np.ndarray, renewable_share : np.ndarray, base_data : np.ndarray,
                   pv : PVInstallation, ev : EVInstallation, batt : Battery, hp : Heatpump):
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
    # Only discharge battery during peak hour: 18-20
    elif time_step%96 >18*4 and time_step%96 <20*4:
        batt.consumption[time_step] = max(-house_load, batt.min)
    else:
        batt.consumption[time_step] = 0

def neighborhood_strategy(time_step, temperature_data : np.ndarray, renewable_share : np.ndarray, baseloads : np.ndarray,
                          pvs : List[PVInstallation], evs : List[EVInstallation], hps : List[Heatpump], batteries : List[Battery]):
    """
    Implement a nice neighborhood strategy here

    Do this by setting on or more of the following values for the assets in pvs, evs, hps, and batteries
    - pv.consumption[time_step] for pv in pvs
    - ev.consumption[time_step] for ev in evs
    - hp.consumption[time_step] for hp in hps
    - batt.consumption[time_step] for batt in batteries
    """
    pass

def main():
    """
    Run this function to start a simulation
    """

    # Set up simulation
    number_of_houses = 100  # <= 100
    amount_of_days_to_simulate = 5  # <= 364
    sim_length = amount_of_days_to_simulate * constants.AMOUNT_OF_TIME_STEPS_IN_DAY

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
    vizualizer = Vizualizer(sim_length)
    vizualizer.plot_results_reference_and_total_load(simulator.reference_load, simulator.total_load)
    vizualizer.print_metrics_renewable_share_total_load(simulator.ren_share, simulator.total_load)

if __name__ == '__main__':
    exit(main())
