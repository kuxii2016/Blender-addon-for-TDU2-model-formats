# Setup script for TDU2 Blender addon

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="tdu2-blender-addon",
    version="1.0.0",
    author="KuxiiSoft",
    description="Blender addon for importing/exporting TDU2 model formats (.3DG/.3DD, .2DM, .2DB)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        # Add any required Python packages here
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Graphics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
)