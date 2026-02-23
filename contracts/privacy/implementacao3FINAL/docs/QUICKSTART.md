# 🚀 Guia de Início Rápido

## ⚡ Setup em 3 Passos

### 1️⃣ Instalar Dependências (5 minutos)

```bash
cd /home/victor/besu-starter-victor/contracts/privacy/implementacao3.5
./install_dependencies.sh
```

**O que acontece:**
- ✅ Cria ambiente virtual Python
- ✅ Instala bibliotecas (osmnx, diffprivlib, web3, etc.)
- ✅ Instala compilador Solidity

---

### 2️⃣ Testar Rapidamente (2 minutos)

```bash
source venv/bin/activate
python3 test_dp.py
```

**Resultado esperado:**
```
🧪 TESTE RÁPIDO - PRIVACIDADE DIFERENCIAL GPS
==================================================================
🔐 Testando com ε = 0.5
...
✅ Teste PASSOU - Deslocamentos dentro do esperado
```

---

### 3️⃣ Processar Seus Dados (depende do tamanho)

#### Opção A: Pipeline Automático (Recomendado)

```bash
./run_pipeline.sh 0.5 10
```

Este script interativo irá:
1. ✅ Processar 10 viagens com ε=0.5
2. ⚠️ Perguntar se você quer gerar gráficos
3. ⚠️ Perguntar se você quer enviar para blockchain

#### Opção B: Passo a Passo Manual

```bash
# 1. Processar com DP
python3 differential_privacy_gps.py dados.csv 0.5 10

# 2. Visualizar resultados
python3 visualize_results.py dados_private.csv

# 3. Deploy do contrato (primeira vez)
python3 deploy_e1_gps.py

# 4. Enviar para blockchain
python3 send_to_blockchain.py dados_private.csv e1_gps_contract_address.json
```

---

## 🎛️ Ajustar Privacidade

### Entendendo Epsilon (ε)

| ε | Privacidade | Deslocamento | Uso Recomendado |
|---|------------|--------------|-----------------|
| **0.1** | Máxima | ~1.1 km | Pesquisa acadêmica |
| **0.5** | Alta | ~220 m | **Produção (padrão)** |
| **1.0** | Moderada | ~110 m | Análises empresariais |
| **2.0** | Baixa | ~55 m | Casos de baixo risco |

**Escolher epsilon:**
```bash
# Mais privado (ε=0.3)
./run_pipeline.sh 0.3 10

# Menos privado (ε=1.0)
./run_pipeline.sh 1.0 10
```

---

## 📊 Arquivos Gerados

| Arquivo | Descrição |
|---------|-----------|
| `dados_private.csv` | Dados com coordenadas protegidas |
| `dp_analysis.png` | Gráficos de análise |
| `dados_blockchain_results.csv` | Hashes das transações |
| `e1_gps_contract_address.json` | Endereço e ABI do contrato |

---

## 🔧 Configuração Blockchain

**1. Editar configurações (primeira vez):**

```bash
cp config.example.json e1_gps_contract_address.json
nano e1_gps_contract_address.json
```

**2. Preencher:**
```json
{
  "rpc_url": "http://localhost:8545",
  "contract_address": "0x...",
  "oracle_private_key": "0x...",
  "contract_abi": [...]
}
```

**3. ⚠️ Segurança:**
- 🔒 Nunca commitar chave privada no Git
- 🔒 Usar variáveis de ambiente em produção

---

## ❓ Comandos Úteis

```bash
# Verificar se Besu está rodando
curl -X POST --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' http://localhost:8545

# Ver ajuda do script
python3 differential_privacy_gps.py --help

# Processar CSV completo (sem limite de linhas)
python3 differential_privacy_gps.py dados.csv 0.5

# Ver estrutura de arquivos
tree -L 2
```

---

## 🐛 Problemas Comuns

### "No module named 'osmnx'"
```bash
source venv/bin/activate
pip install osmnx
```

### "Besu não está rodando"
```bash
cd /home/victor/besu-starter-victor
./run.sh
```

### "InsufficientResponseError" (osmnx)
**Causa:** Área sem dados do OpenStreetMap

**Solução:** Aumentar raio de busca em `differential_privacy_gps.py`:
```python
SEARCH_RADIUS = 2000  # Era 1000
```

---

## 📚 Próximos Passos

1. ✅ Ler documentação completa: [README.md](README.md)
2. ✅ Experimentar diferentes valores de epsilon
3. ✅ Processar dataset completo
4. ✅ Analisar gráficos de privacidade
5. ✅ Integrar com seu pipeline existente

---

## 💡 Dicas

- **Performance:** Use cache de grafos (já implementado automaticamente)
- **Privacidade:** ε < 0.5 para dados sensíveis
- **Utilidade:** ε > 0.5 para análises que requerem precisão
- **Teste:** Sempre processe amostra pequena primeiro

---

## 📞 Suporte

Documentação detalhada: [README.md](README.md)

**Estrutura do projeto:**
```
implementacao3.5/
├── 📖 README.md                      ← Documentação completa
├── 🚀 QUICKSTART.md                  ← Este arquivo
├── 🐍 differential_privacy_gps.py    ← Pipeline principal
├── 🔗 send_to_blockchain.py          ← Integração Web3
├── 🧪 test_dp.py                     ← Teste rápido
├── 📊 visualize_results.py           ← Gráficos
├── ⚙️  run_pipeline.sh                ← Pipeline automático
└── 📦 install_dependencies.sh        ← Instalador
```

---

**🎯 Tudo pronto! Comece com:**

```bash
./install_dependencies.sh && source venv/bin/activate && python3 test_dp.py
```
