"""
Testes de integração para a rota POST /api/v1/besu/compile-contract/

Testa todos os cenários da nova funcionalidade que:
1. Compila o contrato Solidity
2. Valida e converte deployer_address para checksum
3. Parseia constructor_params
4. Encoda construtor com parâmetros
5. Busca nonce, gas_price, chain_id do Besu
6. Retorna objeto transaction pronto para assinar
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile
from src.besu.v1.routes import compile_contract
from src.besu.schemas import ContractCompilationResponse


@pytest.mark.asyncio
class TestCompileContractRoute:
    """
    Testes de integração para a rota /compile-contract/
    """
    
    async def test_success_with_constructor_params(
        self,
        sample_solidity_file,
        mock_web3_with_checksum
    ):
        """
        Cenário: Compilação bem-sucedida com parâmetros do construtor
        Resultado esperado: Retorna abi, bytecode E transaction pronto
        """
        # Arrange
        deployer_address = "0xfe3b557e8fb62b89f4916b721be55ceb828dbd73"
        constructor_params = "[42]"
        gas_limit = 3000000
        
        mock_user_repo = AsyncMock()
        mock_authorization = "Bearer valid_token"
        
        with patch('src.besu.v1.routes.check_authorization', return_value=True), \
             patch('src.besu.v1.routes.check_is_admin', return_value=True), \
             patch('src.besu.v1.routes.compile_solidity_contract') as mock_compile:
            
            # Mock de compilação bem-sucedida
            mock_compile.return_value = ContractCompilationResponse(
                success=True,
                abi=[{'name': 'value', 'type': 'function'}],
                bytecode='0x608060405234801561001057600080fd5b50'
            )
            
            # Act
            result = await compile_contract(
                contract_file=sample_solidity_file,
                deployer_address=deployer_address,
                constructor_params=constructor_params,
                gas_limit=gas_limit,
                authorization=mock_authorization,
                user_repo=mock_user_repo,
                web3_client=mock_web3_with_checksum
            )
        
        # Assert
        assert result.success == True
        assert result.abi is not None
        assert result.bytecode is not None
        assert result.transaction is not None
        
        # Verificar estrutura do transaction
        tx = result.transaction
        assert tx['from'] == '0xFe3B557E8Fb62b89F4916B721be55cEb828dBd73'  # Checksum
        assert tx['nonce'] == 5
        assert tx['gas'] == 3000000
        assert tx['gasPrice'] == 1000
        assert tx['chainId'] == 1337
        assert tx['value'] == 0
        assert 'data' in tx
        assert tx['data'].startswith('0x')
    
    async def test_success_without_constructor_params(
        self,
        sample_solidity_file,
        mock_web3_with_checksum
    ):
        """
        Cenário: Compilação sem parâmetros do construtor
        Resultado esperado: data = apenas bytecode
        """
        # Arrange
        deployer_address = "0xfe3b557e8fb62b89f4916b721be55ceb828dbd73"
        constructor_params = "[]"  # Vazio
        
        mock_user_repo = AsyncMock()
        mock_authorization = "Bearer valid_token"
        
        with patch('src.besu.v1.routes.check_authorization', return_value=True), \
             patch('src.besu.v1.routes.check_is_admin', return_value=True), \
             patch('src.besu.v1.routes.compile_solidity_contract') as mock_compile:
            
            mock_compile.return_value = ContractCompilationResponse(
                success=True,
                abi=[],
                bytecode='608060405234801561001057600080fd5b50'  # Sem 0x
            )
            
            # Act
            result = await compile_contract(
                contract_file=sample_solidity_file,
                deployer_address=deployer_address,
                constructor_params=constructor_params,
                gas_limit=3000000,
                authorization=mock_authorization,
                user_repo=mock_user_repo,
                web3_client=mock_web3_with_checksum
            )
        
        # Assert
        assert result.success == True
        assert result.transaction is not None
        # Data deve ser apenas o bytecode (com 0x adicionado)
        assert result.transaction['data'] == '0x608060405234801561001057600080fd5b50'
    
    async def test_unauthorized_user(
        self,
        sample_solidity_file,
        mock_web3_with_checksum
    ):
        """
        Cenário: Usuário não autenticado
        Resultado esperado: HTTPException 401
        """
        # Arrange
        mock_user_repo = AsyncMock()
        mock_authorization = "Bearer invalid_token"
        
        with patch('src.besu.v1.routes.check_authorization', return_value=False), \
             pytest.raises(Exception) as exc_info:
            
            # Act
            await compile_contract(
                contract_file=sample_solidity_file,
                deployer_address="0xfe3b557e8fb62b89f4916b721be55ceb828dbd73",
                constructor_params="[]",
                gas_limit=3000000,
                authorization=mock_authorization,
                user_repo=mock_user_repo,
                web3_client=mock_web3_with_checksum
            )
        
        # Assert
        assert "401" in str(exc_info.value) or "autorização" in str(exc_info.value).lower()
    
    async def test_non_admin_user(
        self,
        sample_solidity_file,
        mock_web3_with_checksum
    ):
        """
        Cenário: Usuário autenticado mas não é admin
        Resultado esperado: HTTPException 403
        """
        # Arrange
        mock_user_repo = AsyncMock()
        mock_authorization = "Bearer valid_token"
        
        with patch('src.besu.v1.routes.check_authorization', return_value=True), \
             patch('src.besu.v1.routes.check_is_admin', return_value=False), \
             pytest.raises(Exception) as exc_info:
            
            # Act
            await compile_contract(
                contract_file=sample_solidity_file,
                deployer_address="0xfe3b557e8fb62b89f4916b721be55ceb828dbd73",
                constructor_params="[]",
                gas_limit=3000000,
                authorization=mock_authorization,
                user_repo=mock_user_repo,
                web3_client=mock_web3_with_checksum
            )
        
        # Assert
        assert "403" in str(exc_info.value) or "administrador" in str(exc_info.value).lower()
    
    async def test_compilation_failure(
        self,
        sample_solidity_file,
        mock_web3_with_checksum
    ):
        """
        Cenário: Compilação falha (erro de sintaxe, etc)
        Resultado esperado: Retorna erro de compilação, não tenta montar transaction
        """
        # Arrange
        mock_user_repo = AsyncMock()
        mock_authorization = "Bearer valid_token"
        
        with patch('src.besu.v1.routes.check_authorization', return_value=True), \
             patch('src.besu.v1.routes.check_is_admin', return_value=True), \
             patch('src.besu.v1.routes.compile_solidity_contract') as mock_compile:
            
            mock_compile.return_value = ContractCompilationResponse(
                success=False,
                error_message="SyntaxError: Expected identifier"
            )
            
            # Act
            result = await compile_contract(
                contract_file=sample_solidity_file,
                deployer_address="0xfe3b557e8fb62b89f4916b721be55ceb828dbd73",
                constructor_params="[]",
                gas_limit=3000000,
                authorization=mock_authorization,
                user_repo=mock_user_repo,
                web3_client=mock_web3_with_checksum
            )
        
        # Assert
        assert result.success == False
        assert "SyntaxError" in result.error_message
        assert result.transaction is None
    
    async def test_invalid_constructor_params_not_array(
        self,
        sample_solidity_file,
        mock_web3_with_checksum
    ):
        """
        Cenário: constructor_params não é um array JSON
        Resultado esperado: Erro de validação
        """
        # Arrange
        mock_user_repo = AsyncMock()
        mock_authorization = "Bearer valid_token"
        
        with patch('src.besu.v1.routes.check_authorization', return_value=True), \
             patch('src.besu.v1.routes.check_is_admin', return_value=True), \
             patch('src.besu.v1.routes.compile_solidity_contract') as mock_compile:
            
            mock_compile.return_value = ContractCompilationResponse(
                success=True,
                abi=[],
                bytecode='0x608060'
            )
            
            # Act
            result = await compile_contract(
                contract_file=sample_solidity_file,
                deployer_address="0xfe3b557e8fb62b89f4916b721be55ceb828dbd73",
                constructor_params='{"not": "array"}',  # Objeto, não array
                gas_limit=3000000,
                authorization=mock_authorization,
                user_repo=mock_user_repo,
                web3_client=mock_web3_with_checksum
            )
        
        # Assert
        assert result.success == False
        assert "array" in result.error_message.lower()
    
    async def test_invalid_constructor_params_malformed_json(
        self,
        sample_solidity_file,
        mock_web3_with_checksum
    ):
        """
        Cenário: constructor_params não é JSON válido
        Resultado esperado: Erro de parsing
        """
        # Arrange
        mock_user_repo = AsyncMock()
        mock_authorization = "Bearer valid_token"
        
        with patch('src.besu.v1.routes.check_authorization', return_value=True), \
             patch('src.besu.v1.routes.check_is_admin', return_value=True), \
             patch('src.besu.v1.routes.compile_solidity_contract') as mock_compile:
            
            mock_compile.return_value = ContractCompilationResponse(
                success=True,
                abi=[],
                bytecode='0x608060'
            )
            
            # Act
            result = await compile_contract(
                contract_file=sample_solidity_file,
                deployer_address="0xfe3b557e8fb62b89f4916b721be55ceb828dbd73",
                constructor_params='[42, invalid json',  # JSON malformado
                gas_limit=3000000,
                authorization=mock_authorization,
                user_repo=mock_user_repo,
                web3_client=mock_web3_with_checksum
            )
        
        # Assert
        assert result.success == False
        assert "parsear" in result.error_message.lower()
    
    async def test_invalid_deployer_address_no_0x(
        self,
        sample_solidity_file,
        mock_web3_with_checksum
    ):
        """
        Cenário: deployer_address sem prefixo 0x
        Resultado esperado: Erro de validação
        """
        # Arrange
        mock_user_repo = AsyncMock()
        mock_authorization = "Bearer valid_token"
        
        with patch('src.besu.v1.routes.check_authorization', return_value=True), \
             patch('src.besu.v1.routes.check_is_admin', return_value=True), \
             patch('src.besu.v1.routes.compile_solidity_contract') as mock_compile:
            
            mock_compile.return_value = ContractCompilationResponse(
                success=True,
                abi=[],
                bytecode='0x608060'
            )
            
            # Act
            result = await compile_contract(
                contract_file=sample_solidity_file,
                deployer_address="fe3b557e8fb62b89f4916b721be55ceb828dbd73",  # Sem 0x
                constructor_params="[]",
                gas_limit=3000000,
                authorization=mock_authorization,
                user_repo=mock_user_repo,
                web3_client=mock_web3_with_checksum
            )
        
        # Assert
        assert result.success == False
        assert "0x" in result.error_message
    
    async def test_invalid_deployer_address_bad_format(
        self,
        sample_solidity_file,
        mock_web3_with_checksum
    ):
        """
        Cenário: deployer_address com formato inválido
        Resultado esperado: Erro ao converter para checksum
        """
        # Arrange
        mock_user_repo = AsyncMock()
        mock_authorization = "Bearer valid_token"
        
        # Mock que lança exceção ao tentar converter
        mock_w3_failing = AsyncMock()
        mock_w3_failing.is_connected.return_value = True
        mock_w3_failing.to_checksum_address.side_effect = ValueError("Invalid address format")
        
        with patch('src.besu.v1.routes.check_authorization', return_value=True), \
             patch('src.besu.v1.routes.check_is_admin', return_value=True), \
             patch('src.besu.v1.routes.compile_solidity_contract') as mock_compile:
            
            mock_compile.return_value = ContractCompilationResponse(
                success=True,
                abi=[],
                bytecode='0x608060'
            )
            
            # Act
            result = await compile_contract(
                contract_file=sample_solidity_file,
                deployer_address="0xINVALID",
                constructor_params="[]",
                gas_limit=3000000,
                authorization=mock_authorization,
                user_repo=mock_user_repo,
                web3_client=mock_w3_failing
            )
        
        # Assert
        assert result.success == False
        assert "inválido" in result.error_message.lower()
    
    async def test_exception_during_transaction_preparation(
        self,
        sample_solidity_file,
        mock_web3_with_checksum
    ):
        """
        Cenário: Exceção inesperada ao preparar transação (ex: erro ao buscar nonce)
        Resultado esperado: Erro de preparação de transação
        """
        # Arrange
        mock_user_repo = AsyncMock()
        mock_authorization = "Bearer valid_token"
        
        # Mock que falha ao buscar nonce
        mock_w3_failing = AsyncMock()
        mock_w3_failing.is_connected.return_value = True
        mock_w3_failing.to_checksum_address.return_value = '0xFe3B557E8Fb62b89F4916B721be55cEb828dBd73'
        mock_w3_failing.eth.get_transaction_count.side_effect = Exception("Network error")
        
        with patch('src.besu.v1.routes.check_authorization', return_value=True), \
             patch('src.besu.v1.routes.check_is_admin', return_value=True), \
             patch('src.besu.v1.routes.compile_solidity_contract') as mock_compile:
            
            mock_compile.return_value = ContractCompilationResponse(
                success=True,
                abi=[],
                bytecode='0x608060'
            )
            
            # Act
            result = await compile_contract(
                contract_file=sample_solidity_file,
                deployer_address="0xfe3b557e8fb62b89f4916b721be55ceb828dbd73",
                constructor_params="[]",
                gas_limit=3000000,
                authorization=mock_authorization,
                user_repo=mock_user_repo,
                web3_client=mock_w3_failing
            )
        
        # Assert
        assert result.success == False
        assert "preparar transação" in result.error_message.lower()


@pytest.mark.asyncio
class TestEdgeCasesCompileRoute:
    """
    Testes de casos extremos da rota /compile-contract/
    """
    
    async def test_multiple_constructor_params(
        self,
        sample_solidity_file,
        mock_web3_with_checksum
    ):
        """
        Cenário: Múltiplos parâmetros do construtor (string, uint, address)
        Resultado esperado: Todos os parâmetros são encodados corretamente
        """
        # Arrange
        mock_user_repo = AsyncMock()
        mock_authorization = "Bearer valid_token"
        
        # Parâmetros complexos: [string, uint256, address]
        constructor_params = '["TokenName", 1000000, "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"]'
        
        with patch('src.besu.v1.routes.check_authorization', return_value=True), \
             patch('src.besu.v1.routes.check_is_admin', return_value=True), \
             patch('src.besu.v1.routes.compile_solidity_contract') as mock_compile:
            
            mock_compile.return_value = ContractCompilationResponse(
                success=True,
                abi=[],
                bytecode='0x608060'
            )
            
            # Act
            result = await compile_contract(
                contract_file=sample_solidity_file,
                deployer_address="0xfe3b557e8fb62b89f4916b721be55ceb828dbd73",
                constructor_params=constructor_params,
                gas_limit=3000000,
                authorization=mock_authorization,
                user_repo=mock_user_repo,
                web3_client=mock_web3_with_checksum
            )
        
        # Assert
        assert result.success == True
        assert result.transaction is not None
        # Data deve conter bytecode + params encodados
        assert len(result.transaction['data']) > len('0x608060')
    
    async def test_custom_gas_limit(
        self,
        sample_solidity_file,
        mock_web3_with_checksum
    ):
        """
        Cenário: Gas limit customizado (maior que o padrão)
        Resultado esperado: Transaction usa o gas_limit especificado
        """
        # Arrange
        mock_user_repo = AsyncMock()
        mock_authorization = "Bearer valid_token"
        custom_gas_limit = 5000000  # 5 milhões
        
        with patch('src.besu.v1.routes.check_authorization', return_value=True), \
             patch('src.besu.v1.routes.check_is_admin', return_value=True), \
             patch('src.besu.v1.routes.compile_solidity_contract') as mock_compile:
            
            mock_compile.return_value = ContractCompilationResponse(
                success=True,
                abi=[],
                bytecode='0x608060'
            )
            
            # Act
            result = await compile_contract(
                contract_file=sample_solidity_file,
                deployer_address="0xfe3b557e8fb62b89f4916b721be55ceb828dbd73",
                constructor_params="[]",
                gas_limit=custom_gas_limit,
                authorization=mock_authorization,
                user_repo=mock_user_repo,
                web3_client=mock_web3_with_checksum
            )
        
        # Assert
        assert result.success == True
        assert result.transaction['gas'] == custom_gas_limit
