###########################################################################################################################################################
#                                       ANALISES INICIAIS
###########################################################################################################################################################

rm(list = ls())
options(scipen=999)

# Pacotes
# =========================================================================================================================================================
pacman::p_load(tidyverse, lubridate, vroom, readxl, trelliscopejs, plotly, htmlwidgets)
library("sf")
library("tmaptools")
library("ggmap")
library("lwgeom")
library("rgdal")
library("mapview")
library("leaflet")
library("ggplot2")
library("gridExtra")
library("lmtest")
library("readr")

###########################################################################################################################################################
# PARTE 1 - IMPORTANDO E ARRUMANDO OS DADOS
###########################################################################################################################################################

# Passo 1: Importando as bases de dados
# =========================================================================================================================================================
df <- read_csv("dados_UFRN/dados_monetizacao_novas_emissões_etanol_original_gas_1720.csv")


# Passo 2: Imputando manualmente a eficiência de cada automóvel
# =========================================================================================================================================================
city_gasoline <- c(10.3, 10.3, 10.3, 10.3, 12.15, 12.15, 12.15, 12.15, 12.6, 12.6, 12.6, 12.6, " ", 12.83, 12.83, 12.83, 12.83, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 12, 12)
road_gasoline <- c(11.3, 11.3, 11.3, 11.3, 13.65, 13.65, 13.65, 13.65, 13.9, 13.9, 13.9, 13.9, " ", 14.44, 14.44, 14.44, 14.44, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.4, 14.4)
city_ethanol <- c(" ", " ", " ", " ", 8.2, 8.2, 8.2, 8.2, 8.9, 8.9, 8.9, 8.9, " ", 9.11, 9.11, 9.11, 9.11, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8.3, 8.3)
road_ethanol <- c(" ", " ", " ", " ", 9.5, 9.5, 9.5, 9.5, 9.8, 9.8, 9.8, 9.8, " ", 10.26, 10.26, 10.26, 10.26, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 10, 10)


# Passo 3: Adicionando os vetores como novas colunas no df
# =========================================================================================================================================================
df$city_gasoline <- city_gasoline
df$road_gasoline <- road_gasoline
df$city_ethanol  <- city_ethanol
df$road_ethanol  <- road_ethanol

df$city_gasoline <- as.numeric(df$city_gasoline)
df$road_gasoline <- as.numeric(df$road_gasoline)
df$city_ethanol <- as.numeric(df$city_ethanol)
df$road_ethanol <- as.numeric(df$road_ethanol)


df$city_gasoline[is.na(df$city_gasoline)] <- 0
df$road_gasoline[is.na(df$road_gasoline)] <- 0
df$city_ethanol[is.na(df$city_ethanol)] <- 0
df$road_ethanol[is.na(df$road_ethanol)] <- 0


# Passo 4: Adicionando manualmente o preço do combustível no Rio Grande do Norte
# =========================================================================================================================================================
Preco_Gasolina <- c(6.47, 6.47, 6.47, 6.47, 6.47, 6.47, 6.47, 6.47, 6.71, 6.71, 6.59, 6.47, 6.47, 6.47, 6.47, 6.47, 6.47, 6.71, 6.71,
                    6.78, 6.78, 6.78, 6.78, 6.78, 6.78, 6.59, 6.59, 6.59, 6.47, 6.47, 6.47, 6.47, 6.47)
Preco_Etanol <- c(4.94, 4.94, 4.94, 4.94, 4.94, 4.94, 4.94, 4.94, 5.25, 5.25, 5, 4.94, 4.94, 4.94, 4.94, 4.94, 4.94, 5.25, 5.25,
                  5.34, 5.34, 5.34, 5.34, 5.34, 5.34, 5, 5, 5, 4.94, 4.94, 4.94, 4.94, 4.94)

df$Preco_Gasolina <- Preco_Gasolina
df$Preco_Etanol <- Preco_Etanol

df$Preco_Gasolina <- as.numeric(df$Preco_Gasolina)
df$Preco_Etanol <- as.numeric(df$Preco_Etanol)


# Passo 5: Criando vaiável da proporção de gasolina no tanque
# =========================================================================================================================================================
df$Tanque_gasoline <- 100 - (df$`ethanol (%)`)


###########################################################################################################################################################
# PARTE 2 - CALCULANDO O VALOR DE E2
###########################################################################################################################################################

# Distancia Estrada
df$dt_estrada_gasolina <- df$`highway (distance)`*((1/df$road_gasoline)*((df$Tanque_gasoline/100)/df$Preco_Gasolina))
df$dt_estrada_etanol <- df$`highway (distance)`*((1/df$road_ethanol)*(1-(df$Tanque_gasoline/100))/df$Preco_Etanol)

df$dt_estrada_gasolina[is.na(df$dt_estrada_gasolina) | is.infinite(df$dt_estrada_gasolina)] <- 0
df$dt_estrada_etanol[is.na(df$dt_estrada_etanol) | is.infinite(df$dt_estrada_etanol)] <- 0

df$df_estrada <- df$dt_estrada_gasolina + df$dt_estrada_etanol


# Distancia Cidade
df$dt_cidade_gasolina <- df$`city (distance)`*((1/df$city_gasoline)*((df$Tanque_gasoline/100)/df$Preco_Gasolina))
df$dt_cidade_etanol <- df$`city (distance)`*((1/df$city_ethanol)*(1-(df$Tanque_gasoline/100)/df$Preco_Etanol))
  
df$dt_cidade_gasolina[is.na(df$dt_cidade_gasolina) | is.infinite(df$dt_cidade_gasolina)] <- 0  
df$dt_cidade_etanol[is.na(df$dt_cidade_etanol) | is.infinite(df$dt_cidade_etanol)] <- 0 

df$df_cidade <- df$dt_cidade_gasolina + df$dt_cidade_etanol


# Calculando o bonus a receber pela dirigibilidade
df$Prop_Bonus <- 1 + ((df$`behavior_cautious (%)`/100)*0.10 + (df$`behavior_normal (%)`/100)*0.05 + (df$`behavior_aggressive (%)`/100)*0)

# Calculando o E2
df$E2 <- df$Prop_Bonus*(df$df_estrada+df$df_cidade)



###########################################################################################################################################################
# PARTE 3 - PLAOTANDO O GRÁFICO PARA E2
###########################################################################################################################################################
library(gridExtra)

# Gráfico 1 da trajetória dos preços de E2 e da km
g1 <- ggplot(df, aes(x = total_distance, y = E2)) +
  geom_line(color = "blue", size = 1) +
  labs(
    title = "",
    x = "Distância em km percorrida",
    y = "Valor de E2 em R$"
  ) +
  theme_minimal() +
  theme(
    axis.text.x = element_text(hjust = 1, size = 14),  # Aumenta o tamanho da fonte do eixo X
    axis.text.y = element_text(size = 14),  # Aumenta o tamanho da fonte do eixo Y
    panel.background = element_rect(fill = "white", color = NA),
    panel.grid.major.x = element_line(color = "gray", linetype = "dashed"),
    panel.grid.minor.x = element_blank(),
    axis.line = element_line(color = "black"),
    panel.border = element_rect(color = "black", fill = NA, size = 1),
    axis.title.x = element_text(size = 16),  # Aumenta o tamanho da fonte do título do eixo X
    axis.title.y = element_text(size = 16)   # Aumenta o tamanho da fonte do título do eixo Y
  )

# Gráfico 2 da distribuição da km dos trajetos
g2 <- ggplot(df, aes(x = total_distance)) +
  geom_histogram(aes(y = ..density..), bins = 30, fill = "steelblue", color = "black", alpha = 0.7) +
  geom_density(color = "red", size = 1) +
  labs(
    title = "",
    x = "Distância em km percorrida",
    y = "Densidade"
  ) +
  theme_minimal() +
  theme(
    axis.text.x = element_text(hjust = 1, size = 14),
    axis.text.y = element_text(size = 14),
    panel.background = element_rect(fill = "white", color = NA),
    panel.grid.major.x = element_line(color = "gray", linetype = "dashed"),
    panel.grid.minor.x = element_blank(),
    axis.line = element_line(color = "black"),
    panel.border = element_rect(color = "black", fill = NA, size = 1),
    axis.title.x = element_text(size = 16),
    axis.title.y = element_text(size = 16)
  )

# juntando os dois gráficos
grid.arrange(g1, g2, ncol = 2)  # lado a lado


