import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter

def calc_tte(expiry):
    return (pd.to_datetime(expiry) - pd.Timestamp.today()).days / 365

ticker = input("Enter the stock ticker: ").upper()
stock = yf.Ticker(ticker)
expirations = stock.options

if not expirations:
    raise ValueError("No options available for this stock")

vol_data_dict = {}
strike_data_dict = {}
time_to_exp_dict = {}
F = stock.history(period="1d").iloc[-1]["Close"]

for expiration in expirations:
    options_chain = stock.option_chain(expiration)
    calls = options_chain.calls
    puts = options_chain.puts

    calls = calls[(calls['volume'] > 0) & (calls['openInterest'] > 0) & (calls['strike'] > F)]
    puts = puts[(puts['volume'] > 0) & (puts['openInterest'] > 0) & (puts['strike'] < F)]
    options = pd.concat([calls, puts])
    options = options[options['impliedVolatility'] > 0]

    if not options.empty:
        strikes = options['strike'].to_numpy()
        volatilities = options['impliedVolatility'].to_numpy()

        vol_data_dict[expiration] = volatilities
        strike_data_dict[expiration] = strikes
        time_to_exp_dict[expiration] = calc_tte(expiration)

strike_range = np.linspace(min([min(v) for v in strike_data_dict.values()]) / F, max([max(v) for v in strike_data_dict.values()]) / F, 200)
time_range = np.linspace(min(time_to_exp_dict.values()), max(time_to_exp_dict.values()), 200)
strike_grid, time_grid = np.meshgrid(strike_range, time_range)

vol_surface = griddata(
    [(k / F, t) for exp, ks in strike_data_dict.items() for k, t in zip(ks, [time_to_exp_dict[exp]] * len(ks))],
    [v for vs in vol_data_dict.values() for v in vs],
    (strike_grid, time_grid),
    method='linear'
)

vol_surface = gaussian_filter(vol_surface, sigma=1.5)

fig = make_subplots(
    rows=2, cols=1,
    specs=[[{"type": "surface"}], [{"type": "scatter"}]],
    subplot_titles=["Volatility Surface", "Volatility Smile"],
    row_heights=[0.75, 0.25]
)

fig.add_trace(
    go.Surface(
        z=vol_surface,
        x=strike_grid,
        y=time_grid,
        colorscale='Viridis',
        colorbar = dict(title='Implied Volatility'),
        name='Volatility Surface'
    ),
    row=1, col=1
)

initial_expiry = list(expirations)[0]
strikes = strike_data_dict[initial_expiry]
vols = vol_data_dict[initial_expiry]
moneyness = strikes / F

fig.add_trace(
    go.Scatter(
        x=moneyness,
        y=vols,
        mode='markers',
        name=f'Smile: {initial_expiry}'
    ),
    row=2, col=1
)

buttons = []
for i, expiration in enumerate(expirations):
    if expiration in vol_data_dict:
        strikes = strike_data_dict[expiration]
        vols = vol_data_dict[expiration]
        moneyness = strikes / F

        buttons.append(
            dict(
                label=expiration,
                method='restyle',
                args=[
                    {
                        'x': [moneyness],
                        'y': [vols],
                        'type':'scatter'
                    },
                    [1]
                ]
            )
        )

fig.update_layout(
    updatemenus = [
        dict(
            buttons=buttons,
            direction='down',
            showactive=True,
            x=0.1,
            y=1.3
        )
    ],
    title=f'Volatility Surface and Smile for {ticker}',
    scene=dict(
        xaxis_title='Moneyness',
        yaxis_title='Time to Expiry',
        zaxis_title='Implied Volatility'
    ),
    xaxis2 = dict(
        title='Moneyness',
    ),
    yaxis2 = dict(
        title='Implied Volatility',
    )
)

fig.write_html("volatility_surface.html")
