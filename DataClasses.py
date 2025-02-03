from typing import List, Dict
import numpy as np
import constants

TIME_STEP_SECONDS = constants.TIME_STEP_SECONDS

class SimulationEntity:
    """
    General Base class for all simulated entities
    
    Do not change!
    """
    def __init__(self, id : int, strategy):
        self.id = id
        self.strategy = strategy

    def simulate_individual_entity(self, time_step : int, temperature_data : np.ndarray, renewable_share : np.ndarray):
        pass

class Asset(SimulationEntity):
    """
    Base class for all simulated assets

    Do not change!
    """
    def __init__(self, id : int, sim_length: int, strategy):
        super().__init__(id, strategy)
        self.min = 0
        self.max = 0
        self.consumption = np.zeros(sim_length)

    def response(self, time_step : int):
        pass

    def check_response(self, time_step : int):
        pass

    def limit(self, time_step : int):
        pass

class House(SimulationEntity):
    """
    Stores the assets in the house and can execute the house strategy
    
    Do not change!
    """
    def __init__(self, id : int, sim_length: int, baseload : np.ndarray, pv_data : np.ndarray, ev_data : Dict,
                 hp_data : Dict, temperature_data : np.array, house_strategy, pv_strategy, ev_strategy, batt_strategy,
                 hp_strategy):

        super().__init__(id, house_strategy)
        #General House Parameters
        self.base_data = baseload # load base load data into house

        # Assets
        self.pv = PVInstallation(id, pv_data, sim_length, pv_strategy)
        self.ev = EVInstallation(id, ev_data, sim_length, ev_strategy)
        self.batt = Battery(id, sim_length, batt_strategy)
        self.hp = Heatpump(id, sim_length, hp_data, temperature_data, hp_strategy)

    def simulate_individual_entity(self, time_step : int, temperature_data : np.ndarray, renewable_share : np.ndarray):
        return self.strategy(time_step, temperature_data, renewable_share, self.base_data, self.pv, self.ev, self.batt, self.hp)

class PVInstallation(Asset):
    """
    You do not need to change this class, but you can use the .max_power for your pv strategy, and you can use the limit
    function for inspiration for your own strategy
    """

    def __init__(self, id : int, pv_data : np.ndarray, sim_length : int, pv_strategy):
        super().__init__(id, sim_length, pv_strategy)
        self.max_power = pv_data

    def simulate_individual_entity(self, time_step : int, temperature_data : np.ndarray, renewable_share : np.ndarray):
        return self.strategy(time_step, temperature_data, renewable_share, self)

    def response(self, time_step : int):
        # The PVInstallation does not need to update anything
        self.check_response()

    def check_response(self, time_step : int):
        if np.round(self.consumption[time_step], 4) > 0.0:
            raise ValueError(f"PV generation should be < 0")

        if np.round(self.consumption[time_step], 4) < self.max_power[time_step]:
            raise ValueError(f"PV generation should be lower than max power")

    
    def limit(self, time_step : int):
        """
        Two strategies are already implemented, representing a min and a max value the PV can generate:
        - min: fully curtail the PV
        - max: no curtailment, generate the max power
        """

        self.min = 0.0
        self.max = self.max_power[time_step]

class EVInstallation(Asset):
    """
    You do not need to change this class, but you can use the data in this class for your own strategies. You can also
    use the limit function for inspiration for your own strategy
    """

    def __init__(self, id, ev_data, sim_length,ev_strategy):
        super().__init__(id, sim_length, ev_strategy)
        self.power_max = ev_data['charge_cap'] #kW
        self.size = ev_data['max_SoC']#kWh
        self.min_charge = ev_data['min_charge']
        self.energy = ev_data['start_SoC'] #energy in kWh in de battery, changes each timstep
        self.energy_history = np.zeros(sim_length) #array to store previous battery state of charge for analyzing later
        self.session = ev_data['EV_status'] #details of the location of the EV (-1 is not at home, other number indicates the session number)
        self.session_trip_energy = ev_data['Trip_Energy'] #energy required during session
        self.session_arrive = ev_data['T_arrival'] #arrival times of session
        self.session_leave = ev_data['T_leave'] #leave times of session

    def simulate_individual_entity(self, time_step : int, temperature_data : np.ndarray, renewable_share : np.ndarray):
        return self.strategy(time_step, temperature_data, renewable_share, self)
    
    def response(self, time_step : int):
        if time_step != 0: #skip first timestep because you will look back one timestep
            # if the vehicle left the house this timestep, substract the energy lost during driving from the battery
            if self.session[time_step] == -1 and self.session[time_step - 1] != -1: 
                self.energy -= self.session_trip_energy[int(self.session[time_step - 1])]
                if self.energy <= 0:
                    self.energy = 0

        self.energy_history[time_step] = self.energy # save EV SoC for later analysis
        self.energy += self.consumption[time_step] * TIME_STEP_SECONDS / 3600  # update the battery

        self.check_response(time_step)

    def check_response(self, time_step : int):
        if np.round(self.consumption[time_step], 4) < 0.0:
            raise ValueError(f"Consumption of EV should be above 0.0")

        if np.round(self.consumption[time_step], 4) > self.power_max:
            raise ValueError(f"Consumption of EV should be below power_max")

        if np.round(self.energy, 4) < 0.0:
            raise ValueError(f"Energy in EV {self.id} is below 0")

        if np.round(self.energy, 4) > self.size:
            raise ValueError(f"Energy in EV {self.id} is above size")

    def limit(self, time_step):
        """
        Two strategies are already implemented, representing a min and a max value the EV can consume:
        - min: try to reach max state of charge during the session. Spread the load over the available time
        - max: try to reach the max state of charge during the session. As fast as possible.
        """
        
        if self.session[time_step] == -1:  # vehicle not home, so both min and max power are 0
            self.min = 0
            self.max = 0
        else:
            session_nr = int(self.session[time_step])
            required_energy = self.size #always charge to 100% SoC
            energy_to_charge = max(0, required_energy - self.energy)  # in kWh

            # Min strategy
            time_to_charge = (self.session_leave[session_nr] - time_step) * TIME_STEP_SECONDS / 3600  # in hours
            self.min = min(self.power_max, energy_to_charge / time_to_charge)

            # Max strategy
            power_to_charge = energy_to_charge / (TIME_STEP_SECONDS / 3600)  # power required to charge all energy this step in kW
            self.max = min(self.power_max, power_to_charge)


class Battery(Asset):
    """
    You do not need to change this class, but you can use the data in this class for your own strategies. You can also
    use the limit function for inspiration for your own strategy
    """
    
    def __init__(self, id, sim_length, batt_strategy):
        # Based on Tesla Powerwall
        # https://www.tesla.com/sites/default/files/pdfs/powerwall/Powerwall_2_AC_Datasheet_EN_NA.pdf
        super().__init__(id, sim_length, batt_strategy)
        self.power_max = 5 #kW
        self.size = 13.5 #kWh
        self.energy = 6.25 #energy in kWh in de battery at every moment in time
        self.energy_history = np.zeros(sim_length)

    def simulate_individual_entity(self, time_step : int, temperature_data : np.ndarray, renewable_share : np.ndarray):
        return self.strategy(time_step, temperature_data, renewable_share, self)
    
    def response(self, time_step):
        self.energy_history[time_step] = self.energy #save batt SoC for later analysis
        self.energy += self.consumption[time_step] * TIME_STEP_SECONDS / 3600 # update battery

    def check_response(self, time_step : int):
        if np.round(self.consumption[time_step], 4) < - self.power_max:
            raise ValueError(f"Consumption of EV should be below power_max")

        if np.round(self.consumption[time_step], 4) > self.power_max:
            raise ValueError(f"Consumption of EV should be below power_max")

        if np.round(self.energy, 4) < 0.0:
            raise ValueError(f"Energy in EV {self.id} is below 0")

        if np.round(self.energy, 4) > self.size:
            raise ValueError(f"Energy in EV {self.id} is above size")


    def limit(self, time_step):
        """
        Two strategies are already implemented, representing a min and a max value the battery can (dis)charge:
        - min: discharge as much as possible, either all energy in the battery, or max discharge power
        - max: charge as much as possible, either the remaining part in the battery, or max charge power
        """

        # Min Strategy (discharge, negative)
        power_to_charge = - self.energy / (TIME_STEP_SECONDS / 3600)  # power needed to empty the battery this time step
        self.min = max(power_to_charge, - self.power_max)

        # Max Strategy (charge, positive)
        power_to_charge = (self.size - self.energy) / (TIME_STEP_SECONDS / 3600)  # power needed to fill the battery this time step
        self.max = min(power_to_charge, self.power_max)

class Heatpump(Asset):
    def __init__(self, id, sim_length : int, hp_data, T_ambient, hp_strategy):
        super().__init__(id, sim_length, hp_strategy)

        # Thermal Properties House, DO NOT TOUCH OR USE
        self.T_ambient = T_ambient
        self.temperatures = hp_data['temperatures']
        self.super_matrix = hp_data['super_matrix'][id]
        self.a = hp_data['alpha'][id]
        self.v_part = hp_data['v_part'][id]
        self.b_part = hp_data['b_part'][id]
        self.M = hp_data['M'][id]
        self.f_inter = hp_data['f_inter']
        self.K_inv = hp_data["K_inv"][id]
        self.heat_demand_house = np.zeros(sim_length)
        self.heat_capacity_water = 4182  # [J/kg.K]

        # Building properties
        self.T_setpoint = 21 + 273  # set point temperature in the house
        self.T_min = 18 + 273
        self.T_max = 21 + 273
        self.nominal_power = 8000  # [W]       Nominal capacity of heat pump installation
        self.minimal_relative_load =  0.3  # [-]       Minimal operational capacity for heat pump to run
        self.house_tank_mass = 120  # [kg]      Mass of buffer = Volume of buffer (Water)
        self.house_tank_T_min_limit = 25  # [deg C]   Min temperature in the buffer tank
        self.house_tank_T_max_limit = 75  # [deg C]   Min temperature in the buffer tank
        self.house_tank_T_set = 40  # [deg C]   Temperature setpoint in buffer tank
        self.house_tank_T_init = 40  # [deg C]   Initial temperature in buffer tank
        self.house_tank_T = self.house_tank_T_init # Parameter initialized with initial temperature but changes over time
        self.temperature_data = np.zeros((sim_length,2))

    def cop(self, T_tank, T_out):
        T_out = T_out - 273.15
        return 8.736555867367798 - 0.18997851 * (T_tank - T_out) + 0.00125921 * (T_tank - T_out) ** 2
    
    def simulate_individual_entity(self, time_step : int, temperature_data : np.ndarray, renewable_share : np.ndarray):
        return self.strategy(time_step, temperature_data, renewable_share, self)
    
    def response(self, time_step):
        T_ambient = self.T_ambient[time_step]

        heat_to_house_tank = (self.consumption[time_step]*(1000*900)) * self.cop(self.house_tank_T_set, T_ambient[0])

        # calculate the heat going from the house tank to the house
        dT_tank_house = (heat_to_house_tank - self.heat_demand_house[time_step]) / (self.house_tank_mass * self.heat_capacity_water)
        house_tank_T = self.house_tank_T + dT_tank_house
        if house_tank_T < self.house_tank_T_min_limit:  # if demand is too great, the demand will be 0 but the tank will heat up
            self.heat_demand_house[time_step] = 0

        # calculate the corresponding temperature in the house tank
        heat_to_house = self.heat_demand_house[time_step]  # converting the demand to the actual amount that goes in to the house
        dT_tank_house = (heat_to_house_tank - heat_to_house) / (self.house_tank_mass * self.heat_capacity_water)
        self.house_tank_T = self.house_tank_T + dT_tank_house

        heat_power_to_house = heat_to_house/900

        # Update the house temperature given the heat power to house
        q_inter = heat_power_to_house * self.f_inter
        b = np.matmul(self.K_inv, q_inter) + self.b_part[time_step]
        self.temperatures = np.matmul(self.super_matrix, self.temperatures - b) + self.a[time_step] * 900 + b

        self.temperature_data[time_step] = np.array([self.house_tank_T, self.temperatures[1]])

    def limit(self, time_step: int):
        T_ambient = self.T_ambient[time_step]
        # calculate the heat demands for the house to keep temperature at setpoint
        v = np.matmul(self.super_matrix, self.temperatures) + self.v_part[time_step]
        heat_demand_house = max(0, ((self.T_setpoint - v[1])/(self.M[1, 1] * self.f_inter[1] + self.M[1, 2] * self.f_inter[2])) * 900)
    
        #DETERMINING MIN -> keep the household and tank temperature constant
        tank_T_difference_no_hp = heat_demand_house / (self.house_tank_mass * self.heat_capacity_water)
        tank_T_no_hp = self.house_tank_T - tank_T_difference_no_hp
    
        # calculate the resulting heat to the tank
        # Provide no heat to house tank if its temperature is above the set temperature
        if tank_T_no_hp > self.house_tank_T_set:
           min_heat_to_house_tank = 0
        else:
            # supply up to set point if possible
           min_dT_tank_house = self.house_tank_T_set - tank_T_no_hp
           min_heat_to_house_tank = min(self.nominal_power*900,(self.house_tank_mass * self.heat_capacity_water)*min_dT_tank_house + heat_demand_house)
    
        #DETERIMINING HEAT_TANK -> keep temperature household temperature constant but heat up tank temperature
        # supply to max temperature if possible
        max_dT_tank_house = self.house_tank_T_max_limit - tank_T_no_hp
        max_heat_to_house_tank = min(self.nominal_power*900,(self.house_tank_mass * self.heat_capacity_water)*max_dT_tank_house + heat_demand_house)
    
    
        min_power = min_heat_to_house_tank/self.cop(self.house_tank_T_set, T_ambient[0])
        max_power = max_heat_to_house_tank/self.cop(self.house_tank_T_set, T_ambient[0])
    
        self.min = min_power / (1000*900)
        self.max = max_power / (1000*900)
        self.heat_demand_house[time_step] = heat_demand_house #value needs to be stored for response.py




