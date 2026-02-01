from solcx import compile_standard, install_solc
import json
import os

# Instala o compilador solc 0.8.19, se ainda não estiver instalado
solc = "0.8.19"
install_solc(solc)

# Caminho para o contrato
solidity_file = "../../contracts/E1/CarbonCreditNFT_E1.sol"
output_file = "../../contracts/E1/CarbonCreditNFT_E1.json"

# Ler o código do contrato
with open(solidity_file, "r") as f:
    source_code = f.read()

# Caminho absoluto para node_modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
# node_modules_path = os.path.join(project_dir, "node_modules")
node_modules_path = "/home/inmetro/besu-quickstarter-modified/dapps/monetiza_co2/node_modules"

print(f"Diretório do projeto: {project_dir}")
print(f"Caminho node_modules: {node_modules_path}")

# Verificar se OpenZeppelin existe
openzeppelin_path = os.path.join(node_modules_path, "@openzeppelin", "contracts")
if not os.path.exists(openzeppelin_path):
    print(f"❌ ERRO: OpenZeppelin não encontrado em {openzeppelin_path}")
    print("Execute: npm install @openzeppelin/contracts@4.9.6")
    exit(1)

print(f"✅ OpenZeppelin encontrado em: {openzeppelin_path}")

# Compilar
compiled = compile_standard({
    "language": "Solidity",
    "sources": {
        solidity_file: {
            "content": source_code
        }
    },
    "settings": {
        "outputSelection": {
            "*": {
                "*": ["abi", "evm.bytecode", "evm.sourceMap"]
            }
        },
        "remappings": [
            f"@openzeppelin/contracts/={openzeppelin_path}/"
        ]
    }
}, 
allow_paths=[project_dir, node_modules_path, openzeppelin_path],
solc_version=solc)

# Salvar resultado no JSON
with open(output_file, "w") as f:
    json.dump(compiled, f, indent=2)

print(f"Contrato compilado com sucesso! ABI e bytecode salvos em {output_file}")
