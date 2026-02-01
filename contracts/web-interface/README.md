# 🌱 CarbonCredit E2 - Interface Web

Interface web completa para interagir com o contrato CarbonCreditNFT_E2Calculator na blockchain Besu.

## 📋 Funcionalidades

### 🏪 Marketplace
- Visualizar todos os NFTs disponíveis
- Filtrar tokens à venda
- Ver detalhes completos de cada token (cálculos E2, distância, etc.)
- Comprar tokens listados

### ➕ Criar NFT
- Formulário interativo para criar novos NFTs
- Inserir parâmetros de viagem (distâncias, eficiências, comportamento)
- Cálculo automático do valor E2 no blockchain
- Tokenização instantânea

### 🎨 Meus Tokens
- Buscar tokens por endereço
- Visualizar todos os seus NFTs
- Listar tokens para venda no marketplace
- Remover tokens da venda
- Ver detalhes de cada token

## 🚀 Como Usar

### 1. Instalar Dependências

```bash
cd /home/victor/besu-quickstarter-modified/dapps/web-interface
npm install
```

### 2. Configurar Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env`:

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas configurações:

```env
RPC_URL=http://localhost:8545
CONTRACT_ADDRESS=0x33a50F9Fcbb32366b4C2aD1923eB92A454E5B061
PRIVATE_KEY=0x60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3
PORT=3000
```

**⚠️ IMPORTANTE:**
- `CONTRACT_ADDRESS`: Endereço do contrato deployado
- `PRIVATE_KEY`: Chave privada da conta autorizada a criar NFTs
- `RPC_URL`: URL do nó Besu (padrão: http://localhost:8545)

### 3. Iniciar o Servidor

```bash
npm start
```

Ou para desenvolvimento com auto-reload:

```bash
npm run dev
```

### 4. Acessar a Interface

Abra seu navegador em: **http://localhost:3000**

## 🔌 API REST

O servidor também expõe uma API REST completa:

### Informações do Contrato
```
GET /api/contract/info
```

### Listar Todos os Tokens
```
GET /api/tokens
```

### Detalhes de um Token
```
GET /api/tokens/:tokenId
```

### Tokens de um Endereço
```
GET /api/tokens/owner/:address
```

### Criar NFT
```
POST /api/tokens/create
Body: {
  "params": {
    "highwayDistance": 10.5,
    "cityDistance": 15.2,
    "ethanolPercent": 30,
    "roadGasoline": 12.5,
    "roadEthanol": 9.8,
    "cityGasoline": 10.3,
    "cityEthanol": 8.5,
    "behaviorCautious": 60,
    "behaviorNormal": 25,
    "behaviorAggressive": 15
  },
  "recipient": "0x..."
}
```

### Listar Token para Venda
```
POST /api/tokens/:tokenId/list
Body: { "priceBRL": 100.50 }
```

### Remover Token da Venda
```
POST /api/tokens/:tokenId/delist
```

### Comprar Token
```
POST /api/tokens/:tokenId/buy
Body: { "buyerPrivateKey": "0x..." }
```

## 📦 Estrutura do Projeto

```
web-interface/
├── server.js              # Servidor Node.js + Express
├── package.json           # Dependências
├── .env                   # Configurações (NÃO commitar!)
├── .env.example           # Exemplo de configuração
├── README.md              # Este arquivo
└── public/                # Frontend
    ├── index.html         # Interface web
    ├── styles.css         # Estilos
    └── app.js             # Lógica frontend
```

## 🔐 Segurança

**⚠️ ATENÇÃO:**
- Nunca compartilhe sua chave privada (`PRIVATE_KEY`)
- Não commite o arquivo `.env` no git
- Para produção, use variáveis de ambiente seguras
- Para compras, a chave privada é solicitada via prompt (não é ideal para produção)

## 🛠️ Tecnologias Utilizadas

- **Backend:**
  - Node.js
  - Express
  - ethers.js v6
  - CORS
  - dotenv

- **Frontend:**
  - HTML5
  - CSS3 (design responsivo)
  - JavaScript (Vanilla)

## 📊 Exemplo de Uso

### 1. Criar um NFT via Interface
1. Acesse a aba "Criar NFT"
2. Preencha os dados da viagem
3. Certifique-se que os comportamentos somam 100%
4. Digite o endereço do destinatário
5. Clique em "Criar NFT"

### 2. Listar Token no Marketplace
1. Acesse "Meus Tokens"
2. Digite seu endereço
3. Clique em "🏷️ Listar" no token desejado
4. Digite o preço em BRL
5. Confirme

### 3. Comprar Token
1. Acesse o "Marketplace"
2. Clique em um token à venda
3. Clique em "💰 Comprar"
4. Digite sua chave privada
5. Confirme a compra

## 🐛 Troubleshooting

### Servidor não inicia
- Verifique se a porta 3000 está livre
- Confirme que todas as dependências foram instaladas
- Verifique o arquivo `.env`

### Erro ao conectar com blockchain
- Certifique-se que o nó Besu está rodando
- Verifique a `RPC_URL` no `.env`
- Confirme que o contrato está deployado

### Transações falhando
- Verifique se a conta está autorizada no contrato
- Confirme que há saldo suficiente para gas
- Verifique os logs do servidor para detalhes

## 📞 Suporte

Para dúvidas ou problemas, consulte os logs do servidor:
```bash
npm start
```

Os logs mostrarão detalhes de cada requisição e possíveis erros.
