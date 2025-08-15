import pandas as pd
import numpy as np
import joblib
import os

print(f"Current working directory: {os.getcwd()}")

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

# Configuration
DATA_DIR = "sample_data"
MODEL_DIR = "ml"
TRAIN_DATA_PATH = os.path.join(DATA_DIR, "training_data.csv")
VAL_DATA_PATH = os.path.join(DATA_DIR, "validation_data.csv")
MODEL_PATH = os.path.join(MODEL_DIR, "anomaly_detector.joblib")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.joblib")
SEED = 42

def feature_engineering(df):
    """Creates features for the anomaly detection model."""
    df['amount_diff'] = (df['expected_amount'] - df['onchain_amount']).abs()
    # For this model, we won't use the instruction_id or the original amounts directly
    features = [
        'amount_diff',
        'time_to_settlement',
        'gas_used',
        'value_date_delay'
    ]
    return df[features]

def main():
    """Main function to train, evaluate, and save the model."""
    print("--- Anomaly Detection Model Training ---")

    # Load data
    print(f"Looking for data in: {DATA_DIR}")
    print(f"Contents of data dir: {os.listdir(DATA_DIR)}")
    df_train = pd.read_csv(TRAIN_DATA_PATH)
    df_val = pd.read_csv(VAL_DATA_PATH)

    # Separate features and labels
    X_train = feature_engineering(df_train)
    # IsolationForest is unsupervised, but we use labels for evaluation
    y_val_true = df_val['anomaly_label']
    X_val = feature_engineering(df_val)

    print(f"Training with {len(X_train)} records...")

    # Preprocessing
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    # Model Training
    # The 'contamination' parameter is the expected proportion of anomalies in the data.
    # We set it based on our generated data ratio.
    contamination = len(df_train[df_train['anomaly_label'] == 1]) / len(df_train)
    model = IsolationForest(n_estimators=100, contamination=contamination, random_state=SEED)
    model.fit(X_train_scaled)

    print("Model training complete.")

    # Evaluation
    # Predict returns 1 for normal, -1 for anomalies. We need to map this to our labels (0/1).
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
