from solders.keypair import Keypair
from solders.pubkey import Pubkey
import json

from config import client, COLLECTOR_PUBKEY
from discovery import get_token_balances_by_mint
from transfer import build_spl_transfer_tx, send_and_confirm


JSON_PATH = "solana_private_pairs.json"

with open(JSON_PATH, "r") as f:
    public_private: dict[str, str] = json.load(f)

WALLETS = [
    {
        "name": pub,              
        "pubkey": pub,
        "private_key_b58": priv,
    }
    for i, (pub, priv) in enumerate(public_private.items(), start=1)
]


def drain_wallet_all_tokens(wallet_private_key_b58: str):
    keypair = Keypair.from_base58_string(wallet_private_key_b58)
    owner_pubkey = keypair.pubkey()
    owner_str = str(owner_pubkey)

    print(f"\n=== Draining wallet {owner_str} ===")

    token_balances = get_token_balances_by_mint(client, owner_str)

    for mint_str, amount in token_balances.items():
        if amount == 0:
            continue

        mint = Pubkey.from_string(mint_str)
        print(f"Preparing transfer of {amount} of mint {mint_str} to {COLLECTOR_PUBKEY}")

        tx = build_spl_transfer_tx(
            client=client,
            owner=keypair,
            sender_pubkey=owner_pubkey,
            receiver_pubkey=COLLECTOR_PUBKEY,
            mint=mint,
            amount=amount,          # full balance in smallest units
            priority=True,
        )

        # Optional: simulate first
        sim = client.simulate_transaction(tx)
        print("Simulation:", sim)

        sig = send_and_confirm(client, tx)
        print(f"Transferred {amount} of {mint_str} from {owner_str} to {COLLECTOR_PUBKEY} in tx {sig}")


if __name__ == "__main__":
    for w in WALLETS:
        drain_wallet_all_tokens(w["private_key_b58"])
