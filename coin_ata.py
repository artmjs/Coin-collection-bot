from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.types import TokenAccountOpts
from solders.transaction import Transaction
import time
from spl.token.instructions import (
    TransferCheckedParams,
    transfer_checked,
    get_associated_token_address,
    create_associated_token_account,
)
from spl.token.constants import TOKEN_PROGRAM_ID
from solders.message import Message
from solders.transaction_status import TransactionConfirmationStatus
from discovery import get_token_mints
from spl.token.instructions import transfer, TransferParams
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price

client = Client("https://api.mainnet-beta.solana.com")

sender_keypair = Keypair.from_base58_string(
    "SENDER_PRIVATE_B58"
)

receiver_pubkey = Pubkey.from_string("RECEIVER PUBKEY")

mint_test_coin = Pubkey.from_string("TEST COIN MINT")
sender_pubkey = sender_keypair.pubkey()


def confirm_transaction(client, signature):
    confirmation = client.confirm_transaction(signature)
    print(f"Transaction Confirmation Response: {confirmation}")
    return confirmation



def create_simple_transfer_transaction(
    amount: int,
    sender: Pubkey,    # Sender's wallet public key
    receiver: Pubkey,  # Receiver's wallet public key
    mint: Pubkey,      # Token mint public key
    owner: Keypair,    # Sender's Keypair for signing
    client: Client,
) -> Transaction:
    sender_ata = get_associated_token_address(sender, mint)
    receiver_ata = get_associated_token_address(receiver, mint)

    print(f"Sender ATA: {sender_ata}")
    print(f"Receiver ATA: {receiver_ata}")

    receiver_ata_info = client.get_account_info(receiver_ata)
    instructions = []
    if receiver_ata_info.value is None:
        print(f"Receiver's ATA {receiver_ata} does not exist. Adding ATA creation instruction.")
        instructions.append(
            create_associated_token_account(
                payer=owner.pubkey(),
                owner=receiver,
                mint=mint,
            )
        )

    transfer_instruction = transfer(
        TransferParams(
            program_id=TOKEN_PROGRAM_ID,
            source=sender_ata,
            dest=receiver_ata,
            owner=owner.pubkey(),
            amount=amount,
        )
    )
    instructions.append(transfer_instruction)

    message = Message(instructions, payer=owner.pubkey())
    latest_blockhash = client.get_latest_blockhash().value.blockhash
    print(f"Latest Blockhash: {latest_blockhash}")

    transaction = Transaction([owner], message, latest_blockhash)
    return transaction


def confirm_signature(client, signature):
    status_response = client.get_signature_statuses([signature])
    status = status_response.value[0]


    if status is None or status.confirmation_status != TransactionConfirmationStatus.Confirmed:
        raise Exception("Transaction not confirmed.")

    return status

def create_transaction_with_priority_fees(
    amount: int,
    sender: Pubkey,
    receiver: Pubkey,
    mint: Pubkey,
    owner: Keypair,
    client: Client,
) -> Transaction:
    sender_ata = get_associated_token_address(sender, mint)
    receiver_ata = get_associated_token_address(receiver, mint)

    receiver_ata_info = client.get_account_info(receiver_ata)
    instructions = []
    if receiver_ata_info.value is None:
        print(f"Receiver's ATA does not exist. Adding creation instruction.")
        instructions.append(
            create_associated_token_account(
                payer=owner.pubkey(),
                owner=receiver,
                mint=mint,
            )
        )

    transfer_instruction = transfer(
        TransferParams(
            program_id=TOKEN_PROGRAM_ID,
            source=sender_ata,
            dest=receiver_ata,
            owner=owner.pubkey(),
            amount=amount,
        )
    )
    instructions.append(transfer_instruction)

    compute_limit_instruction = set_compute_unit_limit(1_000_000)  # Limit: 1M units
    compute_price_instruction = set_compute_unit_price(10_000)    # Price: 10k micro-lamports

    # Add compute budget instructions at the start of the transaction
    instructions.insert(0, compute_limit_instruction)
    instructions.insert(1, compute_price_instruction)

    message = Message(instructions, payer=owner.pubkey())
    latest_blockhash = client.get_latest_blockhash().value.blockhash
    transaction = Transaction([owner], message, latest_blockhash)

    return transaction


def send_transaction(client, transaction):
    response = client.send_transaction(transaction)
    print(f"Transaction Signature: {response.value}")
    return response

## Test to check if the coin transfer works
if __name__ == "__main__":
    client = Client("https://api.mainnet-beta.solana.com")

    sender_keypair = Keypair.from_base58_string(
        "SENDER PRIVATE KEY"
    )
    sender_pubkey = sender_keypair.pubkey()
    receiver_pubkey = Pubkey.from_string("RECEIVER PUBKEY")
    mint_test_coin = Pubkey.from_string("TEST MINT ADDRESS")

    # Amount to transfer (in lamports)
    amount = 10

    try:
        # Check sender balance before sending
        sender_balance = client.get_balance(sender_pubkey).value
        print(f"Sender Balance: {sender_balance} lamports")

        if sender_balance < 500_000:  # Require at least 0.0005 SOL for safety
            raise Exception("Not enough SOL to cover fees.")

        # Create the transaction with priority fees
        transaction = create_transaction_with_priority_fees(
            amount=10000000,
            sender=sender_pubkey,
            receiver=receiver_pubkey,
            mint=mint_test_coin,
            owner=sender_keypair,
            client=client,
        )

        # Simulate before sending
        simulation_result = client.simulate_transaction(transaction)
        print(f"Simulation Result: {simulation_result}", '\n')

        # Send the transaction
        print(f"sending the tx with transaction values: {transaction}", '\n')

        response = send_transaction(client, transaction)
        # Confirm the transaction
        print(f'response: {response}')

        time.sleep(5)
        confirmation = confirm_signature(client, response.value)

        print(f"Transaction confirmed: {confirmation}")

    except Exception as e:
        print(f"Error: {e}")
