"""Setup for kad package."""

from setuptools import setup, find_packages

version = '0.1'

test_require = [
    'flake8',
    'pytest',
    'pytest-cov',
    'pytest-env',
    'pytest-flask==0.11.0',
    'pytest-ordering',
]

setup(
    name='kad',
    version=version,
    description='Kubernetes application demo',
    author='Tomáš Kukrál',
    author_email='tomas.kukral@prgcont.cz',
    license='MIT',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'Flask',
        'prometheus_client',
        'redis'
    ],
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=test_require,
    extras_require={
        'test': test_require,
        'dev': test_require + [
            'ipython',
        ]
    },
    classifiers=[
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    entry_points={
        'console_scripts': [
            'kad = kad.server:run',
        ],
    },
)
