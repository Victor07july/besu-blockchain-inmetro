from http import HTTPStatus
from typing import Annotated, List, Any, Optional
from web3 import AsyncWeb3

from fastapi import APIRouter, Header, Depends, UploadFile, File, Form, HTTPException
from src.core.middlewares.authentication_middleware import check_authorization
from src.besu.services import is_besu_connected, compile_and_deploy_contract, compile_solidity_contract
from src.besu.schemas import BesuStatus, ContractDeployResponse, ContractCompilationResponse
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


@besu_v1_router.post("/deploy-contract/", response_model=ContractDeployResponse, status_code=HTTPStatus.OK)
async def deploy_contract_endpoint(
        contract_file: UploadFile = File(..., description="Arquivo .sol do contrato Solidity"),
        private_key: str = Form(..., description="Chave privada da conta que irá fazer o deploy (sem o prefixo 0x)"),
        constructor_params: Optional[str] = Form(None, description="Parâmetros do construtor em JSON (ex: [42, 'hello'])"),
        gas_limit: Optional[int] = Form(3000000, description="Limite de gas para o deploy"),
        gas_price: Optional[int] = Form(None, description="Preço do gas (wei). Se não fornecido, usa o preço atual da rede"),
        authorization: Annotated[str | None, Header()] = None,
        web3_client: AsyncWeb3 = Depends(get_web3_client),
    ):
    """
    Compila e realiza o deploy de um contrato Solidity na blockchain Besu
    
    - **contract_file**: Arquivo .sol com o código do contrato
    - **private_key**: Chave privada da conta para assinar a transação
    - **constructor_params**: Parâmetros do construtor em formato JSON (opcional)
    - **gas_limit**: Limite de gas para a transação (padrão: 3000000)
    - **gas_price**: Preço do gas em wei (opcional, usa preço atual se não fornecido)
    """
    is_authorized = await check_authorization(authorization)
    if not is_authorized:
        raise HTTPException(status_code=401, detail="Token de autorização inválido")
    
    # Parse dos parâmetros do construtor
    parsed_constructor_params = []
    if constructor_params:
        try:
            import json
            parsed_constructor_params = json.loads(constructor_params)
            if not isinstance(parsed_constructor_params, list):
                raise ValueError("Parâmetros devem ser uma lista")
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Parâmetros do construtor inválidos: {str(e)}. Use formato JSON como [42, 'hello']"
            )
    
    return await compile_and_deploy_contract(
        contract_file=contract_file,
        w3=web3_client,
        private_key=private_key,
        constructor_params=parsed_constructor_params,
        gas_limit=gas_limit,
        gas_price=gas_price
    )