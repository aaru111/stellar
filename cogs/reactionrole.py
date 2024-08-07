import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
import os
import random

CONFIG_FILE = "reaction_roles.json"


class ReactionRoleButton(discord.ui.Button):
    """
    A button that assigns/removes a role when clicked.
    """

    def __init__(self, role_id: int, emoji: str, colour: discord.ButtonStyle):
        super().__init__(style=colour, emoji=emoji, custom_id=str(role_id))
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        """
        Handles the button click, adding/removing the role to/from the user.
        """
        guild = interaction.guild
        role = guild.get_role(self.role_id)
        user = interaction.user

        try:
            if role in user.roles:
                await user.remove_roles(role)
                await interaction.response.send_message(embed=discord.Embed(
                    title="Role Removed",
                    description=
                    f"You have been removed from the role: **{role.name}**",
                    color=discord.Color.red()),
                                                        ephemeral=True)
            else:
                await user.add_roles(role)
                await interaction.response.send_message(embed=discord.Embed(
                    title="Role Assigned",
                    description=
                    f"You have been assigned the role: **{role.name}**",
                    color=discord.Color.green()),
                                                        ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(embed=discord.Embed(
                title="Permission Error",
                description="I do not have permission to manage roles.",
                color=discord.Color.red()),
                                                    ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(embed=discord.Embed(
                title="Error",
                description=f"An error occurred: {e}",
                color=discord.Color.red()),
                                                    ephemeral=True)


class ReactionRoleView(discord.ui.View):
    """
    A view containing buttons to assign/remove roles.
    """

    def __init__(self, buttons: list[ReactionRoleButton] = None):
        super().__init__(timeout=None)
        if buttons:
            for button in buttons:
                self.add_item(button)


class ReactionRole(commands.Cog):
    """
    A Cog for handling reaction role commands.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession = aiohttp.ClientSession()
        self.load_config()

    async def close(self):
        """
        Closes the aiohttp session.
        """
        await self.session.close()

    @commands.Cog.listener()
    async def on_shutdown(self):
        await self.close()

    @commands.Cog.listener()
    async def on_disconnect(self):
        await self.close()

    def load_config(self):
        """
        Loads the reaction roles configuration from the JSON file.
        """
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                for guild_id, messages in config.items():
                    for message_id, buttons in messages.items():
                        view = ReactionRoleView()
                        for button in buttons:
                            role_id = button["role_id"]
                            emoji = button.get("emoji", "🔘")
                            colour = getattr(discord.ButtonStyle,
                                             button["colour"])
                            view.add_item(
                                ReactionRoleButton(role_id, emoji, colour))
                        self.bot.add_view(view, message_id=int(message_id))

    def save_config(self, guild_id, message_id, button):
        """
        Saves the reaction roles configuration to the JSON file.
        """
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
        else:
            config = {}

        if str(guild_id) not in config:
            config[str(guild_id)] = {}

        if str(message_id) not in config[str(guild_id)]:
            config[str(guild_id)][str(message_id)] = []

        config[str(guild_id)][str(message_id)].append(button)

        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)

    @app_commands.command(
        name="reaction_role",
        description="Assign buttons to a message for role assignment.")
    async def reaction_role(self,
                            interaction: discord.Interaction,
                            message_link: str,
                            role: discord.Role,
                            emoji: str = "🔘",
                            colour: str = None):
        """
        Command to add reaction role buttons to a specified message.

        Parameters:
            interaction (discord.Interaction): The interaction object.
            message_link (str): The link to the message.
            role (discord.Role): The role to assign/remove.
            emoji (str): The emoji for the button.
            colour (str): The colour of the button.
        """
        try:
            # Parse message link to get channel ID and message ID
            parts = message_link.split('/')
            channel_id = int(parts[-2])
            message_id = int(parts[-1])
            channel = self.bot.get_channel(channel_id)
            message = await channel.fetch_message(message_id)

            # Determine button colour
            if colour is None:
                colour = random.choice(["red", "green", "blurple", "grey"])
            colour_map = {
                "red": discord.ButtonStyle.red,
                "green": discord.ButtonStyle.green,
                "blurple": discord.ButtonStyle.blurple,
                "grey": discord.ButtonStyle.grey
            }
            button_colour = colour_map.get(colour, discord.ButtonStyle.grey)

            # Create a new button
            button = ReactionRoleButton(role.id, emoji, button_colour)

            # Create or update the view
            view = discord.ui.View(timeout=None)
            if message.components:
                for action_row in message.components:
                    for item in action_row.children:
                        view.add_item(
                            ReactionRoleButton(int(item.custom_id),
                                               str(item.emoji), item.style))
            view.add_item(button)

            # Register the view globally
            self.bot.add_view(view, message_id=message_id)

            # Save the button configuration
            self.save_config(interaction.guild.id, message_id, {
                "role_id": role.id,
                "emoji": emoji,
                "colour": colour
            })

            await message.edit(view=view)
            await interaction.response.send_message(embed=discord.Embed(
                title="Reaction Role Added",
                description=
                f"Reaction role has been added to [this message]({message_link})",
                color=discord.Color.blue()),
                                                    ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(embed=discord.Embed(
                title="Error",
                description=f"An error occurred: {e}",
                color=discord.Color.red()),
                                                    ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """
    Setup function to add the ReactionRole cog to the bot.

    Parameters:
        bot (commands.Bot): The bot instance.
    """
    await bot.add_cog(ReactionRole(bot))