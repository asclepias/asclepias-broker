from setuptools import setup

from asclepias_broker import __version__

tests_require = ['pytest', 'pytest-cov', 'sqltap', ]
install_requires = [
    'faker',
    'flask',
    'flask-debugtoolbar',
    'flask-shell-ipython',
    'idutils',
    'jsonschema',
    'elasticsearch>=5.0.0,<6.0.0',
    'elasticsearch-dsl>=5.0.0,<6.0.0',
    'marshmallow',
    'sqlalchemy_utils',
    'sqlalchemy',
    'arrow',
]
extras_require = {
    'postgres': ['psycopg2', ],
    'tests': tests_require,
}
extras_require['all'] = sum((v for k, v in extras_require.items()), [])

setup(version=__version__,
      url="https://github.com/asclepias/asclepias-broker",
      name="asclepias-broker",
      description='Prototype broker code for the Asclepias project',
      packages=['asclepias_broker'],
      extras_require=extras_require,
      tests_require=tests_require,
      install_requires=install_requires,
      license='BSD',
      author='Thomas Robitaille',
      author_email='thomas.robitaille@gmail.com')
