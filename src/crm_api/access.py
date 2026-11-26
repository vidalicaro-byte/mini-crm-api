"""Who may see what. Admins see everything; sellers only the contacts and deals they own.

Companies are visible to everyone. Records a user may not see are reported as missing (404), so
the API doesn't reveal that they exist.
"""

from sqlalchemy import ColumnElement, true

from crm_api.models import Contact, Deal, User, UserRole


def can_see_everything(user: User) -> bool:
    return user.role is UserRole.ADMIN


def visible_contacts(user: User) -> ColumnElement[bool]:
    return true() if can_see_everything(user) else Contact.owner_id == user.id


def visible_deals(user: User) -> ColumnElement[bool]:
    return true() if can_see_everything(user) else Deal.owner_id == user.id
