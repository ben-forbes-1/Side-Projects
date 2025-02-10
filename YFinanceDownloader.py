import yfinance as yf
import pandas as pd
import os


class YFinanceDownloader:
    def __init__(self, ticker="SPY"):
        self.ticker = ticker

    def download_data(self):
        stock = yf.Ticker(self.ticker)
        expirations = stock.options
        all_data = pd.DataFrame()

        if not expirations:
            raise ValueError("No options available for this stock")

        for expiry in expirations:
            options_chain = stock.option_chain(expiry)
            calls = options_chain.calls
            puts = options_chain.puts

            calls = calls[(calls['volume'] > 0) & (calls['openInterest'] > 0) & (calls['bid'] > 0) & (calls['ask'] > 0)]
            puts = puts[(puts['volume'] > 0) & (puts['openInterest'] > 0) & (puts['bid'] > 0) & (puts['ask'] > 0)]

            options = pd.concat([calls, puts])
            options['Expiration Date'] = pd.to_datetime(expiry)
            all_data = pd.concat([all_data, options], ignore_index=True)

        all_data['Index Spot'] = stock.history(period="1d").iloc[-1]["Close"]
        all_data = all_data.sort_values(by=['Expiration Date', 'strike'])

        if len(all_data.index) != 0:
            combined_csv_path = "spx_options_combined.csv"
            if os.path.exists(combined_csv_path):
                os.remove(combined_csv_path)
            all_data.to_csv(combined_csv_path, index=False)
            print(f"Data saved to {combined_csv_path}")
        else:
            print("No valid data to save.")