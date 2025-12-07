from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solana.rpc.types import TokenAccountOpts

SPL_TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")


def get_token_balances_by_mint(client: Client, owner_address: str) -> dict[str, int]:
    """
    Returns a dict: {mint_str: total_amount_in_smallest_units}
    for all SPL token accounts belonging to owner_address.
    """
    response = client.get_token_accounts_by_owner_json_parsed(
        Pubkey.from_string(owner_address),
        opts=TokenAccountOpts(program_id=SPL_TOKEN_PROGRAM_ID),
    )

    token_dict: dict[str, int] = {}

    for account in response.value:
        parsed = account.account.data.parsed["info"]
        mint = parsed["mint"]
        amount = int(parsed["tokenAmount"]["amount"])  # smallest unit

        token_dict[mint] = token_dict.get(mint, 0) + amount

    print(f"[{owner_address}] tokens discovered: {token_dict}")
    return token_dict
