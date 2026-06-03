"""
Model initialisation — v3 phase-aware bootstrap.
Handles graceful upgrade from 23-dim (v2) to 35-dim (v3) weights.
On first run with new features: detects mismatch, retrains automatically.
"""

import os
import logging
from typing import Any, Optional

import numpy as np
import joblib
from sklearn.preprocessing import StandardScaler

from app.core.config import settings, N_FEATURES, N_FEATURES_V2

logger = logging.getLogger(__name__)

_model: Optional[Any] = None
_scaler: Optional[StandardScaler] = None


def _detect_saved_feature_count() -> int:
    """Return the feature count of saved weights, or 0 if none exist."""
    if not os.path.exists(settings.MODEL_PATH):
        return 0
    try:
        import torch
        state = torch.load(settings.MODEL_PATH, map_location="cpu", weights_only=True)
        first_key = next(iter(state))
        return state[first_key].shape[1]
    except Exception:
        return 0


def init_model():
    """
    Load saved weights if present and compatible.
    If weights are v2 (23-dim) but N_FEATURES is now 35, retrain.
    """
    global _model, _scaler

    if os.getenv("SKIP_MODEL_INIT") == "1":
        _install_test_mocks()
        return

    os.makedirs(os.path.dirname(settings.MODEL_PATH), exist_ok=True)

    import torch
    from app.models.mlp import MatchMLP

    saved_n = _detect_saved_feature_count()

    if saved_n == N_FEATURES and os.path.exists(settings.SCALER_PATH):
        logger.info(f"  Loading saved v3 model ({N_FEATURES} features)...")
        _model = MatchMLP(n_features=N_FEATURES)
        _model.load_state_dict(
            torch.load(settings.MODEL_PATH, map_location="cpu", weights_only=True)
        )
        _model.eval()
        _scaler = joblib.load(settings.SCALER_PATH)
        logger.info("  Model loaded ✓")

    elif saved_n == N_FEATURES_V2:
        logger.info(
            f"  Found v2 weights ({N_FEATURES_V2} features) but v3 needs {N_FEATURES}. "
            "Retraining with expanded feature set..."
        )
        _model, _scaler = _bootstrap_training(N_FEATURES)
        torch.save(_model.state_dict(), settings.MODEL_PATH)
        joblib.dump(_scaler, settings.SCALER_PATH)
        logger.info("  V3 model saved ✓")

    else:
        logger.info(f"  No compatible weights found — bootstrapping v3 ({N_FEATURES} features)...")
        _model, _scaler = _bootstrap_training(N_FEATURES)
        torch.save(_model.state_dict(), settings.MODEL_PATH)
        joblib.dump(_scaler, settings.SCALER_PATH)
        logger.info(f"  Model saved to {settings.MODEL_PATH}")


def _bootstrap_training(n_features: int):
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    from sklearn.preprocessing import StandardScaler as SS
    from app.models.mlp import MatchMLP

    try:
        from app.data_pipeline.statsbomb_ingest import load_cached_features
        X_base, y = load_cached_features()
        logger.info(f"  Loaded {len(X_base)} cached StatsBomb samples")
        # Pad to new feature count with zeros for v3 columns
        if X_base.shape[1] < n_features:
            pad = np.zeros((X_base.shape[0], n_features - X_base.shape[1]), dtype=np.float32)
            X = np.concatenate([X_base, pad], axis=1)
        else:
            X = X_base[:, :n_features]
    except Exception:
        logger.info(f"  No StatsBomb cache — using synthetic {n_features}-feature data")
        X, y = _synthetic_data(n_features)

    scaler = SS()
    X_sc   = scaler.fit_transform(X)
    split  = int(len(X_sc) * 0.85)

    loader = DataLoader(
        TensorDataset(torch.FloatTensor(X_sc[:split]), torch.LongTensor(y[:split])),
        batch_size=128, shuffle=True,
    )
    model = MatchMLP(n_features=n_features)
    opt   = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, patience=5)
    crit  = nn.CrossEntropyLoss()
    best_loss, best_state = float("inf"), None

    X_val = torch.FloatTensor(X_sc[split:])
    y_val = torch.LongTensor(y[split:])

    max_epochs = int(os.getenv("BOOTSTRAP_EPOCHS", "80"))
    for ep in range(max_epochs):
        model.train()
        ep_loss = 0.0
        for xb, yb in loader:
            opt.zero_grad()
            loss = crit(model(xb), yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            ep_loss += loss.item()
        model.eval()
        with torch.no_grad():
            vl = crit(model(X_val), y_val).item()
        sched.step(vl)
        if vl < best_loss:
            best_loss = vl
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        if ep % 20 == 0:
            logger.info(f"    epoch {ep:3d} | val_loss {vl:.4f}")

    if best_state:
        model.load_state_dict(best_state)
    model.eval()
    return model, scaler


def _synthetic_data(n_features: int):
    rng   = np.random.default_rng(42)
    X     = rng.standard_normal((8000, n_features)).astype(np.float32)
    # Bias signal across key feature indices
    logit = (X[:, 0]*0.85 + X[:, 4]*0.55 - X[:, 11]*0.35
             + X[:, 3]*0.25 - X[:, 23]*0.30   # fatigue hurts
             + X[:, 26]*0.20                    # chemistry helps
             + X[:, 28]*0.20                    # clutch matters
             + X[:, 31]*0.25)                   # tactical edge
    p_win  = 1 / (1 + np.exp(-(logit + 0.25)))
    p_draw = np.clip(0.24 - np.abs(logit) * 0.04, 0.08, 0.32)
    p_loss = np.clip(1 - p_win - p_draw, 0.05, 1.0)
    probs  = np.column_stack([p_win, p_draw, p_loss])
    probs  = np.clip(probs, 1e-6, 1.0)
    probs /= probs.sum(axis=1, keepdims=True)
    y = np.array([rng.choice(3, p=p) for p in probs], dtype=np.int64)
    return X, y


def get_model():
    if _model is None:
        init_model()
    return _model


def get_scaler() -> StandardScaler:
    if _scaler is None:
        init_model()
    return _scaler


def _install_test_mocks():
    """Lightweight mocks for CI / environments without PyTorch."""
    global _model, _scaler
    import numpy as np
    from sklearn.preprocessing import StandardScaler

    class _MockMLP:
        n_features = N_FEATURES

        def eval(self):
            pass

        def predict_proba(self, x):
            batch = x.shape[0] if hasattr(x, "shape") else 1
            return np.tile([0.40, 0.28, 0.32], (batch, 1)).astype(np.float32)

    _model = _MockMLP()
    _scaler = StandardScaler()
    _scaler.fit(np.zeros((10, N_FEATURES), dtype=np.float32))
    logger.info("  Test mock model installed (SKIP_MODEL_INIT=1)")
