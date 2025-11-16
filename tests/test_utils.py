"""Tests for utility modules."""

import pytest
import numpy as np
from astraeus.utils.antenna_math import AntennaMath
from astraeus.utils.conversions import Conversions


class TestAntennaMath:
    """Test antenna math utilities."""

    def test_wavelength(self):
        """Test wavelength calculation."""
        # X-band: 10 GHz
        wl = AntennaMath.wavelength(10.0)
        assert abs(wl - 0.02998) < 0.0001  # ~3 cm

    def test_gain_from_aperture(self):
        """Test gain calculation from aperture."""
        # 1 m² aperture at 10 GHz with 60% efficiency
        wl = AntennaMath.wavelength(10.0)
        gain = AntennaMath.gain_from_aperture(1.0, wl, 0.6)
        assert gain > 30  # Should be significant gain

    def test_beamwidth_from_gain(self):
        """Test beamwidth estimation from gain."""
        # High gain should give narrow beamwidth
        bw_az, bw_el = AntennaMath.beamwidth_from_gain(40.0)
        assert bw_az < 5.0  # Narrow beam for 40 dBi
        assert bw_az == bw_el  # Symmetric

    def test_gain_from_beamwidth(self):
        """Test gain estimation from beamwidth."""
        # 3° beam in both planes
        gain = AntennaMath.gain_from_beamwidth(3.0, 3.0)
        assert gain > 30  # Should be high gain

    def test_radar_range(self):
        """Test radar range equation."""
        # Typical radar parameters
        range_km = AntennaMath.radar_range(
            peak_power_w=1000,
            gain_dbi=35,
            wavelength_m=0.03,
            sigma_m2=1.0,
            snr_db=13,
            loss_db=3
        )
        assert range_km > 0  # Should give positive range
        assert range_km < 1000  # Reasonable range

    def test_array_factor(self):
        """Test array factor calculation."""
        theta = np.linspace(-90, 90, 181)
        af = AntennaMath.array_factor(
            theta,
            element_spacing_wavelengths=0.5,
            num_elements=10
        )
        assert np.max(af) == 1.0  # Normalized
        assert len(af) == len(theta)

    def test_vswr_from_reflection(self):
        """Test VSWR calculation."""
        # Perfect match
        vswr = AntennaMath.vswr_from_reflection_coefficient(0 + 0j)
        assert abs(vswr - 1.0) < 0.001

        # Some reflection
        gamma = 0.1 + 0j
        vswr = AntennaMath.vswr_from_reflection_coefficient(gamma)
        assert vswr > 1.0
        assert vswr < 1.5  # Should be reasonable

    def test_directivity_to_gain(self):
        """Test directivity to gain conversion."""
        # 100% efficiency: gain = directivity
        gain = AntennaMath.directivity_to_gain(30.0, 1.0)
        assert abs(gain - 30.0) < 0.001

        # 50% efficiency
        gain = AntennaMath.directivity_to_gain(30.0, 0.5)
        assert gain < 30.0  # Gain should be less


class TestConversions:
    """Test conversion utilities."""

    def test_db_conversions(self):
        """Test dB to linear conversions."""
        # 10 dB = 10x linear
        linear = Conversions.db_to_linear(10.0)
        assert abs(linear - 10.0) < 0.001

        # Inverse
        db = Conversions.linear_to_db(10.0)
        assert abs(db - 10.0) < 0.001

    def test_power_conversions(self):
        """Test power conversions."""
        # 30 dBm = 1 W
        watts = Conversions.dbm_to_watts(30.0)
        assert abs(watts - 1.0) < 0.001

        # Inverse
        dbm = Conversions.watts_to_dbm(1.0)
        assert abs(dbm - 30.0) < 0.001

    def test_frequency_wavelength(self):
        """Test frequency/wavelength conversions."""
        # 10 GHz ≈ 3 cm
        wl = Conversions.freq_to_wavelength(10.0)
        assert abs(wl - 0.02998) < 0.0001

        # Inverse
        freq = Conversions.wavelength_to_freq(0.02998)
        assert abs(freq - 10.0) < 0.001

    def test_angle_conversions(self):
        """Test angle conversions."""
        rad = Conversions.degrees_to_radians(180.0)
        assert abs(rad - np.pi) < 0.001

        deg = Conversions.radians_to_degrees(np.pi)
        assert abs(deg - 180.0) < 0.001

    def test_vswr_return_loss(self):
        """Test VSWR and return loss conversions."""
        # VSWR = 2 → RL ≈ 9.5 dB
        rl = Conversions.vswr_to_return_loss(2.0)
        assert rl > 9.0
        assert rl < 10.0

        # Inverse
        vswr = Conversions.return_loss_to_vswr(rl)
        assert abs(vswr - 2.0) < 0.01

    def test_eirp(self):
        """Test EIRP calculation."""
        eirp = Conversions.eirp(power_dbm=30.0, gain_dbi=35.0)
        assert eirp == 65.0  # Simple addition in dB

    def test_path_loss(self):
        """Test free space path loss."""
        fspl = Conversions.path_loss_free_space(1.0, 10.0)  # 1 km at 10 GHz
        assert fspl > 0  # Should be positive loss

    def test_g_over_t(self):
        """Test G/T calculation."""
        g_t = Conversions.g_over_t(gain_dbi=40.0, system_temp_k=100.0)
        assert g_t > 0  # Should be positive for good antenna


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
