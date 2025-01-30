import os
import numpy as np
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import csv
from fake_useragent import UserAgent
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scipy.optimize import minimize
import matplotlib.pyplot as plt
import yfinance as yf

def calc_tte(expiry):
    return (pd.to_datetime(expiry) - pd.Timestamp.today()).days / 365

update = input("Do you want to update the option price data? (y/n): ")
source = input("Do you want to use CBOE (SPX) or yfinance (SPY) as the data source? (CBOE/yfinance): ")

if update.lower() == "y" and source.lower() =='cboe':
    # Set up Selenium WebDriver with custom download directory
    options = webdriver.ChromeOptions()
    download_dir = "./cboe_csvs"  # Directory to save downloaded CSVs
    os.makedirs(download_dir, exist_ok=True)

    prefs = {
        "download.default_directory": os.path.abspath(download_dir),      # Set download directory
        "download.prompt_for_download": False,                            # Disable download prompts
        "download.directory_upgrade": True,                               # Allow directory upgrades
        "safebrowsing.enabled": True,                                     # Enable safe browsing
        "profile.default_content_setting_values.automatic_downloads": 1,  # Allow multiple downloads
        "profile.default_content_settings.popups": 0,                     # Disable popups
        "download.open_pdf_in_system_reader": False,                      # Prevent PDF popup
        "download.extensions_to_open": "",                                # Prevent any extensions from auto-opening
        "download.shelf.enabled": False                                   # Disables the "Download Complete" notification popup
    }
    options.add_experimental_option("prefs", prefs)

    ua = UserAgent()
    options.add_argument(f"user-agent={ua.random}")                       # Set a random user agent
    options.add_argument("--window-size=1920x1080")                       # Set window size
    options.add_argument("--headless=new")                                # Run in headless mode to avoid opening a browser window
    options.add_argument("--disable-blink-features=AutomationControlled") # Disable automation control
    options.add_argument("--disable-gpu")                                 # Prevent GPU acceleration
    options.add_argument("--disable-software-rasterizer")                 # Further UI rendering disabling
    options.add_argument("--disable-extensions")                          # Prevent extension issues
    options.add_argument("--no-sandbox")                                  # For running inside containers
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    # Navigate to the Cboe SPX options page
    url = "https://www.cboe.com/delayed_quotes/spx/quote_table"
    driver.get(url)

    # Wait for the page to load
    wait = WebDriverWait(driver, 15)

    # Step 1: Select "All" from the dropdown
    try:
        # Step 1: Dismiss cookies popup
        reject_button_xpath = "//button[contains(@class, 'cky-btn-reject') and @aria-label='Reject All']"
        reject_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, reject_button_xpath))
        )
        reject_button.click()

        # Step 2: Locate and click the dropdown containing 'Near the Money'
        dropdown_xpath = "//div[contains(@class, 'ReactSelect__control') and .//div[text()='Near the Money']]"
        dropdown = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, dropdown_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({ behavior: 'smooth', block: 'center' });", dropdown)
        dropdown.click()

        # Step 3: Type 'All' directly and press Enter
        actions = ActionChains(driver)
        actions.send_keys("All")  # Type 'All'
        actions.send_keys(Keys.RETURN)  # Press Enter
        actions.perform()

        # Step 4: Click 'View Chain' button
        view_button_xpath = "//button[contains(@class, 'Button__StyledButton') and contains(@class, 'QuoteTableLayout___StyledButton')]"
        view_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, view_button_xpath))
        )
        view_button.click()  # Attempt to click
        print("Clicked 'View Chain' button.")
    except Exception as e:
        print(f"Error interacting with the dropdown: {e}")

    # Initialize processed expirations
    processed_expirations = []

    while True:
        try:
            # Dynamically locate all expiration buttons
            expiration_buttons = wait.until(EC.presence_of_all_elements_located(
                (By.XPATH, "//button[contains(@class, 'Button__StyledButton-cui__sc-1ahwe65-2')]")
            ))

            # Filter buttons to include those with "20" in their text
            expiration_buttons = [btn for btn in expiration_buttons if "20" in btn.text]

            # Iterate through expiration buttons
            for i in range(len(expiration_buttons)):
                expiration_buttons = wait.until(EC.presence_of_all_elements_located(
                    (By.XPATH, "//button[contains(@class, 'Button__StyledButton-cui__sc-1ahwe65-2')]")
                ))
                expiration_buttons = [btn for btn in expiration_buttons if "20" in btn.text]

                button = expiration_buttons[i]
                expiration = button.text.strip()

                # Skip already processed expirations
                if expiration in processed_expirations:
                    continue

                print(f"Processing expiration: {expiration}")

                # Scroll the button into view and click it
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", button)
                time.sleep(3)  # Wait for the table to update

                # Locate the "Download CSV" button and click it
                export_button_xpath = "//a[span[text()='Download CSV']]"
                export_button = wait.until(EC.presence_of_element_located((By.XPATH, export_button_xpath)))

                print(f"Clicking 'Download CSV' button for {expiration}")
                driver.execute_script("arguments[0].click();", export_button)

                # Wait for the file to download
                time.sleep(5)

                # Rename the most recently downloaded file to match the expiration
                latest_file = max([os.path.join(download_dir, f) for f in os.listdir(download_dir)], key=os.path.getctime)
                new_file_name = os.path.join(download_dir, f"{expiration.replace(' ', '_')}.csv")
                os.rename(latest_file, new_file_name)
                print(f"File saved as {new_file_name}")

                # Mark this expiration as processed
                processed_expirations.append(expiration)

            # Break the loop if all buttons have been processed
            if len(processed_expirations) >= len(expiration_buttons):
                break
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error locating or processing expiration buttons: {e}")
            break

    # Close the browser
    driver.quit()

    # Step 2: Combine all downloaded CSVs into a single DataFrame
    all_data = pd.DataFrame()
    current_idx_flag = False
    for file in os.listdir(download_dir):
        if file.endswith(".csv"):
            file_path = os.path.join(download_dir, file)
            try:
                if current_idx_flag == False:
                    with open(file_path, newline='') as f:
                        reader = csv.reader(f)
                        row1 = next(reader)  # gets the first (empty) line
                        row2 = next(reader) # gets the second line which contains the index
                        idx_spot = row2[1].split(" ")[1]
                    current_idx_flag = True

                # Skip metadata rows and include all data
                df = pd.read_csv(file_path, skiprows=3).fillna('')  # Start reading at the header
                call_column_headers = ['Expiration Date','Last Sale','Net','Bid','Ask','Volume','IV','Delta','Gamma','Open Interest','Strike']
                put_column_headers = ['Expiration Date','Last Sale.1','Net.1','Bid.1','Ask.1','Volume.1','IV.1','Delta.1','Gamma.1','Open Interest.1','Strike']

                df_calls = df[call_column_headers].copy().dropna(how='any', axis=1)
                df_calls['Type'] = 'Call'
                df_calls.columns = df_calls.columns.str.replace(r'\.1$', '', regex=True)

                df_puts = df[put_column_headers].copy().dropna(how='any', axis=1)
                df_puts['Type'] = 'Put'
                df_puts.columns = df_puts.columns.str.replace(r'\.1$', '', regex=True)

                df = pd.concat([df_calls, df_puts], ignore_index=True)
                all_data = pd.concat([all_data, df], ignore_index=True)
            except pd.errors.ParserError as e:
                print(f"Error parsing file {file_path}: {e}")
                continue

    # Combine into a single DataFrame
    if len(all_data.index) != 0:
        final_df = all_data.copy()
        final_df['Expiration Date'] = pd.to_datetime(final_df['Expiration Date'], format = '%a %b %d %Y')
        final_df = final_df.sort_values(by=['Expiration Date', 'Strike'])
        final_df['Index Spot'] = idx_spot

        combined_csv_path = "spx_options_combined.csv"
        if os.path.exists(combined_csv_path):
            os.remove(combined_csv_path) # If the file already exists, delete it
        final_df.to_csv(combined_csv_path, index=False)
        print(f"Data saved to {combined_csv_path}")

        # Delete individual files after combining
        for file in os.listdir(download_dir):
            if file.endswith(".csv"):
                file_path = os.path.join(download_dir, file)
                try:
                    os.remove(file_path)
                    print(f"Deleted file: {file_path}")
                except OSError as e:
                    print(f"Error deleting file {file_path}: {e}")
    else:
        print("No valid data to save.")

elif update.lower() == "y" and source.lower() == 'yfinance':
    TICKER = "SPY"
    stock = yf.Ticker(TICKER)
    expirations = stock.options
    all_data = pd.DataFrame()

    if not expirations:
        raise ValueError("No options available for this stock")
    
    for expiry in expirations:
        options_chain = stock.opton_chain(expiry)
        calls = options_chain.calls
        puts = options_chain.puts
        
        calls = calls[(calls['volume'] > 0) & (calls['openInterest'] > 0) & (calls['bid'] > 0) & (calls['ask'] > 0)]
        puts = puts[(puts['volume'] > 0) & (puts['openInterest'] > 0) & (puts['bid'] > 0) & (puts['ask'] > 0)]

        options = pd.concat([calls, puts])
        all_data = pd.concat([all_data, options], ignore_index=True)

    all_data['Expiration Date'] = pd.to_datetime(all_data['expiration'])
    all_data['Index Spot'] = stock.history(period="1d").iloc[-1]["Close"]
    all_data = all_data.sort_values(by=['Expiration Date', 'strike'])

    if len(all_data.index) != 0:
        final_df = all_data.copy()
        final_df['Expiration Date'] = pd.to_datetime(final_df['Expiration Date'], format = '%a %b %d %Y')
        final_df = final_df.sort_values(by=['Expiration Date', 'Strike'])

        combined_csv_path = "spx_options_combined.csv"
        if os.path.exists(combined_csv_path):
            os.remove(combined_csv_path) # If the file already exists, delete it
        final_df.to_csv(combined_csv_path, index=False)
        print(f"Data saved to {combined_csv_path}")

    else:
        print("No valid data to save.")


options_data = pd.read_csv("spx_options_combined.csv")
options_data['TTE'] = (pd.to_datetime(options_data['Expiration Date']) - pd.Timestamp.today()).dt.days / 365
options_data = options_data[options_data['Bid'] != 0 and options_data['Ask'] != 0]
options_data['Mid'] = (options_data['Bid'] + options_data['Ask']) / 2
idx_spot = options_data['Index Spot'].iloc[0]
expiries = set(options_data["Expiration Date"])

vol_data_dict = {exp: {} for exp in expiries}
strike_data_dict = {exp: {} for exp in expiries}
time_to_exp_dict = {exp: calc_tte(exp) for exp in expiries}
F = float(idx_spot)
no_volume = input("Do you want to include options with no volume/OI? (y/n): ")
vol_surface_method = input("Enter the interpolation method (linear, cubic, SVI: )")

for expiry in expiries:
    options = options_data[options_data['Expiration Date'] == expiry]
    calls = options[options['Type'] == 'Call']
    puts = options[options['Type'] == 'Put']

    # OTM options
    calls = calls[calls['Strike'] > F]
    puts = puts[puts['Strike'] < F]

    if no_volume.lower() == "n":
        calls = calls[(calls['Volume'] > 0) & (calls['Open Interest'] > 0)]
        puts = puts[(puts['Volume'] > 0) & (puts['Open Interest'] > 0)]

    if not calls.empty:
        strikes = calls['Strike'].to_numpy()
        volatilities = calls['IV'].to_numpy()

        vol_data_dict[expiry] = volatilities
        strike_data_dict[expiry] = strikes
    
    if not puts.empty:
        strikes = puts['Strike'].to_numpy()
        volatilities = puts['IV'].to_numpy()

        vol_data_dict[expiry] = volatilities
        strike_data_dict[expiry] = strikes

strike_range = np.linspace(min([min(v) for v in strike_data_dict.values()]) / F, max([max(v) for v in strike_data_dict.values()]) / F, 200)

if vol_surface_method.lower() == "svi":
    def svi_function(params, k):
        a, b, rho, m, phi = params
        return a + b * (rho * (k - m) + np.sqrt((k - m)**2 + phi**2))
    
    def svi_objective(params, k, iv_observed):
        iv_fitted = svi_function(params, k)
        return np.sum((iv_fitted - iv_observed)**2)

    svi_params_dict = {}

    for expiry, vols in vol_data_dict.items():
        if len(vols) > 0:
            # Prepare data
            strikes = strike_data_dict[expiry]
            k = np.log(strikes / F)  # Log-moneyness
            iv_squared = np.array(vols)**2

            # Initial guesses for parameters
            initial_params = [0.1, 0.1, -0.5, 0.0, 0.1]

            # Fit SVI
            result = minimize(svi_objective, initial_params, args=(k, iv_squared), method='L-BFGS-B')
            if result.success:
                svi_params_dict[expiry] = result.x
            else:
                print(f"Failed to fit SVI for expiry {expiry}: {result.message}")

    
    # Create a grid of strikes and expirations
    strike_grid, expiry_grid = np.meshgrid(strike_range, sorted(time_to_exp_dict.values()))
    vol_surface = np.zeros_like(strike_grid)

    # Calculate volatilities for each grid point
    for i, T in enumerate(sorted(time_to_exp_dict.values())):
        if T in time_to_exp_dict.values():
            params = svi_params_dict[expiry]
            k_grid = np.log(strike_grid[:, i] / F)  # Log-moneyness
            vol_surface[:, i] = np.sqrt(svi_function(params, k_grid))

    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')

    surf = ax.plot_surface(
        strike_grid, expiry_grid, vol_surface,
        cmap='viridis', edgecolor='none'
    )

    ax.set_title('SVI Volatility Surface')
    ax.set_xlabel('Strike / Index Spot')
    ax.set_ylabel('Time to Expiration (Years)')
    ax.set_zlabel('Implied Volatility')
    fig.colorbar(surf, shrink=0.5, aspect=5)
    plt.show()






    
