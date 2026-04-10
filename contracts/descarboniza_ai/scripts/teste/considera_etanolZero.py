import pandas as pd
import numpy as np

# --- INITIAL ANALYSES ---

# PART 1 - IMPORTING AND ARRANGING DATA

# Step 1: Importing the dataset
df = pd.read_csv("dados_UFRN/dados_monetizacao_novas_emissões_etanol_zero_gas_1720.csv")

# Step 2: Manually imputing the efficiency of each car
city_gasoline = [10.3, 10.3, 10.3, 10.3, 12.15, 12.15, 12.15, 12.15, 12.6, 12.6, 12.6, 12.6, np.nan, 12.83, 12.83, 12.83, 12.83, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 12, 12]
road_gasoline = [11.3, 11.3, 11.3, 11.3, 13.65, 13.65, 13.65, 13.65, 13.9, 13.9, 13.9, 13.9, np.nan, 14.44, 14.44, 14.44, 14.44, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.4, 14.4]
city_ethanol = [np.nan, np.nan, np.nan, np.nan, 8.2, 8.2, 8.2, 8.2, 8.9, 8.9, 8.9, 8.9, np.nan, 9.11, 9.11, 9.11, 9.11, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8.3, 8.3]
road_ethanol = [np.nan, np.nan, np.nan, np.nan, 9.5, 9.5, 9.5, 9.5, 9.8, 9.8, 9.8, 9.8, np.nan, 10.26, 10.26, 10.26, 10.26, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 10, 10]

# Step 3: Adding the vectors as new columns in the DataFrame
df['city_gasoline'] = city_gasoline
df['road_gasoline'] = road_gasoline
df['city_ethanol'] = city_ethanol
df['road_ethanol'] = road_ethanol

df['city_gasoline'] = pd.to_numeric(df['city_gasoline'])
df['road_gasoline'] = pd.to_numeric(df['road_gasoline'])
df['city_ethanol'] = pd.to_numeric(df['city_ethanol'])
df['road_ethanol'] = pd.to_numeric(df['road_ethanol'])

df['city_gasoline'] = df['city_gasoline'].fillna(0)
df['road_gasoline'] = df['road_gasoline'].fillna(0)
df['city_ethanol'] = df['city_ethanol'].fillna(0)
df['road_ethanol'] = df['road_ethanol'].fillna(0)

# Step 4: Manually adding the carbon price: "https://br.investing.com/commodities/carbon-emissions-historical-data"
Carbon_Price_European = [67.13, 67.13, 67.69, 67.69, 67.13, 67.13, 67.13, 67.13, 80.91, 80.74, 69.88, 67.13, 68.98,
                         67.13, 67.13, 67.13, 67.13, 80.91, 80.91, 80.92, 78.64, 78.64, 78.64, 78.64, 78.64, 69.56,
                         68.69, 68.69, 67.13, 67.1, 67.69, 67.91, 65.25]
df['Carbon_Price_European'] = Carbon_Price_European
df['Carbon_Price_European'] = pd.to_numeric(df['Carbon_Price_European'])

# Step 5: Manually adding the Euro price: "https://br.investing.com/currencies/eur-brl-historical-data"
Euro_price = [6.1708, 6.1708, 6.1447, 6.1447, 6.1708, 6.1708, 6.1708, 6.1708, 6.1031, 6.0524, 5.9424, 6.1708, 6.1315,
              6.1708, 6.1708, 6.1708, 6.1708, 6.1031, 6.1031, 5.9710, 5.9851, 5.9851, 5.9851, 5.9851, 5.9851,
              6.2429, 6.2070, 6.2070, 6.1708, 6.1708, 6.1447, 6.1031, 6.2200]
df['Euro_price'] = Euro_price
df['Euro_price'] = pd.to_numeric(df['Euro_price'])

# Step 6: Converting the price to real terms
df['Real_price'] = df['Carbon_Price_European'] * df['Euro_price']

# Step 7: Creating the gasoline proportion in the tank variable
df['Tanque_gasoline'] = 100 - (df['ethanol (%)'])

# --- PART 2 - CALCULATING THE EMISSION TARGET ---

# Target CO2 = PART 1 + PART 2
# PART 1 = highway (distance) * [(1/road gasoline consumption) * Gasoline_Tank_Proportion * CO2 emission per liter of gasoline + (1/road ethanol consumption) * Ethanol_Tank_Proportion * CO2 emission per liter of ethanol]
# PART 2 = city (distance) * [(1/city gasoline consumption) * Gasoline_Tank_Proportion * CO2 emission per liter of gasoline + (1/city ethanol consumption) * Ethanol_Tank_Proportion * CO2 emission per liter of ethanol]

# PART 1
# Using .loc to avoid SettingWithCopyWarning and handle division by zero or infinite results
df['parte_1.1'] = df['highway (distance)'] * (((1 / df['road_gasoline']) * (df['Tanque_gasoline'] / 100) * 1.720)) * 1000
df['parte_1.2'] = df['highway (distance)'] * (((1 / df['road_ethanol']) * (df['ethanol (%)'] / 100) * 0)) * 1000

# Replace inf and NaN values with 0
df['parte_1.1'] = df['parte_1.1'].replace([np.inf, -np.inf], np.nan).fillna(0)
df['parte_1.2'] = df['parte_1.2'].replace([np.inf, -np.inf], np.nan).fillna(0)

df['parte_1'] = df['parte_1.1'] + df['parte_1.2']

# PART 2
df['parte_2.1'] = df['city (distance)'] * (((1 / df['city_gasoline']) * (df['Tanque_gasoline'] / 100) * 1.720)) * 1000
df['parte_2.2'] = df['city (distance)'] * (((1 / df['city_ethanol']) * (df['ethanol (%)'] / 100) * 0)) * 1000

# Replace inf and NaN values with 0
df['parte_2.1'] = df['parte_2.1'].replace([np.inf, -np.inf], np.nan).fillna(0)
df['parte_2.2'] = df['parte_2.2'].replace([np.inf, -np.inf], np.nan).fillna(0)

df['parte_2'] = df['parte_2.1'] + df['parte_2.2']

# TARGET
df['Meta_CO2'] = df['parte_1'] + df['parte_2']

# DIFFERENCE = TARGET - ACTUAL EMISSION
df['Diff'] = df['Meta_CO2'] - df['co2_etanol_0_gas_1720_flex']

# Value E2
df['e2'] = df['Diff'] * df['Real_price'] / 1000000

print(df.head())

