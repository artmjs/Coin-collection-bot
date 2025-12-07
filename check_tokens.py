import json
import time
import traceback

from solana.rpc.api import Client
from solana.exceptions import SolanaRpcException

from discovery import get_token_balances_by_mint  # your function

RPC_URL = "https://api.mainnet-beta.solana.com"
JSON_PATH = "solana_private_pairs.json"


def safe_get_token_balances_by_mint(client: Client, owner_address: str, retries: int = 3, delay: float = 1.0):
    """
    Wrapper around get_token_balances_by_mint with simple retry on RPC errors.
    """
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            return get_token_balances_by_mint(client, owner_address)
        except SolanaRpcException as e:
            print(f"[{owner_address}] RPC error on attempt {attempt}/{retries}: {repr(e)}")
            last_exc = e
            time.sleep(delay)
        except Exception as e:
            # For non-RPC errors, bail out and show full traceback
            print(f"[{owner_address}] Non-RPC error: {repr(e)}")
            traceback.print_exc()
            raise
    
    if last_exc is not None:
        raise last_exc


def check_all_wallets_for_tokens():
    client = Client(RPC_URL)

    with open(JSON_PATH, "r") as f:
        public_private: dict[str, str] = json.load(f)

    wallets_with_tokens: dict[str, dict[str, int]] = {}
    wallets_without_tokens: list[str] = []

    for pub_str in public_private.keys():
        print("\n==============================")
        print(f"Checking wallet: {pub_str}")
        print("==============================")

        try:
            token_dict = safe_get_token_balances_by_mint(client, pub_str)  # {mint: amount}
        except Exception as e:
            print(f"Error while querying {pub_str}: {repr(e)}")
            # show traceback
            traceback.print_exc()
            continue

        token_dict = token_dict or {}

        if len(token_dict) == 0:
            print(f"-> No SPL tokens found for {pub_str}")
            wallets_without_tokens.append(pub_str)
        else:
            print(f"-> SPL tokens found for {pub_str}: {token_dict}")
            wallets_with_tokens[pub_str] = token_dict

        # RPC delay
        time.sleep(1)

    print("\n\n===== SUMMARY =====")
    print(f"Total wallets in JSON: {len(public_private)}")
    print(f"Wallets with SPL tokens: {len(wallets_with_tokens)}")
    print(f"Wallets without SPL tokens: {len(wallets_without_tokens)}")

    if wallets_with_tokens:
        print("\nWallets with tokens:")
        for pub, tokens in wallets_with_tokens.items():
            print(f"- {pub}: {tokens}")

    if wallets_without_tokens:
        print("\nWallets without tokens:")
        for pub in wallets_without_tokens:
            print(f"- {pub}")


if __name__ == "__main__":
    check_all_wallets_for_tokens()
