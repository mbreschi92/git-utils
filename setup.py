from setuptools import setup, find_packages

setup(
    name="gatp",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "typer",
        "GitPython",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "gatp=gatp.app:app",
        ],
    },
)
