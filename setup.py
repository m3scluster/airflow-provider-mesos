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



config = {
    'description': 'Apache Mesos Operator for Apache Airflow',
    'author': 'AVENTER UG (haftungsbeschraenkt)',
    'author_email': 'support@aventer.biz',
    'download_url': 'https://github.com/AVENTER-UG/airflow-mesos-operator',
    'version': '0.1.0',
     'classifiers': [
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        # Indicate who your project is intended for
        'Intended Audience :: Science/Research',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8'
    ],
    'install_requires': [
                         'apache-airflow',
                         'avmesos'

                         ],
    'packages': find_packages(),
    'include_package_data': True,
    'scripts': [],
    'name': 'av-airflow-mesos-operator',
}

setup(**config)
