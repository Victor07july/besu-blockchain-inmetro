# 🔒 Implementação 3.5 - Privacidade Diferencial GPS

Sistema de privacidade diferencial para coordenadas GPS com map matching e integração blockchain.

## 📁 Estrutura Organizada

```
implementacao3.5/
│
├── 📖 INDEX.md                         ← Este arquivo (índice principal)
├── 🔧 install_dependencies.sh          ← Instalador de dependências
├── 🚀 run_pipeline.sh                  ← Pipeline automático completo
│
├── 📂 scripts/                         ← Scripts principais
│   ├── differential_privacy_gps.py     ← Processamento DP + Map Matching
│   ├── send_to_blockchain.py           ← Envio para blockchain (Web3)
│   └── deploy_e1_gps.py                ← Deploy do contrato Solidity
│
├── 📂 tests/                           ← Scripts de teste
│   ├── test_dp.py                      ← Teste rápido do pipeline
│   └── visualize_results.py            ← Análise e gráficos
│
├── 📂 docs/                            ← Documentação
│   ├── README.md                       ← Documentação completa
│   └── QUICKSTART.md                   ← Guia de início rápido
│
├── 📂 config/                          ← Configurações
│   ├── requirements.txt                ← Dependências Python
│   └── config.example.json             ← Template de configuração
│
├── 📂 contracts/                       ← Contratos Solidity
│   └── E1RegistryGPS.sol               ← Contrato principal
│
└── 📂 data/                            ← Dados (gitignored)
    └── dados_monetizacao_...csv        ← Seu CSV de entrada
```

---

## ⚡ Início Rápido

### 1️⃣ Instalar (primeira vez)
```bash
./install_dependencies.sh
source venv/bin/activate
```

### 2️⃣ Testar
```bash
python3 tests/test_dp.py
```

### 3️⃣ Processar Dados
```bash
# Pipeline automático
./run_pipeline.sh 0.5 10

# Ou passo a passo
python3 scripts/differential_privacy_gps.py data/dados.csv 0.5 10
python3 tests/visualize_results.py data/dados_private.csv
python3 scripts/send_to_blockchain.py data/dados_private.csv config/e1_gps_contract_address.json
```

---

## 📚 Documentação Completa

- **[README.md](docs/README.md)** - Documentação técnica completa
- **[QUICKSTART.md](docs/QUICKSTART.md)** - Guia rápido de uso

---

## 🎯 Fluxo de Trabalho

```
1. Instalar → ./install_dependencies.sh
2. Testar   → python3 tests/test_dp.py  
3. Processar → python3 scripts/differential_privacy_gps.py dados.csv
4. Analisar → python3 tests/visualize_results.py dados_private.csv
5. Deploy   → python3 scripts/deploy_e1_gps.py
6. Enviar   → python3 scripts/send_to_blockchain.py dados_private.csv config.json
```

---

## 🔐 Parâmetros de Privacidade

| Epsilon (ε) | Privacidade | Deslocamento |
|-------------|-------------|--------------|
| 0.1 | Máxima | ~1.1 km |
| **0.5** | **Alta (padrão)** | **~220 m** |
| 1.0 | Moderada | ~110 m |
| 2.0 | Baixa | ~55 m |

---

## 🛠️ Scripts Principais

### `scripts/differential_privacy_gps.py`
Pipeline completo de privacidade diferencial:
- Download de malha viária (OSMnx)
- Aplicação de ruído (Laplace)
- Map matching para vias trafegáveis
- Validação e exportação

**Uso:**
```bash
python3 scripts/differential_privacy_gps.py <csv> [epsilon] [num_linhas]
```

### `scripts/send_to_blockchain.py`
Envio de dados protegidos para Hyperledger Besu via Web3.py

**Uso:**
```bash
python3 scripts/send_to_blockchain.py <csv_private> <config.json>
```

### `tests/test_dp.py`
Teste rápido com coordenadas de exemplo

**Uso:**
```bash
python3 tests/test_dp.py
```

---

## 📊 Arquivos Gerados

- `data/*_private.csv` - Dados com coordenadas protegidas
- `data/*_blockchain_results.csv` - Resultados do envio
- `dp_analysis.png` - Gráficos de análise
- `config/e1_gps_contract_address.json` - Config do contrato

---

## 🔧 Requisitos

- Python 3.8+
- Bibliotecas: pandas, osmnx, diffprivlib, web3, networkx, scikit-learn
- Hyperledger Besu (para blockchain)

---

**Victor | 2026-02-09 | Implementação 3.5**
