from setuptools import setup, find_packages

setup(
    name="aws-automations",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "boto3>=1.29,<2.0",
        "PyYAML>=6.0,<7.0",
        "rich>=13.7,<14.0",
    ],
    entry_points={
        "console_scripts": [
            "aws-cleanup=aws_automations.main:main",
            "aws-menu=aws_automations.menu:interactive_menu",
        ],
    },
    python_requires=">=3.8",
)
