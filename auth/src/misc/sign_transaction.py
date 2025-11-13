from web3 import Web3
from eth_account import Account
import json

# ===========================
# CONFIGURAÇÃO
# ===========================

# Cole aqui o objeto 'transaction' retornado pela API
TRANSACTION = {
    "from": "0xFE3B557E8Fb62b89F4916B721be55cEb828dBd73",
    "nonce": 0,
    "gas": 3000000,
    "gasPrice": 0,
    "data": "0x...", # bytecode
    "chainId": 1337,
    "value": 0
}

# Sua chave privada
PRIVATE_KEY = ""

# ===========================
# SCRIPT
# ===========================

def main():
    
    # Adicionar 0x se necessário
    if not PRIVATE_KEY.startswith('0x'):
        private_key = '0x' + PRIVATE_KEY
    else:
        private_key = PRIVATE_KEY
    
    # Gerar conta a partir da chave privada
    try:
        account = Account.from_key(private_key)
    except Exception as e:
        print(f" Erro ao criar conta: {e}")
        print("   Verifique se a chave privada está correta")
        return
    
    print(f"Conta: {account.address}")
    
    # Verificar se o endereço 'from' na transação corresponde à conta
    if TRANSACTION['from'].lower() != account.address.lower():
        print(f"\n  ATENÇÃO: Endereço 'from' na transação ({TRANSACTION['from']}) ")
        print(f"    não corresponde à sua conta ({account.address})")
        print("    A transação pode falhar!")
        response = input("\nContinuar mesmo assim? (s/n): ")
        if response.lower() != 's':
            print("Operação cancelada.")
            return
    
    # Assinar transação
    print(f"\n Assinando transação...")
    try:
        signed = account.sign_transaction(TRANSACTION)
        signed_tx_hex = signed.raw_transaction.hex()
        tx_hash = signed.hash.hex()
    except Exception as e:
        print(f" Erro ao assinar transação: {e}")
        return
    
    print(f" Transação assinada com sucesso!")
    print(f"   Hash previsto: {tx_hash}")
    
    # ===========================
    # RESULTADO PARA COPIAR E COLAR NO POSTMAN
    # ===========================

    
    print("\n Body (raw JSON):")
    body = {
        "signed_transaction": signed_tx_hex
    }
    print(json.dumps(body, indent=2))
    
    print("\n" + "=" * 70)
    print("📝 APENAS A TRANSAÇÃO ASSINADA (copie facilmente):")
    print("=" * 70)
    print(signed_tx_hex)
    
    # Salvar em arquivo
    output_data = {
        "signed_transaction": signed_tx_hex,
        "transaction_hash_preview": tx_hash,
        "deployer_address": account.address,
        "nonce": TRANSACTION['nonce'],
        "gas_limit": TRANSACTION['gas'],
        "gas_price": TRANSACTION['gasPrice'],
        "chain_id": TRANSACTION['chainId']
    }
    
    output_file = "signed_transaction_api.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n💾 Dados salvos em: {output_file}")
    
 

if __name__ == "__main__":
    main()