#!/bin/bash
# Pipeline completo: Privacidade Diferencial → Blockchain
# Uso: ./run_pipeline.sh [epsilon] [num_linhas]

set -e  # Parar em caso de erro

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parâmetros
EPSILON=${1:-0.5}
NUM_LINHAS=${2:-10}
CSV_INPUT="data/dados_monetizacao_novas_emissões_etanol_original_gas_1720_v2.csv"
CSV_OUTPUT="data/${CSV_INPUT##*/}"
CSV_OUTPUT="${CSV_OUTPUT%.csv}_private.csv"
CONFIG_FILE="config/e1_gps_contract_address.json"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🚀 PIPELINE COMPLETO${NC}"
echo -e "${BLUE}   Privacidade Diferencial → Blockchain${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "📊 Parâmetros:"
echo -e "   Epsilon (ε): ${YELLOW}${EPSILON}${NC}"
echo -e "   Linhas: ${YELLOW}${NUM_LINHAS}${NC}"
echo -e "   CSV: ${YELLOW}${CSV_INPUT}${NC}"
echo ""

# Verificar se ambiente virtual existe
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Ambiente virtual não encontrado!${NC}"
    echo -e "   Execute primeiro: ${YELLOW}./install_dependencies.sh${NC}"
    exit 1
fi

# Ativar ambiente virtual
echo -e "${GREEN}🔄 Ativando ambiente virtual...${NC}"
source venv/bin/activate

# Verificar se CSV existe
if [ ! -f "$CSV_INPUT" ]; then
    echo -e "${RED}❌ Arquivo CSV não encontrado: $CSV_INPUT${NC}"
    exit 1
fi

# ETAPA 1: Processar com Privacidade Diferencial
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}📍 ETAPA 1: Privacidade Diferencial${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

python3 differential_privacy_gps.py "$CSV_INPUT" "$EPSILON" "$NUM_LINHAS"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Erro no processamento de DP${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Privacidade diferencial aplicada com sucesso!${NC}"
echo -e "   Arquivo gerado: ${YELLOW}${CSV_OUTPUT}${NC}"

# Verificar se arquivo foi gerado
if [ ! -f "$CSV_OUTPUT" ]; then
    echo -e "${RED}❌ Arquivo de saída não foi gerado${NC}"
    exit 1
fi

# ETAPA 2: Análise e Visualização (opcional)
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}📊 ETAPA 2: Análise de Resultados${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

read -p "Deseja gerar análise e gráficos? (s/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Ss]$ ]]; then
    python3 tests/visualize_results.py "$CSV_OUTPUT"
    echo -e "${GREEN}✅ Análise gerada!${NC}"
fi

# ETAPA 3: Blockchain (opcional)
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🔗 ETAPA 3: Envio para Blockchain${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

read -p "Deseja enviar dados para o blockchain? (s/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Ss]$ ]]; then
    # Verificar se contrato foi deployado
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${YELLOW}⚠️  Contrato não deployado ainda${NC}"
        echo ""
        read -p "Deseja fazer deploy agora? (s/N): " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            python3 scripts/deploy_e1_gps.py
            
            if [ $? -ne 0 ]; then
                echo -e "${RED}❌ Erro no deploy do contrato${NC}"
                exit 1
            fi
        else
            echo -e "${YELLOW}⏭️  Pulando envio para blockchain${NC}"
            exit 0
        fi
    fi
    
    # Verificar se Besu está rodando
    echo -e "${GREEN}🔍 Verificando conexão com Besu...${NC}"
    
    BESU_RUNNING=$(curl -s -X POST --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
        http://localhost:8545 2>/dev/null | grep -o "result" | wc -l)
    
    if [ "$BESU_RUNNING" -eq 0 ]; then
        echo -e "${RED}❌ Besu não está rodando!${NC}"
        echo -e "   Inicie o Besu e tente novamente"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Besu conectado${NC}"
    
    # Enviar para blockchain
    python3 scripts/send_to_blockchain.py "$CSV_OUTPUT" "$CONFIG_FILE"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Dados enviados para blockchain!${NC}"
    else
        echo -e "${RED}❌ Erro ao enviar dados${NC}"
        exit 1
    fi
fi

# Resumo final
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🎉 PIPELINE CONCLUÍDO!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}✅ Privacidade diferencial aplicada${NC}"
echo -e "   Arquivo: ${YELLOW}${CSV_OUTPUT}${NC}"

if [ -f "dp_analysis.png" ]; then
    echo -e "${GREEN}✅ Análise visual gerada${NC}"
    echo -e "   Arquivo: ${YELLOW}dp_analysis.png${NC}"
fi

if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo -e "${GREEN}✅ Dados enviados para blockchain${NC}"
fi

echo ""
echo -e "📚 Documentação completa em: ${YELLOW}README.md${NC}"
echo -e "${BLUE}========================================${NC}"
