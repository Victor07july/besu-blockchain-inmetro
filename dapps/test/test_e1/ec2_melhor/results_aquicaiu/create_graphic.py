import pandas as pd
import matplotlib.pyplot as plt

# 1. Carregar e ordenar - AJUSTADO PARA PADRÃO BR
# Precisamos dizer que o separador é ';' e o decimal é ','
df = pd.read_csv('comparison_summary_br.csv', sep=';', decimal=',')
df = df.sort_values('num_workers')

# 2. Preparar os dados
fator_escala = 10 
df['latency_plot'] = (df['avg_latency_ms'] / 1000) * fator_escala
throughput_data = df['throughput_tx_s']

# 3. Configuração da Figura
plt.figure(figsize=(10, 6))
x_indexes = range(len(df))

# 4. Plotar
plt.plot(x_indexes, df['latency_plot'], marker='o', markersize=6, 
         linestyle='-', color='#1f77b4', label=f'Latency (s) x{fator_escala}')

plt.plot(x_indexes, throughput_data, marker='s', markersize=6, 
         linestyle='-', color='#d62728', label='Throughput (s)')

# 5. Formatação de Títulos e Eixos
plt.title('Optimized EC2', fontsize=12)
plt.xlabel('Number of Workers', fontsize=10)
plt.ylabel('Seconds / Scale Unit', fontsize=10)

# 6. Ajuste dinâmico do Eixo Y
y_max = max(df['latency_plot'].max(), throughput_data.max())
plt.ylim(-1, y_max * 1.15) 

# 7. Eixo X (Espaçamento igual e Rotação)
plt.xticks(x_indexes, df['num_workers'], rotation=35, ha='right')

# 8. Grade e Legenda
plt.grid(True, linestyle='--', alpha=0.5, color='gray')
plt.legend(loc='upper left', fontsize=9)

plt.tight_layout()
plt.savefig('optimized_ec2_plot.pdf')
plt.savefig('optimized_ec2_plot.png', dpi=300)

print(f"Gráfico gerado com sucesso usando os dados do padrão BR!")