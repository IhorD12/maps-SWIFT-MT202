import sqlite3
from datetime import datetime

DB_FILE = "reconciliation.db"

def get_db_connection():
    """Creates a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Initializes the database and creates the reconciliation_records table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reconciliation_records (
            instruction_id TEXT PRIMARY KEY,
            transaction_reference TEXT NOT NULL,
            expected_amount REAL NOT NULL,
            onchain_amount REAL,
            currency TEXT NOT NULL,
            value_date TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("Database initialized.")

def insert_intent_record(intent_data: dict):
    """Inserts a new record when a settlement intent is created."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow()
    cursor.execute(
        """
        INSERT INTO reconciliation_records (
            instruction_id, transaction_reference, expected_amount, currency,
            value_date, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            intent_data['instruction_id'],
            intent_data.get('transaction_reference', ''),
            intent_data['amount'],
            intent_data['currency'],
            intent_data['value_date'],
            'PENDING_SETTLEMENT',
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()

def update_record_on_settlement(instruction_id: str, onchain_amount: float):
    """Updates a record when an OnChainSettled event is received."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow()

    # First, get the expected amount to compare
    cursor.execute("SELECT expected_amount FROM reconciliation_records WHERE instruction_id = ?", (instruction_id,))
    record = cursor.fetchone()

    if record:
        expected_amount = record['expected_amount']
        # Simple reconciliation logic: exact match
        if abs(expected_amount - onchain_amount) < 1e-9: # Use tolerance for float comparison
            new_status = 'RECONCILED_SETTLED'
        else:
            new_status = 'MISMATCH_AMOUNT'

        cursor.execute(
            """
            UPDATE reconciliation_records
            SET onchain_amount = ?, status = ?, updated_at = ?
            WHERE instruction_id = ?
            """,
            (onchain_amount, new_status, now, instruction_id),
        )
        conn.commit()

    conn.close()

def get_record(instruction_id: str):
    """Retrieves a single reconciliation record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reconciliation_records WHERE instruction_id = ?", (instruction_id,))
    record = cursor.fetchone()
    conn.close()
    return record if record else None

if __name__ == '__main__':
    # Example usage
    initialize_database()

    # Simulate creating an intent
    test_intent = {
        'instruction_id': 'test-id-001',
        'transaction_reference': 'test-ref-001',
        'amount': 100.50,
        'currency': 'USD',
        'value_date': '2024-08-15'
    }
    insert_intent_record(test_intent)
    print(f"Inserted record: {dict(get_record('test-id-001'))}")

    # Simulate receiving a settlement event
    update_record_on_settlement('test-id-001', 100.50)
    print(f"Updated record after settlement: {dict(get_record('test-id-001'))}")

    # Simulate a mismatch
    test_intent_2 = {
        'instruction_id': 'test-id-002',
        'transaction_reference': 'test-ref-002',
        'amount': 200.00,
        'currency': 'EUR',
        'value_date': '2024-08-16'
    }
    insert_intent_record(test_intent_2)
    update_record_on_settlement('test-id-002', 199.99)
    print(f"Record with mismatch: {dict(get_record('test-id-002'))}")
