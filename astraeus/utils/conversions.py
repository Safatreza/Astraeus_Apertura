"""Unit conversion utilities."""

import numpy as np


class Conversions:
    """
    Unit conversion utilities for antenna design.

    Handles conversions between different unit systems commonly
    used in antenna and RF engineering.
    """

    # Physical constants
    C_LIGHT_M_PER_S = 2.998e8  # Speed of light
    K_BOLTZMANN = 1.38e-23  # Boltzmann constant

    @staticmethod
    def db_to_linear(db_value: float) -> float:
        """Convert dB to linear scale."""
        return 10 ** (db_value / 10)

    @staticmethod
    def linear_to_db(linear_value: float) -> float:
        """Convert linear to dB scale."""
        return 10 * np.log10(linear_value)

    @staticmethod
    def dbm_to_watts(dbm: float) -> float:
        """Convert dBm to watts."""
        return 10 ** ((dbm - 30) / 10)

    @staticmethod
    def watts_to_dbm(watts: float) -> float:
        """Convert watts to dBm."""
        return 10 * np.log10(watts) + 30

    @staticmethod
    def freq_to_wavelength(frequency_ghz: float) -> float:
        """Convert frequency (GHz) to wavelength (meters)."""
        return Conversions.C_LIGHT_M_PER_S / (frequency_ghz * 1e9)

    @staticmethod
    def wavelength_to_freq(wavelength_m: float) -> float:
        """Convert wavelength (meters) to frequency (GHz)."""
        return (Conversions.C_LIGHT_M_PER_S / wavelength_m) / 1e9

    @staticmethod
    def degrees_to_radians(degrees: float) -> float:
        """Convert degrees to radians."""
        return np.deg2rad(degrees)

    @staticmethod
    def radians_to_degrees(radians: float) -> float:
        """Convert radians to degrees."""
        return np.rad2deg(radians)

    @staticmethod
    def return_loss_to_vswr(return_loss_db: float) -> float:
        """Convert return loss (dB) to VSWR."""
        gamma = 10 ** (-abs(return_loss_db) / 20)
        return (1 + gamma) / (1 - gamma)

    @staticmethod
    def vswr_to_return_loss(vswr: float) -> float:
        """Convert VSWR to return loss (dB)."""
        if vswr < 1:
            raise ValueError("VSWR must be >= 1")
        gamma = (vswr - 1) / (vswr + 1)
        return -20 * np.log10(gamma)

    @staticmethod
    def noise_figure_to_temperature(nf_db: float, t0_k: float = 290) -> float:
        """
        Convert noise figure (dB) to noise temperature (K).

        Args:
            nf_db: Noise figure in dB
            t0_k: Reference temperature (default 290 K)

        Returns:
            Noise temperature in Kelvin
        """
        nf_linear = 10 ** (nf_db / 10)
        return t0_k * (nf_linear - 1)

    @staticmethod
    def temperature_to_noise_figure(te_k: float, t0_k: float = 290) -> float:
        """
        Convert noise temperature (K) to noise figure (dB).

        Args:
            te_k: Noise temperature in Kelvin
            t0_k: Reference temperature (default 290 K)

        Returns:
            Noise figure in dB
        """
        nf_linear = 1 + (te_k / t0_k)
        return 10 * np.log10(nf_linear)

    @staticmethod
    def eirp(power_dbm: float, gain_dbi: float) -> float:
        """
        Calculate Effective Isotropic Radiated Power.

        Args:
            power_dbm: Transmit power in dBm
            gain_dbi: Antenna gain in dBi

        Returns:
            EIRP in dBm
        """
        return power_dbm + gain_dbi

    @staticmethod
    def path_loss_free_space(distance_km: float, frequency_ghz: float) -> float:
        """
        Calculate free space path loss.

        Args:
            distance_km: Distance in kilometers
            frequency_ghz: Frequency in GHz

        Returns:
            Path loss in dB
        """
        distance_m = distance_km * 1000
        wavelength_m = Conversions.freq_to_wavelength(frequency_ghz)
        fspl_linear = (4 * np.pi * distance_m / wavelength_m) ** 2
        return 10 * np.log10(fspl_linear)

    @staticmethod
    def g_over_t(gain_dbi: float, system_temp_k: float) -> float:
        """
        Calculate G/T (gain-to-noise-temperature ratio).

        Args:
            gain_dbi: Antenna gain in dBi
            system_temp_k: System noise temperature in Kelvin

        Returns:
            G/T in dB/K
        """
        return gain_dbi - 10 * np.log10(system_temp_k)
