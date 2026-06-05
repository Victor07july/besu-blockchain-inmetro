import matplotlib.pyplot as plt

# Coordenadas Originais (Linha reta ideal)
x_orig = [1, 2, 3, 4]
y_orig = [1, 1, 1, 1]
labels_orig = ['A', 'B', 'C', 'D']

# Coordenadas Ofuscadas (Simulando o erro de sequência)
# Note que o ponto C' (0.8) está atrás do ponto A' (1.5)
x_ofusc = [1.5, 2.5, 0.8, 4.0]
y_ofusc = [0.8, 1.3, 0.5, 1.1]
labels_ofusc = ["A'", "B'", "C'", "D'"]

plt.figure(figsize=(10, 5)) 
plt.rcParams['axes.facecolor'] = 'white'

# Plot da Trajetória Original
plt.plot(x_orig, y_orig, 'o-', color='blue', label='Trajetória Original', markersize=8, alpha=0.4)
for i, label in enumerate(labels_orig):
    plt.annotate(label, (x_orig[i], y_orig[i]), textcoords="offset points", 
                 xytext=(0,10), ha='center', color='blue', fontweight='bold')

# Plot da Trajetória Ofuscada
plt.plot(x_ofusc, y_ofusc, 'o-', color='red', label='Trajetória Ofuscada (Ruído)', markersize=8)
for i, label in enumerate(labels_ofusc):
    plt.annotate(label, (x_ofusc[i], y_ofusc[i]), textcoords="offset points", 
                 xytext=(0,-15), ha='center', color='red', fontweight='bold')

# Setas para indicar o "vai e vem"
for i in range(len(x_ofusc)-1):
    plt.annotate('', xy=(x_ofusc[i+1], y_ofusc[i+1]), xytext=(x_ofusc[i], y_ofusc[i]),
                 arrowprops=dict(arrowstyle="->", color="red", lw=1.5, alpha=0.6))

plt.title('Ilustração da Quebra de Coerência Sequencial', fontsize=14)
plt.xlabel('Eixo X (Longitude)')
plt.ylabel('Eixo Y (Latitude)')
plt.grid(True, linestyle='--', alpha=0.3)
plt.legend()
plt.tight_layout()

# ALTERAÇÃO AQUI: Extensão .pdf e formato especificado
plt.savefig('trajetoria_ofuscada.pdf', format='pdf')