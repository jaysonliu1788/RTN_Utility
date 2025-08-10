import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands, AllowedMentions
import language_tool_python
import mysql.connector
from datetime import datetime

load_dotenv()

# Bot setup
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = 822530323505741834
FOUNDERS_ROLE_ID = 1291213977178865695

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

tool = language_tool_python.LanguageToolPublicAPI('en-US')

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "u6_LHVs9oMpq2",
    "password": os.getenv("DB_PASSWORD"),
    "database": "s6_RTN-Utility-Member-database"
}

bot_enabled = True

OVERRIDE_WORDS = {"Sail", "vr", "SailVr", "Gralilo", "Hamza", "Knight"}

def correct_text(text):
    matches = tool.check(text)
    filtered_matches = []
    for match in matches:
        error_text = text[match.offset : match.offset + match.errorLength]
        if error_text.lower() in (w.lower() for w in OVERRIDE_WORDS):
            continue
        filtered_matches.append(match)
    corrected = language_tool_python.utils.correct(text, filtered_matches)

    summary = []
    for match in filtered_matches:
        error = text[match.offset : match.offset + match.errorLength]
        suggestion = match.replacements[0] if match.replacements else "(no suggestion)"
        summary.append(f"🔧 `{error}` → `{suggestion}` ({match.ruleId})")

    return corrected, summary

def save_submission(user_id, original, corrected):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        query = "INSERT INTO articles (user_id, original, corrected, timestamp) VALUES (%s, %s, %s, %s)"
        values = (user_id, original, corrected, datetime.utcnow())
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Failed to save to database: {e}")

@tree.command(name="edit_article", description="Grammar-check your article using LanguageTool")
@app_commands.describe(text="Paste your article here")
async def edit_article(interaction: discord.Interaction, text: str):
    if not bot_enabled and interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ Bot is currently disabled.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    corrected, summary = correct_text(text)
    summary_text = "\n".join(summary) or "✅ No major corrections found."
    corrected_block = f"```\n{corrected[:1900]}\n```"

    save_submission(interaction.user.id, text, corrected)

    await interaction.followup.send("📄 **Corrected Article:**")
    await interaction.followup.send(corrected_block)
    await interaction.followup.send(f"**📝 Corrections:**\n{summary_text}")

@tree.command(name="maintenance_ping", description="Ping the Founders role for maintenance notice")
async def maintenance_ping(interaction: discord.Interaction):
    if not bot_enabled and interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ Bot is currently disabled.", ephemeral=True)
        return

    role = interaction.guild.get_role(FOUNDERS_ROLE_ID)
    if not role:
        await interaction.response.send_message("❌ Founders role not found.", ephemeral=True)
        return

    message = f"{role.mention} Shutting Down Temporarily For Maintenance. Estimated Time: 5–10 Minutes"
    await interaction.response.send_message(message, allowed_mentions=AllowedMentions(roles=True))

@tree.command(name="enable", description="Enable the bot's features")
async def enable_bot(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return

    global bot_enabled
    bot_enabled = True
    await interaction.response.send_message("🔓 Bot has been enabled.")

@tree.command(name="disable", description="Disable the bot's features")
async def disable_bot(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return

    global bot_enabled
    bot_enabled = False
    await interaction.response.send_message("⛔ Bot has been disabled. It will stay online but stop processing messages and commands.")

@bot.event
async def on_message(message: discord.Message):
    global bot_enabled

    if message.author.bot:
        return

    if not bot_enabled and message.author.id != OWNER_ID:
        if message.content.strip().lower() == "?fixbot" or (bot.user in message.mentions and message.reference):
            await message.channel.send("⛔ Bot has been Locked or Disabled, please message your developer to continue.")
        return

    if message.content.lower().strip() == "?fixbot":
        await message.delete()
        role = message.guild.get_role(FOUNDERS_ROLE_ID)
        if not role:
            await message.channel.send("❌ Founders role not found.")
            return
        maintenance_msg = f"{role.mention} Shutting Down Temporarily For Maintenance. Estimated Time: 5–10 Minutes"
        await message.channel.send(maintenance_msg, allowed_mentions=AllowedMentions(roles=True))
        return

    elif bot.user in message.mentions and message.reference:
        try:
            replied_to = await message.channel.fetch_message(message.reference.message_id)
            if replied_to.author.bot:
                return
            corrected, summary = correct_text(replied_to.content)
            summary_text = "\n".join(summary) or "✅ No major corrections found."
            corrected_block = f"```\n{corrected[:1900]}\n```"
            await replied_to.reply(
                content=f"📄 **Corrected Version of Above Message:**\n{corrected_block}\n\n**📝 Corrections:**\n{summary_text}"
            )
            save_submission(message.author.id, replied_to.content, corrected)
        except Exception as e:
            await message.channel.send(f"❌ Error: {e}")
        return

    await bot.process_commands(message)

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)
