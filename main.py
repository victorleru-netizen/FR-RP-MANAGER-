import discord
from discord.ext import commands
import os
import time
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
from waitress import serve

# ==============================================================================
# 🌐 SERVEUR WEB DE PRODUCTION
# ==============================================================================
app = Flask('')

@app.route('/')
def home():
    return "Bot RP Administration en ligne !"

def run_web_server():
    port = int(os.environ.get("PORT", 3000))
    serve(app, host='0.0.0.0', port=port)

Thread(target=run_web_server).start()

# ==============================================================================
# 🤖 CONFIGURATION DU BOT
# ==============================================================================
intents = discord.Intents.default()
intents.message_content = True  
intents.members = True          

bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

db_users = {}
db_services = {}

ROLE_GENDARME_ID = 123456789012345678  
ROLE_EN_SERVICE_ID = 876543210987654321  

def get_or_create_user(user_id):
    if user_id not in db_users:
        db_users[user_id] = {
            "nom": "Non défini",
            "prenom": "Non défini",
            "permis": False,
            "points": 12,
            "suspendu_jusqua": None,
            "xp_gendarme": 0,
            "argent": 0,
            "grade_gendarme": "Adjoint"
        }
    return db_users[user_id]

@bot.event
async def on_ready():
    print("\n========================================")
    print(f"🤖 BOT EN LIGNE : {bot.user.name}")
    print("Préfixe actif : .")
    print("========================================\n")

# ==============================================================================
# 🛠️ LE SYSTÈME DE DIAGNOSTIC DES ERREURS (NE PAS SUPPRIMER)
# ==============================================================================
@bot.event
async def on_command_error(ctx, error):
    """Ce bloc va écrire l'erreur TRÈS CLAIREMENT dans les logs Render"""
    print(f"\n❌ [ERREUR DETECTEE] Lors de la commande .{ctx.command}")
    print(f"Raison : {error}\n")
    await ctx.send(f"⚠️ Une erreur est survenue : `{error}`")

# ==============================================================================
# 📜 COMMANDES
# ==============================================================================

@bot.command(name="cmds")
async def liste_commandes(ctx):
    print(f"🔔 [LOG] La commande .cmds a été reçue de {ctx.author.name} !")
    embed = discord.Embed(
        title="📜 INDEX DES COMMANDES", 
        description="Système actif. Préfixe : `.`",
        color=discord.Color.blurple()
    )
    embed.add_field(name="👤 Citoyen", value="`.creer-identite` | `.carte-identite` | `.permis`")
    embed.add_field(name="💼 Métier", value="`.service start` | `.service end` | `.carriere`")
    embed.add_field(name="🚔 Gendarmerie", value="`.donner-permis` | `.enlever-points` | `.suspendre-permis`")
    await ctx.send(embed=embed)

@bot.command(name="creer-identite")
async def creer_identite(ctx, prenom: str, nom: str):
    user = get_or_create_user(ctx.author.id)
    user["prenom"] = prenom
    user["nom"] = nom
    await ctx.send(f"✅ Identité enregistrée : **{prenom} {nom}** !")

@bot.command(name="carte-identite")
async def carte_identite(ctx, member: discord.Member = None):
    target = member or ctx.author
    user = get_or_create_user(target.id)
    embed = discord.Embed(title="🪪 CARTE D'IDENTITÉ", color=discord.Color.blue())
    embed.add_field(name="Prénom", value=user["prenom"], inline=True)
    embed.add_field(name="Nom", value=user["nom"], inline=True)
    embed.add_field(name="Argent", value=f"{user['argent']}$", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="permis")
async def afficher_permis(ctx, member: discord.Member = None):
    target = member or ctx.author
    user = get_or_create_user(target.id)
    embed = discord.Embed(title=f"🚗 Permis de {target.display_name}", color=discord.Color.green())
    if not user["permis"]:
        embed.description = "❌ Aucun permis enregistré."
        embed.color = discord.Color.red()
    else:
        embed.add_field(name="Points", value=f"{user['points']} / 12")
    await ctx.send(embed=embed)

@bot.command(name="donner-permis")
async def donner_permis(ctx, member: discord.Member):
    user = get_or_create_user(member.id)
    user["permis"] = True
    await ctx.send(f"🚗 Permis accordé à {member.mention}.")

# ==============================================================================
# 🚀 DÉMARRAGE
# ==============================================================================
token = os.environ.get("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ Variable DISCORD_TOKEN manquante.")
