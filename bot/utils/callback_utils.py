"""Callback utilities for bot reaction messages."""

from enum import auto, Enum
from typing import Any, Callable, Dict, Tuple

import discord
import utils.bot_utils as bot_utils
from config.config import CONFIRM_EMOJI, DECLINE_EMOJI
from utils.logging_utils import LOG, log_message


class CallbackType(Enum):
    """Enum of callback types for bot reaction messages."""
    STRIKE = auto()
    KICK = auto()


class CallbackManager:
    """Holds bot reaction messages and handles callbacks."""

    class CallbackMessage:
        """Message that a user can react to."""
        callback_type: CallbackType = None
        callback_function: Callable[..., discord.Embed] = None
        decline_embed: discord.Embed = None
        callback_args: Tuple[Any, ...]

        def __init__(self,
                     callback_type: CallbackType,
                     callback_function: Callable[..., discord.Embed],
                     decline_embed: discord.Embed,
                     args: Tuple[Any, ...]):
            """Save information needed for callback.

            Args:
                callback_type: What type of bot reaction message this represents.
                callback_function: What function should be called when reacted to.
                decline_embed: Embed to replace message with if message is declined.
                args: Arguments to pass to callback_function.
            """
            self.callback_type = callback_type
            self.callback_function = callback_function
            self.decline_embed = decline_embed
            self.callback_args = args

        def __str__(self):
            return f"Type: {self.callback_type}, Function: {self.callback_function}, Args: {self.callback_args}"

        def is_allowed(self, user: discord.User) -> bool:
            """Check if the user who reacted is allowed to react to this message.

            Args:
                user: Person who reacted to the message.

            Returns:
                Whether the callback function can be performed by the user.
            """
            if self.callback_type == CallbackType.STRIKE:
                return bot_utils.is_leader_or_higher(user)
            elif self.callback_type == CallbackType.KICK:
                return bot_utils.is_elder_or_higher(user)
            else:
                return False

        async def __call__(self, reaction: discord.Reaction) -> bool:
            """Call the callback function.

            Args:
                reaction: Reaction that triggered the callback.
            """
            legal_reaction = False

            if reaction.emoji == CONFIRM_EMOJI:
                embed = await self.callback_function(*self.callback_args)
                await reaction.message.edit(embed=embed)
                legal_reaction = True
            elif reaction.emoji == DECLINE_EMOJI:
                await reaction.message.edit(embed=self.decline_embed)
                legal_reaction = True

            return legal_reaction

    messages: Dict[int, CallbackMessage] = {}

    def save_callback(self,
                      message_id: int,
                      callback_type: CallbackType,
                      callback_function: Callable[..., discord.Embed],
                      decline_embed: discord.Embed,
                      *args):
        """Save a callback message for when a user to react to later.

        Args:
            message_id: ID of message to react to.
            callback_type: What type of callback this is.
            callback_function: Function to call when the message is reacted to.
            decline_embed: Embed to replace message with if message is declined.
            args: Arguments to pass to callback_function.
        """
        self.messages[message_id] = self.CallbackMessage(callback_type, callback_function, decline_embed, args)

    async def handle_callback(self, reaction: discord.Reaction, user: discord.User):
        """Determine if reacted to message has a callback function tied to it. Handle callback if so.

        Args:
            reaction: Reaction that triggered this.
            user: User who reacted to a message.
        """
        saved_message = self.messages.get(reaction.message.id)

        if saved_message is None:
            return

        LOG.info(log_message("Detected reaction to saved message", emoji=reaction.emoji, user=user, saved_message=saved_message))

        if saved_message.is_allowed(user):
            legal_reaction = await saved_message(reaction)

            if legal_reaction:
                LOG.info("Legal reaction made. Removing message from saved messages.")
                await reaction.message.clear_reactions()
                self.messages.pop(reaction.message.id)
            else:
                LOG.debug("Invalid reaction made")
                await reaction.message.remove_reaction(reaction.emoji, user)
        else:
            LOG.debug("Invalid reaction made")
            await reaction.message.remove_reaction(reaction.emoji, user)



CALLBACK_MANAGER = CallbackManager()
