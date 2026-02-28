# 🔑 Pseudônimos Rotativos no Besu - Guia Completo

## ❓ Pergunta Original

**"É possível no Besu utilizar pseudônimos na hora de receber o pagamento? Toda vez usar uma chave diferente, mas de forma que o pagamento vá para o motorista de fato?"**

## ✅ Resposta: SIM! É totalmente possível!

---

## 🎯 Como Funciona

### Conceito: HD Wallet (Hierarchical Deterministic Wallet)
 
```
Motorista tem:
├─ 1 SEED MESTRA (12 palavras secretas)
│   └─ Guardada em segurança (papel, cofre, hardware wallet)
│
└─ INFINITAS carteiras derivadas
    ├─ Carteira 0: 0x1234... (PRINCIPAL - para receber consolidado)
    ├─ Carteira 1: 0x5678... → Viagem 1
    ├─ Carteira 2: 0x9abc... → Viagem 2
    ├─ Carteira 3: 0xdef0... → Viagem 3
    └─ ...infinitas...
```

### Padrão BIP-32/BIP-44 (Bitcoin/Ethereum)

**BIP-32**: Permite derivar chaves hierarquicamente  
**BIP-44**: Define estrutura padrão de paths

```
Path: m / 44' / 60' / 0' / 0 / {index}
         │     │      │    │     │
         │     │      │    │     └─ Index (0, 1, 2, 3...)
         │     │      │    └─ External chain (0) ou Change (1)
         │     │      └─ Account (sempre 0)
         │     └─ Coin type (60 = Ethereum/Besu)
         └─ Purpose (44 = BIP-44)

Exemplos:
├─ m/44'/60'/0'/0/0  → Carteira principal (index 0)
├─ m/44'/60'/0'/0/1  → Pseudônimo 1
├─ m/44'/60'/0'/0/2  → Pseudônimo 2
└─ m/44'/60'/0'/0/N  → Pseudônimo N
```

**Propriedade matemática mágica**: 
- Da mesma seed, SEMPRE gera os mesmos endereços
- Ninguém consegue vincular os endereços (sem a seed)
- Motorista pode provar propriedade assinando mensagens

---

## 🔄 Fluxo Completo

### 1️⃣ Setup Inicial (Uma vez)

```python
from eth_account.hdaccount import generate_mnemonic

# Gerar seed mestra
mnemonic = generate_mnemonic(num_words=12)
# Exemplo: "abandon ability able about above absent absorb abstract absurd abuse access accident"

# Motorista guarda isso em SEGURANÇA:
# - Papel (em cofre físico)
# - Hardware wallet (Ledger, Trezor)
# - NUNCA digital/online!
```

**Carteira Principal** (Index 0):
```
Address: 0x1a2b3c4d5e6f7890...
└─ NUNCA usada para viagens
└─ Apenas para receber consolidado final
```

### 2️⃣ Cada Viagem (Pseudônimo Diferente)

```python
# Viagem 1
pseudo_1 = gerar_proximo_pseudonimo()  # Index 1
# Address: 0x9876543210abcdef...

# Registrar viagem no contrato usando pseudo_1
registrar_viagem(
    from_address=pseudo_1.address,
    distancia=5.7,
    co2_economizado=0.85
)

# Smart contract envia pagamento para pseudo_1
# Saldo: 0x9876... recebe R$ 0.12
```

```python
# Viagem 2 (novo pseudônimo!)
pseudo_2 = gerar_proximo_pseudonimo()  # Index 2
# Address: 0xfedcba9876543210...

registrar_viagem(
    from_address=pseudo_2.address,
    distancia=6.1,
    co2_economizado=0.92
)

# Saldo: 0xfed... recebe R$ 0.15
```

**Observador externo vê**:
```
0x9876... recebeu R$ 0.12
0xfed... recebeu R$ 0.15

❓ São pessoas diferentes? Mesma pessoa? 
→ IMPOSSÍVEL SABER sem a seed!
```

### 3️⃣ Final do Mês (Resgate)

```python
# Motorista quer resgatar tudo para carteira principal

# 1. Listar todos pseudônimos usados
pseudonimos = [
    {'address': '0x9876...', 'saldo': 0.12},
    {'address': '0xfed...', 'saldo': 0.15},
    {'address': '0xabc...', 'saldo': 0.10},
    # ... mais 27 viagens
]
# Total: R$ 3.96

# 2. Provar propriedade de cada pseudônimo
# Assina mensagem "Eu controlo 0x9876..." com chave privada de 0x9876
provas = []
for pseudo in pseudonimos:
    assinatura = assinar_com_chave_privada(pseudo.address)
    provas.append(assinatura)

# 3. Chamar smart contract
vincularEResgatar(
    pseudonimos=[0x9876..., 0xfed..., 0xabc...],
    carteira_destino=0x1a2b...,  # Principal
    provas=[sig1, sig2, sig3, ...]
)

# 4. Smart contract verifica:
# ✓ Cada assinatura é válida?
# ✓ Cada pseudônimo foi usado no sistema?
# ✓ Nenhum já foi resgatado?

# 5. Se OK: Transfere R$ 3.96 → 0x1a2b... (principal)
```


## ⚠️ Considerações Importantes

### 1. Seed é TUDO
```
🔐 GUARDE COM SEGURANÇA:
✓ Papel em cofre físico
✓ Hardware wallet
✓ Múltiplas cópias (locais diferentes)

❌ NUNCA:
✗ Screenshot no celular
✗ Email/Cloud
✗ Compartilhar com ninguém
```

### 2. Gas Fees
```
Problema: Pseudônimos novos não têm ETH para gas

Solução 1: Meta-transactions (GSN)
├─ Relayer paga gas
└─ Motorista assina transação
└─ Gas deduzido da recompensa

Solução 2: Pre-funding
├─ Enviar 0.001 ETH para cada pseudônimo antes
└─ Suficiente para 1-2 transações
```

### 3. Timing de Resgate
```
Frequência recomendada:
├─ Mensal: 30 pseudônimos → 1 resgate
├─ Semanal: 7 pseudônimos → 4 resgates/mês
└─ Diário: 1 pseudônimo → 30 resgates/mês (não vale a pena)

Trade-off: Privacy vs Gas costs
```

### 4. Limite de Pseudônimos
```
BIP-32 permite:
├─ 2^31 endereços (2 bilhões)
└─ Mais que suficiente para vida inteira!

Prático:
├─ 30 viagens/mês × 12 meses = 360/ano
├─ 360 × 50 anos = 18,000 pseudônimos
└─ Longe do limite ✓
```

---