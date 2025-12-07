from solana.rpc.api import Client
from solders import Pubkey
import os

RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")

# CENTRAL COLLECTION WALLET
COLLECTOR_PUBKEY = Pubkey.from_string(os.getenv("COLLECTOR_PUBKEY", "REPLACE_ME"))

client = Client(RPC_URL)
