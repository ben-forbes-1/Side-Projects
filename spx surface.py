import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv
from fake_useragent import UserAgent

update = input("Do you want to update the option price data? (y/n): ")

if update.lower() == "y":
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
    options.add_argument(f"user-agent={ua.random}")

    options.add_argument("--window-size=1920x1080")
    options.add_argument("--headless=new")                                 # Run in headless mode to avoid opening a browser window
    options.add_argument("--disable-blink-features=AutomationControlled")

    options.add_argument("--disable-gpu")                                  # Prevent GPU acceleration
    options.add_argument("--disable-software-rasterizer")                  # Further UI rendering disabling
    options.add_argument("--disable-extensions")                           # Prevent extension issues
    options.add_argument("--no-sandbox")                                   # For running inside containers
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    # Navigate to the Cboe SPX options page
    url = "https://www.cboe.com/delayed_quotes/spx/quote_table"
    driver.get(url)

    # Wait for the page to load
    wait = WebDriverWait(driver, 15)

    # Step 1: Select "All" from the dropdown
    try:
        dropdown_xpath = "//div[contains(@class, 'ReactSelect__control')]"
        option_xpath = "//div[contains(@class, 'ReactSelect__option') and text()='All']"

        # Click the dropdown
        dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, dropdown_xpath)))
        dropdown.click()
        time.sleep(1)

        # Select "All" from the dropdown
        option = wait.until(EC.element_to_be_clickable((By.XPATH, option_xpath)))
        option.click()
        print("Selected 'All' from the dropdown.")
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
        final_df = final_df[final_df['Volume'] != 0]
        final_df = final_df[final_df['Open Interest'] != 0]
        final_df['Expiration Date'] = pd.to_datetime(final_df['Expiration Date'], format = '%a %b %d %Y')
        df = df[df['Expiration Date'] >= pd.Timestamp.today()]
        final_df = final_df.sort_values(by=['Expiration Date', 'Strike'])

        combined_csv_path = "spx_options_combined.csv"
        if os.path.exists(combined_csv_path):
            os.remove(combined_csv_path)
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
