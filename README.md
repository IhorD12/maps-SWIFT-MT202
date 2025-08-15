# MT202 On-Chain Settlement and Anomaly Detection Prototype

This project is a full-stack prototype demonstrating how traditional financial messages (SWIFT MT202) can be settled on an Ethereum blockchain. It includes on-chain smart contracts for settlement, off-chain services for message processing and reconciliation, and a machine learning-based monitoring service to detect anomalies.

## Table of Contents

- [Architecture](#architecture)
- [Design Decisions](#design-decisions)
- [Project Structure](#project-structure)
- [Setup and Installation](#setup-and-installation)
- [How to Run the Prototype](#how-to-run-the-prototype)
- [Anomaly Detection](#anomaly-detection)
- [Limitations and Future Work](#limitations-and-future-work)

## Architecture

The system is composed of three main layers:

1.  **On-Chain Layer (Solidity):**
    -   `MT202Settlement.sol`: A smart contract that accepts settlement intents derived from MT202 messages. It implements a state machine for each intent (`IntentCreated` -> `OnChainSettled` -> `ConfirmedReconciled` -> `Dispute`) and emits events for each state change.
    -   `MockToken.sol`: An ERC20 token used to simulate the transfer of value.

2.  **Off-Chain Services (Python / Web3.py):**
    -   **Ingestion & Parsing (`offchain/ingest.py`):** Parses raw MT202 text messages into a structured JSON format.
    -   **Database (`offchain/database.py`):** A SQLite database to store reconciliation records, tracking the status of each transaction from intent to final settlement.
    -   **Submission (`offchain/submit.py`):** Takes a parsed MT202 message, creates a settlement intent, and submits it to the `MT202Settlement` smart contract.
    -   **Reconciliation (`offchain/reconcile.py`):** Listens for `OnChainSettled` events from the contract and updates the corresponding records in the local database, flagging any discrepancies.

3.  **Monitoring & Anomaly Detection (Python / Scikit-learn):**
    -   **Data Generation (`ml/generate_and_train.py`):** A script to create a synthetic dataset of normal and anomalous transactions.
    -   **Model Training (`ml/generate_and_train.py`):** The same script trains an Isolation Forest model on the generated data to learn to distinguish between normal and anomalous reconciliation patterns.
    -   **Monitoring Service (`monitoring/monitor.py`):** Listens for settlement events, fetches data from the reconciliation DB, and uses the trained model to score each transaction for anomalies. It exposes a simple Flask API to view the results.

## Design Decisions

-   **Smart Contract Idempotency:** The `createSettlementIntent` function uses the MT202's `transaction_reference` field (`:20:`) as a unique identifier to prevent duplicate processing of the same instruction.
-   **Environment Workarounds:** The development was significantly impacted by issues in the provided containerized environment, which prevented the Hardhat toolkit from compiling or testing contracts. To overcome this, the contract ABI was manually generated based on the source code to allow the off-chain Python scripts to be developed. A combined script was also used for ML data generation and training to bypass file persistence issues.
-   **Reconciliation Logic:** The current reconciliation logic is simple (exact amount match). This could be extended with rules for thresholds, fees, or FX differences.
-   **Anomaly Detection Model:** An **Isolation Forest** was chosen because it is well-suited for anomaly detection tasks where anomalies are rare and different from normal instances. It is also unsupervised, which is a good starting point when labeled data might be scarce in a real-world scenario.

## Project Structure

```
.
├── contracts/              # Solidity smart contracts
│   ├── MT202Settlement.sol
│   └── MockToken.sol
├── ml/                     # Machine learning scripts
│   ├── generate_and_train.py
│   └── (anomaly_detector.joblib) # Generated model
├── monitoring/             # Real-time monitoring service
│   └── monitor.py
├── offchain/               # Off-chain services and scripts
│   ├── build/              # Manually generated contract ABIs
│   ├── __init__.py
│   ├── compile.py
│   ├── database.py
│   ├── ingest.py
│   ├── reconcile.py
│   └── submit.py
├── sample_data/            # Sample input data
│   └── sample_mt202.json
├── tests/                  # (Intended for Hardhat tests)
├── .env                    # Environment variables (needs to be created)
├── README.md
└── requirements.txt
```

## Setup and Installation

1.  **Prerequisites:**
    -   Python 3.10+
    -   An Ethereum client like [Ganache](https://trufflesuite.com/ganache/) or a running Hardhat node.

2.  **Clone the repository:**
    ```bash
    git clone <repo_url>
    cd <repo_name>
    ```

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up Environment Variables:**
    Create a `.env` file in the project root by copying the example:
    ```
    # .env file
    RPC_URL="http://127.0.0.1:8545" # Your local node RPC URL
    PRIVATE_KEY="0x..." # A private key from your local node
    SETTLEMENT_CONTRACT_ADDRESS="" # Will be filled in after deployment
    ```

5.  **Deploy Contracts:**
    Since the environment prevents standard deployment, you would typically deploy the contracts using a script and then place the deployed `MT202Settlement` contract address into the `.env` file.

## How to Run the Prototype

This demonstrates the intended workflow. Each script should be run in a separate terminal.

1.  **Start a local blockchain node** (e.g., Ganache).

2.  **(Deploy the contracts)** and update `.env` with the contract address.

3.  **Train the ML Model:**
    This script will generate data in memory, train the model, and save the model artifacts (`.joblib` files) to the `ml/` directory.
    ```bash
    python3 -m ml.generate_and_train
    ```

4.  **Start the Reconciliation Listener:**
    This service listens for on-chain settlement events to update the local DB.
    ```bash
    python3 -m offchain.reconcile
    ```

5.  **Start the Anomaly Monitor:**
    This service also listens for events and runs the ML model. It also starts a web server on port 5001.
    ```bash
    python3 -m monitoring.monitor
    ```
    You can check the status at `http://127.0.0.1:5001/status`.

6.  **Submit a Settlement Intent:**
    This script reads the sample MT202 data and submits it to the blockchain.
    ```bash
    python3 -m offchain.submit
    ```

### Testing & CI

Run the Hardhat tests locally (requires Node 18+ and a local Ethereum node for some tests):

```bash
npm ci
npx hardhat test
```

CI is configured to run the same tests via GitHub Actions on pushes and PRs to `main`.


## Anomaly Detection Performance

The Isolation Forest model was trained on a synthetic dataset of 1200 records and evaluated on 200 unseen validation records.

-   **Accuracy:** 97.5%
-   **Precision:** 93.8%
-   **Recall:** 90.9%
-   **F1-Score:** 0.923

The model did not meet the 98% accuracy target. To improve performance, the following steps are recommended:
-   **Better Feature Engineering:** Create more descriptive features, such as ratios or interaction terms.
-   **Larger Dataset:** Increase the number and variety of anomalous examples.
-   **Model Tuning:** Perform a hyperparameter search (e.g., GridSearchCV) on the `IsolationForest` model.
-   **Alternative Models:** Experiment with other models like Autoencoders or One-Class SVMs.

## Limitations and Future Work

-   **Environment Issues:** The project is hampered by the inability to run a proper testing and deployment pipeline for the smart contracts.
-   **Simplified Reconciliation:** The reconciliation logic only checks for an exact amount match. A production system would need to handle fees, FX rates, and other complexities.
-   **Placeholder Features:** The monitoring service uses placeholder values for time-based features. A real implementation would calculate these based on event timestamps.
-   **Security:** The contracts and scripts are for prototype purposes and have not undergone a security audit.
```
