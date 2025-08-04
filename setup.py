try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

from distutils.command.install import install
import os
import json

here = os.path.abspath(os.path.dirname(__file__))
try:
    with open(os.path.join(here, "README.md")) as f:
        README = f.read()
except UnicodeDecodeError:
    with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
        README = f.read()

setup(
    name="avmesos_airflow_provider",
    version="0.3.0",
    description="Apache Mesos Provider",
    long_description=README,
    long_description_content_type="text/markdown",
    license="Apache License 2.0",
    packages=find_packages(),
    install_requires=["apache-airflow>=2.0", "avmesos>=0.4.2", "waitress", "flask_httpauth", "prometheus-client"],
    setup_requires=["avmesos>=0.4.2", "waitress", "flask_httpauth", "prometheus-client"],
    author="Andreas Peters",
    author_email="support@aventer.biz",
    url="https://www.aventer.biz/",
    python_requires=">=3.6",
)
