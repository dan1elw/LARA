from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="lara",
    version="v0.1.1",
    author="Daniel Weber",
    author_email="dadanielweber@googlemail.com",
    description="Local Air Route Analysis - Track and analyze flights over your location",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dan1elw/LARA",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: GIS",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "pyyaml>=6.0",
        "folium>=0.15.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "lara-collect=scripts.collect:main",
            "lara-read=scripts.read:main",
        ],
    },
)
