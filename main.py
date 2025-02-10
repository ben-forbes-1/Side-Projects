from CBOEDownloader import CBOEDownloader
from RNDCalculator import RNDCalculator
from VolSurfaceCalculator import VolSurfaceCalculator
from YFinanceDownloader import YFinanceDownloader
import logging

update_data = input("Update data (y/n): ")
if update_data == "y":
    data_source = input("Enter data source (cboe/yfinance): ")
    if data_source == "cboe":
        cboe_downloader = CBOEDownloader()
        cboe_downloader.download_data()
        cboe_downloader.combine_csv_files()

    elif data_source == "yfinance":
        yf_downloader = YFinanceDownloader()
        yf_downloader.download_data()

    else:
        logging.error("Invalid data source. Attempting to use yfinance as default.")
        yf_downloader = YFinanceDownloader()
        yf_downloader.download_data()
