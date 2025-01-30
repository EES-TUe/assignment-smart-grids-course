import numpy as np

class SimulationEntity:
    def __init__(self, strategy):
        self.strategy = strategy

    def simulate_individual_entity(self, time_step : int):
        pass

    def response(self, time_step : int):
        pass

    def limit(self, time_step : int):
        pass

class house(SimulationEntity):

    def __init__(self, sim_length, id, baseload, pv_data, ev_data, hp_data, temperature_data, house_strategy, pv_strategy, ev_strategy, batt_strategy, hp_strategy):
        super().__init__(house_strategy)
        #General House Parameters
        self.id = id + 1 #give each household an ID
        self.base_data = baseload #load baseload data into house

        #DERS
        self.pv = pv(pv_data,sim_length, pv_strategy)
        self.ev = ev(ev_data,sim_length, ev_strategy)
        self.batt = batt(sim_length, batt_strategy)
        self.hp = hp(sim_length, id, hp_data, temperature_data, hp_strategy)

    def simulate_individual_entity(self, time_step : int):
        return self.strategy(time_step, self.base_data, self.pv, self.ev, self.batt, self.hp)

class pv(SimulationEntity):
    def __init__(self,pv_data,sim_length,pv_strategy):
        super().__init__(pv_strategy)
        self.data = pv_data
        self.min = 0
        self.max = 0
        self.consumption = np.zeros(sim_length)

    def simulate_individual_entity(self, time_step : int):
        return self.strategy(time_step, self)

class ev(SimulationEntity):
    def __init__(self,ev_data,sim_length,ev_strategy):
        super().__init__(ev_strategy)
        self.min = 0
        self.max = 0
        self.consumption = np.zeros(sim_length)
        self.power_max = ev_data['charge_cap'] #kW
        self.size = ev_data['max_SoC']#kWh
        self.min_charge = ev_data['min_charge']
        self.energy = ev_data['start_SoC'] #energy in kWh in de battery, changes each timstep
        self.energy_history = np.zeros(sim_length) #array to store previous battery state of charge for analyzing later
        self.session = ev_data['EV_status'] #details of the location of the EV (-1 is not at home, other number indicates the session number)
        self.session_trip_energy = ev_data['Trip_Energy'] #energy required during session
        self.session_arrive = ev_data['T_arrival'] #arrival times of session
        self.session_leave = ev_data['T_leave'] #leave times of session

    def simulate_individual_entity(self, time_step : int):
        return self.strategy(time_step, self)
    
    def response(self, time_step):
        if time_step != 0: #skip first timestep because you will look back one timestep
            if self.session[time_step] == -1 and self.session[time_step - 1] != -1: #if the vehicle left the house this timestep, substract the energy lost during driving from the battery
                self.energy -= self.session_trip_energy[int(self.session[time_step - 1])]
                if self.energy <= 0:
                    self.energy = 0

        self.energy_history[time_step] = self.energy #save EV SoC for later analysis
        self.energy += self.consumption[time_step]/4 #update battery (note conversion from kW to kWh)
        if (0 > np.round(self.energy,4)) or (np.round(self.energy,4) > self.size): #double check if battery is too full or empty
            print("battery too empty/full: ", time_step)

    def limit(self, time_step):
        if self.session[time_step] == -1:  # vehicle not home, so minmax = [0,0]
            self.minmax = [0, 0]
        else:
            session = int(self.session[time_step]) #determine the ev charging session number
            # minimum power required to charge the EV to the "required energy" in the time where the vehicle is home
            required_energy = self.size #always charge to 100% SoC
            min_power = (max(0, (required_energy - self.energy))) * 4 #multiply by four because of conversion from kWh to kW
            time_left = self.session_leave[session] - time_left #determine how many timesteps are left before the vehicle leaves
            min_power = min(self.power_max, (min_power / time_left)) #determine the min power by dividing the required power by the number of timesteps left
            # max charge power possible
            energy_left = self.size - self.energy #this max power is either what is left to fully charge the battery or the max charging capability
            max_power = min(self.power_max, energy_left * 4)
    
            self.minmax = [min_power, max_power] #store value in house

class batt(SimulationEntity):
    def __init__(self,sim_length,batt_strategy):
        # Based on Tesla Powerwall https://www.tesla.com/sites/default/files/pdfs/powerwall/Powerwall_2_AC_Datasheet_EN_NA.pdf
        super().__init__(batt_strategy)
        self.min = 0
        self.max = 0
        self.consumption = np.zeros(sim_length)
        self.afrr = np.zeros(sim_length)
        self.power_max = 5 #kW
        self.size = 13.5 #kWh
        self.energy = 6.25 #energy in kWh in de battery at every moment in time
        self.energy_history = np.zeros(sim_length)

    def simulate_individual_entity(self, time_step : int):
        return self.strategy(time_step, self)
    
    def response(self, time_step):
        self.energy_history[time_step] = self.energy #save batt SoC for later analysis
        self.energy += self.consumption[time_step]/4 #update battery (note conversion from kW to kWh)

    def limit(self, time_step):
        dis_power = max(-(self.energy * 4), -self.power_max) #determine maximum discharge power (either what is left or max discharge power), this value is negative (multiplication by 4 for conversion from energy to power)
        charge_power = min((self.size - self.energy) * 4, self.power_max) #max charging power (either what is left to fully charge battery or max charge power), this value is positive
        self.min = dis_power
        self.max = charge_power

class hp(SimulationEntity):
    def __init__(self, sim_length : int, id : int, hp_data, T_ambient, hp_startegy):
        super().__init__(hp_startegy)

        #Thermal Properties House
        self.T_ambient = T_ambient
        self.temperatures = hp_data['temperatures']
        self.T_setpoint = 293
        self.T_min = 18+273
        self.T_max = 21+273
        self.super_matrix = hp_data['super_matrix'][id]
        self.a = hp_data['alpha'][id]
        self.v_part = hp_data['v_part'][id]
        self.b_part = hp_data['b_part'][id]
        self.M = hp_data['M'][id]
        self.f_inter = hp_data['f_inter']
        self.K_inv = hp_data["K_inv"][id]
        self.heat_demand_house = np.zeros(sim_length)

        self.heat_capacity_water = 4182  # [J/kg.K]
        #building properties
        self.nominal_power = 8000  # [W]       Nominal capacity of heat pump installation
        self.minimal_relative_load =  0.3  # [-]       Minimal operational capacity for heat pump to run
        # house tank properties
        self.house_tank_mass = 120  # [kg]      Mass of buffer = Volume of buffer (Water)
        self.house_tank_T_min_limit = 25  # [deg C]   Min temperature in the buffer tank
        self.house_tank_T_max_limit = 75  # [deg C]   Min temperature in the buffer tank
        self.house_tank_T_set = 40  # [deg C]   Temperature setpoint in buffer tank
        self.house_tank_T_init = 40  # [deg C]   Initial temperature in buffer tank
        self.house_tank_T = self.house_tank_T_init #Parameter initialized with initial temperature but changes over time
        self.min = 0
        self.max = 0
        self.consumption = np.zeros(sim_length)
        self.temperature_data = np.zeros((sim_length,2))
        self.actual = np.zeros(sim_length)

    def cop(self, T_tank, T_out):
        T_out = T_out - 273.15
        return 8.736555867367798 - 0.18997851 * (T_tank - T_out) + 0.00125921 * (T_tank - T_out) ** 2
    
    def simulate_individual_entity(self, time_step : int):
        return self.strategy(time_step, self)
    
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




