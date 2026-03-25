# ======================================================================
#                               ANÁLISES INICIAIS
# ======================================================================

import numpy as np
import pandas as pd

# Desativar notação científica na visualização
pd.set_option("display.float_format", lambda v: f"{v:.6f}")

# ======================================================================
# PARTE 1 - IMPORTANDO E ARRUMANDO OS DADOS
# ======================================================================

# Passo 1: Importando a base de dados
df = pd.read_csv("./dados_gas.csv")

# Passo 2: Imputando manualmente a eficiência de cada automóvel
city_gasoline = [10.3, 10.3, 10.3, 10.3, 12.15, 12.15, 12.15, 12.15, 12.6, 12.6, 12.6, 12.6, 11.8, 12.83, 12.83, 12.83, 12.83, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 12.0, 12.0]
road_gasoline = [11.3, 11.3, 11.3, 11.3, 13.65, 13.65, 13.65, 13.65, 13.9, 13.9, 13.9, 13.9, 13.3, 14.44, 14.44, 14.44, 14.44, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.4, 14.4]
city_ethanol  = [" ", " ", " ", " ", 8.2, 8.2, 8.2, 8.2, 8.9, 8.9, 8.9, 8.9, 8.1, 9.11, 9.11, 9.11, 9.11, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8.3, 8.3]
road_ethanol  = [" ", " ", " ", " ", 9.5, 9.5, 9.5, 9.5, 9.8, 9.8, 9.8, 9.8, 9.2, 10.26, 10.26, 10.26, 10.26, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 10.0, 10.0]

df["city_gasoline"] = pd.to_numeric(pd.Series(city_gasoline), errors="coerce")
df["road_gasoline"] = pd.to_numeric(pd.Series(road_gasoline), errors="coerce")
df["city_ethanol"]  = pd.to_numeric(pd.Series(city_ethanol),  errors="coerce")
df["road_ethanol"]  = pd.to_numeric(pd.Series(road_ethanol),  errors="coerce")

for col in ["city_gasoline", "road_gasoline", "city_ethanol", "road_ethanol"]:
    df[col] = df[col].fillna(0)

# Passo 4: Adicionando manualmente o preço do combustível no Rio Grande do Norte
df["preco_tarifa_convencional"] = 0.774
df["preco_tarifa_convencional"] = pd.to_numeric(df["preco_tarifa_convencional"], errors="coerce")

# Passo 5: Proporção de gasolina no tanque
df["Tanque_gasoline"] = 100 - pd.to_numeric(df["ethanol (%)"], errors="coerce")

# ======================================================================
# PARTE 2 - CALCULANDO O VALOR DE E2
# ======================================================================

MJ_kWh    = 0.2778
gasoline_MJ = 29.5
etanol_MJ   = 21.3

df["convert_gasoline"] = (MJ_kWh * gasoline_MJ * df["preco_tarifa_convencional"] * (df["Tanque_gasoline"] / 100.0))
df["convert_etanol"]   = (MJ_kWh * etanol_MJ   * df["preco_tarifa_convencional"] * (1 - (df["Tanque_gasoline"] / 100.0)))

rg = df["road_gasoline"]
re = df["road_ethanol"]
cg = df["city_gasoline"]
ce = df["city_ethanol"]

df["Valores_estrada"] = (
    np.where(rg == 0, 0, df["convert_gasoline"] / rg) +
    np.where(re == 0, 0, df["convert_etanol"]   / re)
) * pd.to_numeric(df["highway (distance)"], errors="coerce")

df["Valores_cidade"] = (
    np.where(rg == 0, 0, df["convert_gasoline"] / cg) +
    np.where(re == 0, 0, df["convert_etanol"]   / ce)
) * pd.to_numeric(df["highway (distance)"], errors="coerce")

df["Prop_Bonus"] = (
    pd.to_numeric(df["behavior_cautious (%)"], errors="coerce")/100.0 * 0.05 +
    pd.to_numeric(df["behavior_normal (%)"],  errors="coerce")/100.0 * 0.02 +
    pd.to_numeric(df["behavior_aggressive (%)"], errors="coerce")/100.0 * 0.005
)

df["E2"] = df["Prop_Bonus"] * (df["Valores_estrada"] + df["Valores_cidade"])


print("Primeira linha do DataFrame:")
print(df.iloc[0])