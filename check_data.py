import pickle

f = open('data.pkl', 'rb')
scenario_data = pickle.load(f)
print(len(scenario_data['ev_data'][0]['Trip_Energy']))
print(scenario_data.keys())