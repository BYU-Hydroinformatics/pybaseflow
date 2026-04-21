# Installation

## From PyPI

The simplest way to install baseflowx is from the Python Package Index:

```bash
pip install baseflowx
```

This will install baseflowx along with its required dependencies: **numpy** and **pandas**. These are pulled in automatically by pip, so no extra steps are needed for a working installation.

baseflowx requires **Python 3.9 or later**. It is tested on Python 3.9 through 3.13.

## Optional dependencies

**matplotlib** is not installed automatically but is needed if you want to plot hydrographs or baseflow results. You can install it separately:

```bash
pip install matplotlib
```

## Development install

If you want to contribute to baseflowx or run its test suite, clone the repository and install in editable mode with the development extras:

```bash
git clone https://github.com/njones61/baseflowx.git
cd baseflowx
pip install -e ".[dev]"
```

The `[dev]` extra installs **pytest** and **matplotlib** in addition to the core dependencies, giving you everything needed to run the tests and generate figures.
