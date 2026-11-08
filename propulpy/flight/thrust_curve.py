"""Synthetic thrust curve utilities for preliminary first-order sizing.

When neither experimental test-stand data nor a full internal-ballistics
simulation is used, ``synthesize_neutral_thrust_curve`` constructs a
representative neutral/BATES-like ``(t, F)`` curve scaled to match a target
total impulse and burn time.
"""

from __future__ import annotations

import numpy as np

_trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))


def synthesize_neutral_thrust_curve(
    total_impulse: float,
    burn_time: float,
    average_thrust: float,
    ignition_spike_factor: float = 1.25,
    n_points: int = 60,
) -> list[tuple[float, float]]:
    """Generate a synthetic ``(t, F)`` curve scaled to match ``total_impulse``.

    Parameters
    ----------
    total_impulse : float
        Target total impulse [N s].
    burn_time : float
        Burn duration [s].
    average_thrust : float
        Nominal average thrust [N].
    ignition_spike_factor : float, optional
        Initial ignition spike multiplier relative to average thrust. Default 1.25.
    n_points : int, optional
        Number of time discretization points. Default 60.

    Returns
    -------
    list of (float, float)
        Time-thrust pairs ``(t [s], F [N])``.
    """
    if burn_time <= 0 or total_impulse <= 0:
        raise ValueError("burn_time and total_impulse must be positive.")

    t_norm = np.linspace(0.0, 1.0, n_points)
    shape = np.ones_like(t_norm) * average_thrust

    # Ignition spike in the first 5% of burn
    spike_mask = t_norm < 0.05
    shape[spike_mask] = average_thrust * (
        1.0 + (ignition_spike_factor - 1.0) * (1.0 - t_norm[spike_mask] / 0.05)
    )

    # Gentle plateau slope (+8% to -8% of average) between 5% and 90% of burn
    plateau_mask = (t_norm >= 0.05) & (t_norm < 0.90)
    shape[plateau_mask] = average_thrust * (
        1.08 - 0.16 * (t_norm[plateau_mask] - 0.05) / 0.85
    )

    # Rapid tail-off in the last 10%
    tailoff_mask = t_norm >= 0.90
    shape[tailoff_mask] = (
        average_thrust * 0.92 * (1.0 - (t_norm[tailoff_mask] - 0.90) / 0.10)
    )
    shape[0] = 0.0
    shape[-1] = 0.0

    t = t_norm * burn_time
    raw_impulse = float(_trapz(shape, t))
    scale = total_impulse / raw_impulse
    f_scaled = shape * scale

    return [(float(tt), float(ff)) for tt, ff in zip(t, f_scaled, strict=False)]

