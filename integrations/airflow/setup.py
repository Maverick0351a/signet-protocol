"""
Setup script for Signet Protocol Airflow Provider
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="signet-airflow-provider",
    version="1.0.0",
    author="ODIN Protocol Corporation",
    author_email="support@odinprotocol.com",
    description="Apache Airflow provider for Signet Protocol verified exchanges",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/odin-protocol/signet-protocol",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: Apache Airflow",
        "Framework :: Apache Airflow :: Provider",
    ],
    python_requires=">=3.8",
    install_requires=[
        "apache-airflow>=2.5.0",
        "requests>=2.25.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
        ],
    },
    entry_points={
        "apache_airflow_provider": [
            "provider_info=signet_provider:get_provider_info"
        ]
    },
    include_package_data=True,
    zip_safe=False,
)
