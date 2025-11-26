from setuptools import setup, find_packages

setup(
    name="gitflow",
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
            "gitflow=gitflow.app:app",
        ],
    },
)
