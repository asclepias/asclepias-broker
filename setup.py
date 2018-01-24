from setuptools import setup

from asclepias_broker import __version__

tests_require = ['pytest']
install_requires = [
    'flask',
    'jsonschema',
    'psycopg2',
    'sqlalchemy_utils',
    'sqlalchemy',
]
extras_require = {
    'postgres': ['psycopg2'],
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
