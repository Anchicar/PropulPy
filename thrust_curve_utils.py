"""
thrust_curve_utils.py
======================
Cuando aún NO se tiene la curva de empuje real digitalizada (de un banco de
pruebas, de un .eng de fabricante, o de un software de balística interna
como OpenMotor), pero SÍ se conocen los estadísticos agregados típicos de
una hoja de especificaciones (impulso total, empuje promedio, tiempo de
quemado), esta utilidad construye una curva representativa de esa forma,
escalada para que su impulso total coincida EXACTAMENTE con el valor dado.

IMPORTANTE: esto es un sustituto de demostración/primer orden, NO el
resultado de una simulación de combustión del grano. En cuanto el equipo
tenga datos reales (banco de pruebas o simulación de grano progresivo en
OpenMotor/BurnSim), hay que reemplazar esta curva sintética por
ThrustCurveData(file_path=...) con la curva real.
"""

from __future__ import annotations
from typing import List, Tuple
import numpy as np


def synthesize_neutral_thrust_curve(
    total_impulse: float,
    burn_time: float,
    average_thrust: float,
    ignition_spike_factor: float = 1.25,
    n_points: int = 60,
) -> List[Tuple[float, float]]:
    """
    Genera una curva (t, F) con forma típica de un motor KNSB/BATES:
    pico corto de ignición, meseta cercana al empuje promedio con ligera
    caída (progresiva->ligeramente regresiva), y apagado rápido al final.
    Se reescala para que el impulso total (área bajo la curva) coincida
    exactamente con `total_impulse`.
    """
    if burn_time <= 0 or total_impulse <= 0:
        raise ValueError("burn_time y total_impulse deben ser positivos.")

    t_norm = np.linspace(0, 1, n_points)
    shape = np.ones_like(t_norm) * average_thrust

    # Pico de ignición en el primer 5% del quemado
    spike_mask = t_norm < 0.05
    shape[spike_mask] = average_thrust * (
        1 + (ignition_spike_factor - 1) * (1 - t_norm[spike_mask] / 0.05)
    )

    # Ligera caída (de +8% a -8% del promedio) entre 5% y 90% del quemado
    plateau_mask = (t_norm >= 0.05) & (t_norm < 0.90)
    shape[plateau_mask] = average_thrust * (
        1.08 - 0.16 * (t_norm[plateau_mask] - 0.05) / 0.85
    )

    # Apagado rápido en el último 10%
    tailoff_mask = t_norm >= 0.90
    shape[tailoff_mask] = average_thrust * 0.92 * (1 - (t_norm[tailoff_mask] - 0.90) / 0.10)
    shape[-1] = 0.0

    t = t_norm * burn_time
    trapz_fn = getattr(np, "trapezoid", None) or np.trapz
    raw_impulse = float(trapz_fn(shape, t))
    scale = total_impulse / raw_impulse
    f_scaled = shape * scale

    samples = [(0.0, 0.0)] + [(float(tt), float(ff)) for tt, ff in zip(t[1:], f_scaled[1:])]
    return samples
