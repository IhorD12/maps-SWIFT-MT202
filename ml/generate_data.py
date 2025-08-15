import pandas as pd
import numpy as np
import os
import uuid

# Configuration
N_NORMAL = 1000
N_ANOMALOUS = 200
N_VALIDATION = 200 # A mix of normal and anomalous for the validation set
DATA_DIR = "sample_data"
SEED = 42

np.random.seed(SEED)

def generate_base_data(n_samples):
    """Generates the base features for a set of transactions."""
    data = {
        'instruction_id': [str(uuid.uuid4()) for _ in range(n_samples)],
        'expected_amount': np.random.uniform(1000, 100000, n_samples).round(2),
        'time_to_settlement': np.random.normal(loc=60, scale=20, size=n_samples).clip(5), # in seconds
        'gas_used': np.random.normal(loc=50000, scale=10000, size=n_samples).clip(21000),
        'value_date_delay': np.random.poisson(lam=0.2, size=n_samples) # in days
    }
    return pd.DataFrame(data)

def generate_anomalies(base_df):
    """Injects anomalies into a dataframe of normal transactions."""
    anomalous_df = base_df.copy()

    # Create different types of anomalies
    n = len(anomalous_df)
    indices = np.arange(n)
    np.random.shuffle(indices)

    # Type 1: Amount mismatch (40% of anomalies)
    mismatch_indices = indices[:int(n * 0.4)]
    anomalous_df.loc[mismatch_indices, 'onchain_amount'] *= np.random.uniform(0.5, 1.5, len(mismatch_indices))

    # Type 2: Delayed settlement (30% of anomalies)
    delay_indices = indices[int(n * 0.4):int(n * 0.7)]
    anomalous_df.loc[delay_indices, 'time_to_settlement'] *= np.random.uniform(10, 50, len(delay_indices))

    # Type 3: High gas usage (20% of anomalies)
    gas_indices = indices[int(n * 0.7):int(n * 0.9)]
    anomalous_df.loc[gas_indices, 'gas_used'] *= np.random.uniform(3, 8, len(gas_indices))

    # Type 4: Value date delay (10% of anomalies)
    date_delay_indices = indices[int(n * 0.9):]
    anomalous_df.loc[date_delay_indices, 'value_date_delay'] += np.random.randint(5, 15, len(date_delay_indices))

    return anomalous_df

def main():
    """Main function to generate and save datasets."""
    print("Generating synthetic data for anomaly detection...")

    # --- Generate Training Data ---
    # Normal data
    df_normal = generate_base_data(N_NORMAL)
    df_normal['onchain_amount'] = df_normal['expected_amount'] * np.random.normal(1.0, 0.001, N_NORMAL)
    df_normal['anomaly_label'] = 0

    # Anomalous data
    df_anomalous_base = generate_base_data(N_ANOMALOUS)
    # Start with onchain amount being same as expected before injecting anomalies
    df_anomalous_base['onchain_amount'] = df_anomalous_base['expected_amount']
    df_anomalous = generate_anomalies(df_anomalous_base)
    df_anomalous['anomaly_label'] = 1

    # Combine for training set
    df_train = pd.concat([df_normal, df_anomalous], ignore_index=True).sample(frac=1).reset_index(drop=True)

    # --- Generate Validation Data ---
    # A separate set to test the model on unseen data
    n_val_normal = N_VALIDATION - int(N_VALIDATION * (N_ANOMALOUS / (N_NORMAL + N_ANOMALOUS)))
    n_val_anomalous = N_VALIDATION - n_val_normal

    df_val_normal = generate_base_data(n_val_normal)
    df_val_normal['onchain_amount'] = df_val_normal['expected_amount'] * np.random.normal(1.0, 0.001, n_val_normal)
    df_val_normal['anomaly_label'] = 0

    df_val_anomalous_base = generate_base_data(n_val_anomalous)
    df_val_anomalous_base['onchain_amount'] = df_val_anomalous_base['expected_amount']
    df_val_anomalous = generate_anomalies(df_val_anomalous_base)
    df_val_anomalous['anomaly_label'] = 1

    df_validation = pd.concat([df_val_normal, df_val_anomalous], ignore_index=True).sample(frac=1).reset_index(drop=True)

    # Save to CSV
    os.makedirs(DATA_DIR, exist_ok=True)
    train_path = os.path.join(DATA_DIR, "training_data.csv")
    val_path = os.path.join(DATA_DIR, "validation_data.csv")

    df_train.to_csv(train_path, index=False)
    df_validation.to_csv(val_path, index=False)

    print(f"Successfully generated {len(df_train)} training records and {len(df_validation)} validation records.")
    print(f"Training data saved to: {train_path}")
    print(f"Validation data saved to: {val_path}")

if __name__ == "__main__":
    main()
