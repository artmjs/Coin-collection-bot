from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.message import Message
from solders.transaction_status import TransactionConfirmationStatus
import time

from spl.token.instructions import (
    get_associated_token_address,
    create_associated_token_account,
    transfer,
    TransferParams,
)
from spl.token.constants import TOKEN_PROGRAM_ID
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price


# ===== CONFIG =====

RPC_URL = "https://api.mainnet-beta.solana.com"

# Sender w/ SAMO
SENDER_PRIVATE_KEY_B58 = "SENDER PRIVATE KEY"

# Pubkey for the receiver of SAMO
RECEIVER_PUBKEY_STR = "SENDER PUBKE"

# SAMO mint
TEST_COIN_PUBKEY = "TEST COIN PUBKEY"

# Amount in smallest units (0.01 SAMO)
TEST_AMOUNT = 10_000_000


# ===== HELPER FUNCTIONS =====

def build_samo_transfer_tx(
    client: Client,
    owner: Keypair,
    sender_pubkey: Pubkey,
    receiver_pubkey: Pubkey,
    amount: int,
) -> Transaction:
    
    """
    Build a tx that transfers a test token from sender to receiver with priority fees.
    """

    mint = Pubkey.from_string(TEST_COIN_PUBKEY)

    sender_ata = get_associated_token_address(sender_pubkey, mint)
    receiver_ata = get_associated_token_address(receiver_pubkey, mint)

    instructions = []

    # Ensure receiver ATA exists
    receiver_ata_info = client.get_account_info(receiver_ata)
    if receiver_ata_info.value is None:
        print(f"Receiver ATA {receiver_ata} does not exist. Adding create ATA instruction.")
        instructions.append(
            create_associated_token_account(
                payer=owner.pubkey(),
                owner=receiver_pubkey,
                mint=mint,
            )
        )

    # Transfer instruction
    instructions.append(
        transfer(
            TransferParams(
                program_id=TOKEN_PROGRAM_ID,
                source=sender_ata,
                dest=receiver_ata,
                owner=owner.pubkey(),
                amount=amount,
            )
        )
    )

    # Priority fees (optional but keeps same behavior as your earlier code)
    compute_limit_ix = set_compute_unit_limit(1_000_000)
    compute_price_ix = set_compute_unit_price(10_000)

    instructions.insert(0, compute_price_ix)
    instructions.insert(0, compute_limit_ix)

    latest_blockhash = client.get_latest_blockhash().value.blockhash
    message = Message(instructions, payer=owner.pubkey())
    tx = Transaction([owner], message, latest_blockhash)
    return tx


def send_and_confirm(client: Client, tx: Transaction, *, max_retries: int = 15, wait_sec: float = 2.0) -> str:
    """Send tx and poll until it is at least Confirmed or ends in timeout."""
    send_resp = client.send_transaction(tx)
    sig = send_resp.value
    print(f"Sent transaction: {sig}")

    for attempt in range(max_retries):
        status_resp = client.get_signature_statuses([sig])
        status = status_resp.value[0]

        print(f"[attempt {attempt+1}/{max_retries}] status: {status}")

        if status is not None:

            # inspect status.err:
            if status.err is not None:
                raise RuntimeError(f"Transaction {sig} failed: {status.err}")
            
            if status.confirmation_status in (
                TransactionConfirmationStatus.Processed,
                TransactionConfirmationStatus.Confirmed,
                TransactionConfirmationStatus.Finalized,
            ):
                print(f"Transaction {sig} confirmed with status {status.confirmation_status}")
                return sig

        time.sleep(wait_sec)

    raise RuntimeError(f"Transaction {sig} not confirmed after {max_retries} attempts")


# ===== MAIN TEST =====

if __name__ == "__main__":
    client = Client(RPC_URL)

    sender_keypair = Keypair.from_base58_string(SENDER_PRIVATE_KEY_B58)
    sender_pubkey = sender_keypair.pubkey()
    receiver_pubkey = Pubkey.from_string(RECEIVER_PUBKEY_STR)

    print(f"Sender:   {sender_pubkey}")
    print(f"Receiver: {receiver_pubkey}")
    print(f"SAMO mint: {TEST_COIN_PUBKEY}")
    print(f"Test amount (smallest units): {TEST_AMOUNT}")

    # Check sender SOL balance (fees)
    sender_balance = client.get_balance(sender_pubkey).value
    print(f"Sender SOL balance: {sender_balance} lamports")

    if sender_balance < 500_000:
        raise RuntimeError("Not enough SOL to cover fees (need at least ~0.0005 SOL).")

    # Build tx
    tx = build_samo_transfer_tx(
        client=client,
        owner=sender_keypair,
        sender_pubkey=sender_pubkey,
        receiver_pubkey=receiver_pubkey,
        amount=TEST_AMOUNT,
    )

    # Simulate before sending
    sim = client.simulate_transaction(tx)
    print("Simulation result:")
    print(sim, "\n")

    # If simulation looks good, send:
    print("Sending transaction...")
    signature = send_and_confirm(client, tx)

    print(f"\nDone. Tx signature: {signature}")
