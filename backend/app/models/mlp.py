"""
MatchMLP — version-aware architecture.
V3 (35 features): adds wider first layer to handle new contextual intelligence inputs.
V2 (23 features): preserved for backward-compatible weight loading.
"""

import torch
import torch.nn as nn
from app.core.config import N_FEATURES, N_FEATURES_V2


class MatchMLP(nn.Module):
    """
    Deep Learning MLP for match outcome prediction.

    V3 input:  35-dimensional feature vector
    V2 input:  23-dimensional feature vector (legacy)
    Output:    3-class softmax [P_win, P_draw, P_loss]

    Architecture scales with input:
        35 → 512 → 256 → 128 → 64 → 3
        23 → 256 → 128 →  64 → 3
    """

    def __init__(self, n_features: int = N_FEATURES):
        super().__init__()
        self.n_features = n_features

        if n_features >= 30:  # V3
            self.net = nn.Sequential(
                nn.Linear(n_features, 512),
                nn.BatchNorm1d(512),
                nn.ReLU(),
                nn.Dropout(0.3),

                nn.Linear(512, 256),
                nn.BatchNorm1d(256),
                nn.ReLU(),
                nn.Dropout(0.3),

                nn.Linear(256, 128),
                nn.BatchNorm1d(128),
                nn.ReLU(),
                nn.Dropout(0.25),

                nn.Linear(128, 64),
                nn.BatchNorm1d(64),
                nn.ReLU(),
                nn.Dropout(0.2),

                nn.Linear(64, 3),
            )
        else:  # V2 / legacy
            self.net = nn.Sequential(
                nn.Linear(n_features, 256),
                nn.BatchNorm1d(256),
                nn.ReLU(),
                nn.Dropout(0.3),

                nn.Linear(256, 128),
                nn.BatchNorm1d(128),
                nn.ReLU(),
                nn.Dropout(0.3),

                nn.Linear(128, 64),
                nn.BatchNorm1d(64),
                nn.ReLU(),
                nn.Dropout(0.2),

                nn.Linear(64, 3),
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """Return softmax probabilities [P_win, P_draw, P_loss]."""
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            return torch.softmax(logits, dim=1)
