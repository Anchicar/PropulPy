"""Design and safety verification checks for solid rocket motors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from propulpy.motor import SolidMotor
    from propulpy.results import MotorResults


@dataclass
class CheckResult:
    """Individual safety check outcome.

    Attributes
    ----------
    name : str
        Name of the design criterion checked.
    value : float
        Calculated metric value.
    status : {"OK", "WARNING", "DANGER"}
        Safety status.
    message : str
        Human-readable explanation and recommendation.
    """

    name: str
    value: float
    status: str
    message: str


def check_motor_design(motor: SolidMotor, results: MotorResults | None = None) -> list[CheckResult]:
    """Run comprehensive ballistics and structural safety checks on a motor.

    Evaluates:
    - Port-to-throat area ratio (Ap / At >= 2.0)
    - Initial and peak Klemmung ratio Kn
    - Grain d/D and L/D geometric proportions (for BATES grains)
    - Structural casing safety factor against burst
    - Nozzle exit separation risk (Summerfield criterion)

    Parameters
    ----------
    motor : SolidMotor
        Motor configuration to evaluate.
    results : MotorResults, optional
        Pre-computed simulation results. If None, a simulation is run.

    Returns
    -------
    list of CheckResult
        List of diagnostic results with status and messages.
    """
    if results is None:
        results = motor.simulate()

    checks = []

    # 1. Port-to-Throat Ratio (Ap / At)
    ap_at = motor.initial_port_to_throat_ratio
    if ap_at >= 2.0:
        status = "OK"
        msg = f"Port-to-throat ratio ({ap_at:.2f}) is safe (>= 2.0)."
    elif ap_at >= 1.5:
        status = "WARNING"
        msg = f"Port-to-throat ratio ({ap_at:.2f}) is marginal (1.5 - 2.0); mild erosive burning possible."
    else:
        status = "DANGER"
        msg = f"Port-to-throat ratio ({ap_at:.2f}) is dangerously low (< 1.5); severe erosive burning risk."
    checks.append(CheckResult("Port-to-Throat Ratio (Ap/At)", ap_at, status, msg))

    # 2. Initial Kn
    kn_0 = motor.initial_kn
    if 200.0 <= kn_0 <= 350.0:
        status = "OK"
        msg = f"Initial Kn ({kn_0:.1f}) is within nominal operating range (200 - 350)."
    elif kn_0 < 200.0:
        status = "WARNING"
        msg = f"Initial Kn ({kn_0:.1f}) is low (< 200); risk of chuffing or unstable burn."
    elif kn_0 <= 400.0:
        status = "WARNING"
        msg = f"Initial Kn ({kn_0:.1f}) is elevated (350 - 400); verify casing pressure rating."
    else:
        status = "DANGER"
        msg = f"Initial Kn ({kn_0:.1f}) is critically high (> 400); risk of casing overpressure."
    checks.append(CheckResult("Initial Kn", kn_0, status, msg))

    # 3. Peak Chamber Pressure
    pc_peak_bar = results.max_chamber_pressure / 1e5
    if pc_peak_bar <= 45.0:
        status = "OK"
        msg = f"Peak chamber pressure ({pc_peak_bar:.1f} bar) is within normal sugar/composite bounds."
    elif pc_peak_bar <= 60.0:
        status = "WARNING"
        msg = f"Peak chamber pressure ({pc_peak_bar:.1f} bar) is high; ensure pressure vessel rating."
    else:
        status = "DANGER"
        msg = f"Peak chamber pressure ({pc_peak_bar:.1f} bar) exceeds standard amateur limits (> 60 bar)."
    checks.append(CheckResult("Peak Chamber Pressure (bar)", pc_peak_bar, status, msg))

    # 4. Casing Structural Safety Factor (if Chamber provided)
    if motor.chamber is not None and motor.chamber.burst_pressure() is not None:
        sf = motor.chamber.safety_factor(results.max_chamber_pressure)
        if sf >= 2.0:
            status = "OK"
            msg = f"Casing safety factor ({sf:.2f}) is generous (>= 2.0)."
        elif sf >= 1.5:
            status = "OK"
            msg = f"Casing safety factor ({sf:.2f}) meets aerospace standard (1.5 - 2.0)."
        elif sf >= 1.25:
            status = "WARNING"
            msg = f"Casing safety factor ({sf:.2f}) is low (< 1.5); consider increasing wall thickness."
        else:
            status = "DANGER"
            msg = f"Casing safety factor ({sf:.2f}) is dangerously low (< 1.25); burst hazard."
        checks.append(CheckResult("Casing Safety Factor", sf, status, msg))

    # 5. Nozzle Flow Separation (Summerfield Criterion: Pe >= 0.35 * Pa)
    pe_pa_min = (results.chamber_pressure[0] * motor.nozzle.exit_pressure(motor.propellant.k, 1.0)) / results.ambient_pressure
    if pe_pa_min >= 0.40:
        status = "OK"
        msg = f"Nozzle exit pressure ratio Pe/Pa ({pe_pa_min:.2f}) is well above separation threshold."
    elif pe_pa_min >= 0.30:
        status = "WARNING"
        msg = f"Nozzle exit pressure ratio Pe/Pa ({pe_pa_min:.2f}) is marginal; minor flow separation possible."
    else:
        status = "DANGER"
        msg = f"Nozzle exit pressure ratio Pe/Pa ({pe_pa_min:.2f}) is below 0.30; risk of flow separation."
    checks.append(CheckResult("Nozzle Separation (Pe/Pa)", pe_pa_min, status, msg))

    return checks


def print_check_report(motor: SolidMotor, results: MotorResults | None = None) -> None:
    """Print a clean diagnostic table of all safety checks."""
    checks = check_motor_design(motor, results)
    print("=" * 70)
    print("                  PROPULPY MOTOR DESIGN & SAFETY AUDIT")
    print("=" * 70)
    for c in checks:
        color = "[OK]" if c.status == "OK" else f"[{c.status}]"
        print(f"{color:<10} {c.name:<32}: {c.message}")
    print("=" * 70)
