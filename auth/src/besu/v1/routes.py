from http import HTTPStatus
from typing import Annotated, List, Any, Optional
from web3 import AsyncWeb3

from fastapi import APIRouter, Header, Depends, UploadFile, File, Form, HTTPException, Body
from src.core.middlewares.authentication_middleware import check_authorization
from src.besu.services import (
    is_besu_connected, 
    compile_solidity_contract,
    broadcast_signed_transaction
)
from src.besu.schemas import (
    BesuStatus, 
    ContractDeployResponse, 
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
        authorization: Annotated[str | None, Header()] = None,
    ):
    """
    Compila um contrato Solidity e retorna ABI e bytecode
    """
    is_authorized = await check_authorization(authorization)
    if not is_authorized:
        raise HTTPException(status_code=401, detail="Token de autorização inválido")
    
    return await compile_solidity_contract(contract_file)


@besu_v1_router.post("/deploy-signed/", response_model=SignedTransactionResponse, status_code=HTTPStatus.OK)
async def deploy_signed_contract(
        request: SignedTransactionRequest = Body(...),
        authorization: Annotated[str | None, Header()] = None,
        web3_client: AsyncWeb3 = Depends(get_web3_client),
    ):
    """
    ROTA RECOMENDADA PARA PRODUÇÃO 
    
    Faz o broadcast de uma transação de deploy já assinada localmente pelo cliente.
    
    **Fluxo Seguro:**
    1. Cliente chama /compile-contract/ e recebe bytecode + ABI
    2. Cliente monta a transação de deploy localmente
    3. Cliente assina a transação com sua chave privada (NUNCA sai do cliente)
    4. Cliente envia a transação assinada para esta rota
    5. Servidor faz apenas o broadcast para a rede Besu
    
    **Vantagens:**
    - Chave privada NUNCA trafega na rede
    - Compatível com hardware wallets (Ledger, Trezor)
    - Compatível com MetaMask e outras carteiras
    - Servidor não precisa armazenar chaves privadas
    - Maior auditabilidade e segurança
    
    **Parâmetros:**
    - **signed_transaction**: Raw transaction em hexadecimal (com ou sem prefixo 0x)
    
    **Retorno:**
    - **contract_address**: Endereço do contrato deployado (se for deploy)
    - **transaction_hash**: Hash da transação
    - **gas_used**: Quantidade de gas consumida
    """
    is_authorized = await check_authorization(authorization)
    if not is_authorized:
        raise HTTPException(status_code=401, detail="Token de autorização inválido")
    
    return await broadcast_signed_transaction(
        w3=web3_client,
        signed_transaction=request.signed_transaction
    )