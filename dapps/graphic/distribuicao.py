import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Carregar os dados
df = pd.read_csv('all_runs_distance_analysis.csv', sep=';', decimal=',')

# 2. Extrair a coluna de diferença (em km)
dados = df['Diferenca_Distancia_km']

# 3. Calcular estatísticas
media = dados.mean()
mediana = dados.median()

# 4. Configuração visual do gráfico
plt.figure(figsize=(10, 6))
sns.set_theme(style="whitegrid")

# AJUSTE AQUI: 
# color="darkblue" (ou "navy") para o azul escuro
# edgecolor="black" e linewidth=1.5 para a borda preta nítida
ax = sns.histplot(dados, kde=True, color="steelblue", edgecolor="black", linewidth=1.2, alpha=0.8)

# Adicionar linhas de Média e Mediana
plt.axvline(media, color='red', linestyle='--', linewidth=2, label=f'Média: {media:.4f} km')
plt.axvline(mediana, color='green', linestyle='-', linewidth=2, label=f'Mediana: {mediana:.4f} km')

# Títulos e Labels
plt.title('Distribuição da Diferença de Distância (Original vs Offset)', fontsize=14)
plt.xlabel('Diferença de Distância (km)', fontsize=12)
plt.ylabel('Frequência', fontsize=12)
plt.legend()

# 5. Salvar em PDF
plt.tight_layout()
plt.savefig('distribuicao_diferenca_distancia.pdf')

# ADICIONE ESTAS LINHAS PARA A BORDA EXTERNA:
for spine in ax.spines.values():
    spine.set_visible(True)      # Garante que as bordas existam
    spine.set_color('black')     # Cor da borda externa
    spine.set_linewidth(1.5)     # Espessura da borda externa

print(f"Gráfico gerado com sucesso!\nMédia: {media:.4f}\nMediana: {mediana:.4f}")
plt.show()