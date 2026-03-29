#!/usr/bin/env python3
"""Utilitarios de HD wallet para derivacao de pseudonimos Ethereum."""

from typing import Dict, List, Tuple, Union

from eth_account import Account
from web3 import Web3


DEFAULT_ACCOUNT_PATH_TEMPLATE = "m/44'/60'/0'/0/{index}"


def normalize_mnemonic(text: str) -> str:
    """Normaliza espacos e quebra de linha do mnemonic."""
    return " ".join((text or "").strip().split())


def load_mnemonic_from_file(seed_file: str) -> str:
    with open(seed_file, "r", encoding="utf-8") as f:
        content = f.read()
    mnemonic = normalize_mnemonic(content)
    if not mnemonic:
        raise ValueError(f"Arquivo de seed vazio: {seed_file}")
    return mnemonic


def validate_mnemonic(mnemonic: str) -> None:
    """Valida mnemonic BIP-39 usando parser interno do eth_account."""
    Account.enable_unaudited_hdwallet_features()
    try:
        Account.from_mnemonic(mnemonic, account_path=DEFAULT_ACCOUNT_PATH_TEMPLATE.format(index=0))
    except Exception as exc:
        raise ValueError("Mnemonic invalido. Verifique palavras e checksum BIP-39.") from exc


def derive_account_from_mnemonic(mnemonic: str, account_path: str) -> Tuple[str, str]:
    """Retorna (address, private_key_hex) para um caminho HD especifico."""
    Account.enable_unaudited_hdwallet_features()
    account = Account.from_mnemonic(mnemonic, account_path=account_path)
    private_key_hex = account.key.hex()
    if not private_key_hex.startswith("0x"):
        private_key_hex = f"0x{private_key_hex}"
    return account.address, private_key_hex


def build_vehicle_private_keys(
    vehicle_ids: List[str],
    mnemonic: str,
    account_path_template: str = DEFAULT_ACCOUNT_PATH_TEMPLATE,
    start_index: int = 0,
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Deriva uma chave privada por vehicle_id de forma deterministica.

    Retorna:
    - private_keys_by_vehicle: dict vehicle_id -> private_key_hex
    - addresses_by_vehicle: dict vehicle_id -> address
    """
    validate_mnemonic(mnemonic)

    if start_index < 0:
        raise ValueError("start_index deve ser >= 0")

    unique_sorted_ids = sorted({str(v) for v in vehicle_ids})
    if not unique_sorted_ids:
        raise ValueError("Nenhum vehicle_id informado para derivacao HD")

    private_keys_by_vehicle: Dict[str, str] = {}
    addresses_by_vehicle: Dict[str, str] = {}

    for i, vehicle_id in enumerate(unique_sorted_ids):
        index = start_index + i
        account_path = account_path_template.format(index=index)
        address, private_key_hex = derive_account_from_mnemonic(mnemonic, account_path)
        private_keys_by_vehicle[vehicle_id] = private_key_hex
        addresses_by_vehicle[vehicle_id] = address

    return private_keys_by_vehicle, addresses_by_vehicle


def recover_wallet_indices(
    mnemonic: str,
    web3_provider: Union[str, Web3],
    gap_limit: int = 20,
) -> int:
    """
    Busca sequencial de enderecos HD para recuperar o ultimo indice usado.

    Regra de parada:
    - Para quando encontrar `gap_limit` enderecos consecutivos sem atividade.

    Atividade considerada:
    - saldo > 0 OU transaction_count > 0

    Retorno:
    - ultimo indice com atividade on-chain; retorna -1 se nenhum endereco foi usado.
    """
    validate_mnemonic(mnemonic)

    if gap_limit <= 0:
        raise ValueError("gap_limit deve ser > 0")

    if isinstance(web3_provider, Web3):
        w3 = web3_provider
    else:
        w3 = Web3(Web3.HTTPProvider(str(web3_provider)))

    if not w3.is_connected():
        raise ConnectionError("Nao foi possivel conectar ao provider Web3 para recuperar indices HD")

    last_used_index = -1
    current_index = 0
    empty_streak = 0

    while empty_streak < gap_limit:
        account_path = DEFAULT_ACCOUNT_PATH_TEMPLATE.format(index=current_index)
        address, _ = derive_account_from_mnemonic(mnemonic, account_path)

        balance = w3.eth.get_balance(address)
        tx_count = w3.eth.get_transaction_count(address, "latest")
        has_activity = balance > 0 or tx_count > 0

        if has_activity:
            last_used_index = current_index
            empty_streak = 0
        else:
            empty_streak += 1

        current_index += 1

    return last_used_index
