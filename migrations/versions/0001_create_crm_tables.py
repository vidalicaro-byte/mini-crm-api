"""create crm tables

Revision ID: 0001
Revises:
Create Date: 2026-11-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "companies",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("industry", sa.String(length=80), nullable=False),
        sa.Column(
            "size",
            sa.Enum(
                "pequena",
                "media",
                "grande",
                name="company_size",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("website", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_companies")),
    )
    with op.batch_alter_table("companies", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_companies_name"), ["name"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "admin",
                "vendedor",
                name="user_role",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "contacts",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("job_title", sa.String(length=80), nullable=False),
        sa.Column("company_id", sa.String(length=40), nullable=False),
        sa.Column("owner_id", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], name=op.f("fk_contacts_company_id_companies")
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_contacts_owner_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contacts")),
        sa.UniqueConstraint("email", name=op.f("uq_contacts_email")),
    )
    with op.batch_alter_table("contacts", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_contacts_company_id"), ["company_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_contacts_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_contacts_name"), ["name"], unique=False)
        batch_op.create_index(batch_op.f("ix_contacts_owner_id"), ["owner_id"], unique=False)

    op.create_table(
        "deals",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column(
            "stage",
            sa.Enum(
                "novo",
                "contato",
                "proposta",
                "negociacao",
                "ganho",
                "perdido",
                name="deal_stage",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("contact_id", sa.String(length=40), nullable=False),
        sa.Column("company_id", sa.String(length=40), nullable=False),
        sa.Column("owner_id", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expected_close_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], name=op.f("fk_deals_company_id_companies")
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"], ["contacts.id"], name=op.f("fk_deals_contact_id_contacts")
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name=op.f("fk_deals_owner_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deals")),
    )
    with op.batch_alter_table("deals", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_deals_company_id"), ["company_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_deals_contact_id"), ["contact_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_deals_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_deals_owner_id"), ["owner_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_deals_stage"), ["stage"], unique=False)

    op.create_table(
        "activities",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "call",
                "email",
                "meeting",
                "note",
                name="activity_type",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("contact_id", sa.String(length=40), nullable=False),
        sa.Column("deal_id", sa.String(length=40), nullable=True),
        sa.Column("owner_id", sa.String(length=40), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["contact_id"], ["contacts.id"], name=op.f("fk_activities_contact_id_contacts")
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"], ["deals.id"], name=op.f("fk_activities_deal_id_deals")
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_activities_owner_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activities")),
    )
    with op.batch_alter_table("activities", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_activities_contact_id"), ["contact_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("activities", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_activities_contact_id"))

    op.drop_table("activities")
    with op.batch_alter_table("deals", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_deals_stage"))
        batch_op.drop_index(batch_op.f("ix_deals_owner_id"))
        batch_op.drop_index(batch_op.f("ix_deals_created_at"))
        batch_op.drop_index(batch_op.f("ix_deals_contact_id"))
        batch_op.drop_index(batch_op.f("ix_deals_company_id"))

    op.drop_table("deals")
    with op.batch_alter_table("contacts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_contacts_owner_id"))
        batch_op.drop_index(batch_op.f("ix_contacts_name"))
        batch_op.drop_index(batch_op.f("ix_contacts_created_at"))
        batch_op.drop_index(batch_op.f("ix_contacts_company_id"))

    op.drop_table("contacts")
    op.drop_table("users")
    with op.batch_alter_table("companies", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_companies_name"))

    op.drop_table("companies")
