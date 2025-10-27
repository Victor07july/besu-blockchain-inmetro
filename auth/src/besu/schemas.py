from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class BesuStatus(BaseModel):
    status: str

class ContractDeployRequest(BaseModel):
    private_key: str
    constructor_params: Optional[List[Any]] = []
    gas_limit: Optional[int] = 3000000
    gas_price: Optional[int] = None

class ContractDeployResponse(BaseModel):
    success: bool
    contract_address: Optional[str] = None
    transaction_hash: Optional[str] = None
    gas_used: Optional[int] = None
    compilation_output: Optional[Dict] = None
    error_message: Optional[str] = None

class ContractCompilationResponse(BaseModel):
    success: bool
    abi: Optional[List[Dict]] = None
    bytecode: Optional[str] = None
    error_message: Optional[str] = None

class SignedTransactionRequest(BaseModel):
    """
    Schema para deploy de contrato usando transação pré-assinada
    A assinatura é feita localmente pelo cliente, mantendo a chave privada segura
    """
    signed_transaction: str  # Raw transaction em hexadecimal (com ou sem 0x)

class SignedTransactionResponse(BaseModel):
    """
    Resposta do broadcast de uma transação assinada
    """
    success: bool
    contract_address: Optional[str] = None
    transaction_hash: Optional[str] = None
    gas_used: Optional[int] = None
    error_message: Optional[str] = None