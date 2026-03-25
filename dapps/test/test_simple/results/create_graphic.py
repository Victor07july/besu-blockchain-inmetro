import pandas as pd
import matplotlib.pyplot as plt

# Carregar o arquivo
df = pd.read_csv('comparison_summary.csv')

# Criar o gráfico
plt.figure(figsize=(10, 6))
plt.plot(df['workers'], df['throughput_total_tx_s'], marker='o', linestyle='-', color='b', label='Throughput (tx/s)')

# Formatação
plt.title('Crescimento do Throughput vs Número de Workers')
plt.xlabel('Número de Workers')
plt.ylabel('Throughput (Total tx/s)')
plt.grid(True, linestyle='--', alpha=0.7)
plt.xticks(df['workers']) # Garante que todos os números de workers apareçam no eixo X

plt.savefig('throughput_growth.png')