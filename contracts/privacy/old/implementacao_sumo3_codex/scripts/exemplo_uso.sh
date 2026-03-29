#!/bin/bash
# Script de exemplo de uso da implementação v3 (offset determinístico)

echo "======================================================================"
echo "🚗 EXEMPLO DE USO - IMPLEMENTAÇÃO SUMO V3 (OFFSET DETERMINÍSTICO)"
echo "======================================================================"
echo ""

# Verificar se arquivo de entrada existe
INPUT_FILE="../data/vehicles_step.csv"

if [ ! -f "$INPUT_FILE" ]; then
    echo "❌ Arquivo não encontrado: $INPUT_FILE"
    echo "   Execute o SUMO primeiro para gerar os dados"
    exit 1
fi

echo "📂 Arquivo de entrada: $INPUT_FILE"
echo ""

# Exemplo 1: Offset padrão
echo "📌 EXEMPLO 1: Offset padrão (0.01°, raio 2km)"
echo "   Comando: python3 process_sumo_csv.py $INPUT_FILE"
echo ""
# python3 process_sumo_csv.py "$INPUT_FILE"

# Exemplo 2: Offset personalizado - maior privacidade
echo "📌 EXEMPLO 2: Offset alto (0.02°, raio 3km)"
echo "   Comando: python3 process_sumo_csv.py $INPUT_FILE ../data/trips_high.csv 12.0 1 0.02 0.02 3.0"
echo ""
# python3 process_sumo_csv.py "$INPUT_FILE" ../data/trips_high.csv 12.0 1 0.02 0.02 3.0

# Exemplo 3: Offset personalizado - menor privacidade
echo "📌 EXEMPLO 3: Offset baixo (0.005°, raio 1km)"
echo "   Comando: python3 process_sumo_csv.py $INPUT_FILE ../data/trips_low.csv 12.0 1 0.005 0.005 1.0"
echo ""
# python3 process_sumo_csv.py "$INPUT_FILE" ../data/trips_low.csv 12.0 1 0.005 0.005 1.0

echo "======================================================================"
echo "💡 Para executar um exemplo, descomente a linha correspondente"
echo "======================================================================"
echo ""
echo "Após processar, visualize com:"
echo "  python3 visualize_trips.py ../data/trips_sumo_processed_trajectories.json"
echo ""
echo "======================================================================"
echo ""
echo "🔑 PARÂMETROS:"
echo "   offset_x: Deslocamento em latitude (graus)"
echo "   offset_y: Deslocamento em longitude (graus)"
echo "   max_radius_km: Raio máximo de deslocamento (km)"
echo ""
echo "📏 CONVERSÃO:"
echo "   0.001° ≈ 111 metros"
echo "   0.01° ≈ 1.1 km"
echo "   0.02° ≈ 2.2 km"
echo ""
echo "⚠️  AVISO: Se offset ultrapassar raio, será automaticamente reduzido"
echo "======================================================================"
