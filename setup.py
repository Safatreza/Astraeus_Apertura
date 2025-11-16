"""Setup configuration for Astraeus Apertura."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    with open(requirements_path) as f:
        requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]

setup(
    name="astraeus-apertura",
    version="0.1.0",
    author="Astraeus Development Team",
    author_email="",
    description="Multi-Agent Autonomous Radar and Antenna Design System",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Safatreza/Astraeus_Apertura",
    packages=find_packages(exclude=["tests", "examples", "docs"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.3.0",
            "pytest-cov>=4.1.0",
            "black>=23.3.0",
            "flake8>=6.0.0",
            "mypy>=1.3.0",
        ],
        "docs": [
            "sphinx>=6.2.0",
            "sphinx-rtd-theme>=1.2.0",
        ],
        "simulation": [
            # "openems-python>=0.0.1",
            # "pyaedt>=0.6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "astraeus=astraeus.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
