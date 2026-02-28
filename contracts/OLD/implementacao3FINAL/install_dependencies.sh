#!/bin/bash
# Script de instalação de dependências para privacidade diferencial GPS

echo "=================================================="
echo "🔧 INSTALAÇÃO DE DEPENDÊNCIAS"
echo "   Privacidade Diferencial GPS + Blockchain"
echo "=================================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 não encontrado!${NC}"
    echo "   Instale Python 3.8+ antes de continuar."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓ Python encontrado: $PYTHON_VERSION${NC}"

# Verificar se pip está instalado
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ pip3 não encontrado!${NC}"
    echo "   Instale pip antes de continuar."
    exit 1
fi

echo -e "${GREEN}✓ pip encontrado${NC}"

# Criar ambiente virtual (opcional mas recomendado)
echo ""
echo "📦 Criando ambiente virtual..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Ambiente virtual criado${NC}"
else
    echo -e "${YELLOW}⚠️  Ambiente virtual já existe${NC}"
fi

# Ativar ambiente virtual
echo "🔄 Ativando ambiente virtual..."
source venv/bin/activate

# Atualizar pip
echo ""
echo "⬆️  Atualizando pip..."
pip install --upgrade pip

# Instalar dependências
echo ""
echo "📥 Instalando dependências do requirements.txt..."
pip install -r config/requirements.txt

# Verificar instalação crítica
echo ""
echo "🔍 Verificando instalações críticas..."

PACKAGES=("pandas" "web3" "osmnx" "diffprivlib" "solcx")
ALL_OK=true

for package in "${PACKAGES[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $package"
    else
        echo -e "  ${RED}✗${NC} $package (FALHOU)"
        ALL_OK=false
    fi
done

# Instalar compilador Solidity
echo ""
echo "📥 Instalando compilador Solidity..."
python3 -c "from solcx import install_solc; install_solc('0.8.19')" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Solidity 0.8.19 instalado${NC}"
else
    echo -e "${YELLOW}⚠️  Erro ao instalar Solidity (tente manualmente)${NC}"
fi

# Resultado final
echo ""
echo "=================================================="
if [ "$ALL_OK" = true ]; then
    echo -e "${GREEN}✅ INSTALAÇÃO CONCLUÍDA COM SUCESSO!${NC}"
    echo ""
    echo "Para ativar o ambiente virtual:"
    echo "  source venv/bin/activate"
    echo ""
    echo "Para desativar:"
    echo "  deactivate"
else
    echo -e "${RED}⚠️  INSTALAÇÃO CONCLUÍDA COM ERROS${NC}"
    echo "   Verifique os pacotes que falharam acima."
fi
echo "=================================================="
