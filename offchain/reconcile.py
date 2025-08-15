import os
import json
import time
from dotenv import load_dotenv
from web3 import Web3
from offchain.database import update_record_on_settlement, initialize_database

# Load environment variables
load_dotenv()

# Configuration
# For real-time events, a WebSocket provider is needed.
RPC_URL = os.getenv("RPC_URL", "").replace("http", "ws")
CONTRACT_ADDRESS = os.getenv("SETTLEMENT_CONTRACT_ADDRESS")
ABI_PATH = os.path.join("offchain", "build", "MT202Settlement.json")

def get_contract_abi():
    """Loads the contract ABI from the build file."""
    with open(ABI_PATH, 'r') as f:
        return json.load(f)['abi']

def handle_event(event, w3):
    """Callback function to handle a new event."""
    instruction_id_hex = event['args']['instructionId'].hex()
    settled_amount_wei = event['args']['settledAmount']
    settled_amount = w3.from_wei(settled_amount_wei, 'ether')

    print(f"\n--- Event Received: OnChainSettled ---")
    print(f"  Instruction ID: {instruction_id_hex}")
    print(f"  Settled Amount: {settled_amount} ETH")

    # Update the database with reconciliation logic
    update_record_on_settlement(instruction_id_hex, float(settled_amount))
    print(f"  Updated database for instruction ID: {instruction_id_hex}")

def main():
    """Main execution function to listen for events."""
    print("--- Off-chain Reconciliation Listener ---")
    print("NOTE: This script cannot be fully executed without a deployed contract and a running WebSocket RPC.")

    if not all([RPC_URL, CONTRACT_ADDRESS]):
        print("Error: RPC_URL (as WebSocket) and SETTLEMENT_CONTRACT_ADDRESS must be set in .env")
        return

    # Initialize DB
    initialize_database()

    # Connect to Web3 via WebSocket
    w3 = Web3(Web3.WebsocketProvider(RPC_URL))
    if not w3.is_connected():
        print(f"Error: Could not connect to the WebSocket RPC at {RPC_URL}.")
        return

    print(f"Connected to WebSocket RPC at {RPC_URL}")

    # Load contract
    contract_abi = get_contract_abi()
    contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

    # Create event filter
    event_filter = contract.events.OnChainSettled.create_filter(fromBlock='latest')
    print("Listening for OnChainSettled events...")

    while True:
        try:
            for event in event_filter.get_new_entries():
                handle_event(event, w3)
            time.sleep(2)
        except KeyboardInterrupt:
            print("\nListener stopped.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            print("This is expected if the RPC is not running or the contract is not deployed.")
            break

if __name__ == "__main__":
    main()
