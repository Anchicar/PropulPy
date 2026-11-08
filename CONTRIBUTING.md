# Contributing to PropulPy

¡Gracias por contribuir! / Thanks for contributing!

## Setup

```bash
pip install -e ".[dev]"
pre-commit install
pytest
```

## Rules

1. **SI units internally.** Convert only at the boundaries (`propulpy.units`).
2. **Code, identifiers and docstrings in English** (NumPy docstring style). Docs and discussions may be in Spanish or English.
3. **Every physical model needs a test**: an analytic solution, a cross-check against openMotor/CEA, or real test data. Cite the source of every constant and propellant property.
4. **No hard-coded ambient conditions.** Use `AmbientConditions` (fixed value or `rocketpy.Environment`).
5. Keep the forward model fast and side-effect free — the inverse-design layer calls it thousands of times.
6. Run `ruff check .` and `ruff format .` before opening a PR.

## Branches

- `main`: always passing CI.
- Feature branches: `feat/<topic>`, fixes: `fix/<topic>`.
