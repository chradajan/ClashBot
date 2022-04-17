"""Roles used on Discord server."""

from enum import Enum
from typing import List, Union
import discord

from config.config import (
    ADMIN_ROLE_NAME,
    CHECK_RULES_ROLE_NAME,
    ELDER_ROLE_NAME,
    LEADER_ROLE_NAME,
    MEMBER_ROLE_NAME,
    NEW_ROLE_NAME,
    VISITOR_ROLE_NAME
)

class RoleNames(Enum):
    """Enum of relevant role names."""
    ADMIN = ADMIN_ROLE_NAME
    CHECK_RULES = CHECK_RULES_ROLE_NAME
    ELDER = ELDER_ROLE_NAME
    LEADER = LEADER_ROLE_NAME
    MEMBER = MEMBER_ROLE_NAME
    NEW = NEW_ROLE_NAME
    VISITOR = VISITOR_ROLE_NAME


class Roles:
    """Stores roles relevant to bot."""
    def __init__(self):
        """Create roles dictionary."""
        self.roles = {
            RoleNames.ADMIN: None,
            RoleNames.CHECK_RULES: None,
            RoleNames.ELDER: None,
            RoleNames.LEADER: None,
            RoleNames.MEMBER: None,
            RoleNames.NEW: None,
            RoleNames.VISITOR: None
        }

    def initialize(self, guild: discord.Guild):
        """Save relevant roles to dictionary based on configured role names.

        Args:
            guild: Discord server to get roles from.
        """
        self.roles[RoleNames.ADMIN] = discord.utils.get(guild.roles, name=RoleNames.ADMIN.value)
        self.roles[RoleNames.CHECK_RULES] = discord.utils.get(guild.roles, name=RoleNames.CHECK_RULES.value)
        self.roles[RoleNames.ELDER] = discord.utils.get(guild.roles, name=RoleNames.ELDER.value)
        self.roles[RoleNames.LEADER] = discord.utils.get(guild.roles, name=RoleNames.LEADER.value)
        self.roles[RoleNames.MEMBER] = discord.utils.get(guild.roles, name=RoleNames.MEMBER.value)
        self.roles[RoleNames.NEW] = discord.utils.get(guild.roles, name=RoleNames.NEW.value)
        self.roles[RoleNames.VISITOR] = discord.utils.get(guild.roles, name=RoleNames.VISITOR.value)

    def admin(self) -> discord.Role:
        """Get admin role.

        Returns:
            Admin role.
        """
        return self.roles[RoleNames.ADMIN]

    def check_rules(self) -> discord.Role:
        """Get check rules role.

        Returns:
            Check rules role.
        """
        return self.roles[RoleNames.CHECK_RULES]

    def elder(self) -> discord.Role:
        """Get elder role.

        Returns:
            Elder role.
        """
        return self.roles[RoleNames.ELDER]

    def leader(self) -> discord.Role:
        """Get leader role.

        Returns:
            Leader role.
        """
        return self.roles[RoleNames.LEADER]

    def member(self) -> discord.Role:
        """Get member role.

        Returns:
            Member role.
        """
        return self.roles[RoleNames.MEMBER]

    def new(self) -> discord.Role:
        """Get new role.

        Returns:
            New role.
        """
        return self.roles[RoleNames.NEW]

    def visitor(self) -> discord.Role:
        """Get visitor role.

        Returns:
            Visitor role.
        """
        return self.roles[RoleNames.VISITOR]

    def normal_roles(self) -> List[discord.TextChannel]:
        """Get a list of normal roles.

        Returns:
            List consisting of elder, leader, member, and visitor roles.
        """
        return [
            self.roles[RoleNames.ELDER],
            self.roles[RoleNames.LEADER],
            self.roles[RoleNames.MEMBER],
            self.roles[RoleNames.VISITOR]
        ]

    def special_roles(self) -> List[discord.TextChannel]:
        """Get a list of special roles.

        Returns:
            List consisting of admin, check rules, and new roles.
        """
        return [self.roles[RoleNames.ADMIN], self.roles[RoleNames.CHECK_RULES], self.roles[RoleNames.NEW]]

    def get_role_from_name(self, role_name: str) -> Union[discord.Role, None]:
        """Get a role from its name.

        Args:
            role_name: Name of role to get.

        Returns:
            Role corresponding to specified name, or None if name does not match a role.
        """
        try:
            role_enum = RoleNames(role_name)
        except ValueError:
            return None

        return self.roles[role_enum]


ROLE = Roles()


def prepare_roles(guild: discord.Guild):
    """Initialize ROLE object.

    Args:
        Guild to get channels of.
    """
    global ROLE
    ROLE.initialize(guild)
