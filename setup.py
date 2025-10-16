"""Setup configuration for dagster_pipeline package"""

from setuptools import setup, find_packages

setup(
    name="dagster-pipeline",
    version="0.1.0",
    description="Dagster ETL pipeline for Google Drive data processing",
    author="Juan Wills",
    packages=find_packages(include=["dagster_pipeline", "dagster_pipeline.*", "config"]),
    python_requires=">=3.13",
    install_requires=[
        "duckdb>=1.4.1",
        "numpy>=2.3.3",
        "pandas>=2.3.3",
    ],
    extras_require={
        "dagster": [
            "dagster>=1.11.14",
            "dagster-docker>=0.27.14",
            "dagster-postgres>=0.27.14",
        ],
        "google-api": [
            "google-api-python-client>=2.184.0",
            "google-auth-httplib2>=0.2.0",
            "google-auth-oauthlib>=1.2.2",
        ],
        "dev": [
            "black>=25.9.0",
            "pytest>=8.4.2",
        ],
    },
    entry_points={
        "console_scripts": [
            "dagster-pipeline-check=scripts.setup_check:main",
        ],
    },
)
