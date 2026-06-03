"""Simulation request/response schemas."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class SimulationWeights(BaseModel):
    """Feature-group emphasis — values are relative multipliers (0–1 scale)."""

    elo_weight: float = Field(0.40, ge=0.0, le=1.0)
    form_weight: float = Field(0.25, ge=0.0, le=1.0)
    pdv_weight: float = Field(0.20, ge=0.0, le=1.0)
    xg_weight: float = Field(0.15, ge=0.0, le=1.0)
    srr_weight: float = Field(0.10, ge=0.0, le=1.0)


class LayerToggles(BaseModel):
    fatigue: bool = True
    chemistry: bool = True
    momentum: bool = True
    tactical: bool = True


class SimulateRequest(BaseModel):
    n_simulations: int = Field(1000, ge=100, le=10_000)
    elo_weight: float = Field(0.40, ge=0.0, le=1.0)
    form_weight: float = Field(0.25, ge=0.0, le=1.0)
    pdv_weight: float = Field(0.20, ge=0.0, le=1.0)
    xg_weight: float = Field(0.15, ge=0.0, le=1.0)
    srr_weight: float = Field(0.10, ge=0.0, le=1.0)
    injuries: Optional[Dict[str, List[str]]] = None
    enable_fatigue: bool = True
    enable_chemistry: bool = True
    enable_momentum: bool = True
    enable_tactical: bool = True
    use_cache: bool = True

    @property
    def weights(self) -> SimulationWeights:
        return SimulationWeights(
            elo_weight=self.elo_weight,
            form_weight=self.form_weight,
            pdv_weight=self.pdv_weight,
            xg_weight=self.xg_weight,
            srr_weight=self.srr_weight,
        )

    @property
    def layers(self) -> LayerToggles:
        return LayerToggles(
            fatigue=self.enable_fatigue,
            chemistry=self.enable_chemistry,
            momentum=self.enable_momentum,
            tactical=self.enable_tactical,
        )

    def cache_payload(self) -> dict:
        return {
            "n": self.n_simulations,
            "w": [self.elo_weight, self.form_weight, self.pdv_weight, self.xg_weight, self.srr_weight],
            "l": [self.enable_fatigue, self.enable_chemistry, self.enable_momentum, self.enable_tactical],
            "i": self.injuries or {},
        }
