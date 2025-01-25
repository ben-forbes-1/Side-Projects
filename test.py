import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from scipy.stats import norm

# Black-Scholes Call Price Function
def black_scholes_call(F, K, T, r, sigma):
    """
    Calculate the Black-Scholes call option price.

    Parameters:
    F : float : Forward price of the underlying
    K : float : Strike price
    T : float : Time to expiration in years
    r : float : Risk-free interest rate
    sigma : float : Implied volatility

    Returns:
    float : Call option price
    """
    d1 = (np.log(F / K) + (0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return np.exp(-r * T) * (F * norm.cdf(d1) - K * norm.cdf(d2))

# Risk-Neutral Density Function
def compute_rnd(F, T, r, strikes, implied_vols):
    """
    Compute the Risk-Neutral Density (RND) using the second derivative of the call price.

    Parameters:
    F : float : Forward price of the underlying
    T : float : Time to expiration in years
    r : float : Risk-free interest rate
    strikes : array : Array of strike prices
    implied_vols : array : Array of implied volatilities

    Returns:
    tuple : (fine_strikes, rnd) where fine_strikes are the strike prices on a fine grid,
            and rnd is the risk-neutral density.
    """
    # Remove duplicate strikes
    strikes, implied_vols = remove_duplicates(strikes, implied_vols)

    # Ensure the strikes and implied vols are sorted
    sorted_indices = np.argsort(strikes)
    strikes = strikes[sorted_indices]
    implied_vols = implied_vols[sorted_indices]

    # Interpolate implied volatilities for smoothness
    iv_interp = interp1d(strikes, implied_vols, kind='cubic', fill_value="extrapolate")

    # Define a fine grid for strikes
    fine_strikes = np.linspace(min(strikes), max(strikes), 500)
    fine_vols = iv_interp(fine_strikes)

    # Compute option prices using Black-Scholes
    call_prices = [black_scholes_call(F, K, T, r, sigma) for K, sigma in zip(fine_strikes, fine_vols)]

    # First derivative (risk-neutral CDF)
    dC_dK = np.gradient(call_prices, fine_strikes)

    # Second derivative (risk-neutral density)
    d2C_dK2 = np.gradient(dC_dK, fine_strikes)

    return fine_strikes, d2C_dK2

def remove_duplicates(strikes, implied_vols):
    """
    Remove duplicate strikes by averaging implied volatilities for duplicates.

    Parameters:
    strikes : array : Strike prices
    implied_vols : array : Implied volatilities

    Returns:
    tuple : (unique_strikes, unique_implied_vols)
    """
    unique_strikes = {}
    for strike, iv in zip(strikes, implied_vols):
        if strike in unique_strikes:
            unique_strikes[strike].append(iv)
        else:
            unique_strikes[strike] = [iv]

    averaged_strikes = []
    averaged_vols = []
    for strike, ivs in unique_strikes.items():
        averaged_strikes.append(strike)
        averaged_vols.append(np.mean(ivs))

    return np.array(averaged_strikes), np.array(averaged_vols)


# Main Workflow
def main():
    # Load the options data
    options_data = pd.read_csv("spx_options_combined.csv")
    idx_spot = float(options_data['Index Spot'].iloc[0])  # Underlying index spot price
    r = 0.01  # Risk-free rate (adjust this as needed)

    # Choose expiry
    expiry_choice = input("Enter the desired expiry (e.g., 2025-01-19): ")
    expiry_data = options_data[options_data['Expiration Date'] == expiry_choice]

    if expiry_data.empty:
        print("No data available for the chosen expiry.")
        return

    # Extract strikes and implied volatilities
    strikes = expiry_data['Strike'].to_numpy()
    implied_vols = expiry_data['IV'].to_numpy()
    T = (pd.to_datetime(expiry_choice) - pd.Timestamp.today()).days / 365

    # Compute Risk-Neutral Density
    fine_strikes, rnd = compute_rnd(idx_spot, T, r, strikes, implied_vols)

    # Plot the RND
    plt.figure(figsize=(10, 6))
    plt.plot(fine_strikes, rnd, label="Risk-Neutral Density", color='blue')
    plt.title(f"Risk-Neutral Density for Expiry {expiry_choice}")
    plt.xlabel("Strike Price")
    plt.ylabel("Density")
    plt.legend()
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    main()
