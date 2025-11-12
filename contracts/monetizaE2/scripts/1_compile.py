from solcx import compile_standard, install_solc
import json
import os

# Instala o compilador solc 0.8.19, se ainda não estiver instalado
solc = "0.8.20"
install_solc(solc)

# Caminho para o contrato
solidity_file = "../contracts/CarbonCreditNFT_E2.sol"
output_file = "../contracts/CarbonCreditNFT_E2.json"

# Ler o código do contrato
with open(solidity_file, "r") as f:
    source_code = f.read()

# Caminho absoluto para node_modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
node_modules_path = os.path.join(project_dir, "node_modules")

print(f"Diretório do projeto: {project_dir}")
print(f"Caminho node_modules: {node_modules_path}")

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
            f"@openzeppelin/={node_modules_path}/@openzeppelin/"
        ]
    }
}, 
allow_paths=f".,{node_modules_path}",
solc_version=solc)

# Salvar resultado no JSON
with open(output_file, "w") as f:
    json.dump(compiled, f, indent=2)

print(f"Contrato compilado com sucesso! ABI e bytecode salvos em {output_file}")
