import json
import time
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.message import Message
from solders.transaction_status import TransactionConfirmationStatus
from solders.system_program import transfer as sol_transfer, TransferParams as SolTransferParams
from solana.exceptions import SolanaRpcException

# ===== CONFIG =====

RPC_URL = "https://api.mainnet-beta.solana.com"

# Funding wallet
FUNDING_PRIVATE_KEY_B58 = "PRIVATEKEY"

# How much SOL to send to each wallet in lamports
# 1 SOL = 1_000_000_000 lamports
FUNDING_PER_WALLET_LAMPORTS = 200_000  # 0.0002 SOL, adjust as needed

# Minimum SOL balance threshold: if a wallet already has at least this much -> skip it
MIN_BALANCE_THRESHOLD_LAMPORTS = 100_000  # 0.0001 SOL

# Keep at least this much in the funding wallet to avoid over-draining
FUNDING_MIN_REMAINING_LAMPORTS = 200_000  # 0.002 SOL safety buffer


# ===== LOAD WALLET LIST =====

with open("solana_private_pairs.json", "r") as f:
    public_private: dict[str, str] = json.load(f)

client = Client(RPC_URL)

funding_keypair = Keypair.from_base58_string(FUNDING_PRIVATE_KEY_B58)
funding_pubkey = funding_keypair.pubkey()

print(f"Funding wallet: {funding_pubkey}")
initial_funding_balance = client.get_balance(funding_pubkey).value
print(f"Funding wallet SOL balance: {initial_funding_balance} lamports")


def send_sol_and_confirm(
    recipient_pubkey: Pubkey,
    amount_lamports: int,
    *,
    max_retries: int = 15,
    wait_sec: float = 2.0,
) -> str:
    """Send SOL from funding wallet to recipient and wait for confirmation."""
    ix = sol_transfer(
        SolTransferParams(
            from_pubkey=funding_pubkey,
            to_pubkey=recipient_pubkey,
            lamports=amount_lamports,
        )
    )

    recent_blockhash = client.get_latest_blockhash().value.blockhash
    message = Message([ix], payer=funding_pubkey)
    tx = Transaction([funding_keypair], message, recent_blockhash)

    sim = client.simulate_transaction(tx)
    print(f"Simulation for {recipient_pubkey}: {sim}")

    if sim.value.err is not None:
        raise RuntimeError(
            f"Simulation failed for {recipient_pubkey}: {sim.value.err}"
        )

    send_resp = client.send_transaction(tx)
    sig = send_resp.value
    print(f"Sent SOL tx to {recipient_pubkey}: {sig}")

    # Poll for confirmation
    for attempt in range(max_retries):
        status_resp = client.get_signature_statuses([sig])
        status = status_resp.value[0]
        print(f"[{recipient_pubkey}] attempt {attempt+1}/{max_retries}, status: {status}")

        if status is not None:
            if status.err is not None:
                raise RuntimeError(f"Tx {sig} failed: {status.err}")

            if status.confirmation_status in (
                TransactionConfirmationStatus.Processed,
                TransactionConfirmationStatus.Confirmed,
                TransactionConfirmationStatus.Finalized,
            ):
                print(f"Tx {sig} confirmed with status {status.confirmation_status}")
                return sig

        time.sleep(wait_sec)

    raise RuntimeError(f"Tx {sig} not confirmed after {max_retries} attempts")


def safe_get_balance(pubkey: Pubkey) -> int:
    """Get balance with a simple retry on RPC 429."""
    try:
        return client.get_balance(pubkey).value
    except SolanaRpcException as e:
        print(f"RPC error on get_balance for {pubkey}: {e}. Retrying once...")
        time.sleep(2.0)
        return client.get_balance(pubkey).value


# ===== MAIN: FUND ALL WALLETS =====

def fund_all_wallets():
    num_wallets = len(public_private)
    print(
        f"\nWill attempt to fund up to {num_wallets} wallets with "
        f"{FUNDING_PER_WALLET_LAMPORTS} lamports each."
    )

    for pub_str in public_private.keys():
        recipient_pubkey = Pubkey.from_string(pub_str)

        # skip funding wallet itself
        if recipient_pubkey == funding_pubkey:
            print(f"Skipping funding wallet itself: {recipient_pubkey}")
            continue

        # check current funding wallet balance each time to avoid over-draining
        current_funding_balance = safe_get_balance(funding_pubkey)
        print(f"\nCurrent funding wallet balance: {current_funding_balance} lamports")
        if current_funding_balance <= FUNDING_MIN_REMAINING_LAMPORTS + FUNDING_PER_WALLET_LAMPORTS:
            print("Funding wallet is too low to continue safely. Stopping.")
            break

        # check current balance of recipient, skip wallets with balance over the treshold
        balance = safe_get_balance(recipient_pubkey)
        print(f"Wallet {recipient_pubkey} current balance: {balance} lamports")

        if balance >= MIN_BALANCE_THRESHOLD_LAMPORTS:
            print(
                f"Skipping {recipient_pubkey}: already has "
                f">= {MIN_BALANCE_THRESHOLD_LAMPORTS} lamports"
            )
            continue

        # Send SOL
        try:
            sig = send_sol_and_confirm(recipient_pubkey, FUNDING_PER_WALLET_LAMPORTS)
            print(
                f"Funded {recipient_pubkey} with {FUNDING_PER_WALLET_LAMPORTS} lamports "
                f"in tx {sig}"
            )
        except Exception as e:
            print(f"ERROR funding {recipient_pubkey}: {e}")

        # Small delay between wallets 
        time.sleep(1)


if __name__ == "__main__":
    fund_all_wallets()
