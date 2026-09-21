import os
import json
import asyncio
import datetime
import threading
import logging
from flask import Flask, jsonify
import discord
from discord.ext import commands

# Configuration de Flask pour Render
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "Bot Empire Astral en ligne", "timestamp": str(datetime.datetime.now())})

def run_flask():
    # Render attribue dynamiquement un port via la variable PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

# Configuration du bot Discord
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="+", intents=intents, help_command=None)

# Variables de configuration des salons
auto_rank_channel_id = None
welcome_channel_id = None

@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user}")

# Arrivée d'un membre
@bot.event
async def on_member_join(member):
    if welcome_channel_id:
        channel = member.guild.get_channel(welcome_channel_id)
        if channel:
            await channel.send(f"Bienvenue sur le serveur de l’Empire Astral {member.mention} 🪐")

# Détection de changement de statut
@bot.event
async def on_presence_update(before, after):
    if not auto_rank_channel_id or not after.member:
        return

    channel = after.guild.get_channel(auto_rank_channel_id)
    if not channel:
        return

    has_status = False
    for activity in after.activities:
        if activity.type == discord.ActivityType.custom and activity.name:
            if "Empire Astral" in activity.name:
                has_status = True
                break

    if has_status:
        await channel.send(f"{bot.user.mention} {after.member.mention} [ Empire Astral ] Protect t’as Rank. 🪐")
    else:
        await channel.send(f"{after.member.mention} Ta pas ton statut ! 🪐")

# Commandes du Bot

@bot.command(name="cmds")
async def cmds(ctx):
    """Affiche la liste des commandes et leur utilisation"""
    msg = (
        "🪐 **Liste des commandes du bot Empire Astral** 🪐\n\n"
        "**Modération :**\n"
        "• `+ban [user] [raison]` : Banni un membre du serveur pour 7 jours.\n"
        "• `+bl [user] [raison]` : Banni définitivement un membre (Blacklist).\n"
        "• `+deban [id]` : Débanni un membre grâce à son ID.\n"
        "• `+mute [user] [durée] [raison]` : Rend muet un membre (durée ex: 10m, 1h, 2j).\n"
        "• `+unmute [user] [raison]` : Retire le mute d'un membre.\n\n"
        "**Gestion des salons :**\n"
        "• `+lock` : Verrouille le salon actuel.\n"
        "• `+unlock` : Déverrouille le salon actuel.\n\n"
        "**Configuration :**\n"
        "• `+active auto+rank [#salon]` : Définit le salon de vérification du statut Empire Astral.\n"
        "• `+arrive [#salon]` : Définit le salon des messages de bienvenue.\n"
        "• `+cmds` : Affiche ce menu d'aide."
    )
    await ctx.send(msg)

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "Aucune raison fournie"):
    """Ban pour 7 jours"""
    await ctx.guild.ban(member, reason=reason, delete_message_days=7)
    await ctx.send(f"{member.mention} a été banni pour 7 jours.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def bl(ctx, member: discord.Member, *, reason: str = "Aucune raison fournie (Blacklist)"):
    """Ban permanent"""
    await ctx.guild.ban(member, reason=reason)
    await ctx.send(f"{member.mention} a été banni définitivement.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def deban(ctx, user_id: int):
    """Débannir par ID"""
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"L'utilisateur {user.name} a été débanni.")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, duration: str, *, reason: str = "Aucune raison fournie"):
    """Mute temporaire (ex: +mute @user 10m / 1h / 2j)"""
    unit = duration[-1]
    amount = int(duration[:-1])
    
    if unit == 'm':
        delta = datetime.timedelta(minutes=amount)
    elif unit == 'h':
        delta = datetime.timedelta(hours=amount)
    elif unit == 'j':
        delta = datetime.timedelta(days=amount)
    else:
        return await ctx.send("Unité invalide (utilise m, h ou j).")

    await member.timeout(delta, reason=reason)
    await ctx.send(f"{member.mention} a été rendu muet pour {duration}.")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member, *, reason: str = "Aucune raison fournie"):
    await member.timeout(None, reason=reason)
    await ctx.send(f"{member.mention} n'est plus muet.")

@bot.command(name="active")
@commands.has_permissions(administrator=True)
async def active_autorank(ctx, option: str, channel: discord.TextChannel):
    global auto_rank_channel_id
    if option == "auto+rank":
        auto_rank_channel_id = channel.id
        await ctx.send(f"Auto-rank activé dans {channel.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def arrive(ctx, channel: discord.TextChannel):
    global welcome_channel_id
    welcome_channel_id = channel.id
    await ctx.send(f"Salon d'arrivée configuré sur {channel.mention}")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("Salon verrouillé.")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("Salon déverrouillé.")

# Lancement du serveur Web et du Bot
async def main():
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ Variable DISCORD_TOKEN manquante.")
        return
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
