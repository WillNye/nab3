from setuptools import find_namespace_packages, setup

setup(
    name='nab3',
    version='0.1.2',
    description='Easily inspect AWS resources',
    long_description='Easily inspect AWS resources',
    url='https://github.com/WillNye/nab3',
    python_requires='>=3.7',
    install_requires=[
        'boto3<2.0.0',
        'double-click<1.0.0',
    ],
    packages=find_namespace_packages(include=['nab3', 'nab3.*']),
    package_data={'': ['*.md']},
    include_package_data=True,
    author='Will Beasley',
    author_email='willbeas88@gmail.com',
    classifiers=[
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries'
    ]
)
