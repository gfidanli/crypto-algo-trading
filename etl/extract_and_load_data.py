# Import requirements
import pandas as pd
import cbpro
from datetime import datetime, timedelta
import urllib.request
import json
import time
import sqlite3
import sys

# sys.path.insert(1, '../inputs/')
# from apis import lunarCrush_API

# Make using PublicClient Methods easier
public_client = cbpro.PublicClient()

# Create function that allows for parameterization during the API call
def get_end_date(start_date,days):
    """ Given a start date in datetime format, 
        calculate the end date in datetime format
        based on the number of days provided."""
    
    end_date = start_date + timedelta(days=days)
    return end_date

# Get list of crypto currencies available on CoinbasePro
currencies = public_client.get_currencies()

currency_ids = []

for currency in currencies:
    currency_ids.append(currency['id'])

# ========================
#     Database Set-up
# ========================

# Create folder for the database file, give full permissions
import os
os.system("mkdir -m 777 db")

# Create connection
conn = sqlite3.connect('../db/crypto-analysis.db')
c = conn.cursor()

# Drop Tables
c.execute('''DROP TABLE IF EXISTS coinbase''')
c.execute('''DROP TABLE IF EXISTS lunarCrush''')

conn.commit()

# ========================
# CoinbasePro Data Extract
# ========================

# Containers
historical_data = {}
symbol = []
dates = []
low = []
high = []
opn = []
close = []
volume = []

# Parameters
start = '2015-01-01'
time_delta = 300
granularity = 86400 #Daily candles
today = datetime.now()

# Pull the data and save to DataFrame
print("Extracting CoinbasePro data...")
for c in currency_ids:
    
    start_date = datetime.strptime(start,'%Y-%m-%d')
    
    while start_date <= today:
        
        end_date = get_end_date(start_date,time_delta)
        
        # Adjust for end_date being in the future
        if end_date > today:
            end_date = today

        historic_rates = public_client.get_product_historic_rates(
            f"{c}-USD", 
            start=datetime.strftime(start_date,'%Y-%m-%d'), 
            end=datetime.strftime(end_date,'%Y-%m-%d'), 
            granularity=granularity
        )

        # Handle case where there is no data available
        # Return from API call will be in dict format if no data is availble
        if type(historic_rates) is not dict: 
            try:

                for day in historic_rates:
                    
                    # Date from timestamp needs to be adjusted to reflect actual value
                    date_clean = datetime.fromtimestamp(day[0]) + timedelta(days=1)
                    date_clean = datetime.strftime(date_clean,'%Y-%m-%d')

                    symbol.append(c)
                    dates.append(date_clean)
                    low.append(day[1])
                    high.append(day[2])
                    opn.append(day[3])
                    close.append(day[4])
                    volume.append(day[5])
            
            except Exception as e:
                print('c')
                print(day[0])
                print(e)

        # Calculate new start date to use
        start_date = end_date + timedelta(days=1)

# Create DataFrame
data = {
    'symbol':symbol,
    'date':dates,
    'high':high,
    'low':low,
    'open':opn,
    'close':close,
    'volume':volume
}
pd.DataFrame(data).to_sql('coinbase', conn, if_exists='replace', index=False)
print("CoinbasePro data saved to database.")

# =======================
# LunarCrush Data Extract
# =======================

# # For each asset, get the timeseries information and create one dataframe
# asset_list = []
# today = datetime.now()

# # API Call params
# params = {
#     'site':"https://api.lunarcrush.com/v2?",
#     'endpoint':'assets',
#     'interval':'day',
#     'start':'2015-01-01',
#     'data_points':300, # Set to match coinbase pro API, max is 720
# }

# print("Extracting lunarCrush data...")
# for symbol in currency_ids:
#     # print(symbol)
#     start_date = datetime.strptime(params['start'],'%Y-%m-%d')

#     while start_date <= today:

#         end_date = get_end_date(start_date,params['data_points'])

#         # Adjust for end_date being in the future
#         if end_date > today:
#             end_date = today

#         try:

#             # Perform API Call
#             start = "2015-01-01" # UNIX timestamp .timestamp()
#             end = ""
#             url = f"{params['site']}data={params['endpoint']}&key={lunarCrush_API}&symbol={symbol}&interval={params['interval']}&start={time.mktime(start_date.timetuple())}&end={time.mktime(end_date.timetuple())}&data_points={params['data_points']}"

#             assets = json.loads(urllib.request.urlopen(url).read())

#             for asset_data in assets['data']:
                
#                 for time_data in asset_data['timeSeries']:
                    
#                     # Clean-up
#                     time_data['asset_id'] = asset_data['symbol']
#                     time_data['time'] = datetime.fromtimestamp(time_data['time'])
                    
#                     asset_list.append(time_data)
        
#         except Exception as e:
#             print(f"Symbol: {symbol}; {e}")
        
#         # Calculate new start date to use
#         start_date = end_date + timedelta(days=1)
            
# df = pd.DataFrame(asset_list)
# df.rename(columns={'asset_id':'symbol'},inplace=True)
# df.to_sql('lunarCrush', conn, if_exists='replace', index=False)
# print("lunarCrush data saved to database.")

# ========================
#    Test Database Load
# ========================

print("Confirm data loaded into Sqlite DB:")
# print(pd.read_sql('''SELECT * FROM lunarCrush''', conn).head())
print(pd.read_sql(
    '''
    SELECT * 
    FROM coinbase
    GROUP BY symbol, date
    ORDER BY symbol, date
    ''', conn).tail())