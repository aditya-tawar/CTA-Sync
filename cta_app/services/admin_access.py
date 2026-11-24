"""Admin-console persistence for users, roles, and access rules."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, Table, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DATABASE_URL = "sqlite:///admin_console.db"

Base = declarative_base()

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("role_id", Integer, ForeignKey("roles.id")),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id")),
    Column("permission_id", Integer, ForeignKey("permissions.id")),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)

    roles = relationship("Role", secondary=user_roles, back_populates="users")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String)

    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    name = Column(String)

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


class BrandGeo(Base):
    __tablename__ = "brand_geo"

    id = Column(Integer, primary_key=True)
    brand = Column(String)
    geo = Column(String)


class TaxonomyRule(Base):
    __tablename__ = "taxonomy_rules"

    id = Column(Integer, primary_key=True)
    role_name = Column(String)
    brand = Column(String)
    geo = Column(String)
    access_level = Column(String)


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def initialize_admin_database() -> None:
    Base.metadata.create_all(engine)


class AdminAccessRepository:
    """Thin persistence wrapper used by the admin Streamlit page."""

    def __init__(self):
        initialize_admin_database()
        self.session = SessionLocal()

    def close(self) -> None:
        self.session.close()

    def create_user(self, name: str, email: str) -> None:
        self.session.add(User(name=name, email=email))
        self.session.commit()

    def list_users(self) -> list[User]:
        return self.session.query(User).all()

    def create_role(self, role_name: str) -> None:
        self.session.add(Role(name=role_name))
        self.session.commit()

    def list_roles(self) -> list[Role]:
        return self.session.query(Role).all()

    def assign_role_to_user(self, user_id: int, role_id: int) -> None:
        user = self.session.get(User, user_id)
        role = self.session.get(Role, role_id)
        if user is None or role is None:
            return
        user.roles.append(role)
        self.session.commit()

    def create_taxonomy_rule(
        self, role: str, brand: str, geo: str, access: str
    ) -> None:
        self.session.add(
            TaxonomyRule(
                role_name=role,
                brand=brand,
                geo=geo,
                access_level=access,
            )
        )
        self.session.commit()

    def list_taxonomy_rules(self) -> list[TaxonomyRule]:
        return self.session.query(TaxonomyRule).all()

    def check_access(self, user_email: str, brand: str, geo: str) -> str:
        user = self.session.query(User).filter_by(email=user_email).first()
        if user is None:
            return "No Access"

        for role in user.roles:
            rule = (
                self.session.query(TaxonomyRule)
                .filter_by(role_name=role.name, brand=brand, geo=geo)
                .first()
            )
            if rule is not None:
                return rule.access_level

        return "No Access"

