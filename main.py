iimport discord
from discord.ext import commands
import os
import time
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
from waitress import serve

# ==============================================================================
# 🌐 SERVEUR WEB DE PRODUCTION (Pour Render + UptimeRobot)
# ==============================================================================
app = Flask('')

@app.route('/')
def home():
    return "Bot RP Administration en ligne et fonctionnel !"

def run_web_server():
    port = int(os.environ.get("PORT", 3000))
    serve(app, host='0.0.0.0', port=port)

Thread(target=run_web_server).start()

# ==============================================================================
# 🤖 CONFIGURATION DU BOT (Préfixe : .)
# ==============================================================================
intents = discord.Intents.default()
intents.message_content = True  
intents.members = True          

# Utilisation directe du bot de commandes sans surcouche d'événement bloquant
bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

# 💾 STOCKAGE TEMPORAIRE
db_users = {}
db_services = {}

# 🔒 CONFIGURATION DES ROLES (Mets tes IDs ici)
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
    print("----------------------------------------")
    print(f"FR RP MANAGER connecté avec succès !")
    print("Le système de commandes directes est actif.")
    print("----------------------------------------")

# ==============================================================================
# 📜 L'INDEX DES COMMANDES (.cmds)
# ==============================================================================

@bot.command(name="cmds")
async def liste_commandes(ctx):
    """Affiche l'aide de toutes les commandes disponibles."""
    print(f"[EXECUTION] .cmds lancé par {ctx.author.name}")
    embed = discord.Embed(
        title="📜 INDEX DES COMMANDES DE L'ADMINISTRATION RP", 
        description="Voici la liste complète des interactions. Utilisez le préfixe point `.`",
        color=discord.Color.blurple()
    )
    
    embed.add_field(
        name="👤 Pôle Citoyen", 
        value="`.creer-identite [Prenom] [Nom]` • Crée ton identité civile\n`.carte-identite` • Visualise tes papiers d'identité\n`.permis` • Vérifie tes points restants", 
        inline=False
    )
    
    embed.add_field(
        name="💼 Pôle Faction / Métier", 
        value="`.service start` • Entre en service actif\n`.service end` • Termine ton service (salaire + XP)\n`.carriere` • Regarde ton grade et ton expérience", 
        inline=False
    )
    
    embed.add_field(
        name="🚔 Pôle Gendarmerie", 
        value="`.donner-permis [@joueur]` • Enregistre le permis d'un citoyen\n`.enlever-points [@joueur] [nb] [raison]` • Sanction routière\n`.suspendre-permis [@joueur] [jours] [raison]` • Rétention du permis", 
        inline=False
    )
    
    embed.set_footer(text="FR RP MANAGER • Système automatisé.")
    await ctx.send(embed=embed)

# ==============================================================================
# 👤 MODULE CITOYEN & IDENTITÉ
# ==============================================================================

@bot.command(name="creer-identite")
async def creer_identite(ctx, prenom: str, nom: str):
    user = get_or_create_user(ctx.author.id)
    user["prenom"] = prenom
    user["nom"] = nom
    await ctx.send(f"✅ Identité RP enregistrée : **{prenom} {nom}** !")

@bot.command(name="carte-identite")
async def carte_identite(ctx, member: discord.Member = None):
    target = member or ctx.author
    user = get_or_create_user(target.id)
    
    embed = discord.Embed(title="🪪 CARTE NATIONALE D'IDENTITÉ", color=discord.Color.blue())
    embed.add_field(name="Prénom", value=user["prenom"], inline=True)
    embed.add_field(name="Nom", value=user["nom"], inline=True)
    embed.add_field(name="Portefeuille", value=f"{user['argent']}$", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="permis")
async def afficher_permis(ctx, member: discord.Member = None):
    target = member or ctx.author
    user = get_or_create_user(target.id)
    
    embed = discord.Embed(title=f"🚗 Permis de Conduire de {target.display_name}", color=discord.Color.green())
    
    if not user["permis"]:
        embed.description = "❌ Aucun permis de conduire enregistré."
        embed.color = discord.Color.red()
    elif user["suspendu_jusqua"] and datetime.now() < user["suspendu_jusqua"]:
        temps_restant = user["suspendu_jusqua"] - datetime.now()
        heures, rest = divmod(temps_restant.seconds, 3600)
        minutes, _ = divmod(rest, 60)
        embed.description = f"🛑 **SUSPENDU**\n**Raison :** Infraction grave\n**Temps restant :** {temps_restant.days}j {heures}h {minutes}m"
        embed.color = discord.Color.dark_red()
    else:
        embed.add_field(name="Statut", value="✅ Valide", inline=True)
        embed.add_field(name="Points", value=f"{user['points']} / 12", inline=True)
        
    await ctx.send(embed=embed)

# ==============================================================================
# 💼 MODULE METIER & TEMPS DE SERVICE
# ==============================================================================

@bot.command(name="service")
async def gestion_service(ctx, action: str):
    user_id = ctx.author.id
    user = get_or_create_user(user_id)
    
    gendarme_role = ctx.guild.get_role(ROLE_GENDARME_ID)
    en_service_role = ctx.guild.get_role(ROLE_EN_SERVICE_ID)
    
    if gendarme_role not in ctx.author.roles:
        await ctx.send("❌ Vous ne faites pas partie de la Gendarmerie.")
        return

    if action.lower() == "start":
        if user_id in db_services:
            await ctx.send("⚠️ Vous êtes déjà en service !")
