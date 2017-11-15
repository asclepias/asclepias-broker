from setuptools import setup

from asclepias_broker import __version__

setup(version=__version__,
      url="https://github.com/astrofrog/asclepias-toy-broker",
      name="asclepias-broker",
      description='Prototype broker code for the Asclepias project',
      packages=['asclepias_broker'],
      install_requires=['sqlalchemy'],
      license='BSD',
      author='Thomas Robitaille',
      author_email='thomas.robitaille@gmail.com')
