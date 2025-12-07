from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.message import Message
from solders.transaction_status import TransactionConfirmationStatus

from spl.token.instructions import (
    get_associated_token_address,
    create_associated_token_account,
    transfer,
    TransferParams,
)
from spl.token.constants import TOKEN_PROGRAM_ID
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price


def build_spl_transfer_tx(
    client: Client,
    owner: Keypair,      # sender keypair
    sender_pubkey: Pubkey,
    receiver_pubkey: Pubkey,
    mint: Pubkey,
    amount: int,
    *,
    priority: bool = True,
) -> Transaction:
    """
    Build a Transaction that transfers `amount` of SPL token `mint`
    from sender to receiver, creating receiver's ATA if needed.
    """
    sender_ata = get_associated_token_address(sender_pubkey, mint)
    receiver_ata = get_associated_token_address(receiver_pubkey, mint)

    instructions = []

    # Ensure receiver ATA exists
    receiver_ata_info = client.get_account_info(receiver_ata)
    if receiver_ata_info.value is None:
        instructions.append(
            create_associated_token_account(
                payer=owner.pubkey(),
                owner=receiver_pubkey,
                mint=mint,
            )
        )

    # Token transfer
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

    # Optional priority fees
    if priority:
        compute_limit_instruction = set_compute_unit_limit(1_000_000)
        compute_price_instruction = set_compute_unit_price(10_000)
        instructions.insert(0, compute_price_instruction)
        instructions.insert(0, compute_limit_instruction)

    latest_blockhash = client.get_latest_blockhash().value.blockhash
    message = Message(instructions, payer=owner.pubkey())
    tx = Transaction([owner], message, latest_blockhash)
    return tx


def send_and_confirm(client: Client, tx: Transaction) -> str:
    """
    Send a transaction and wait until it's confirmed.
    Returns the signature string.
    """
    send_resp = client.send_transaction(tx)
    sig = send_resp.value
    print(f"Sent tx: {sig}")

    # very simple one-shot confirmation
    status_resp = client.get_signature_statuses([sig])
    status = status_resp.value[0]

    if status is None or status.confirmation_status != TransactionConfirmationStatus.Confirmed:
        raise RuntimeError(f"Transaction {sig} not confirmed: {status_resp}")

    print(f"Transaction confirmed: {status}")
    return sig
