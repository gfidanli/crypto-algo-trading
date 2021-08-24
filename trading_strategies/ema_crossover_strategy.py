import pandas as pd
from datetime import datetime, timedelta
import itertools
import sqlite3

# Create db connection
conn = sqlite3.connect('../db/crypto-analysis.db')
c = conn.cursor()

# Get parameters
symbol = input("Enter a cryptocurrency symbol: ")
start_input = input("Enter start date in format yyyy-mm-dd: ")
end_input = input("Enter end date in format yyyy-mm-dd: ")

# Start needs to be adjusted to pull enough data for the EMA calculation
start = datetime.strptime(start_input,'%Y-%m-%d') - timedelta(days=365)
start =  datetime.strftime(start,'%Y-%m-%d')

df = pd.read_sql(f"""
    SELECT * 
    FROM coinbase 
    WHERE symbol = '{symbol}' AND
    date BETWEEN '{start} 19:00:00' AND '{end_input} 19:00:00'
    """, conn
)

# Clean Up
df['date'] = df['date'].apply(lambda x: x[:10])
df['date'] = df['date'].apply(lambda x: datetime.strptime(x,'%Y-%m-%d'))

df.set_index('date', inplace=True)
df.sort_index(inplace=True)

# ===================
# Generate EMA values
# ===================
emaFast = [5,8,9,10]
emaSlow = [15,18,21,45,50,55,65]

emasUsed = emaFast + emaSlow

for ema in emasUsed:
    df["EMA_"+str(ema)] = df['close'].ewm(span=ema,min_periods=0,adjust=False,ignore_na=False).mean()

# Get combinations for testing
combos = list(itertools.product(emaFast, emaSlow))

# ==========================
# Run EMA Crossover Strategy
# ==========================

# Containers for summary stats
trades = []
batting_avg = []
risk_reward_ratios = []
average_gains = []
average_losses = []
max_returns = []
max_losses = []
cumulative_returns = []

dates_to_use = df.loc[start_input:end_input].index

# Show results of just buying and holding (HODL)
start_open = df.loc[[start_input]]['open'].item()
end_close = df.loc[[end_input]]['close'].item()
hodl_return = round(((end_close - start_open) / (start_open)) * 100, 2)

print("")
print("=======================")
print("    Results if HODL    ")
print("=======================")
print(f"Open Price at {start_input}: {start_open}")
print(f"Close Price at {end_input}: {end_close}")
print(f"Percent Return if HODL: {hodl_return}")
print("")

for combo in combos:
    fast = str(combo[0])
    slow = str(combo[1])

    in_position_flag = 0
    counter = 0

    ticker = []
    dates = []
    buy_prices = []
    fast_ema_values = []
    slow_ema_values = []
    sell_prices = []
    percent_changes = []

    for i in dates_to_use:

        # Save index values for easier access
        index_loc = df.index.get_loc(i)
        prev_index_val = df.iloc[index_loc - 1]
        
        close = df["close"][i]

        if(df[f"EMA_{fast}"][i] > df[f"EMA_{slow}"][i]):
            
            if(in_position_flag == 0): # Not currently in a in_position_flagition
                
                # Enter on first crossover
                if((df.iloc[index_loc-1][f"EMA_{fast}"])<(df.iloc[index_loc-1][f"EMA_{slow}"])): 

                    in_position_flag = 1
                    buy_price = close

                    # Output Data
                    dates.append([i])
                    ticker.append(symbol)
                    buy_prices.append(buy_price)
                    fast_ema_values.append(df[f"EMA_{fast}"][i])
                    slow_ema_values.append(df[f"EMA_{slow}"][i])
                    sell_prices.append(0)
                    percent_changes.append(0)
            
        elif(df[f"EMA_{fast}"][i] < df[f"EMA_{slow}"][i]):
            if(in_position_flag==1):
                in_position_flag=0
                sell_price=close

                percent_change = (sell_price / buy_price - 1) * 100

                # Output Data
                dates.append([i])
                ticker.append(symbol)
                buy_prices.append(buy_price)
                fast_ema_values.append(df[f"EMA_{fast}"][i])
                slow_ema_values.append(df[f"EMA_{slow}"][i])
                sell_prices.append(sell_price)
                percent_changes.append(percent_change)

        # Check if last row of the dataset and close position if so
        if((counter == len(dates_to_use) - 1) and (in_position_flag == 1)): 
            in_position_flag = 0
            sell_price = close

            percent_change = (sell_price / buy_price - 1) * 100
            
            # Save Trade Data
            dates.append([i])
            ticker.append(symbol)
            buy_prices.append(buy_price)
            fast_ema_values.append(df[f"EMA_{fast}"][i])
            slow_ema_values.append(df[f"EMA_{slow}"][i])
            sell_prices.append(sell_price)
            percent_changes.append(percent_change)
        
        counter += 1
    
    # Write out trade history for each ema-crossover strategy
    trade_history = {
        'date':dates,
        'symbol':ticker,
        'buy_price':buy_prices,
        f"ema_{fast}":fast_ema_values,
        f"ema_{slow}":slow_ema_values,
        'sell_price':sell_prices,
        'percent_change':percent_changes
    }
    # Output trade history
    # pd.DataFrame(trade_history).to_csv(f"../output/ema_cross_{combo[0]}_{combo[1]}.csv", index=False)

    # Analyze Results
    win_sum = 0
    loss_sum = 0
    number_of_wins = 0
    number_of_losses = 0
    cumulative_return = 1

    for i in percent_changes:
        if (i > 0):
            win_sum += i
            number_of_wins += 1
        elif (i < 0):
            loss_sum += i
            number_of_losses += 1
        
        # Running total return
        cumulative_return = cumulative_return * ((i / 100) + 1) 

    cumulative_return = round((cumulative_return - 1) * 100, 2)

    if(number_of_wins > 0):
        average_win = win_sum / number_of_wins
        max_return = round(max(percent_changes), 2)
    else:
        average_win = 0
        max_return = 'undefined'

    if(number_of_losses > 0):
        average_loss = loss_sum / number_of_losses
        max_loss = round(min(percent_changes), 2)
        risk_reward_ratio = round(abs(average_win / average_loss), 2)
    else:
        average_win = 0
        max_return = 'undefined'
        risk_reward_ratio = 'inf'

    # Percentage of trades that make money
    if(number_of_wins > 0 or number_of_losses > 0):
        batting_average = number_of_wins / (number_of_wins + number_of_losses)
    else:
        batting_average = 0

    # ==================
    # Save Trade Results
    # ==================
    trades.append(number_of_wins + number_of_losses)
    batting_avg.append(round(batting_average,2))
    risk_reward_ratios.append(risk_reward_ratio)
    average_gains.append(round(average_win,2))
    average_losses.append(round(average_loss,2))
    max_returns.append(max_return)
    max_losses.append(max_loss)
    cumulative_returns.append(cumulative_return)

# ===========
# Output Data
# ===========
trade_stats = {
    'Trades':trades,
    'Batting Avg':batting_avg,
    'WL Ratio':risk_reward_ratios,
    'Avg Win':average_gains,
    'Avg Loss':average_losses,
    'Max Return':max_returns,
    'Max Loss':max_losses,
    'Cum Return':cumulative_returns
}
output_table = pd.DataFrame(data=trade_stats,index=combos).sort_values('Cum Return', ascending=False)
print("=======================")
print("     Trade Results     ")
print("=======================")
print(output_table)

# output_table.to_csv(f"../output/backtesting_strategies_EMA_cross_output_{stock}.csv", mode='w', header=True, index=True)