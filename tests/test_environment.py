import numpy as np
import pytest

from propulpy import AmbientConditions, constants_from_environment


class FakeEnvironment:
    """Minimal stand-in for rocketpy.Environment (exponential atmosphere)."""

    elevation = 2600.0

    @staticmethod
    def pressure(h):
        return 101325.0 * np.exp(-h / 8434.0)


def test_default_is_standard_sea_level():
    assert AmbientConditions().ground_pressure == 101325.0


def test_constant_pressure():
    amb = AmbientConditions(96325.0)
    assert amb.is_constant
    assert amb.pressure(5000.0) == 96325.0
    assert np.all(amb.pressure([0.0, 1000.0]) == 96325.0)


def test_environment_like_source_uses_elevation():
    amb = AmbientConditions(FakeEnvironment())
    assert not amb.is_constant
    assert amb.ground_pressure == pytest.approx(FakeEnvironment.pressure(2600.0))
    profile = amb.pressure([2600.0, 3600.0])
    assert profile[1] < profile[0]


def test_real_rocketpy_environment():
    rocketpy = pytest.importorskip("rocketpy")
    env = rocketpy.Environment(latitude=4.6, longitude=-74.08, elevation=2600)
    amb = AmbientConditions(env)
    # Standard atmosphere at 2600 m ASL is ~74 kPa
    assert amb.ground_pressure == pytest.approx(74_000, rel=0.03)
    assert amb.ground_gravity == pytest.approx(float(env.gravity(2600)), rel=1e-6)
    assert amb.ground_temperature == pytest.approx(
        float(env.temperature(2600)), rel=1e-6
    )
    assert amb.ground_density == pytest.approx(float(env.density(2600)), rel=1e-6)
    assert amb.ground_speed_of_sound == pytest.approx(
        float(env.speed_of_sound(2600)), rel=1e-6
    )

    consts = constants_from_environment(env)
    assert consts.altitude_asl == 2600.0
    assert consts.pressure == pytest.approx(amb.ground_pressure, rel=1e-6)
    assert consts.gravity == pytest.approx(amb.ground_gravity, rel=1e-6)
    assert consts.temperature == pytest.approx(amb.ground_temperature, rel=1e-6)
    assert consts.density == pytest.approx(amb.ground_density, rel=1e-6)
    assert consts.speed_of_sound == pytest.approx(amb.ground_speed_of_sound, rel=1e-6)

    amb_direct = AmbientConditions.from_rocketpy(
        latitude=4.6, longitude=-74.08, elevation=2600.0
    )
    assert amb_direct.ground_pressure == pytest.approx(amb.ground_pressure, rel=1e-5)


def test_invalid_source():
    with pytest.raises(TypeError):
        AmbientConditions("Bogota")
    with pytest.raises(TypeError, match="\\[constants_from_environment\\]"):
        constants_from_environment("invalid_env")
