from solcx import compile_source, install_solc, set_solc_version

# Ler o contrato
with open('CarbonCreditNFT_E2.sol', 'r') as f:
    source = f.read()

# Instalar e configurar solc
install_solc('0.8.20')
set_solc_version('0.8.20')

# Configurar remappings
import_remappings = [
    '@openzeppelin/contracts=/usr/local/lib/node_modules/@openzeppelin/contracts'
]

try:
    # Compilar
    compiled = compile_source(
        source,
        import_remappings=import_remappings,
        allow_paths='/usr/local/lib/node_modules',
        output_values=['abi', 'bin']
    )
    
    print("✅ Compilação bem-sucedida!")
    print(f"📦 Contratos compilados: {len(compiled)}")
    
    for contract_id, contract_data in compiled.items():
        contract_name = contract_id.split(':')[-1]
        bytecode_size = len(contract_data['bin']) // 2
        abi_functions = len([x for x in contract_data['abi'] if x['type'] == 'function'])
        
        print(f"\n📝 {contract_name}:")
        print(f"   - Bytecode: {bytecode_size} bytes")
        print(f"   - Funções: {abi_functions}")
        
        if contract_name == "CarbonCreditNFT_E2Calculator":
            print(f"\n🎯 Contrato principal encontrado!")
            print(f"   Gas estimado para deploy: ~{bytecode_size * 200} gas")
        
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
