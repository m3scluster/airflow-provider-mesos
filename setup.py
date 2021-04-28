try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

from distutils.command.install import install
import os

here = os.path.abspath(os.path.dirname(__file__))
try:
    with open(os.path.join(here, 'README.md')) as f:
        README = f.read()
    with open(os.path.join(here, 'CHANGES.txt')) as f:
        CHANGES = f.read()
except UnicodeDecodeError:
    with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        README = f.read()
    with open(os.path.join(here, 'CHANGES.txt'), encoding='utf-8') as f:
        CHANGES = f.read()

setup(
    name='airflow-provider-mesos',
    version="0.1.2",
    description='Apache Mesos Provider',
    long_description=README,
    long_description_content_type='text/markdown',
    entry_points={
        "apache_airflow_provider": [
            "provider_info=mesos_provider.__init__:get_provider_info"
        ]
    },
    license='Apache License 2.0',
    packages=['mesos_provider'],
    install_requires=['apache-airflow>=2.0'],
    setup_requires=['avmesos'],
    author='Andreas Peters',
    author_email='support@aventer.biz',
    url='https://www.aventer.biz/',
    python_requires='~=3.8',
)

