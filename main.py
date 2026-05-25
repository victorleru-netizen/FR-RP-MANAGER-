import discord
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
    # Utilisation de Waitress pour un déploiement propre sans warning
    serve(app, host='0.0.0.0', port=port)

# Lancement du serveur web dans un thread séparé
Thread(target=run_web_server).start()

# ==============================================================================
# 🤖 CONFIGURATION DES INTENTS ET DU BOT
# ==============================================================================
intents = discord.Intents.default()
intents.message_content = True  # Obligatoire pour lire les commandes en prefix /
intents.members = True          # Obligatoire pour interagir avec les membres et les rôles

bot = commands.Bot(command_prefix="/", intents=intents)

# 💾 STOCKAGE TEMPORAIRE (Données des joueurs)
db_users = {}
db_services = {}

# 🔒 CONFIGURATION DES ROLES (Remplacer par tes vrais IDs dans Discord)
ROLE_GENDARME_ID = 123456789012345678  
ROLE_EN_SERVICE_ID = 876543210987654321  

def get_or_create_user(user_id):
    """Initialise un profil civil s'il n'existe pas dans la base."""
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
    print(f"Connecté avec succès en tant que : {bot.user.name}")
    print("Le bot écoute et lit les commandes.")
    print("----------------------------------------")

# 🔥 LE CORRECTIF CRUCIAL : Traiter les messages pour exécuter les commandes
@bot.event
async def on_message(message):
    # Ignorer les messages du bot lui-même
    if message.author == bot.user:
        return
        
    # Permet de voir dans les logs de Render si le bot "entend" le chat
    if message.content.startswith("/"):
        print(f"[LOG] Commande détectée : {message.content} par {message.author.name}")
        
    # Cette ligne indique au bot de chercher si le message correspond à une commande ci-dessous
    await bot.process_commands(message)

# ==============================================================================
# 👤 MODULE CITOYEN & IDENTITÉ
# ==============================================================================

@bot.command(name="creer-identite")
async def creer_identite(ctx, prenom: str, nom: str):
    """Permet au joueur de créer sa carte d'identité."""
    user = get_or_create_user(ctx.author.id)
    user["prenom"] = prenom
    user["nom"] = nom
    await ctx.send(f"✅ Identité RP enregistrée : **{prenom} {nom}** !")

@bot.command(name="carte-identite")
async def carte_identite(ctx, member: discord.Member = None):
    """Affiche la carte d'identité d'un joueur."""
    target = member or ctx.author
    user = get_or_create_user(target.id)
    
    embed = discord.Embed(title="🪪 CARTE NATIONALE D'IDENTITÉ", color=discord.Color.blue())
    embed.add_field(name="Prénom", value=user["prenom"], inline=True)
    embed.add_field(name="Nom", value=user["nom"], inline=True)
    embed.add_field(name="Portefeuille", value=f"{user['argent']}$", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="permis")
async def afficher_permis(ctx, member: discord.Member = None):
    """Affiche le statut du permis de conduire."""
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
    """Gère les prises et fins de service (/service start ou /service end)."""
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
            return
        
        db_services[user_id] = time.time()
        if en_service_role:
            try:
                await ctx.author.add_roles(en_service_role)
            except discord.Forbidden:
                print("[ERREUR] Le bot n'a pas les permissions de donner le rôle de service.")
        await ctx.send("🚔 **Prise de service validée.** Bon courage, les citoyens comptent sur vous !")

    elif action.lower() == "end":
        if user_id not in db_services:
            await ctx.send("⚠️ Vous n'étiez pas en service.")
            return
        
        debut = db_services.pop(user_id)
        fin = time.time()
        temps_minutes = int((fin - debut) / 60)
        
        # Sécurité pour les tests rapides (si 0 minute passée, on donne quand même une base)
        if temps_minutes == 0:
            temps_minutes = 1
        
        salaire = temps_minutes * 10
        xp_gagne = temps_minutes * 5
        
        user["argent"] += salaire
        user["xp_gendarme"] += xp_gagne
        
        if en_service_role:
            try:
                await ctx.author.remove_roles(en_service_role)
            except discord.Forbidden:
                pass
            
        embed = discord.Embed(title="🧾 RAPPORT DE FIN DE SERVICE", color=discord.Color.gold())
        embed.add_field(name="Temps effectué", value=f"{temps_minutes} minute(s)", inline=False)
        embed.add_field(name="Salaire versé", value=f"{salaire}$", inline=True)
        embed.add_field(name="XP Faction", value=f"+{xp_gagne} XP", inline=True)
        await ctx.send(embed=embed)

@bot.command(name="carriere")
async def afficher_carriere(ctx):
    """Affiche l'XP et le grade actuel du joueur."""
    user = get_or_create_user(ctx.author.id)
    embed = discord.Embed(title="🎖️ Évolution de Carrière Gendarmerie", color=discord.Color.teal())
    embed.add_field(name="Grade Actuel", value=user["grade_gendarme"], inline=True)
    embed.add_field(name="Points d'Expérience", value=f"{user['xp_gendarme']} XP", inline=True)
    await ctx.send(embed=embed)

# ==============================================================================
# 🚔 MODULE INTERVENTIONS GENDARMERIE
# ==============================================================================

@bot.command(name="enlever-points")
@commands.has_any_role(ROLE_GENDARME_ID)
async def enlever_points(ctx, member: discord.Member, points: int, *, raison: str):
    """Retire des points à un civil (Réservé Gendarmerie)."""
    user = get_or_create_user(member.id)
    
    if not user["permis"]:
        await ctx.send("❌ Cet individu n'a pas le permis de conduire.")
        return
        
    user["points"] -= points
    msg = f"👮 Le Gendarme **{ctx.author.display_name}** a retiré **{points} points** à {member.mention}.\n**Raison :** {raison}\n"
    
    if user["points"] <= 0:
        user["points"] = 0
        user["suspendu_jusqua"] = datetime.now() + timedelta(days=7)
        msg += "🛑 **Le permis a été automatiquement SUSPENDU pour solde de points nul (7 jours) !**"
        
    await ctx.send(msg)

@bot.command(name="suspendre-permis")
@commands.has_any_role(ROLE_GENDARME_ID)
async def suspendre_permis(ctx, member: discord.Member, jours: int, *, raison: str):
    """Suspend immédiatement le permis d'un individu pour X jours (Réservé Gendarmerie)."""
    user = get_or_create_user(member.id)
    
    if not user["permis"]:
        await ctx.send("❌ Cet individu n'a pas de permis valide à suspendre.")
        return
        
    user["suspendu_jusqua"] = datetime.now() + timedelta(days=jours)
    
    embed = discord.Embed(title="🛑 RETRAIT IMMÉDIAT DU PERMIS", color=discord.Color.dark_red())
    embed.add_field(name="Contrevenant", value=member.mention, inline=True)
    embed.add_field(name="Agent", value=ctx.author.display_name, inline=True)
    embed.add_field(name="Durée de rétention", value=f"{jours} jours", inline=True)
    embed.add_field(name="Motif", value=raison, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name="donner-permis")
async def donner_permis(ctx, member: discord.Member):
    """Attribue le permis de conduire à un joueur (Simule l'auto-école)."""
    user = get_or_create_user(member.id)
    user["permis"] = True
    user["points"] = 12
    user["suspendu_jusqua"] = None
    await ctx.send(f"🚗 Le permis de conduire de {member.mention} a été validé avec succès (12/12 pts).")

# ==============================================================================
# 📜 L'INDEX DES COMMANDES (/cmds)
# ==============================================================================

@bot.command(name="cmds")
async def liste_commandes(ctx):
    """Affiche l'aide de toutes les commandes disponibles."""
    embed = discord.Embed(
        title="📜 INDEX DES COMMANDES DE L'ADMINISTRATION RP", 
        description="Voici la liste complète des intéractions. *Rappel : Tapez les commandes en entier, elles n'apparaissent pas dans la liste automatique de Discord.*",
        color=discord.Color.blurple()
    )
    
    embed.add_field(
        name="👤 Pôle Citoyen", 
        value="`/creer-identite [Prenom] [Nom]` • Crée ton identité civile\n`/carte-identite` • Visualise tes papiers d'identité\n`/permis` • Vérifie ton code et tes points restants", 
        inline=False
    )
    
    embed.add_field(
        name="💼 Pôle Faction / Métier", 
        value="`/service start` • Entre en service actif (lance le compteur)\n`/service end` • Termine ton service (reçois ton salaire et ton XP)\n`/carriere` • Regarde ton grade et ton expérience", 
        inline=False
    )
    
    embed.add_field(
        name="🚔 Pôle Gendarmerie (Requiert le rôle)", 
        value="`/donner-permis [@joueur]` • Enregistre le permis d'un citoyen\n`/enlever-points [@joueur] [nb] [raison]` • Sanction routière\n`/suspendre-permis [@joueur] [jours] [raison]` • Rétention du permis", 
        inline=False
    )
    
    embed.set_footer(text="FR RP MANAGER • Système d'administration automatisé.")
    await ctx.send(embed=embed)

# ==============================================================================
# 🚀 CONNEXION DU BOT
# ==============================================================================
token = os.environ.get("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ Erreur critique : La variable d'environnement DISCORD_TOKEN n'a pas été trouvée.")
