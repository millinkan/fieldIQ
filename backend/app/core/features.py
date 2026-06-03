"""Feature matrix utilities shared by training and inference."""

import numpy as np

from app.core.config import N_FEATURES


def pad_features(X: np.ndarray, n_features: int = N_FEATURES) -> np.ndarray:
    """Pad or truncate feature matrix to the target dimension."""
    if X.ndim != 2:
        raise ValueError(f"Expected 2D array, got shape {X.shape}")
    if X.shape[1] == n_features:
        return X.astype(np.float32)
    if X.shape[1] < n_features:
        pad = np.zeros((X.shape[0], n_features - X.shape[1]), dtype=np.float32)
        return np.concatenate([X.astype(np.float32), pad], axis=1)
    return X[:, :n_features].astype(np.float32)
