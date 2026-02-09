"""HIE - Healthcare Integration Engine setup."""

from setuptools import setup, find_packages

setup(
    name="hie",
    version="1.0.0",
    description="Healthcare Integration Engine",
    author="HIE Team",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "aiohttp>=3.9.0",
        "pydantic>=2.5.0",
        "structlog>=23.2.0",
        "msgpack>=1.0.7",
        "click>=8.1.7",
        "pyyaml>=6.0.1",
        "asyncpg>=0.29.0",
        "redis>=5.0.0",
        "aiofiles>=23.2.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.12.0",
            "ruff>=0.1.8",
            "mypy>=1.7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "hie=Engine.cli:main",
        ],
    },
)
