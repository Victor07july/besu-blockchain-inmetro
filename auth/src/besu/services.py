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
            # Versão padrão se não encontrar pragma
            solc_version = "0.8.10"
        
        # Instalar e configurar versão do solc se necessário
        try:
            install_solc(solc_version)
            set_solc_version(solc_version)
        except Exception as version_error:
            # Se falhar, tentar com versão padrão
            try:
                install_solc("0.8.10")
                set_solc_version("0.8.10")
            except Exception as fallback_error:
                return ContractCompilationResponse(
                    success=False,
                    error_message=f"Erro ao instalar compilador Solidity: {str(fallback_error)}"
                )
        
        # Compilar o contrato
        try:
            compiled_sol = compile_source(source_code)
            
            # Pegar o primeiro contrato compilado
            contract_id, contract_interface = next(iter(compiled_sol.items()))
            
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
    constructor_params: List[Any] = None,
    gas_limit: int = 3000000,
    gas_price: Optional[int] = None
) -> ContractDeployResponse:
    """
    Realiza o deploy de um contrato compilado na blockchain Besu
    """
    try:
        # Verificar conexão
        if not await w3.is_connected():
            return ContractDeployResponse(
                success=False,
                error_message="Não foi possível conectar ao Besu"
            )
        
        # Obter contas disponíveis
        accounts = await w3.eth.accounts
        if not accounts:
            return ContractDeployResponse(
                success=False,
                error_message="Nenhuma conta disponível para deploy"
            )
        
        # Usar primeira conta como padrão
        from_account = accounts[0]
        
        # Preparar parâmetros do construtor
        if constructor_params is None:
            constructor_params = []
        
        # Criar contrato
        contract = w3.eth.contract(abi=abi, bytecode=bytecode)
        
        # Preparar transação de deploy
        transaction = contract.constructor(*constructor_params).build_transaction({
            'from': from_account,
            'gas': gas_limit,
            'gasPrice': gas_price or await w3.eth.gas_price,
            'nonce': await w3.eth.get_transaction_count(from_account),
        })
        
        # Enviar transação
        tx_hash = await w3.eth.send_transaction(transaction)
        
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
            return ContractDeployResponse(
                success=False,
                error_message="Transação falhou durante o deploy"
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

