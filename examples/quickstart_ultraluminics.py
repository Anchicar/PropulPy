"""PropulPy Quickstart: complete design, simulation and RocketPy integration.

Replicating and upgrading the UltraLuminics 2x BATES motor design:
1. Environment & atmospheric pressure definition (Bogota elevation).
2. Level 1 inverse design: exact nozzle dimensions (Dt, De, L_div, L_conv).
3. Assembly of Chamber, Grains, Nozzle and Propellant into a SolidMotor.
4. Comprehensive design and safety audit (Ap/At, Kn, burst margin).
5. Quasi-steady firing simulation with chamber blowdown.
6. Export to CSV, RASP (.eng) and openMotor (.ric).
7. One-line conversion to RocketPy SolidMotor object.
"""

from pathlib import Path

from rocketpy import Environment

from propulpy import BATES, KNSB, Chamber, SolidMotor
from propulpy.analysis.checks import print_check_report
from propulpy.design.nozzle import dimension_nozzle

# 1. Environment: Launch conditions in Bogota (elevation 2600 m ASL)
env = Environment(latitude=4.6, longitude=-74.08, elevation=2600.0)
print(f"Ambient ground pressure: {env.pressure(2600) / 1e5:.3f} bar")

# 2. Propellant definition
prop = KNSB(cstar_efficiency=0.95)

# 3. Level 1 Inverse Design: Dimension optimal nozzle for 40 bar nominal pressure
nozzle_dims = dimension_nozzle(
    throat_diameter=5.88e-3,
    chamber_pressure=40.0e5,
    propellant=prop,
    chamber_diameter=42.0e-3,
    ambient_pressure=env,
    area_ratio_safety_factor=0.85,  # avoid overexpansion / separation
    efficiency=0.90,
)
nozzle_dims.report()

# 4. Grains & Chamber
grains = [
    BATES(
        diameter=38.0e-3,
        core_diameter=12.5e-3,
        length=62.0e-3,
        inhibited_ends="neither",
    )
] * 2

chamber = Chamber(
    inner_diameter=42.0e-3,
    length=0.19,
    outer_diameter=46.0e-3,
    yield_strength=276.0e6,  # Aluminum 6061-T6
)

# 5. Assemble SolidMotor
motor = SolidMotor(
    propellant=prop,
    grains=grains,
    nozzle=nozzle_dims.to_nozzle(),
    chamber=chamber,
)

# 6. Safety and Ballistic Audit
print_check_report(motor)

# 7. Quasi-Steady Firing Simulation
results = motor.simulate(ambient_pressure=env)
results.info()

# 8. Export Files
out_dir = Path("outputs")
out_dir.mkdir(exist_ok=True)
results.export_csv(out_dir / "ultraluminics_motor.csv")
results.export_eng(out_dir / "ultraluminics_motor.eng", motor_name="H150-UL")
results.export_ric(
    out_dir / "ultraluminics_motor.ric", description="UltraLuminics KNSB"
)
print(f"\nMotor files successfully exported to '{out_dir.absolute()}/'")

# 9. Ready for RocketPy
rp_motor = results.to_rocketpy(
    dry_mass=0.600,
    dry_inertia=(0.05, 0.05, 0.001),
    center_of_dry_mass_position=0.10,
)
print(f"RocketPy motor generated: Total Impulse = {rp_motor.total_impulse:.1f} Ns")
