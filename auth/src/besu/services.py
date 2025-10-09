import os
import json
from typing import Dict, List, Any, Optional
from web3 import AsyncWeb3
from web3.exceptions import ContractLogicError, TransactionNotFound
from fastapi import UploadFile, HTTPException

from src.besu.schemas import ContractDeployResponse, ContractCompilationResponse


async def is_besu_connected(w3: AsyncWeb3):
    return {"status": "ok"} if await w3.is_connected() else {"status": "error"}


async def compile_solidity_contract(contract_file: UploadFile) -> ContractCompilationResponse:
    """
    Compila um contrato Solidity usando py-solc-x (compilador Python)
    """
    try:
        from solcx import compile_source, install_solc, set_solc_version
        import re
        
        # Validar extensão do arquivo
        if not contract_file.filename.endswith('.sol'):
            return ContractCompilationResponse(
                success=False,
                error_message="Arquivo deve ter extensão .sol"
            )
        
        # Ler conteúdo do arquivo
        content = await contract_file.read()
        source_code = content.decode('utf-8')
        
        # Detectar versão do Solidity do pragma
        pragma_match = re.search(r'pragma\s+solidity\s+[\^~]?([0-9]+\.[0-9]+\.[0-9]+)', source_code)
        if pragma_match:
            solc_version = pragma_match.group(1)
        else:
            # Tentar detectar apenas major.minor
            pragma_match = re.search(r'pragma\s+solidity\s+[\^~]?([0-9]+\.[0-9]+)', source_code)
            if pragma_match:
                version_parts = pragma_match.group(1)
                # Para versões antigas como ^0.4.8, usar a última versão da série
                if version_parts.startswith('0.4'):
                    solc_version = "0.4.26"  # Última versão 0.4.x
                elif version_parts.startswith('0.5'):
                    solc_version = "0.5.17"  # Última versão 0.5.x
                elif version_parts.startswith('0.6'):
                    solc_version = "0.6.12"  # Última versão 0.6.x
                elif version_parts.startswith('0.7'):
                    solc_version = "0.7.6"   # Última versão 0.7.x
                elif version_parts.startswith('0.8'):
                    solc_version = "0.8.19"  # Versão estável 0.8.x
                else:
                    solc_version = "0.8.19"  # Versão padrão
            else:
                # Versão padrão se não encontrar pragma
                solc_version = "0.8.19"
        
        # Instalar e configurar versão do solc se necessário
        try:
            install_solc(solc_version)
            set_solc_version(solc_version)
        except Exception as version_error:
            # Se falhar, tentar com versão padrão
            try:
                install_solc("0.8.19")
                set_solc_version("0.8.19")
            except Exception as fallback_error:
                return ContractCompilationResponse(
                    success=False,
                    error_message=f"Erro ao instalar compilador Solidity: {str(fallback_error)}"
                )
        
        # Compilar o contrato
        try:
            # Configurar remappings para OpenZeppelin (formato correto para py-solc-x)
            import_remappings = [
                '@openzeppelin/contracts=/usr/local/lib/node_modules/@openzeppelin/contracts'
            ]
            
            # Tentar compilar com remappings
            try:
                compiled_sol = compile_source(
                    source_code,
                    import_remappings=import_remappings,
                    allow_paths='/usr/local/lib/node_modules'
                )
            except Exception as e:
                # Se falhar com remappings, tentar sem (para contratos simples)
                compiled_sol = compile_source(source_code)
            
            # Pegar o contrato PRINCIPAL (aquele com maior bytecode)
            # Quando há imports OpenZeppelin, múltiplos contratos são compilados
            # O contrato principal é aquele que tem bytecode deployável (maior tamanho)
            main_contract = None
            max_bytecode_size = 0
            
            for contract_id, contract_interface in compiled_sol.items():
                bytecode_size = len(contract_interface['bin'])
                if bytecode_size > max_bytecode_size:
                    max_bytecode_size = bytecode_size
                    main_contract = (contract_id, contract_interface)
            
            if not main_contract:
                # Fallback: pegar o primeiro contrato
                contract_id, contract_interface = next(iter(compiled_sol.items()))
            else:
                contract_id, contract_interface = main_contract
            
            # Extrair ABI e bytecode
            abi = contract_interface['abi']
            bytecode = contract_interface['bin']
            
            return ContractCompilationResponse(
                success=True,
                abi=abi,
                bytecode=bytecode
            )
            
        except Exception as compile_error:
            error_message = str(compile_error)
            
            # Tratar erros comuns de compilação
            if "DeclarationError" in error_message:
                error_message = f"Erro de declaração no contrato: {error_message}"
            elif "TypeError" in error_message:
                error_message = f"Erro de tipo no contrato: {error_message}"
            elif "SyntaxError" in error_message:
                error_message = f"Erro de sintaxe no contrato: {error_message}"
            
            return ContractCompilationResponse(
                success=False,
                error_message=f"Erro de compilação: {error_message}"
            )
                
    except ImportError:
        return ContractCompilationResponse(
            success=False,
            error_message="Biblioteca py-solc-x não está instalada. Execute: pip install py-solc-x"
        )
    except Exception as e:
        return ContractCompilationResponse(
            success=False,
            error_message=f"Erro interno: {str(e)}"
        )


async def deploy_contract(
    w3: AsyncWeb3,
    abi: List[Dict],
    bytecode: str,
    private_key: str,
    constructor_params: List[Any] = None,
    gas_limit: int = 3000000,
    gas_price: Optional[int] = None
) -> ContractDeployResponse:
    """
    Realiza o deploy de um contrato compilado na blockchain Besu
    """
    try:
        from eth_account import Account
        
        # Verificar conexão
        if not await w3.is_connected():
            return ContractDeployResponse(
                success=False,
                error_message="Não foi possível conectar ao Besu"
            )
        
        # Validar chave privada
        if not private_key:
            return ContractDeployResponse(
                success=False,
                error_message="Chave privada não fornecida"
            )
        
        # Adicionar '0x' se necessário
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        
        # Obter conta a partir da chave privada
        try:
            account = Account.from_key(private_key)
            from_account = account.address
        except Exception as e:
            return ContractDeployResponse(
                success=False,
                error_message=f"Chave privada inválida: {str(e)}"
            )
        
        # Preparar parâmetros do construtor
        if constructor_params is None:
            constructor_params = []
        
        # Criar contrato
        contract = w3.eth.contract(abi=abi, bytecode=bytecode)
        
        # Obter valores necessários primeiro
        current_gas_price = gas_price or await w3.eth.gas_price
        current_nonce = await w3.eth.get_transaction_count(from_account)
        current_chain_id = await w3.eth.chain_id
        
        # Preparar transação de deploy (await para AsyncWeb3)
        transaction = await contract.constructor(*constructor_params).build_transaction({
            'from': from_account,
            'gas': gas_limit,
            'gasPrice': current_gas_price,
            'nonce': current_nonce,
            'chainId': current_chain_id,
        })
        
        # Assinar transação localmente
        signed_txn = account.sign_transaction(transaction)
        
        # Enviar transação assinada
        tx_hash = await w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        
        # Aguardar confirmação
        tx_receipt = await w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Verificar se o deploy foi bem-sucedido
        if tx_receipt.status == 1:
            return ContractDeployResponse(
                success=True,
                contract_address=tx_receipt.contractAddress,
                transaction_hash=tx_hash.hex(),
                gas_used=tx_receipt.gasUsed
            )
        else:
            # Deploy falhou - coletar informações detalhadas
            error_details = {
                'status': tx_receipt.status,
                'gasUsed': tx_receipt.gasUsed,
                'gasLimit': gas_limit,
                'blockNumber': tx_receipt.blockNumber,
                'transactionHash': tx_hash.hex()
            }
            
            # Verificar se ficou sem gas
            if tx_receipt.gasUsed >= gas_limit * 0.95:
                error_msg = f"Out of Gas: usou {tx_receipt.gasUsed}/{gas_limit} gas. Aumente o gas_limit para pelo menos {int(gas_limit * 1.5)}"
            else:
                error_msg = f"Transação revertida (status=0). Gas usado: {tx_receipt.gasUsed}/{gas_limit}. Possível erro no construtor do contrato."
            
            return ContractDeployResponse(
                success=False,
                error_message=error_msg,
                gas_used=tx_receipt.gasUsed,
                transaction_hash=tx_hash.hex()
            )
            
    except ContractLogicError as e:
        return ContractDeployResponse(
            success=False,
            error_message=f"Erro de lógica do contrato: {str(e)}"
        )
    except Exception as e:
        return ContractDeployResponse(
            success=False,
            error_message=f"Erro durante deploy: {str(e)}"
        )


async def compile_and_deploy_contract(
    contract_file: UploadFile,
    w3: AsyncWeb3,
    private_key: str,
    constructor_params: List[Any] = None,
    gas_limit: int = 3000000,
    gas_price: Optional[int] = None
) -> ContractDeployResponse:
    """
    Função principal que compila e realiza o deploy de um contrato
    """
    try:
        # Reset file pointer
        await contract_file.seek(0)
        
        # Compilar contrato
        compilation_result = await compile_solidity_contract(contract_file)
        
        if not compilation_result.success:
            return ContractDeployResponse(
                success=False,
                error_message=f"Falha na compilação: {compilation_result.error_message}",
                compilation_output=compilation_result.dict()
            )
        
        # Deploy contrato
        deploy_result = await deploy_contract(
            w3=w3,
            abi=compilation_result.abi,
            bytecode=compilation_result.bytecode,
            private_key=private_key,
            constructor_params=constructor_params,
            gas_limit=gas_limit,
            gas_price=gas_price
        )
        
        # Adicionar informações de compilação ao resultado
        deploy_result.compilation_output = compilation_result.dict()
        
        return deploy_result
        
    except Exception as e:
        return ContractDeployResponse(
            success=False,
            error_message=f"Erro geral: {str(e)}"
        )

