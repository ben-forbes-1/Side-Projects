import pandas as pd

# Load the CSV file
df = pd.read_csv("spx_quotedata.csv", skiprows=3)

# Display the first few rows and the columns
print("Column Names:", df.columns)
df.head()
