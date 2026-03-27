"""
Setup configuration for hermes-autoresearch.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("SKILL.md", "r", encoding="utf-8") as fh:
    long_description += "\n\n"
    long_description += fh.read()

setup(
    name="hermes-autoresearch",
    version="1.0.5",
    author="Joy Boy",
    author_email="hermes@vugru.com",
    description="Autonomous experiment loop for Hermes skills",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/joyboy257/hermes-autoresearch",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Testing",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.10",
    install_requires=[
        # No external dependencies - uses stdlib only
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "mypy>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "hermes-autoresearch=hermes_autoresearch.commands:cli_main",
        ],
    },
    package_data={
        "hermes_autoresearch": ["py.typed"],
    },
    include_package_data=True,
    zip_safe=False,
)
