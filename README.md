# Code for the assginment of 5SEF0
The simulation code for the course: 5SEF0 Smart grids, ICT and electricity markets

## User guide

### Running the code
To be able to run the code execute the following steps:

1. Create a new python virtual environment (optional).
2. Download the data from canvas and place it in a folder called `data`.
3. run `pip install -r requirements.txt`
4. run `python main.py`

A simulation should now start and when the simulation sucessfully finishes a plot should be shown and the following output in the console should be shown:
```
PS C:\Users\20180029\repos\assignment-smart-grids-course> python main.py
Start simulation
finished simulation
Duration: 78.59630060195923 seconds
Energy Exported:  2586.7528469028875
Energy Imported:  639472.100936528
Renewable Share: 16.2445571647953
```

### Making changes
In principle the only changes required to implement different strategies should be made in `main.py`.

Strategies can be implemented on three different levels. On the household level, individual DER level and neigborhood level. These strategies are executed in an order to be defined by you.

```python
def house_strategy(time_step : int, 
                    temperature_data : np.ndarray, 
                    renewable_share : np.ndarray,
                    base_data : np.ndarray, 
                    pv : PVInstallation, 
                    ev : EVInstallation, 
                    batt : Battery, 
                    hp : Heatpump):

    pv.consumption[time_step] = pv.max 
    ev.consumption[time_step] = ev.max
    hp.consumption[time_step] = hp.min
    house_load = base_data[time_step] + pv.consumption[time_step] + 
        ev.consumption[time_step] + hp.consumption[time_step]
    if house_load <= 0: # if the combined load is negative, charge the battery
        batt.consumption[time_step] = min(-house_load, batt.max)
    else: # always immediately discharge the battery
        batt.consumption[time_step] = max(-house_load, batt.min)
```
The first level is the household level, in this function a strategy can be implemented that holds for every individual household. The above code snippit shows a strategy where pv and ev consumption is always set the to the maximum and the heatpump consumption is set to its minimal value. Next, depending on the resulting total load on the house the battery is either charged or discharged.

```python
def pv_strategy(time_step : int, temperature_data : np.ndarray, renewable_share : np.ndarray,
                pv : PVInstallation):
    pv.consumption[time_step] = pv.max
```
The second level is on the level of individual DERs. The above example highligts a pv strategy where similar to the household strategy the consumption of pv is set to the maximum possible value.

```python
def neighborhood_strategy(time_step, 
                          temperature_data : np.ndarray, 
                          renewable_share : np.ndarray,
                          baseloads, pvs : List[PVInstallation], 
                          evs : List[EVInstallation], 
                          hps : List[Heatpump], 
                          batteries : List[Battery]):
    pvs[0].consumption[time_step] = pvs[0].max
```
The final level of strategy is on the level of neighborhoods. Here a strategy can be implemented that holds on the level of all the houses in the dataset. In the example above the pv consumption of the first house is set to its maximum value. Observe that you have the possibility to change consumption patterns of different houses depending on what other houses are doing.

Finally, in the `main.py` there is a line stating the order of the strategies:
```python
strategy_order = [StrategyOrder.INDIVIDUAL, StrategyOrder.HOUSEHOLD, StrategyOrder.NEIGHBORHOOD]
```
This determines the order in which the different strategies are executed. In the example above first, the individual DER strategies are executed then the household strategy and finally the neigborhood strategy. 
```python
strategy_order = [StrategyOrder.HOUSEHOLD, StrategyOrder.INDIVIDUAL, StrategyOrder.NEIGHBORHOOD, StrategyOrder.INDIVIDUAL]
```
Other orders of the strategies are possible such as the one in the above example.