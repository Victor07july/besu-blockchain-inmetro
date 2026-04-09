import pandas as pd
import matplotlib.pyplot as plt

# 1. Preparação dos Dados (Baseado no seu CSV)
data = {
    'num_workers': [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024],
    'throughput_tx_s': [0.87, 1.74, 3.45, 6.96, 13.87, 27.78, 55.71, 111.0, 220.6, 390.01],
    'avg_latency_ms': [2285.94, 2286.15, 2276.12, 2271.32, 2262.6, 2261.25, 2261.85, 2264.14, 2273.76, 2482.71]
}

df = pd.DataFrame(data)
df['latency_s'] = df['avg_latency_ms'] / 1000 # Conversão para segundos

# 2. Configuração da Figura e do Eixo Principal (Throughput)
fig, ax1 = plt.subplots(figsize=(10, 6))
x_indexes = range(len(df)) # Truque para espaçamento igual no eixo X

# Plot Throughput - Linha Vermelha com Quadrados (conforme imagem)
color_red = '#d62728'
ax1.set_xlabel('Number of Workers', fontsize=10)
ax1.set_ylabel('Throughput (tx/s)', color=color_red, fontsize=10, fontweight='bold')
line1 = ax1.plot(x_indexes, df['throughput_tx_s'], marker='s', markersize=6, 
                 linestyle='-', color=color_red, label='Throughput (tx/s)')
ax1.tick_params(axis='y', labelcolor=color_red)

# 3. Criar o Eixo Secundário (Latência)
ax2 = ax1.twinx() 
color_blue = '#1f77b4'
ax2.set_ylabel('Latency (s)', color=color_blue, fontsize=10, fontweight='bold')
line2 = ax2.plot(x_indexes, df['latency_s'], marker='o', markersize=6, 
                 linestyle='-', color=color_blue, label='Latency (s)')
ax2.tick_params(axis='y', labelcolor=color_blue)

# 4. Formatação Estética (Idêntica ao Baseline EC2)
plt.title('Optimized EC2', fontsize=12)

# Ajustar o Eixo X para mostrar os números de workers reais
ax1.set_xticks(x_indexes)
ax1.set_xticklabels(df['num_workers'], rotation=35, ha='right')

# Grid pontilhado cinza
ax1.grid(True, linestyle='--', alpha=0.5, color='gray')

# 5. Legenda Unificada (Junta as duas linhas em uma única caixa)
lines = line1 + line2
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='upper left', frameon=True)

# 6. Finalização e Salvamento
plt.tight_layout()
plt.savefig('performance_double_y.pdf', format='pdf')
plt.savefig('performance_double_y.png', dpi=300)

print("Gráfico gerado com sucesso: performance_double_y.pdf")