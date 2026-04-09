import pandas as pd
import matplotlib.pyplot as plt

# 1. Carregar os dados
file_path = "comparação_trajetos - offset_1000_noforce.csv"
df = pd.read_csv(file_path)

# 2. Função de limpeza para colunas numéricas que usam vírgula como decimal
def clean_numeric(val):
    if isinstance(val, str):
        return float(val.replace(',', '.'))
    return val

# 3. Limpar as colunas de distância
df['Distancia OSM'] = df['Distancia OSM'].apply(clean_numeric)
df['Distancia com Offset'] = df['Distancia com Offset'].apply(clean_numeric)

# 4. Criar o Gráfico de Dispersão (Scatter Plot)
plt.figure(figsize=(10, 7))
plt.scatter(df['Distancia OSM'], df['Distancia com Offset'], 
            alpha=0.4, color='#1f77b4', edgecolors='w', s=30, label='Amostras ($N=1000$)')

# 5. Adicionar a linha de referência y = x (Utilidade Ideal)
max_dist = max(df['Distancia OSM'].max(), df['Distancia com Offset'].max())
plt.plot([0, max_dist], [0, max_dist], color='red', linestyle='--', linewidth=2, label='Referência de Identidade ($y=x$)')

# 6. Formatação técnica
plt.title('Correlação de Utilidade: Distância Original vs. Distância com Offset', fontsize=14, fontweight='bold')
plt.xlabel('Distância Original (OSM) [km]', fontsize=12)
plt.ylabel('Distância Ofuscada (Offset) [km]', fontsize=12)
plt.legend(loc='upper left')
plt.grid(True, linestyle=':', alpha=0.6)

# 7. Ajustar layout para evitar cortes
plt.tight_layout()

# 8. Salvar em PDF (Gráfico Vetorial de alta resolução)
plt.savefig('correlacao.pdf', format='pdf', bbox_inches='tight')
plt.close()