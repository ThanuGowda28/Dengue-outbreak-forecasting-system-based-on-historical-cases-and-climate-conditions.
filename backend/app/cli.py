import click
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from .extensions import db
from .models import User


@click.group()
def admin():
    """Administrator account maintenance commands."""


@admin.command("promote")
@click.argument("email")
def promote_admin(email):
    """Grant administrator access to an existing account."""
    user = User.query.filter_by(email=email.strip().lower()).first()
    if user is None:
        raise click.ClickException("No account exists with that email address.")
    if user.role == "admin":
        click.echo(f"{user.email} is already an administrator.")
        return
    user.role = "admin"
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not promote administrator account")
        raise click.ClickException("Administrator role could not be updated.")
    click.echo(f"Administrator access granted to {user.email}.")
