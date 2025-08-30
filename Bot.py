import os
import discord
from discord.ext import commands
from discord import app_commands, AllowedMentions
from dotenv import load_dotenv
import mysql.connector

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN is None:
    raise ValueError("❌ DISCORD_TOKEN is missing. Please set it in your .env file!")

# Bot setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="?", intents=intents, allowed_mentions=AllowedMentions.none())

OWNER_ID = 822530323505741834
bot_enabled = True  # Toggle for enable/disable

# Database connection (localhost:3306)
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        port=3306,
        user=os.getenv("MYSQL_USER"),       
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")

# ==========================
# Enable / Disable Commands
# ==========================

@bot.tree.command(name="enable", description="Enable the bot (Owner only)")
async def enable_bot(interaction: discord.Interaction):
    global bot_enabled
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔ You are not authorized to use this command.", ephemeral=True)
        return
    bot_enabled = True
    await interaction.response.send_message("🔓 Bot has been enabled.")

@bot.tree.command(name="disable", description="Disable the bot (Owner only)")
async def disable_bot(interaction: discord.Interaction):
    global bot_enabled
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔ You are not authorized to use this command.", ephemeral=True)
        return
    bot_enabled = False
    await interaction.response.send_message("⛔ Bot has been disabled. It will stay online but stop processing messages and commands.")

# ==========================
# Example Message Edit Handler
# ==========================

@bot.event
async def on_message_edit(before, after):
    global bot_enabled
    if not bot_enabled:
        return
    if after.author.bot:
        return
    await after.channel.send(f"✏️ {after.author.mention} edited their message:\n**Before:** {before.content}\n**After:** {after.content}")

# ==========================
# Leave Command (Owner only)
# ==========================

@bot.tree.command(name="leave", description="Force the bot to leave the server (Owner only)")
async def leave_guild(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔ You are not authorized to use this command.", ephemeral=True)
        return
    await interaction.response.send_message("👋 Leaving server as requested by the owner.")
    await interaction.guild.leave()

# ==========================
# Block Commands When Disabled
# ==========================

@bot.event
async def on_message(message):
    global bot_enabled
    if not bot_enabled and not message.author.bot:
        if not message.content.startswith("?") and not message.content.startswith("/"):
            return
        await message.channel.send("⛔ Bot has been Locked or Disabled, please message your developer to continue.")
        return
    await bot.process_commands(message)

# ==========================
# Run Bot
# ==========================

bot.run(TOKEN)
