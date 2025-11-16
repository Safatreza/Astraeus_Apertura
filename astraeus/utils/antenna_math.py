"""Mathematical functions for antenna design calculations."""

import numpy as np
from typing import Tuple, Optional


class AntennaMath:
    """
    Collection of antenna design mathematical functions.

    Provides analytical calculations for:
    - Gain and directivity
    - Beamwidth estimation
    - Radar range calculations
    - Array factors
    - Impedance matching
    """

    @staticmethod
    def wavelength(frequency_ghz: float) -> float:
        """
        Calculate wavelength from frequency.

        Args:
            frequency_ghz: Frequency in GHz

        Returns:
            Wavelength in meters
        """
        c = 2.998e8  # Speed of light m/s
        return c / (frequency_ghz * 1e9)

    @staticmethod
    def gain_from_aperture(
        aperture_area_m2: float,
        wavelength_m: float,
        efficiency: float = 0.6
    ) -> float:
        """
        Calculate gain from physical aperture area.

        Args:
            aperture_area_m2: Aperture area in square meters
            wavelength_m: Wavelength in meters
            efficiency: Aperture efficiency (0 to 1)

        Returns:
            Gain in dBi
        """
        gain_linear = (4 * np.pi * efficiency * aperture_area_m2) / (wavelength_m ** 2)
        return 10 * np.log10(gain_linear)

    @staticmethod
    def aperture_from_gain(
        gain_dbi: float,
        wavelength_m: float,
        efficiency: float = 0.6
    ) -> float:
        """
        Calculate required aperture area from desired gain.

        Args:
            gain_dbi: Gain in dBi
            wavelength_m: Wavelength in meters
            efficiency: Aperture efficiency (0 to 1)

        Returns:
            Required aperture area in square meters
        """
        gain_linear = 10 ** (gain_dbi / 10)
        return (gain_linear * wavelength_m ** 2) / (4 * np.pi * efficiency)

    @staticmethod
    def beamwidth_from_gain(gain_dbi: float) -> Tuple[float, float]:
        """
        Estimate beamwidth from gain (assuming pencil beam).

        Args:
            gain_dbi: Gain in dBi

        Returns:
            Tuple of (azimuth_beamwidth_deg, elevation_beamwidth_deg)
        """
        gain_linear = 10 ** (gain_dbi / 10)

        # Approximate formula: G ≈ 41253 / (θ_az * θ_el)
        beamwidth_sq = 41253 / gain_linear
        beamwidth = np.sqrt(beamwidth_sq)

        return (beamwidth, beamwidth)

    @staticmethod
    def gain_from_beamwidth(
        beamwidth_az_deg: float,
        beamwidth_el_deg: float
    ) -> float:
        """
        Estimate gain from beamwidth.

        Args:
            beamwidth_az_deg: Azimuth beamwidth in degrees
            beamwidth_el_deg: Elevation beamwidth in degrees

        Returns:
            Estimated gain in dBi
        """
        gain_linear = 41253 / (beamwidth_az_deg * beamwidth_el_deg)
        return 10 * np.log10(gain_linear)

    @staticmethod
    def radar_range(
        peak_power_w: float,
        gain_dbi: float,
        wavelength_m: float,
        sigma_m2: float,
        snr_db: float = 13.0,
        loss_db: float = 3.0
    ) -> float:
        """
        Calculate radar detection range using radar equation.

        Args:
            peak_power_w: Peak transmit power in watts
            gain_dbi: Antenna gain in dBi
            wavelength_m: Wavelength in meters
            sigma_m2: Target radar cross-section in square meters
            snr_db: Required signal-to-noise ratio in dB
            loss_db: System losses in dB

        Returns:
            Maximum detection range in kilometers
        """
        # Convert to linear
        gain = 10 ** (gain_dbi / 10)
        snr = 10 ** (snr_db / 10)
        loss = 10 ** (loss_db / 10)

        # Radar equation: R^4 = (Pt * G^2 * λ^2 * σ) / ((4π)^3 * SNR * L)
        k_boltzmann = 1.38e-23
        T_system = 290  # System temperature in K (typical)
        bandwidth = 1e6  # 1 MHz bandwidth (typical)

        noise_power = k_boltzmann * T_system * bandwidth

        numerator = peak_power_w * (gain ** 2) * (wavelength_m ** 2) * sigma_m2
        denominator = ((4 * np.pi) ** 3) * snr * noise_power * loss

        range_m = (numerator / denominator) ** 0.25

        return range_m / 1000  # Convert to km

    @staticmethod
    def array_factor(
        theta_deg: np.ndarray,
        element_spacing_wavelengths: float,
        num_elements: int,
        amplitude_taper: Optional[np.ndarray] = None,
        phase_taper: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Calculate array factor for linear array.

        Args:
            theta_deg: Angle array in degrees
            element_spacing_wavelengths: Element spacing in wavelengths
            num_elements: Number of array elements
            amplitude_taper: Amplitude weights (uniform if None)
            phase_taper: Phase weights in radians (0 if None)

        Returns:
            Normalized array factor
        """
        theta_rad = np.deg2rad(theta_deg)
        k = 2 * np.pi  # Wave number in units of 1/wavelength

        # Default uniform amplitude and phase
        if amplitude_taper is None:
            amplitude_taper = np.ones(num_elements)
        if phase_taper is None:
            phase_taper = np.zeros(num_elements)

        # Element positions
        element_positions = np.arange(num_elements) * element_spacing_wavelengths

        # Calculate array factor
        af = np.zeros_like(theta_rad, dtype=complex)

        for n, (amp, phase, pos) in enumerate(zip(amplitude_taper, phase_taper, element_positions)):
            af += amp * np.exp(1j * (k * pos * np.sin(theta_rad) + phase))

        # Normalize
        af = np.abs(af) / np.max(np.abs(af))

        return af

    @staticmethod
    def vswr_from_reflection_coefficient(gamma: complex) -> float:
        """
        Calculate VSWR from reflection coefficient.

        Args:
            gamma: Complex reflection coefficient

        Returns:
            VSWR
        """
        mag_gamma = np.abs(gamma)
        return (1 + mag_gamma) / (1 - mag_gamma)

    @staticmethod
    def reflection_coefficient(z_load: complex, z0: float = 50.0) -> complex:
        """
        Calculate reflection coefficient.

        Args:
            z_load: Load impedance (complex)
            z0: Characteristic impedance (typically 50 Ω)

        Returns:
            Complex reflection coefficient
        """
        return (z_load - z0) / (z_load + z0)

    @staticmethod
    def directivity_to_gain(directivity_dbi: float, efficiency: float) -> float:
        """
        Convert directivity to gain using efficiency.

        Args:
            directivity_dbi: Directivity in dBi
            efficiency: Radiation efficiency (0 to 1)

        Returns:
            Gain in dBi
        """
        directivity_linear = 10 ** (directivity_dbi / 10)
        gain_linear = directivity_linear * efficiency
        return 10 * np.log10(gain_linear)

    @staticmethod
    def friis_transmission(
        pt_dbm: float,
        gt_dbi: float,
        gr_dbi: float,
        distance_km: float,
        frequency_ghz: float
    ) -> float:
        """
        Calculate received power using Friis transmission equation.

        Args:
            pt_dbm: Transmit power in dBm
            gt_dbi: Transmit antenna gain in dBi
            gr_dbi: Receive antenna gain in dBi
            distance_km: Distance in kilometers
            frequency_ghz: Frequency in GHz

        Returns:
            Received power in dBm
        """
        # Convert to linear
        pt_w = 10 ** ((pt_dbm - 30) / 10)
        gt = 10 ** (gt_dbi / 10)
        gr = 10 ** (gr_dbi / 10)

        # Wavelength
        wavelength_m = AntennaMath.wavelength(frequency_ghz)

        # Free space path loss
        distance_m = distance_km * 1000
        fspl = (4 * np.pi * distance_m / wavelength_m) ** 2

        # Received power
        pr_w = pt_w * gt * gr / fspl

        # Convert to dBm
        pr_dbm = 10 * np.log10(pr_w) + 30

        return pr_dbm
