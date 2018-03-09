import click
from flask.cli import FlaskGroup
from .app import create_app


@click.group(cls=FlaskGroup, create_app=lambda _: create_app())
def cli():
    """CLI for Asclepias Broker"""
    pass


if __name__ == '__main__':
    cli()
