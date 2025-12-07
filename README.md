# Solana Token Collector

This project is a small Python toolkit to:

1. Discover SPL tokens held by a set of wallets.
2. Fund those wallets with a bit of SOL so they can pay transaction fees.
3. Test a single SPL token transfer between two wallets.
4. Drain tokens from multiple wallets into a single collector wallet.

## Project structure

Typical layout:

- `config.py`  
  Holds the shared Solana RPC client and the collector wallet public key. Not in use at this moment

- `discovery.py`  
  Functions to read SPL token balances for a given owner address.

- `solana_private_pairs.json`  
  Local JSON mapping of public keys to their base58 private keys for the wallets you want to work with. Format: public key: private key.

- `solana_deposit.py`  
  Script to send small amounts of SOL from a single funding wallet to multiple wallets so they can pay fees.

- `check_tokens.py`  
  Script to iterate over all wallets in `solana_private_pairs.json` and print which SPL tokens each wallet holds, with some retry/backoff for RPC rate limiting.

- `test_coin_transfer.py`  
  One-off test script to send a specific SPL token from one wallet to another, including ATA creation and priority fees.

- `collect_all.py`  
  Script that (once wired up) orchestrates discovering SPL token balances for each wallet and transferring them to the central collector wallet.

- `README.md` (this file)

## Configuration

### 1. Python environment

Use Python 3.9+ with a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS / Linux
```

Or if using windows powerhell:

```bash
.venv\Scripts\Activate.ps1 
```

Then: 

```bash
pip install --upgrade pip
pip install solana solders
```