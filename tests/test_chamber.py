import pytest

from propulpy.chamber import Chamber


def test_chamber_basic_properties():
    c = Chamber(inner_diameter=42e-3, length=0.20)
    assert c.wall_thickness is None
    assert c.burst_pressure() is None
    assert c.safety_factor(40e5) is None
    assert c.internal_volume == pytest.approx(3.14159265 / 4 * 0.042**2 * 0.20)


def test_chamber_structural_burst_and_safety_factor():
    # 6061-T6 aluminum tube: ID 42 mm, OD 46 mm (wall thickness 2 mm), yield strength 276 MPa
    c = Chamber(
        inner_diameter=42e-3,
        length=0.20,
        outer_diameter=46e-3,
        yield_strength=276e6,
    )
    assert c.wall_thickness == pytest.approx(2e-3)
    p_burst = c.burst_pressure()
    # Barlow formula: 2 * 276e6 * 2e-3 / 46e-3 = 24.0 MPa (240 bar)
    assert p_burst == pytest.approx(24.0e6, rel=1e-3)
    sf = c.safety_factor(40e5)  # 40 bar operating pressure
    assert sf == pytest.approx(6.0, rel=1e-3)


def test_invalid_chamber_dimensions():
    with pytest.raises(ValueError):
        Chamber(inner_diameter=45e-3, length=0.2, outer_diameter=40e-3)
    with pytest.raises(ValueError):
        Chamber(inner_diameter=-0.01, length=0.2)
