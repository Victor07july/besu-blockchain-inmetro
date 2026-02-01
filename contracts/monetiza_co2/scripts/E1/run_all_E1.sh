#!/bin/bash

# Script Master - Executa todo o fluxo E1
# Uso: ./run_all_E1.sh [--skip-compile] [--skip-deploy] [--test-only]

echo "🚀 SCRIPT MASTER E1 - Carbon Credit NFT"
echo "========================================"
echo ""

# Parse argumentos
SKIP_COMPILE=false
SKIP_DEPLOY=false
TEST_ONLY=false

for arg in "$@"
do
    case $arg in
        --skip-compile)
        SKIP_COMPILE=true
        shift
        ;;
        --skip-deploy)
        SKIP_DEPLOY=true
        shift
        ;;
        --test-only)
        TEST_ONLY=true
        shift
        ;;
        --help)
        echo "Uso: ./run_all_E1.sh [opções]"
        echo ""
        echo "Opções:"
        echo "  --skip-compile    Pula a compilação do contrato"
        echo "  --skip-deploy     Pula o deploy (usa contrato já deployado)"
        echo "  --test-only       Executa apenas teste com primeiro registro"
        echo "  --help            Mostra esta ajuda"
        echo ""
        echo "Exemplos:"
        echo "  ./run_all_E1.sh                    # Executa tudo"
        echo "  ./run_all_E1.sh --test-only        # Apenas testa"
        echo "  ./run_all_E1.sh --skip-compile     # Usa contrato já compilado"
        exit 0
        ;;
    esac
done

# Função para verificar erro
check_error() {
    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ Erro na etapa: $1"
        echo "Abortando execução..."
        exit 1
    fi
}

# Ir para diretório do script
cd "$(dirname "$0")"

# ========================================
# ETAPA 1: COMPILAÇÃO
# ========================================
if [ "$SKIP_COMPILE" = false ]; then
    echo "📝 ETAPA 1/4: Compilando contrato E1..."
    echo "────────────────────────────────────────"
    python3 1_compile_E1.py
    check_error "Compilação"
    echo ""
    echo "✅ Compilação concluída!"
    echo ""
    sleep 2
else
    echo "⏭️  ETAPA 1/4: Compilação pulada (--skip-compile)"
    echo ""
fi

# ========================================
# ETAPA 2: DEPLOY
# ========================================
if [ "$SKIP_DEPLOY" = false ]; then
    echo "🚀 ETAPA 2/4: Deploy do contrato E1..."
    echo "────────────────────────────────────────"
    python3 2_deploy_E1.py
    check_error "Deploy"
    echo ""
    echo "✅ Deploy concluído!"
    echo ""
    sleep 2
else
    echo "⏭️  ETAPA 2/4: Deploy pulado (--skip-deploy)"
    echo ""
fi

# ========================================
# ETAPA 3: TESTE
# ========================================
echo "🧪 ETAPA 3/4: Testando com primeiro registro..."
echo "────────────────────────────────────────"
python3 3_test_first_E1.py
check_error "Teste"
echo ""
echo "✅ Teste concluído!"
echo ""

if [ "$TEST_ONLY" = true ]; then
    echo "🎯 Modo --test-only: Parando aqui"
    echo ""
    echo "Para processar todos os registros, execute:"
    echo "  python3 4_send_data_E1.py"
    echo ""
    exit 0
fi

sleep 2

# ========================================
# ETAPA 4: PROCESSAR CSV COMPLETO
# ========================================
echo "📊 ETAPA 4/4: Processando todos os registros do CSV..."
echo "────────────────────────────────────────"
echo ""
echo "⚠️  ATENÇÃO: Isso vai criar um NFT para cada registro do CSV"
echo "   e pode demorar vários minutos."
echo ""
read -p "Deseja continuar? (s/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Ss]$ ]]; then
    python3 4_send_data_E1.py
    check_error "Processamento CSV"
    echo ""
    echo "✅ Processamento concluído!"
else
    echo ""
    echo "⏭️  Processamento cancelado pelo usuário"
    echo ""
    echo "Para processar depois, execute:"
    echo "  python3 4_send_data_E1.py"
fi

# ========================================
# FINALIZAÇÃO
# ========================================
echo ""
echo "========================================"
echo "🎉 FLUXO E1 CONCLUÍDO!"
echo "========================================"
echo ""
echo "📋 Próximos passos:"
echo "   • Consultar NFTs: python3 5_query_nfts_E1.py"
echo "   • Ver endereço contrato: cat contract_address_E1.txt"
echo "   • Ver documentação: cat README.md"
echo ""
echo "✅ Tudo pronto!"
