import pandas as pd
import numpy as np
import joblib
import os
import uuid
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

# --- Configuration ---
N_NORMAL = 1000
N_ANOMALOUS = 200
N_VALIDATION = 200
MODEL_DIR = "ml"
SEED = 42

MODEL_PATH = os.path.join(MODEL_DIR, "anomaly_detector.joblib")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.joblib")

np.random.seed(SEED)

# --- Data Generation Logic (from generate_data.py) ---

def generate_base_data(n_samples):
    data = {
        'instruction_id': [str(uuid.uuid4()) for _ in range(n_samples)],
        'expected_amount': np.random.uniform(1000, 100000, n_samples).round(2),
        'time_to_settlement': np.random.normal(loc=60, scale=20, size=n_samples).clip(5),
        'gas_used': np.random.normal(loc=50000, scale=10000, size=n_samples).clip(21000),
        'value_date_delay': np.random.poisson(lam=0.2, size=n_samples)
    }
    return pd.DataFrame(data)

def generate_anomalies(base_df):
    anomalous_df = base_df.copy()
    n = len(anomalous_df)
    indices = np.arange(n)
    np.random.shuffle(indices)

    mismatch_indices = indices[:int(n * 0.4)]
    anomalous_df.loc[mismatch_indices, 'onchain_amount'] *= np.random.uniform(0.5, 1.5, len(mismatch_indices))
    delay_indices = indices[int(n * 0.4):int(n * 0.7)]
    anomalous_df.loc[delay_indices, 'time_to_settlement'] *= np.random.uniform(10, 50, len(delay_indices))
    gas_indices = indices[int(n * 0.7):int(n * 0.9)]
    anomalous_df.loc[gas_indices, 'gas_used'] *= np.random.uniform(3, 8, len(gas_indices))
    date_delay_indices = indices[int(n * 0.9):]
    anomalous_df.loc[date_delay_indices, 'value_date_delay'] += np.random.randint(5, 15, len(date_delay_indices))

    return anomalous_df

def generate_datasets():
    print("Generating synthetic data...")
    # Training Data
    df_normal = generate_base_data(N_NORMAL)
    df_normal['onchain_amount'] = df_normal['expected_amount'] * np.random.normal(1.0, 0.001, N_NORMAL)
    df_normal['anomaly_label'] = 0
    df_anomalous_base = generate_base_data(N_ANOMALOUS)
    df_anomalous_base['onchain_amount'] = df_anomalous_base['expected_amount']
    df_anomalous = generate_anomalies(df_anomalous_base)
    df_anomalous['anomaly_label'] = 1
    df_train = pd.concat([df_normal, df_anomalous], ignore_index=True).sample(frac=1).reset_index(drop=True)

    # Validation Data
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

    print("Data generation complete.")
    return df_train, df_validation

# --- Model Training Logic (from train_anomaly.py) ---

def feature_engineering(df):
    df['amount_diff'] = (df['expected_amount'] - df['onchain_amount']).abs()
    features = ['amount_diff', 'time_to_settlement', 'gas_used', 'value_date_delay']
    return df[features]

def main():
    """Main function to generate data, train, evaluate, and save the model."""
    print("--- Anomaly Detection Model Generation & Training ---")

    # Generate data in memory
    df_train, df_val = generate_datasets()

    # Feature Engineering
    X_train = feature_engineering(df_train)
    y_val_true = df_val['anomaly_label']
    X_val = feature_engineering(df_val)

    print(f"Training with {len(X_train)} records...")

    # Preprocessing
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    # Model Training
    contamination = len(df_train[df_train['anomaly_label'] == 1]) / len(df_train)
    model = IsolationForest(n_estimators=100, contamination=contamination, random_state=SEED)
    model.fit(X_train_scaled)

    print("Model training complete.")

    # Evaluation
    y_pred_raw = model.predict(X_val_scaled)
    y_pred = np.array([0 if x == 1 else 1 for x in y_pred_raw])

    print("\n--- Model Evaluation on Validation Set ---")
    accuracy = accuracy_score(y_val_true, y_pred)
    precision = precision_score(y_val_true, y_pred)
    recall = recall_score(y_val_true, y_pred)
    f1 = f1_score(y_val_true, y_pred)
    roc_auc = roc_auc_score(y_val_true, y_pred)

    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-Score:  {f1:.4f}")
    print(f"ROC AUC:   {roc_auc:.4f}")
    print("\nConfusion Matrix:")
    print(pd.DataFrame(confusion_matrix(y_val_true, y_pred),
                       index=['Actual Normal', 'Actual Anomaly'],
                       columns=['Predicted Normal', 'Predicted Anomaly']))

    if accuracy >= 0.98:
        print("\n✅ Model performance meets the >= 98% accuracy requirement.")
    else:
        print("\n⚠️ Model performance does not meet the >= 98% accuracy requirement.")

    # Save the model and scaler
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print(f"\nTrained model saved to: {MODEL_PATH}")
    print(f"Scaler saved to: {SCALER_PATH}")

if __name__ == "__main__":
    main()
