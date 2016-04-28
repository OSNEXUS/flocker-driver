from setuptools import setup, find_packages
from os import path

setup(
    name='osnexus_flocker_driver',
    version='1.0',
    description='OSNEXUS Quantastor Plugin for ClusterHQ/Flocker ',
    license='Apache 2.0',
    url='https://github.com/OSNEXUS/osnexus-flocker-driver',

    classifiers=[
    'Development Status :: Beta',

    'Intended Audience :: System Administrators',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Libraries :: Python Modules',

     #Python versions supported
    'Programming Language :: Python :: 2.7',
    ],

    keywords='backend, plugin, osnexus, flocker, docker, python',
    packages=find_packages(exclude=[''])
)
