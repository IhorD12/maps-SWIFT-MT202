import os
import json
from dotenv import load_dotenv
from web3 import Web3
from offchain.database import insert_intent_record, initialize_database

# Load environment variables
load_dotenv()

# Configuration
RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("SETTLEMENT_CONTRACT_ADDRESS")
ABI_PATH = os.path.join("offchain", "build", "MT202Settlement.json")

def get_contract_abi():
    """Loads the contract ABI from the build file."""
    with open(ABI_PATH, 'r') as f:
        return json.load(f)['abi']

def submit_intent(w3, contract, intent_data, account):
    """Submits a settlement intent to the smart contract."""
    print("Submitting settlement intent...")

    # Convert data to contract-friendly format
    instruction_id_bytes = Web3.to_bytes(text=intent_data['transaction_reference']).ljust(32, b'\0')
    amount_in_wei = w3.to_wei(intent_data['amount'], 'ether') # Assuming amount is in ether-like units

    # Build transaction
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contract.functions.createSettlementIntent(
        instruction_id_bytes,
        account.address,  # Payer is the submitting account for this prototype
        "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", # A placeholder payee address
        amount_in_wei,
        intent_data['currency'],
        int(Web3.to_timestamp(intent_data['value_date'])),
        intent_data['ordering_institution'],
        intent_data['beneficiary_institution']
    ).build_transaction({
        'chainId': 1337, # Hardhat default
        'gas': 2000000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce,
    })

    # Sign and send transaction
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    print(f"Transaction sent with hash: {tx_hash.hex()}")

    # Wait for confirmation
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction confirmed.")
    return receipt

def main():
    """Main execution function."""
    # Since we can't deploy, we can't run this.
    # This script is for demonstration of how it would work.
    print("--- Off-chain Intent Submission Script ---")
    print("NOTE: This script cannot be fully executed without a deployed contract.")

    if not all([RPC_URL, PRIVATE_KEY, CONTRACT_ADDRESS]):
        print("Error: RPC_URL, PRIVATE_KEY, and SETTLEMENT_CONTRACT_ADDRESS must be set in .env")
        return

    # Connect to Web3
    w3 = Web3(Web3.HTTPProvider(RPC_URL))

    if not w3.is_connected():
        print("Error: Could not connect to the Ethereum node.")
        return

    print(f"Connected to RPC at {RPC_URL}")

    # Set up account
    account = w3.eth.account.from_key(PRIVATE_KEY)
    w3.eth.default_account = account.address
    print(f"Using account: {account.address}")

    # Load contract
    contract_abi = get_contract_abi()
    contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

    # Load sample data
    with open('sample_data/sample_mt202.json', 'r') as f:
        intent_data = json.load(f)

    # Initialize DB and store intent
    initialize_database()
    db_intent_data = {
        'instruction_id': intent_data['transaction_reference'],
        **intent_data
    }
    insert_intent_record(db_intent_data)
    print(f"Stored pending record in DB for instruction ID: {intent_data['transaction_reference']}")

    # Submit to contract
    try:
        submit_intent(w3, contract, intent_data, account)
        print("Submission process complete.")
    except Exception as e:
        print(f"\nAn error occurred during submission: {e}")
        print("This is expected if the contract is not deployed or the RPC is not running.")


if __name__ == "__main__":
    main()
