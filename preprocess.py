import json
import pandas as pd


df = pd.read_excel('CoronavirusFacts.xlsx', sheet_name=1)
df.to_pickle("covidFacts.pickle")