# Installation

## From PyPI

The simplest way to install pybaseflow is from the Python Package Index:

```bash
pip install pybaseflow
```

This will install pybaseflow along with its required dependencies: **numpy**, **numba**, and **pandas**. These are pulled in automatically by pip, so no extra steps are needed for a working installation.

pybaseflow requires **Python 3.9 or later**. It is tested on Python 3.9 through 3.13.

## Optional dependencies

**matplotlib** is not installed automatically but is needed if you want to plot hydrographs or baseflow results. You can install it separately:

```bash
pip install matplotlib
```

## Development install

If you want to contribute to pybaseflow or run its test suite, clone the repository and install in editable mode with the development extras:

```bash
git clone https://github.com/ciroh-ua/pybaseflow.git
cd pybaseflow
pip install -e ".[dev]"
```

The `[dev]` extra installs **pytest** and **matplotlib** in addition to the core dependencies, giving you everything needed to run the tests and generate figures.

## A note about Numba

pybaseflow uses [Numba](https://numba.pydata.org/) to JIT-compile several performance-critical inner loops (HYSEP interval methods, UKIH turning-point detection, and the BFlow filter). The first time you import pybaseflow -- or the first time you call a Numba-accelerated function with a new argument signature -- you may notice a pause of a few seconds while Numba compiles the relevant functions to machine code. This is a one-time cost per Python session; subsequent calls to the same function will execute at compiled speed. Numba caches its compiled output on disk, so even across sessions the compilation overhead is typically only incurred once after installation or after a pybaseflow version upgrade.
