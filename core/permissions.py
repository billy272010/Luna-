"""
Système de permissions par rôle.
Priorité 1 (owner) > Priorité 2 (spouse) > Priorité 3 (child)
"""

ROLES = {
    "owner": {
        "priority": 1,
        "label": "Propriétaire",
        "permissions": {
            "all": True,
            "manage_users": True,
            "view_all_history": True,
            "change_settings": True,
            "adult_content": True,
            "financial_info": True,
            "sensitive_commands": True,
        },
    },
    "spouse": {
        "priority": 2,
        "label": "Épouse",
        "permissions": {
            "all": False,
            "manage_users": False,
            "view_all_history": False,
            "change_settings": False,
            "adult_content": True,
            "financial_info": True,
            "sensitive_commands": False,
        },
    },
    "child": {
        "priority": 3,
        "label": "Enfant",
        "permissions": {
            "all": False,
            "manage_users": False,
            "view_all_history": False,
            "change_settings": False,
            "adult_content": False,
            "financial_info": False,
            "sensitive_commands": False,
        },
    },
}


def get_role_config(role: str) -> dict:
    return ROLES.get(role, ROLES["child"])


def has_permission(role: str, permission: str) -> bool:
    config = get_role_config(role)
    if config["permissions"].get("all"):
        return True
    return config["permissions"].get(permission, False)


def get_priority(role: str) -> int:
    return get_role_config(role)["priority"]
