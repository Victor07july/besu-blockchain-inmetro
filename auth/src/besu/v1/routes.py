from http import HTTPStatus
from typing import Annotated, List, Any, Optional
from web3 import AsyncWeb3

from fastapi import APIRouter, Header, Depends, UploadFile, File, Form, HTTPException, Body
from src.core.middlewares.authentication_middleware import check_authorization, check_is_admin
from src.core.repositories.users import UserBaseRepository, get_user_repository
from src.besu.services import (
    is_besu_connected, 
    compile_solidity_contract,
    broadcast_signed_transaction
)
from src.besu.schemas import (
    BesuStatus, 
    ContractCompilationResponse,
    SignedTransactionRequest,
    SignedTransactionResponse
)
from src.config.web3.setup import get_web3_client

besu_v1_router = APIRouter(prefix="/v1/besu")

@besu_v1_router.get("/connected/", response_model=BesuStatus, status_code=HTTPStatus.OK)
async def is_connected(
        authorization: Annotated[str | None, Header()] = None, 
        web3_client: AsyncWeb3 = Depends(get_web3_client),
    ):
    is_authorized = await check_authorization(authorization)
    if is_authorized:
        return await is_besu_connected(web3_client)
    return None


@besu_v1_router.post("/compile-contract/", response_model=ContractCompilationResponse, status_code=HTTPStatus.OK)
async def compile_contract(
        contract_file: UploadFile = File(..., description="Arquivo .sol do contrato Solidity"),
        deployer_address: str = Form(..., description="Endereço público da conta que fará o deploy"),
        constructor_params: str = Form("[]", description="Parâmetros do construtor em formato JSON array. Ex: [42] ou []"),
        gas_limit: int = Form(3000000, description="Limite de gas para a transação"),
        authorization: Annotated[str | None, Header()] = None,
        user_repo: UserBaseRepository = Depends(get_user_repository),
        web3_client: AsyncWeb3 = Depends(get_web3_client),
    ):

    import json
    
    is_authorized = await check_authorization(authorization)
    if not is_authorized:
        raise HTTPException(status_code=401, detail="Token de autorização inválido")
    
    # Verifica se o usuário é admin
    is_admin = await check_is_admin(authorization, user_repo)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores podem compilar contratos")
    
    # 1. Compilar o contrato
    compilation_result = await compile_solidity_contract(contract_file)
    
    if not compilation_result.success:
        return compilation_result
    
    # 2. Parsear constructor_params (vem como JSON string do Form)
    try:
        params = json.loads(constructor_params)
        if not isinstance(params, list):
            return ContractCompilationResponse(
                success=False,
                error_message="constructor_params deve ser um array JSON. Ex: [42] ou []"
            )
    except json.JSONDecodeError as e:
        return ContractCompilationResponse(
            success=False,
            error_message=f"Erro ao parsear constructor_params: {str(e)}"
        )
    
    # 3. Validar e converter deployer_address para checksum
    if not deployer_address or not deployer_address.startswith('0x'):
        return ContractCompilationResponse(
            success=False,
            error_message="deployer_address inválido. Deve começar com 0x"
        )
    
    try:
        # Converter para checksum address (Web3.py exige)
        deployer_address = web3_client.to_checksum_address(deployer_address)
    except Exception as e:
        return ContractCompilationResponse(
            success=False,
            error_message=f"deployer_address inválido: {str(e)}"
        )
    
    try:
        # 4. Criar contrato e encodar construtor com os parâmetros
        contract = web3_client.eth.contract(
            abi=compilation_result.abi,
            bytecode=compilation_result.bytecode
        )
        
        if params:
            # Encodar construtor com parâmetros
            data = contract.constructor(*params).data_in_transaction
        else:
            # Sem parâmetros, apenas bytecode
            bytecode = compilation_result.bytecode
            if not bytecode.startswith('0x'):
                bytecode = '0x' + bytecode
            data = bytecode
        
        # 5. Buscar informações da rede para montar a transação
        nonce = await web3_client.eth.get_transaction_count(deployer_address)
        gas_price = await web3_client.eth.gas_price
        chain_id = await web3_client.eth.chain_id
        
        # 6. Montar objeto transaction
        transaction = {
            'from': deployer_address,
            'nonce': nonce,
            'gas': gas_limit,
            'gasPrice': gas_price,
            'data': data,
            'chainId': chain_id,
            'value': 0
        }
        
        # 7. Retornar tudo
        return ContractCompilationResponse(
            success=True,
            abi=compilation_result.abi,
            bytecode=compilation_result.bytecode,
            transaction=transaction,
        )
        
    except Exception as e:
        return ContractCompilationResponse(
            success=False,
            error_message=f"Erro ao preparar transação: {str(e)}"
        )


@besu_v1_router.post("/deploy-signed/", response_model=SignedTransactionResponse, status_code=HTTPStatus.OK)
async def deploy_signed_contract(
        request: SignedTransactionRequest = Body(...),
        authorization: Annotated[str | None, Header()] = None,
        web3_client: AsyncWeb3 = Depends(get_web3_client),
        user_repo: UserBaseRepository = Depends(get_user_repository),
    ):

    is_authorized = await check_authorization(authorization)
    if not is_authorized:
        raise HTTPException(status_code=401, detail="Token de autorização inválido")
    
    # Verifica se o usuário é admin
    is_admin = await check_is_admin(authorization, user_repo)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores podem fazer deploy de contratos")
    
    return await broadcast_signed_transaction(
        w3=web3_client,
        signed_transaction=request.signed_transaction
    )