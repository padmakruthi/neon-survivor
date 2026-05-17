# ═══════════════════════════════════════════════════════════
# GoldenBatch AI — ML Model
# Team DeepThinkers · IARE · AVEVA Hackathon
#
# This file:
# 1. Reads the 60 batch Excel file
# 2. Trains an XGBoost model on it
# 3. Saves the trained model as model.pkl
# 4. Has a predict() function that takes 8 parameters
#    and returns quality predictions
# ═══════════════════════════════════════════════════════════

import pandas as pd
import numpy as np
import joblib
import os
import json

from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score
import xgboost as xgb

# ───────────────────────────────────────────
# FILE PATHS
# ───────────────────────────────────────────
EXCEL_FILE  = "_h_batch_production_data.xlsx"   # your Excel file
MODEL_FILE  = "model.pkl"                        # saved trained model
SCALER_FILE = "scaler.pkl"                       # saved scaler

# ───────────────────────────────────────────
# QUALITY STANDARDS
# What values are considered PASS or FAIL
# ───────────────────────────────────────────
STANDARDS = {
    "dissolution_rate":    {"min": 85.0,  "max": 100.0},
    "hardness":            {"min": 80.0,  "max": 130.0},
    "friability":          {"min": 0.0,   "max": 1.0  },
    "content_uniformity":  {"min": 95.0,  "max": 105.0},
}

# ───────────────────────────────────────────
# COLUMN NAMES
# Must match exactly what's in your Excel file
# ───────────────────────────────────────────
INPUT_COLUMNS = [
    "Granulation_Time",
    "Binder_Amount",
    "Drying_Temp",
    "Drying_Time",
    "Compression_Force",
    "Machine_Speed",
    "Lubricant_Conc",
    "Moisture_Content"
]

OUTPUT_COLUMNS = [
    "Dissolution_Rate",
    "Hardness",
    "Friability",
    "Content_Uniformity"
]

# ───────────────────────────────────────────
# GOLDEN SIGNATURE
# Best batch from your dataset — used as benchmark
# Will be set when data is loaded
# ───────────────────────────────────────────
GOLDEN_BATCH = None
TOP_BATCHES  = None

# Global model and scaler objects
MODEL  = None
SCALER = None


# ═══════════════════════════════════════════
# STEP 1 — LOAD DATA FROM EXCEL
# ═══════════════════════════════════════════
def load_data():
    """
    Reads the Excel file containing 60 batches.
    Returns X (inputs) and y (outputs) as numpy arrays.
    Also sets the GOLDEN_BATCH and TOP_BATCHES globals.
    """
    global GOLDEN_BATCH, TOP_BATCHES

    if not os.path.exists(EXCEL_FILE):
        raise FileNotFoundError(
            f"Excel file '{EXCEL_FILE}' not found!\n"
            f"Make sure the file is in the same folder as model.py"
        )

    print(f"📂 Reading data from {EXCEL_FILE}...")
    df = pd.read_excel(EXCEL_FILE)

    print(f"✅ Loaded {len(df)} rows, {len(df.columns)} columns")
    print(f"   Columns found: {list(df.columns)}")

    # ── Clean column names (remove spaces, fix case) ──
    df.columns = df.columns.str.strip().str.replace(" ", "_")

    # ── Check all required columns exist ──
    missing_inputs  = [c for c in INPUT_COLUMNS  if c not in df.columns]
    missing_outputs = [c for c in OUTPUT_COLUMNS if c not in df.columns]

    if missing_inputs or missing_outputs:
        print(f"⚠ WARNING: Missing input columns:  {missing_inputs}")
        print(f"⚠ WARNING: Missing output columns: {missing_outputs}")
        print(f"   Available columns: {list(df.columns)}")

        # Try to auto-map common variations
        df = auto_map_columns(df)

    # ── Extract X and y ──
    X = df[INPUT_COLUMNS].values
    y = df[OUTPUT_COLUMNS].values

    print(f"   Input shape:  {X.shape}  (rows x features)")
    print(f"   Output shape: {y.shape} (rows x targets)")

    # ── Find golden signature (highest dissolution rate) ──
    best_idx = df["Dissolution_Rate"].idxmax()
    best_row = df.iloc[best_idx]

    GOLDEN_BATCH = {
        "batch_id": str(best_row.get("Batch_ID", f"T{best_idx+1:03d}")),
        "inputs": {col: float(best_row[col]) for col in INPUT_COLUMNS},
        "outputs": {
            "dissolution_rate":   float(best_row["Dissolution_Rate"]),
            "hardness":           float(best_row["Hardness"]),
            "friability":         float(best_row["Friability"]),
            "content_uniformity": float(best_row["Content_Uniformity"]),
        },
        "note": "Highest dissolution rate batch — used as golden benchmark"
    }

    print(f"✦  Golden Batch: {GOLDEN_BATCH['batch_id']} "
          f"(Dissolution: {GOLDEN_BATCH['outputs']['dissolution_rate']}%)")

    # ── Top 5 batches by dissolution ──
    top5 = df.nlargest(5, "Dissolution_Rate")
    TOP_BATCHES = []
    for i, (_, row) in enumerate(top5.iterrows()):
        TOP_BATCHES.append({
            "rank": i + 1,
            "batch_id": str(row.get("Batch_ID", f"T{_+1:03d}")),
            "dissolution_rate":   round(float(row["Dissolution_Rate"]), 1),
            "hardness":           round(float(row["Hardness"]), 1),
            "friability":         round(float(row["Friability"]), 2),
            "content_uniformity": round(float(row["Content_Uniformity"]), 1),
            "compression_force":  round(float(row["Compression_Force"]), 1),
        })

    return X, y, df


# ═══════════════════════════════════════════
# STEP 2 — AUTO MAP COLUMNS
# If column names in Excel are slightly different,
# this tries to find the right ones automatically
# ═══════════════════════════════════════════
def auto_map_columns(df):
    """
    Tries to match Excel column names to expected names.
    For example: "Granulation Time" → "Granulation_Time"
    """
    rename_map = {}
    for col in df.columns:
        normalized = col.strip().replace(" ", "_").replace("-", "_")
        rename_map[col] = normalized

    df = df.rename(columns=rename_map)
    print(f"   Auto-mapped columns: {rename_map}")
    return df


# ═══════════════════════════════════════════
# STEP 3 — TRAIN THE MODEL
# ═══════════════════════════════════════════
def train_model(X, y):
    """
    Trains an XGBoost model on the 60 batch dataset.

    Why XGBoost?
    - Works well with small datasets (60 rows is small for ML)
    - Handles non-linear relationships between parameters
    - Fast to train
    - Gives feature importance (which parameter matters most)

    MultiOutputRegressor wraps XGBoost so it can predict
    multiple outputs at once (dissolution, hardness, friability, uniformity)
    """
    global MODEL, SCALER

    print("🧠 Training ML model...")

    # ── Scale the inputs ──
    # StandardScaler converts all inputs to same scale
    # so no single parameter dominates just because of its unit
    # e.g. Machine Speed (100-280 RPM) vs Lubricant (0.2-2.8%)
    SCALER = StandardScaler()
    X_scaled = SCALER.fit_transform(X)

    # ── Split into train/test sets ──
    # 80% for training, 20% for testing accuracy
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42
    )

    # ── XGBoost model ──
    # n_estimators: number of trees (100 is good for small datasets)
    # max_depth: how deep each tree goes (3 prevents overfitting)
    # learning_rate: how fast it learns (0.1 is standard)
    xgb_model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.1,
        random_state=42,
        verbosity=0
    )

    # MultiOutputRegressor trains one XGBoost model per output
    # So we get 4 models: dissolution, hardness, friability, uniformity
    MODEL = MultiOutputRegressor(xgb_model)
    MODEL.fit(X_train, y_train)

    # ── Evaluate accuracy ──
    y_pred = MODEL.predict(X_test)
    r2_scores = r2_score(y_test, y_pred, multioutput='raw_values')

    print(f"✅ Model trained successfully!")
    print(f"   R² Scores (closer to 1.0 = more accurate):")
    for i, col in enumerate(OUTPUT_COLUMNS):
        print(f"   {col:25s}: {r2_scores[i]:.3f}")

    return MODEL, SCALER


# ═══════════════════════════════════════════
# STEP 4 — SAVE THE TRAINED MODEL
# ═══════════════════════════════════════════
def save_model():
    """
    Saves the trained model and scaler to disk.
    Next time server starts, we load these instead of retraining.
    """
    joblib.dump(MODEL,  MODEL_FILE)
    joblib.dump(SCALER, SCALER_FILE)
    print(f"💾 Model saved to {MODEL_FILE}")
    print(f"💾 Scaler saved to {SCALER_FILE}")


# ═══════════════════════════════════════════
# LOAD OR TRAIN — Called at server startup
# ═══════════════════════════════════════════
def load_or_train_model():
    """
    If model.pkl already exists → load it (fast, 1 second)
    If not → train from scratch (takes 3-5 seconds)
    """
    global MODEL, SCALER

    # Always load the data to set GOLDEN_BATCH and TOP_BATCHES
    X, y, df = load_data()

    if os.path.exists(MODEL_FILE) and os.path.exists(SCALER_FILE):
        print(f"📦 Loading saved model from {MODEL_FILE}...")
        MODEL  = joblib.load(MODEL_FILE)
        SCALER = joblib.load(SCALER_FILE)
        print(f"✅ Model loaded successfully (no retraining needed)")
    else:
        print(f"🔄 No saved model found — training from scratch...")
        train_model(X, y)
        save_model()


# ═══════════════════════════════════════════
# PREDICT — The main function called by main.py
# ═══════════════════════════════════════════
def predict(inputs: dict) -> dict:
    """
    Takes 8 batch parameters as a dictionary.
    Runs them through the trained ML model.
    Returns predicted quality metrics + pass/fail + recommendations.

    inputs = {
        "Granulation_Time": 16,
        "Binder_Amount": 8.5,
        "Drying_Temp": 60,
        "Drying_Time": 28,
        "Compression_Force": 12.5,
        "Machine_Speed": 160,
        "Lubricant_Conc": 1.0,
        "Moisture_Content": 2.1
    }
    """
    if MODEL is None or SCALER is None:
        raise RuntimeError("Model not loaded. Call load_or_train_model() first.")

    # ── Pack inputs into array in correct order ──
    X_input = np.array([[
        inputs["Granulation_Time"],
        inputs["Binder_Amount"],
        inputs["Drying_Temp"],
        inputs["Drying_Time"],
        inputs["Compression_Force"],
        inputs["Machine_Speed"],
        inputs["Lubricant_Conc"],
        inputs["Moisture_Content"]
    ]])

    # ── Scale inputs the same way we scaled training data ──
    X_scaled = SCALER.transform(X_input)

    # ── Run prediction ──
    y_pred = MODEL.predict(X_scaled)[0]

    dissolution   = round(float(y_pred[0]), 1)
    hardness      = round(float(y_pred[1]), 1)
    friability    = round(float(y_pred[2]), 2)
    uniformity    = round(float(y_pred[3]), 1)

    # ── Clamp values to realistic ranges ──
    dissolution = max(70.0, min(100.0, dissolution))
    hardness    = max(30.0, min(160.0, hardness))
    friability  = max(0.1,  min(3.0,   friability))
    uniformity  = max(85.0, min(110.0, uniformity))

    # ── Energy estimate ──
    # Based on compression force and machine speed (proxy formula)
    energy = round(
        (inputs["Compression_Force"] * 0.85) +
        (inputs["Machine_Speed"] * 0.045) +
        (inputs["Drying_Temp"] * 0.08) +
        (inputs["Drying_Time"] * 0.12) + 2.5,
        1
    )
    co2 = round(energy * 0.44, 2)   # 0.44 kg CO2 per kWh (India grid factor)

    # ── Check against quality standards ──
    pass_dissolution = dissolution >= STANDARDS["dissolution_rate"]["min"]
    pass_hardness    = (STANDARDS["hardness"]["min"]
                        <= hardness <=
                        STANDARDS["hardness"]["max"])
    pass_friability  = friability <= STANDARDS["friability"]["max"]
    pass_uniformity  = (STANDARDS["content_uniformity"]["min"]
                        <= uniformity <=
                        STANDARDS["content_uniformity"]["max"])

    overall_pass = all([pass_dissolution, pass_hardness,
                        pass_friability,  pass_uniformity])

    individual_results = {
        "dissolution":  {"value": dissolution, "pass": pass_dissolution, "standard": "≥85%"},
        "hardness":     {"value": hardness,    "pass": pass_hardness,    "standard": "80–130 N"},
        "friability":   {"value": friability,  "pass": pass_friability,  "standard": "≤1.0%"},
        "uniformity":   {"value": uniformity,  "pass": pass_uniformity,  "standard": "95–105%"},
    }

    # ── Generate root cause explanation ──
    root_cause = generate_root_cause(inputs, dissolution, hardness,
                                     friability, uniformity,
                                     pass_dissolution, pass_hardness,
                                     pass_friability, pass_uniformity)

    # ── Generate recommendations ──
    recommendations = generate_recommendations(
        inputs, dissolution, hardness, friability, uniformity,
        pass_dissolution, pass_hardness, pass_friability, pass_uniformity
    )

    # ── Compare vs golden signature ──
    vs_golden = {}
    if GOLDEN_BATCH:
        g = GOLDEN_BATCH["outputs"]
        vs_golden = {
            "dissolution":  {"this": dissolution,  "golden": g["dissolution_rate"],   "better": dissolution  >= g["dissolution_rate"]},
            "hardness":     {"this": hardness,     "golden": g["hardness"],            "better": hardness     <= g["hardness"]},
            "friability":   {"this": friability,   "golden": g["friability"],          "better": friability   <= g["friability"]},
            "uniformity":   {"this": uniformity,   "golden": g["content_uniformity"],  "better": uniformity   >= g["content_uniformity"]},
            "energy":       {"this": energy,       "golden": "~12 kWh",               "better": energy       <= 12},
        }

    return {
        "dissolution_rate":    dissolution,
        "hardness":            hardness,
        "friability":          friability,
        "content_uniformity":  uniformity,
        "energy_estimate":     energy,
        "co2_estimate":        co2,
        "overall_pass":        overall_pass,
        "individual_results":  individual_results,
        "recommendations":     recommendations,
        "root_cause":          root_cause,
        "vs_golden":           vs_golden,
    }


# ═══════════════════════════════════════════
# ROOT CAUSE EXPLANATION
# Explains WHY the batch will pass or fail
# This is your key differentiator!
# ═══════════════════════════════════════════
def generate_root_cause(inputs, dissolution, hardness, friability,
                         uniformity, pass_d, pass_h, pass_f, pass_u) -> str:
    """
    Generates a human-readable explanation of WHY the model
    predicted what it predicted.

    This is based on the key correlations found in your dataset:
    - Moisture Content is the #1 driver of Dissolution Rate
    - Compression Force drives Hardness and hurts Dissolution
    - High Drying Temp can cause uneven moisture removal
    """

    causes = []

    # Dissolution root cause
    if not pass_d:
        if inputs["Moisture_Content"] > 2.5:
            causes.append(
                f"Dissolution {dissolution}% is below target. "
                f"Primary cause: Moisture Content {inputs['Moisture_Content']}% is too high "
                f"(target ≤2.0%). High moisture reduces drug release rate."
            )
        elif inputs["Compression_Force"] > 13:
            causes.append(
                f"Dissolution {dissolution}% is below target. "
                f"Primary cause: Compression Force {inputs['Compression_Force']} kN is too high. "
                f"Over-compression creates dense tablets that resist dissolution."
            )
        elif inputs["Drying_Temp"] > 65:
            causes.append(
                f"Dissolution {dissolution}% is below target. "
                f"Likely cause: Drying Temperature {inputs['Drying_Temp']}°C may be causing "
                f"uneven moisture distribution, affecting drug release."
            )
        else:
            causes.append(
                f"Dissolution {dissolution}% is below target. "
                f"Review combination of Moisture Content and Compression Force."
            )

    # Hardness root cause
    if not pass_h:
        if hardness < STANDARDS["hardness"]["min"]:
            causes.append(
                f"Hardness {hardness} N is too low (need ≥80 N). "
                f"Cause: Compression Force {inputs['Compression_Force']} kN may be too low. "
                f"Tablets will be too fragile."
            )
        elif hardness > STANDARDS["hardness"]["max"]:
            causes.append(
                f"Hardness {hardness} N is too high (need ≤130 N). "
                f"Cause: Compression Force {inputs['Compression_Force']} kN is too high. "
                f"This also negatively impacts dissolution."
            )

    # Friability root cause
    if not pass_f:
        causes.append(
            f"Friability {friability}% exceeds limit (need ≤1.0%). "
            f"Tablets are too fragile — likely due to low compression or high lubricant concentration."
        )

    # Uniformity root cause
    if not pass_u:
        causes.append(
            f"Content Uniformity {uniformity}% is out of range (need 95–105%). "
            f"Mixing may be insufficient — review Granulation Time and Binder Amount."
        )

    if not causes:
        return (
            f"All parameters within specification. "
            f"Dissolution {dissolution}%, Hardness {hardness} N, "
            f"Friability {friability}%, Uniformity {uniformity}%. "
            f"Batch is predicted to pass all quality standards."
        )

    return " | ".join(causes)


# ═══════════════════════════════════════════
# RECOMMENDATIONS
# Specific parameter changes to fix failures
# ═══════════════════════════════════════════
def generate_recommendations(inputs, dissolution, hardness, friability,
                              uniformity, pass_d, pass_h, pass_f, pass_u) -> list:
    """
    Returns a list of specific, actionable recommendations
    to fix any quality failures.
    """
    recs = []

    if not pass_d:
        if inputs["Moisture_Content"] > 2.0:
            recs.append(
                f"Reduce Moisture Content: {inputs['Moisture_Content']}% → "
                f"target ≤2.0%. This is the strongest predictor of dissolution rate."
            )
        if inputs["Compression_Force"] > 12:
            new_force = round(inputs["Compression_Force"] - 2.0, 1)
            recs.append(
                f"Reduce Compression Force: {inputs['Compression_Force']} kN → "
                f"{new_force} kN. Lower force improves dissolution."
            )
        if inputs["Drying_Temp"] > 62:
            recs.append(
                f"Lower Drying Temperature: {inputs['Drying_Temp']}°C → "
                f"{inputs['Drying_Temp'] - 5}°C. Prevents uneven moisture distribution."
            )

    if not pass_h:
        if hardness < STANDARDS["hardness"]["min"]:
            new_force = round(inputs["Compression_Force"] + 1.5, 1)
            recs.append(
                f"Increase Compression Force: {inputs['Compression_Force']} kN → "
                f"{new_force} kN to achieve adequate hardness."
            )
        elif hardness > STANDARDS["hardness"]["max"]:
            new_force = round(inputs["Compression_Force"] - 2.0, 1)
            recs.append(
                f"Decrease Compression Force: {inputs['Compression_Force']} kN → "
                f"{new_force} kN to reduce hardness."
            )

    if not pass_f:
        recs.append(
            f"Friability too high ({friability}%). "
            f"Try increasing Compression Force slightly or reducing Lubricant "
            f"Concentration from {inputs['Lubricant_Conc']}% to "
            f"{round(inputs['Lubricant_Conc'] - 0.3, 1)}%."
        )

    if not pass_u:
        if inputs["Granulation_Time"] < 15:
            recs.append(
                f"Increase Granulation Time: {inputs['Granulation_Time']} → "
                f"{inputs['Granulation_Time'] + 5} min for better blend uniformity."
            )
        recs.append(
            f"Check Binder Amount ({inputs['Binder_Amount']} g). "
            f"Golden signature uses {GOLDEN_BATCH['inputs']['Binder_Amount']} g "
            f"for optimal uniformity."
            if GOLDEN_BATCH else
            f"Review Binder Amount and Granulation Time for uniformity issues."
        )

    if not recs:
        recs.append("All standards met. Proceed with batch using current parameters.")
        if GOLDEN_BATCH:
            g_force = GOLDEN_BATCH["inputs"]["Compression_Force"]
            if abs(inputs["Compression_Force"] - g_force) > 2:
                recs.append(
                    f"Optional: Align Compression Force closer to golden signature "
                    f"({g_force} kN) for optimal energy efficiency."
                )

    return recs


# ═══════════════════════════════════════════
# GET GOLDEN SIGNATURE — called by main.py
# ═══════════════════════════════════════════
def get_golden_signature() -> dict:
    """Returns the golden batch details."""
    if GOLDEN_BATCH is None:
        return {"error": "Model not loaded yet"}
    return GOLDEN_BATCH


# ═══════════════════════════════════════════
# GET TOP BATCHES — called by main.py
# ═══════════════════════════════════════════
def get_top_batches() -> list:
    """Returns top 5 batches by dissolution rate."""
    if TOP_BATCHES is None:
        return []
    return TOP_BATCHES