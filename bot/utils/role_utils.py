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

class ROLE_NAMES(Enum):
    """Enum of relevant role names."""
    ADMIN = ADMIN_ROLE_NAME
    CHECK_RULES = CHECK_RULES_ROLE_NAME
    ELDER = ELDER_ROLE_NAME
    LEADER = LEADER_ROLE_NAME
    MEMBER = MEMBER_ROLE_NAME
    NEW = NEW_ROLE_NAME
    VISITOR = VISITOR_ROLE_NAME


class Roles:
    def __init__(self):
        """Create roles dictionary."""
        self.roles = {
            ROLE_NAMES.ADMIN: None,
            ROLE_NAMES.CHECK_RULES: None,
            ROLE_NAMES.ELDER: None,
            ROLE_NAMES.LEADER: None,
            ROLE_NAMES.MEMBER: None,
            ROLE_NAMES.NEW: None,
            ROLE_NAMES.VISITOR: None
        }

    def initialize(self, guild: discord.Guild):
        """
        Save relevant roles to dictionary based on configured role names.

        Args:
            guild (discord.Guild): Discord server to get roles from.
        """
        self.roles[ROLE_NAMES.ADMIN] = discord.utils.get(guild.roles, name=ROLE_NAMES.ADMIN.value)
        self.roles[ROLE_NAMES.CHECK_RULES] = discord.utils.get(guild.roles, name=ROLE_NAMES.CHECK_RULES.value)
        self.roles[ROLE_NAMES.ELDER] = discord.utils.get(guild.roles, name=ROLE_NAMES.ELDER.value)
        self.roles[ROLE_NAMES.LEADER] = discord.utils.get(guild.roles, name=ROLE_NAMES.LEADER.value)
        self.roles[ROLE_NAMES.MEMBER] = discord.utils.get(guild.roles, name=ROLE_NAMES.MEMBER.value)
        self.roles[ROLE_NAMES.NEW] = discord.utils.get(guild.roles, name=ROLE_NAMES.NEW.value)
        self.roles[ROLE_NAMES.VISITOR] = discord.utils.get(guild.roles, name=ROLE_NAMES.VISITOR.value)

    def admin(self) -> discord.Role:
        """
        Get admin role.

        Returns:
            discord.Role: Admin role.
        """
        return self.roles[ROLE_NAMES.ADMIN]
    
    def check_rules(self) -> discord.Role:
        """
        Get check rules role.

        Returns:
            discord.Role: Check rules role.
        """
        return self.roles[ROLE_NAMES.CHECK_RULES]

    def elder(self) -> discord.Role:
        """
        Get elder role.

        Returns:
            discord.Role: Elder role.
        """
        return self.roles[ROLE_NAMES.ELDER]

    def leader(self) -> discord.Role:
        """
        Get leader role.

        Returns:
            discord.Role: Leader role.
        """
        return self.roles[ROLE_NAMES.LEADER]

    def member(self) -> discord.Role:
        """
        Get member role.

        Returns:
            discord.Role: Member role.
        """
        return self.roles[ROLE_NAMES.MEMBER]

    def new(self) -> discord.Role:
        """
        Get new role.

        Returns:
            discord.Role: New role.
        """
        return self.roles[ROLE_NAMES.NEW]

    def visitor(self) -> discord.Role:
        """
        Get visitor role.

        Returns:
            discord.Role: Visitor role.
        """
        return self.roles[ROLE_NAMES.VISITOR]

    def normal_roles(self) -> List[discord.TextChannel]:
        """
        Get a list of normal roles.

        Returns:
            List[TextChannel]: List consisting of elder, leader, member, and visitor roles.
        """
        return [
            self.roles[ROLE_NAMES.ELDER],
            self.roles[ROLE_NAMES.LEADER],
            self.roles[ROLE_NAMES.MEMBER],
            self.roles[ROLE_NAMES.VISITOR]
        ]

    def special_roles(self) -> List[discord.TextChannel]:
        """
        Get a list of special roles.

        Returns:
            List[TextChannel]: List consisting of admin, check rules, and new roles.
        """
        return [
            self.roles[ROLE_NAMES.ADMIN],
            self.roles[ROLE_NAMES.CHECK_RULES],
            self.roles[ROLE_NAMES.NEW]
        ]

    def get_role_from_name(self, role_name: str) -> Union[discord.Role, None]:
        """
        Get a role from its name.

        Args:
            role_name (str): Name of role to get.

        Returns:
            discord.Role: Role corresponding to specified name, or None if name does not match a role.
        """
        try:
            role_enum = ROLE_NAMES(role_name)
        except ValueError:
            return None

        return self.roles[role_enum]


ROLE = Roles()

def prepare_roles(guild: discord.Guild):
    """
    Find roles in guild and save to dictionary.

    Args:
        guild(discord.Guild): Guild to find roles within.
    """
    global ROLE
    ROLE.initialize(guild)
