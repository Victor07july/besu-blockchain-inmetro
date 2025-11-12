"""
Fixtures compartilhadas para testes do módulo besu
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_web3():
    """
    Mock básico do Web3 conectado
    """
    mock_w3 = AsyncMock()
    mock_w3.is_connected.return_value = True
    return mock_w3


@pytest.fixture
def mock_web3_disconnected():
    """
    Mock do Web3 desconectado
    """
    mock_w3 = AsyncMock()
    mock_w3.is_connected.return_value = False
    return mock_w3


@pytest.fixture
def valid_signed_transaction():
    """Transação assinada válida em formato hexadecimal"""
    # Uma transação RLP-encoded válida (simplificada para testes)
    # Esta é uma transação real serializada que passa na validação bytes.fromhex()
    return "0xf86c808504a817c800825208949876543210abcdef0123456789abcdef0123456789880de0b6b3a764000080820a96a01234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdefa01234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"


@pytest.fixture
def mock_tx_hash():
    """
    Mock de transaction hash
    """
    mock_hash = MagicMock()
    mock_hash.hex.return_value = '0xabc123def456...'
    return mock_hash


@pytest.fixture
def mock_success_receipt():
    """
    Mock de receipt bem-sucedido (status=1)
    """
    mock_receipt = MagicMock()
    mock_receipt.status = 1
    mock_receipt.contractAddress = '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb'
    mock_receipt.gasUsed = 180910
    return mock_receipt


@pytest.fixture
def mock_failed_receipt():
    """
    Mock de receipt com falha (status=0)
    """
    mock_receipt = MagicMock()
    mock_receipt.status = 0
    mock_receipt.gasUsed = 100000
    return mock_receipt


@pytest.fixture
def mock_transaction():
    """
    Mock de transaction object
    """
    mock_tx = MagicMock()
    mock_tx.gas = 3000000
    return mock_tx


@pytest.fixture
def mock_web3_with_checksum():
    """
    Mock do Web3 com suporte a to_checksum_address e operações da rede
    """
    mock_w3 = AsyncMock()
    mock_w3.is_connected.return_value = True
    
    # Mock para conversão de checksum
    def to_checksum(address):
        # Simula conversão para checksum (uppercase em posições específicas)
        if not address.startswith('0x'):
            raise ValueError("Address must start with 0x")
        return '0xFe3B557E8Fb62b89F4916B721be55cEb828dBd73'  # Checksum válido
    
    mock_w3.to_checksum_address = to_checksum
    
    # Mock para operações da rede
    mock_w3.eth.get_transaction_count = AsyncMock(return_value=5)
    mock_w3.eth.gas_price = 1000
    mock_w3.eth.chain_id = 1337
    
    # Mock para contract
    mock_contract = MagicMock()
    mock_constructor = MagicMock()
    mock_constructor.data_in_transaction = '0x608060405234801561001057600080fd5b500000002a'  # bytecode + encoded param
    mock_contract.constructor.return_value = mock_constructor
    
    mock_w3.eth.contract.return_value = mock_contract
    
    return mock_w3


@pytest.fixture
def sample_solidity_file():
    """
    Mock de arquivo Solidity válido
    """
    mock_file = MagicMock()
    mock_file.filename = "SimpleStorage.sol"
    mock_file.read = AsyncMock(return_value=b'''
        pragma solidity ^0.8.19;
        contract SimpleStorage {
            uint256 public value;
            constructor(uint256 _initialValue) {
                value = _initialValue;
            }
        }
    ''')
    return mock_file


@pytest.fixture
def compiled_contract_result():
    """
    Resultado de compilação bem-sucedida
    """
    return {
        'abi': [
            {
                'inputs': [{'name': '_initialValue', 'type': 'uint256'}],
                'stateMutability': 'nonpayable',
                'type': 'constructor'
            },
            {
                'inputs': [],
                'name': 'value',
                'outputs': [{'name': '', 'type': 'uint256'}],
                'stateMutability': 'view',
                'type': 'function'
            }
        ],
        'bytecode': '0x608060405234801561001057600080fd5b50'
    }
