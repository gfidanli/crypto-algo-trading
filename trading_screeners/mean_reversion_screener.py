import pandas as pd
import sqlite3

# Create db connection
conn = sqlite3.connect('../db/crypto-analysis.db')
c = conn.cursor()

cryptos = pd.read_sql(
    '''
    SELECT DISTINCT(symbol)
    FROM coinbase
    ''', conn
)

symbols = []
means = []
stdevs = []
current_days = []
num_stdevs = []
num_observations = []

for symbol in cryptos.iloc[:,0].tolist():

    try:
        
        df = pd.read_sql(f"""
            SELECT date, symbol, close
            FROM coinbase
            WHERE symbol = '{symbol}'
            ORDER BY date 
            """, conn
        )

        sma = 50 #int(input("Enter a SMA: "))
        limit = 10 #int(input("Enter warning limit: ")) # Define a threshold where market may be overextended (ex: 10 = 10% higher than SMA)

        df[f"SMA_{sma}"] = df.iloc[:,2].rolling(window=sma).mean()
        df[f"SMA_{sma}_Pct_Chg"] = ((df["close"]/df[f"SMA_{sma}"]) - 1) * 100 # calculate pct change between close and SMA

        mean = round(df[f"SMA_{sma}_Pct_Chg"].mean(),2) # On average, how far does the close deviate from SMA
        stdev = round(df[f"SMA_{sma}_Pct_Chg"].std(),2)
        
        current_day = round(df['SMA_50_Pct_Chg'].values[-1],2)#round(df.iloc[-1,2],2)

        num_stdev = round((current_day-mean)/stdev,2)
        num_obs = df[f"SMA_{sma}"].count()

        # Add data to containers
        symbols.append(symbol)
        means.append(mean)
        stdevs.append(stdev)
        current_days.append(current_day)
        num_stdevs.append(num_stdev)
        num_observations.append(num_obs)

    except Exception as e:
        print(symbol)
        print(e)

# Populate dataframe
summary_table = pd.DataFrame({
    'Symbol':symbols,
    'Num_Days':num_observations,
    'Mean':means,
    'Stdev':stdevs,
    'Today_PctChg':current_days,
    'Num_Stdevs':num_stdevs
})

# Cut-off will be +- 1.5 Std Dev because beyond that is 6.7% of the observed data
# Two standard deviations and above is 2.3%
overbought = summary_table[(summary_table['Num_Stdevs'] >= 1.5) & (summary_table['Num_Days'] >= 100)].sort_values(by=['Num_Stdevs'], ascending=False)
oversold = summary_table[(summary_table['Num_Stdevs'] <= -1.5) & (summary_table['Num_Days'] >= 100)].sort_values(by=['Num_Stdevs'], ascending=True)

print(" ===================================== ")
print(" Overbought >= 1.5 Standard Deviations ")
print(" ===================================== ")
print(overbought)
print("")
print(" ==================================== ")
print(" Oversold <= -1.5 Standard Deviations ")
print(" ==================================== ")
print(oversold)