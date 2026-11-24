"""Admin console page."""

from __future__ import annotations

import streamlit as st

from cta_app.services.admin_access import AdminAccessRepository
from cta_app.services.allowed_domains import (
    add_allowed_domain,
    load_allowed_domains,
    remove_allowed_domain,
)


def _render_admin_sidebar_styles() -> None:
    st.markdown(
        """
        <style>
            section[data-testid="stSidebar"] {
                display: block !important;
                visibility: visible !important;
                opacity: 1 !important;
                width: auto !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_users(repository: AdminAccessRepository) -> None:
    st.header("Create User")
    name = st.text_input("Name")
    email = st.text_input("Email")

    if st.button("Create User"):
        repository.create_user(name, email)
        st.success("User Created")

    st.subheader("All Users")
    for user in repository.list_users():
        st.write(f"{user.id} - {user.name} ({user.email})")


def _render_roles(repository: AdminAccessRepository) -> None:
    st.header("Create Role")
    role_name = st.text_input("Role Name")

    if st.button("Create Role"):
        repository.create_role(role_name)
        st.success("Role Created")

    st.subheader("All Roles")
    for role in repository.list_roles():
        st.write(f"{role.id} - {role.name}")


def _render_assign_roles(repository: AdminAccessRepository) -> None:
    st.header("Assign Role to User")
    users = repository.list_users()
    roles = repository.list_roles()

    if not users or not roles:
        st.warning("Create at least one user and one role first.")
        return

    user_options = {f"{user.name} ({user.email})": user.id for user in users}
    role_options = {role.name: role.id for role in roles}

    selected_user = st.selectbox("User", list(user_options.keys()))
    selected_role = st.selectbox("Role", list(role_options.keys()))

    if st.button("Assign"):
        repository.assign_role_to_user(
            user_options[selected_user], role_options[selected_role]
        )
        st.success("Role Assigned")


def _render_taxonomy_rules(repository: AdminAccessRepository) -> None:
    st.header("Create Taxonomy Rule")
    roles = repository.list_roles()
    role_names = [role.name for role in roles]

    if not role_names:
        st.warning("Create at least one role first.")
        return

    role = st.selectbox("Role", role_names)
    brand = st.text_input("Brand")
    geo = st.text_input("Geo")
    access = st.selectbox("Access Level", ["read", "write", "admin"])

    if st.button("Create Rule"):
        repository.create_taxonomy_rule(role, brand, geo, access)
        st.success("Rule Created")

    st.subheader("Existing Rules")
    for rule in repository.list_taxonomy_rules():
        st.write(f"{rule.role_name} | {rule.brand} | {rule.geo} -> {rule.access_level}")


def _render_allowed_domains() -> None:
    st.header("Allowed Domains")
    st.caption(
        "Only URLs whose host matches one of these domains (or a subdomain of one) "
        "will pass CTA validation. Leave the list empty to disable this check."
    )

    new_domain = st.text_input(
        "Add Domain",
        placeholder="e.g. gskpro.com",
        key="allowed_domain_input",
    )
    if st.button("Add Domain"):
        if not new_domain.strip():
            st.warning("Enter a domain to add.")
        elif add_allowed_domain(new_domain):
            st.success(f"Added '{new_domain.strip().lower()}'.")
            st.rerun()
        else:
            st.info("Domain already in the list (or invalid).")

    st.subheader("Current Allowed Domains")
    domains = load_allowed_domains()
    if not domains:
        st.info("No domains configured — allowlist check is currently disabled.")
        return

    for domain in domains:
        col_domain, col_action = st.columns([4, 1])
        col_domain.write(domain)
        if col_action.button("Remove", key=f"remove_{domain}"):
            remove_allowed_domain(domain)
            st.rerun()


def _render_access_check(repository: AdminAccessRepository) -> None:
    st.header("Check User Access")
    email = st.text_input("User Email")
    brand = st.text_input("Brand")
    geo = st.text_input("Geo")

    if st.button("Check"):
        access = repository.check_access(email, brand, geo)
        st.success(f"Access Level: {access}")


def render_admin_console() -> None:
    st.markdown('<section class="workspace-hero"><div class="eyebrow">CTA Sync administration</div><h1>Access & governance</h1><p>Manage people, roles, campaign access, and trusted domains.</p></section>', unsafe_allow_html=True)

    menu = st.selectbox(
        "Menu",
        [
            "Users",
            "Roles",
            "Assign Roles",
            "Taxonomy Rules",
            "Access Check",
            "Allowed Domains",
        ],
    )
    repository = AdminAccessRepository()
    try:
        if menu == "Users":
            _render_users(repository)
        elif menu == "Roles":
            _render_roles(repository)
        elif menu == "Assign Roles":
            _render_assign_roles(repository)
        elif menu == "Taxonomy Rules":
            _render_taxonomy_rules(repository)
        elif menu == "Access Check":
            _render_access_check(repository)
        elif menu == "Allowed Domains":
            _render_allowed_domains()
    finally:
        repository.close()
