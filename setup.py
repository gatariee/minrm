from setuptools import setup, find_packages

setup(
    name="minrm",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["pypsrp"],
    entry_points={
        "console_scripts": [
            "minrm = minrm.minrm:main"
        ]
    },
)
