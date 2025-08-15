import os
import json
import time
import joblib
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from web3 import Web3
from flask import Flask, jsonify
from threading import Thread
from collections import deque

# --- Local Imports ---
# Assuming this is run as a module from the root directory
from offchain.database import get_record

# --- Configuration ---
load_dotenv()
RPC_URL = os.getenv("RPC_URL", "").replace("http", "ws")
CONTRACT_ADDRESS = os.getenv("SETTLEMENT_CONTRACT_ADDRESS")
ABI_PATH = os.path.join("offchain", "build", "MT202Settlement.json")
MODEL_PATH = os.path.join("ml", "anomaly_detector.joblib")
SCALER_PATH = os.path.join("ml", "scaler.joblib")

# --- Global State for Web Server ---
# A thread-safe deque to store the last N events
LAST_N_EVENTS = deque(maxlen=50)

# --- Anomaly Detection Logic ---

def predict_anomaly(record):
    """Predicts if a given reconciliation record is an anomaly."""
    try:
        model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
    except FileNotFoundError:
        print("Error: Model or scaler not found. Run the training script first.")
        return {"error": "Model not found"}, -1

    # Feature engineering must match the training script
    # We need to simulate some features if they aren't in the DB
    # In a real system, these would be calculated based on event timestamps etc.
    features = pd.DataFrame({
        'amount_diff': [abs(record['expected_amount'] - record['onchain_amount'])],
        'time_to_settlement': [60], # Placeholder
        'gas_used': [50000], # Placeholder
        'value_date_delay': [1] # Placeholder
    })

    scaled_features = scaler.transform(features)
    prediction = model.predict(scaled_features)
    decision_score = model.decision_function(scaled_features)

    # Prediction is -1 for anomaly, 1 for normal
    is_anomaly = True if prediction[0] == -1 else False

    result = {
        "instruction_id": record["instruction_id"],
        "expected_amount": record["expected_amount"],
        "onchain_amount": record["onchain_amount"],
        "status": record["status"],
        "is_anomaly": is_anomaly,
        "anomaly_score": float(decision_score[0])
    }
    return result

# --- Web Server (Flask) ---

app = Flask(__name__)

@app.route('/')
def index():
    return "Monitoring service is running. Visit /status to see recent events."

@app.route('/status')
def status():
    return jsonify(list(LAST_N_EVENTS))

def run_web_server():
    # Running in debug mode is not recommended for production
    # Use a proper WSGI server like Gunicorn or Waitress
    print("Starting Flask web server on http://127.0.0.1:5001")
    app.run(host='0.0.0.0', port=5001)


# --- Blockchain Event Listener ---

def handle_event(event, w3):
    """Callback function to handle a new event."""
    instruction_id = event['args']['instructionId'].hex()

    print(f"\n--- Monitor received event for instruction ID: {instruction_id} ---")

    # Fetch the full record from the database
    # Note: there might be a race condition if the listener is faster than the reconciler's DB update.
    # In a real system, you'd handle this, e.g., with a small delay or a retry mechanism.
    time.sleep(1) # Simple delay to allow DB to update
    record = get_record(instruction_id)

    if not record:
        print(f"  -> ERROR: Could not find record for {instruction_id} in the database.")
        return

    if not record['onchain_amount']:
        print(f"  -> INFO: Record for {instruction_id} not yet reconciled. Skipping anomaly check for now.")
        return

    # Predict anomaly
    prediction_result = predict_anomaly(dict(record))

    if "error" in prediction_result:
        print(f"  -> Prediction failed: {prediction_result['error']}")
    else:
        print(f"  -> Anomaly Detection Result: {'ANOMALY' if prediction_result['is_anomaly'] else 'Normal'}")
        print(f"  -> Anomaly Score: {prediction_result['anomaly_score']:.4f}")
        # Add to global state for the web server
        LAST_N_EVENTS.appendleft(prediction_result)


def main_listener():
    """Main function to listen for events."""
    print("\n--- Anomaly Monitoring Service ---")
    print("NOTE: This script is for demonstration and requires a running node and deployed contract.")

    if not all([RPC_URL, CONTRACT_ADDRESS]):
        print("Error: WebSocket RPC_URL and SETTLEMENT_CONTRACT_ADDRESS must be set in .env")
        return

    w3 = Web3(Web3.WebsocketProvider(RPC_URL))
    if not w3.is_connected():
        print(f"Error: Could not connect to WebSocket at {RPC_URL}")
        return

    contract_abi = json.load(open(ABI_PATH))['abi']
    contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)
    event_filter = contract.events.OnChainSettled.create_filter(fromBlock='latest')

    print("Listening for OnChainSettled events...")
    while True:
        try:
            for event in event_filter.get_new_entries():
                handle_event(event, w3)
            time.sleep(2)
        except KeyboardInterrupt:
            print("\nMonitor stopped.")
            break
        except Exception as e:
            print(f"An error occurred in the listener loop: {e}")
            break

if __name__ == "__main__":
    # Start the web server in a background thread
    web_thread = Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # Start the main listener
    # Adding a small delay to let the web server start up
    time.sleep(2)
    main_listener()
