from setuptools import setup

from asclepias_broker import __version__

tests_require = ['pytest', 'jsonschema']
install_requires = ['sqlalchemy', 'sqlalchemy_utils', 'jsonschema']
extras_require = {
    'tests': tests_require,
}

setup(version=__version__,
      url="https://github.com/astrofrog/asclepias-toy-broker",
      name="asclepias-broker",
      description='Prototype broker code for the Asclepias project',
      packages=['asclepias_broker'],
      extras_require=extras_require,
      tests_require=tests_require,
      install_requires=install_requires,
      license='BSD',
      author='Thomas Robitaille',
      author_email='thomas.robitaille@gmail.com')
