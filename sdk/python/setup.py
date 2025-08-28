#!/usr/bin/env python3

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Signet Protocol - Python Verification SDK"

# Read version from __init__.py
def read_version():
    version_path = os.path.join(os.path.dirname(__file__), 'signet_verify.py')
    with open(version_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"\'')
    return '1.0.0'

setup(
    name='signet-verify',
    version=read_version(),
    description='Signet Protocol - Python Verification SDK',
    long_description=read_readme(),
    long_description_content_type='text/markdown',
    author='ODIN Protocol Corporation',
    author_email='support@odinprotocol.com',
    url='https://github.com/odin-protocol/signet-protocol',
    license='Apache License 2.0',
    
    # Package configuration
    py_modules=['signet_verify'],
    python_requires='>=3.7',
    
    # Dependencies
    install_requires=[
        'cryptography>=3.0.0',
        'requests>=2.25.0',
    ],
    
    # Optional dependencies
    extras_require={
        'dev': [
            'pytest>=6.0.0',
            'pytest-cov>=2.10.0',
            'black>=21.0.0',
            'flake8>=3.8.0',
        ],
        'test': [
            'pytest>=6.0.0',
            'pytest-asyncio>=0.18.0',
        ]
    },
    
    # Classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Security :: Cryptography',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet :: WWW/HTTP',
    ],
    
    # Keywords
    keywords='signet protocol verification cryptography receipts blockchain audit',
    
    # Entry points
    entry_points={
        'console_scripts': [
            'signet-verify=signet_verify:main',
        ],
    },
    
    # Include additional files
    include_package_data=True,
    package_data={
        '': ['*.md', '*.txt', '*.json'],
    },
    
    # Project URLs
    project_urls={
        'Documentation': 'https://github.com/odin-protocol/signet-protocol/docs',
        'Source': 'https://github.com/odin-protocol/signet-protocol',
        'Tracker': 'https://github.com/odin-protocol/signet-protocol/issues',
    },
)
