#!/bin/bash

# Script para compilar, deployar o contrato E2 e atualizar o .env automaticamente

echo "🔧 Iniciando processo de deploy do contrato E2..."
echo ""

# Diretório do contrato E2
CONTRACT_DIR="/home/inmetro/besu-quickstarter-modified/dapps/monetiza_co2/scripts/E2"
WEB_INTERFACE_DIR="/home/inmetro/besu-quickstarter-modified/dapps/web-interface"
VENV_DIR="/home/inmetro/besu-quickstarter-modified/dapps/monetiza_co2/scripts/myenv"

# Ativar ambiente virtual
echo "🐍 Ativando ambiente virtual Python..."
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Ambiente virtual não encontrado em: $VENV_DIR"
    exit 1
fi

source "$VENV_DIR/bin/activate"

if [ $? -ne 0 ]; then
    echo "❌ Erro ao ativar ambiente virtual!"
    exit 1
fi

echo "✅ Ambiente virtual ativado!"
echo ""

# 1. Compilar o contrato
echo "📦 Compilando contrato..."
cd "$CONTRACT_DIR" || exit 1
python3 1_compile.py

if [ $? -ne 0 ]; then
    echo "❌ Erro na compilação do contrato!"
    exit 1
fi

echo "✅ Compilação concluída com sucesso!"
echo ""

# 2. Fazer o deploy
echo "🚀 Fazendo deploy do contrato..."
python3 2_deploy.py

if [ $? -ne 0 ]; then
    echo "❌ Erro no deploy do contrato!"
    exit 1
fi

echo "✅ Deploy concluído com sucesso!"
echo ""

# 3. Ler o endereço do contrato deployado
if [ ! -f "contract_address.txt" ]; then
    echo "❌ Arquivo contract_address.txt não encontrado!"
    exit 1
fi

CONTRACT_ADDRESS=$(cat contract_address.txt)
echo "📝 Novo endereço do contrato: $CONTRACT_ADDRESS"
echo ""

# 4. Atualizar o .env
echo "🔄 Atualizando arquivo .env..."
cd "$WEB_INTERFACE_DIR" || exit 1

if [ ! -f ".env" ]; then
    echo "❌ Arquivo .env não encontrado!"
    exit 1
fi

# Fazer backup do .env
cp .env .env.backup
echo "💾 Backup criado: .env.backup"

# Atualizar o CONTRACT_ADDRESS no .env
sed -i "s/^CONTRACT_ADDRESS=.*/CONTRACT_ADDRESS=$CONTRACT_ADDRESS/" .env

if [ $? -ne 0 ]; then
    echo "❌ Erro ao atualizar o .env!"
    echo "🔙 Restaurando backup..."
    mv .env.backup .env
    exit 1
fi

echo "✅ Arquivo .env atualizado com sucesso!"
echo ""

# 5. Verificar se o servidor está rodando
echo "🔍 Verificando servidor Node.js..."
SERVER_PID=$(ps aux | grep "node.*server.js" | grep -v grep | awk '{print $2}')

if [ -n "$SERVER_PID" ]; then
    echo "⚠️  Servidor Node.js detectado (PID: $SERVER_PID)"
    echo "⚠️  IMPORTANTE: Reinicie o servidor para aplicar as mudanças:"
    echo ""
    echo "   1. Pare o servidor atual (Ctrl+C no terminal do servidor)"
    echo "   2. Execute novamente: node server.js"
    echo ""
else
    echo "ℹ️  Nenhum servidor Node.js detectado em execução"
    echo "ℹ️  Inicie o servidor com: node server.js"
    echo ""
fi

echo "✨ Processo concluído!"
echo ""
echo "📋 Resumo:"
echo "   - Contrato compilado: ✅"
echo "   - Deploy realizado: ✅"
echo "   - .env atualizado: ✅"
echo "   - Novo endereço: $CONTRACT_ADDRESS"
echo ""
echo "🎯 Próximo passo: Reinicie o servidor Node.js!"
echo ""

# Desativar ambiente virtual
deactivate
