"""EndBurner and 2D cross-section grains (Finocyl, Star) via Euclidean distance transform.

Uses ``scipy.ndimage.distance_transform_edt`` to compute the exact 2D web
regression map of arbitrary core perforations (like ``openMotor``), pre-tabulating
the core perimeter $P(x)$ and port area $A_p(x)$ at initialization so that
evaluating ``burn_area(x)``, ``port_area(x)`` and ``volume(x)`` during simulation
or inverse-design optimization runs in microseconds via ``numpy.interp``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.ndimage import distance_transform_edt

from propulpy.grains.base import Grain

_FREE_ENDS = {"neither": 2, "top": 1, "bottom": 1, "both": 0}


def _scalar(value):
    arr = np.asarray(value)
    return float(arr) if arr.ndim == 0 else arr


@dataclass
class EndBurner(Grain):
    """Cigarette-burning (end-burning) solid cylindrical grain.

    Burns axially from one uninhibited end face with constant burning area
    ``Ab = pi * D^2 / 4``.

    Parameters
    ----------
    diameter : float
        Grain outer diameter [m].
    length : float
        Initial grain length [m].
    """

    diameter: float
    length: float

    def __post_init__(self):
        if self.diameter <= 0.0:
            raise ValueError("diameter must be positive.")
        if self.length <= 0.0:
            raise ValueError("length must be positive.")

    @property
    def outer_diameter(self) -> float:
        return self.diameter

    @property
    def web_thickness(self) -> float:
        return self.length

    def burn_area(self, x):
        x_arr = np.asarray(x, dtype=float)
        area = math.pi * self.diameter**2 / 4.0
        return _scalar(np.where((x_arr >= 0.0) & (x_arr < self.length), area, 0.0))

    def port_area(self, x):
        x_arr = np.asarray(x, dtype=float)
        area = math.pi * self.diameter**2 / 4.0
        return _scalar(np.full_like(x_arr, area, dtype=float))

    def volume(self, x):
        x_arr = np.clip(np.asarray(x, dtype=float), 0.0, self.length)
        rem_len = self.length - x_arr
        vol = (math.pi * self.diameter**2 / 4.0) * rem_len
        return _scalar(np.where(x_arr < self.length, vol, 0.0))

    def length_at(self, x):
        x_arr = np.clip(np.asarray(x, dtype=float), 0.0, self.length)
        return _scalar(np.where(x_arr < self.length, self.length - x_arr, 0.0))


@dataclass
class CrossSectionGrain2D(Grain):
    """Base class for 2D perforated grains using Euclidean Distance Transform (EDT).

    Subclasses implement ``_build_core_mask(X, Y)`` returning a boolean array
    where ``True`` indicates the initial hollow port/core and ``False`` indicates
    solid propellant.
    """

    diameter: float
    length: float
    inhibited_ends: str = "neither"
    grid_resolution: int = 401
    _x_table: np.ndarray = field(init=False, repr=False)
    _perim_table: np.ndarray = field(init=False, repr=False)
    _prop_area_table: np.ndarray = field(init=False, repr=False)
    _port_area_table: np.ndarray = field(init=False, repr=False)
    _radial_web: float = field(init=False, repr=False)

    def _validate_base(self):
        if self.diameter <= 0.0:
            raise ValueError("diameter must be positive.")
        if self.length <= 0.0:
            raise ValueError("length must be positive.")
        if self.inhibited_ends not in _FREE_ENDS:
            raise ValueError(f"inhibited_ends must be one of {sorted(_FREE_ENDS)}.")

    def _build_core_mask(self, X: np.ndarray, Y: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def _precompute_edt_tables(self):
        r_out = self.diameter / 2.0
        n = int(self.grid_resolution)
        lin = np.linspace(-r_out, r_out, n)
        dx = lin[1] - lin[0]
        cell_area = dx * dx
        X, Y = np.meshgrid(lin, lin)
        R = np.hypot(X, Y)

        inside_casing = R <= r_out
        core_mask = self._build_core_mask(X, Y) & inside_casing
        propellant_mask = inside_casing & (~core_mask)

        # Distance from every propellant pixel to the nearest core pixel [m]
        dist_map = distance_transform_edt(~core_mask) * dx
        prop_dists = dist_map[propellant_mask]
        max_radial_web = float(np.max(prop_dists)) if prop_dists.size > 0 else 0.0
        self._radial_web = max_radial_web

        total_circle_area = math.pi * r_out**2
        if max_radial_web <= 0.0:
            self._x_table = np.array([0.0, 1e-6])
            self._prop_area_table = np.zeros(2)
            self._port_area_table = np.full(2, total_circle_area)
            self._perim_table = np.zeros(2)
            return

        # Choose bin width >= 2.5 * dx to eliminate pixel staircase noise
        n_bins = max(min(int(max_radial_web / (2.5 * dx)), 80), 15)
        edges = np.linspace(0.0, max_radial_web, n_bins + 1)
        counts, _ = np.histogram(prop_dists, bins=edges)
        shell_areas = counts.astype(float) * cell_area
        bin_widths = np.diff(edges)
        shell_perims = shell_areas / bin_widths
        midpoints = 0.5 * (edges[:-1] + edges[1:])

        # Remaining propellant area at each bin edge (from x=0 to x=max_radial_web)
        rem_prop_at_edges = np.concatenate(
            [
                [float(np.sum(shell_areas))],
                np.cumsum(shell_areas[::-1])[::-1][1:],
                [0.0],
            ]
        )
        self._x_table = edges
        self._prop_area_table = rem_prop_at_edges
        self._port_area_table = np.maximum(total_circle_area - rem_prop_at_edges, 0.0)

        # Interpolate/extrapolate perimeter onto bin edges
        perim_at_edges = np.interp(edges, midpoints, shell_perims)
        if len(midpoints) >= 2:
            # Linear extrapolation to x=0 from first two shell midpoints
            slope0 = (shell_perims[1] - shell_perims[0]) / (midpoints[1] - midpoints[0])
            perim_at_edges[0] = max(shell_perims[0] - slope0 * midpoints[0], 0.0)
        perim_at_edges[-1] = 0.0
        self._perim_table = np.maximum(perim_at_edges, 0.0)

    @property
    def free_ends(self) -> int:
        return _FREE_ENDS[self.inhibited_ends]

    @property
    def outer_diameter(self) -> float:
        return self.diameter

    @property
    def web_thickness(self) -> float:
        if self.free_ends == 0:
            return self._radial_web
        return min(self._radial_web, self.length / self.free_ends)

    def _state(self, x):
        x_arr = np.clip(np.asarray(x, dtype=float), 0.0, self.web_thickness)
        rem_length = np.maximum(self.length - self.free_ends * x_arr, 0.0)
        burning = (x_arr < self.web_thickness) & (rem_length > 0.0)
        perim = np.interp(x_arr, self._x_table, self._perim_table, right=0.0)
        a_prop = np.interp(x_arr, self._x_table, self._prop_area_table, right=0.0)
        a_port = np.interp(
            x_arr,
            self._x_table,
            self._port_area_table,
            right=math.pi * self.diameter**2 / 4.0,
        )
        return x_arr, rem_length, burning, perim, a_prop, a_port

    def burn_area(self, x):
        _, rem_length, burning, perim, a_prop, _ = self._state(x)
        lateral = perim * rem_length
        ends = self.free_ends * a_prop
        return _scalar(np.where(burning, lateral + ends, 0.0))

    def port_area(self, x):
        _, _, burning, _, _, a_port = self._state(x)
        full_area = math.pi * self.diameter**2 / 4.0
        return _scalar(np.where(burning, a_port, full_area))

    def volume(self, x):
        _, rem_length, burning, _, a_prop, _ = self._state(x)
        return _scalar(np.where(burning, a_prop * rem_length, 0.0))

    def length_at(self, x):
        _, rem_length, burning, _, _, _ = self._state(x)
        return _scalar(np.where(burning, rem_length, 0.0))


@dataclass
class Finocyl(CrossSectionGrain2D):
    """Finned cylindrical (Finocyl) grain segment.

    Parameters
    ----------
    diameter : float
        Grain outer diameter [m].
    core_diameter : float
        Central circular port diameter [m].
    fin_length : float
        Radial tip diameter (or radial extent from center: ``fin_tip_diameter / 2``)
        measured as total tip-to-tip diameter across opposing fins [m], or radial
        fin span from center if ``fin_length < diameter / 2``. Specifically, a fin
        extends from the center out to radius ``r_fin = core_diameter / 2 + fin_length``.
    fin_width : float
        Width (thickness) of each radial fin slot [m].
    num_fins : int
        Number of radial fins [-].
    length : float
        Initial grain segment length [m].
    inhibited_ends : {"neither", "top", "bottom", "both"}, optional
        Which end faces are inhibited. Default ``"neither"``.
    """

    core_diameter: float = 0.01
    fin_length: float = 0.005
    fin_width: float = 0.002
    num_fins: int = 6

    def __post_init__(self):
        self._validate_base()
        if not 0.0 < self.core_diameter < self.diameter:
            raise ValueError("Require 0 < core_diameter < diameter.")
        if self.num_fins < 1:
            raise ValueError("num_fins must be >= 1.")
        if self.fin_length <= 0 or self.fin_width <= 0:
            raise ValueError("fin_length and fin_width must be positive.")
        self._precompute_edt_tables()

    def _build_core_mask(self, X: np.ndarray, Y: np.ndarray) -> np.ndarray:
        r_core = self.core_diameter / 2.0
        r_tip = min(r_core + self.fin_length, self.diameter / 2.0 * 0.98)
        mask = np.hypot(X, Y) <= r_core
        half_w = self.fin_width / 2.0
        for k in range(self.num_fins):
            angle = 2.0 * math.pi * k / self.num_fins
            ca, sa = math.cos(angle), math.sin(angle)
            # Coordinates along and perpendicular to fin k
            u = X * ca + Y * sa
            v = -X * sa + Y * ca
            fin_k = (u >= 0.0) & (u <= r_tip) & (np.abs(v) <= half_w)
            mask = mask | fin_k
        return mask


@dataclass
class Star(CrossSectionGrain2D):
    """Star-perforated grain segment.

    Parameters
    ----------
    diameter : float
        Grain outer diameter [m].
    inner_diameter : float
        Inner star valley diameter [m].
    point_diameter : float
        Outer star point tip-to-tip diameter [m].
    num_points : int
        Number of star points [-].
    length : float
        Initial grain segment length [m].
    inhibited_ends : {"neither", "top", "bottom", "both"}, optional
        Which end faces are inhibited. Default ``"neither"``.
    """

    inner_diameter: float = 0.010
    point_diameter: float = 0.024
    num_points: int = 5

    def __post_init__(self):
        self._validate_base()
        if not 0.0 < self.inner_diameter < self.point_diameter < self.diameter:
            raise ValueError("Require 0 < inner_diameter < point_diameter < diameter.")
        if self.num_points < 3:
            raise ValueError("num_points must be >= 3.")
        self._precompute_edt_tables()

    def _build_core_mask(self, X: np.ndarray, Y: np.ndarray) -> np.ndarray:
        r_in = self.inner_diameter / 2.0
        r_pt = self.point_diameter / 2.0
        n_verts = 2 * self.num_points
        angles = np.linspace(0.0, 2.0 * math.pi, n_verts, endpoint=False)
        radii = np.where(np.arange(n_verts) % 2 == 0, r_pt, r_in)
        vx = radii * np.cos(angles)
        vy = radii * np.sin(angles)

        # Ray-casting point-in-polygon vectorized over (X, Y)
        inside = np.zeros(X.shape, dtype=bool)
        j = n_verts - 1
        for i in range(n_verts):
            yi, yj = vy[i], vy[j]
            xi, xj = vx[i], vx[j]
            cond = (yi > Y) != (yj > Y)
            x_intersect = (xj - xi) * (Y - yi) / ((yj - yi) + 1e-30) + xi
            inside ^= cond & (X < x_intersect)
            j = i
        return inside
