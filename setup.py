#!/usr/bin/env python

from setuptools import find_packages, setup

setup(
    name='swaggertosdk',
    version='0.1',
    description='Swagger to SDK tools for Microsoft',
    license='MIT License',
    author='Microsoft Corporation',
    author_email='azpysdkhelp@microsoft.com',
    url='https://github.com/lmazuel/swagger-to-sdk',
    packages=find_packages(exclude=["tests"]),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: MIT License',
    ],
    install_requires=[
        "PyGithub>=1.34", # Compatible with 3.6 after 1.34
        "GitPython",
        "requests",
        "mistune",
        "pyyaml",
        "cookiecutter",
        "wheel"
    ],
    extras_require={
        'rest': [
            'flask',
            'json-rpc'
        ]
    }
)