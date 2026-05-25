import discord
from discord.ext import commands
import os
import time
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

# ==============================================================================
# 🌐 CONFIGURATION DU SERVEUR WEB (Pour Render + UptimeRobot)
# ==============================================================================
app = Flask('')

@app.route('/')
def home():
    return "Bot RP Administration en ligne et fonctionnel !"

def run_web_server():
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port)

# Lancement du serveur web dans un thread secondaire
Thread(target=run_web_server).start()

# ==============================================================================
# 🤖 CONFIGURATION DU BOT DISCORD
# ==============================================================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# 💾 BASE DE DONNÉES TEMPORAIRE (En production, privilégier SQLite ou MongoDB)
# Structure d'un utilisateur : 
# { id: { "nom": str, "prenom": str, "permis": bool, "points": int, "suspendu_jusqua": datetime, "xp_gendarme": int, "argent": int } }
db_users = {}

# { id: timestamp_debut }
db_services = {}

# 🔒 ROLES DE CONFIGURATION (À adapter ou automatiser via des commandes)
ROLE_GENDARME_ID = 123456789012345678  # Remplace par l'ID du rôle Gendarme
ROLE_EN_SERVICE_ID = 876543210987654321  # Remplace par l'ID du rôle [En Service]

def get_or_create_user(user_id):
    """Initialise un profil civil s'il n'existe pas."""
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
    print(f"Connecté en tant que {bot.user.name}")

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
    """Gère les prises et fins de service (/service start /service end)."""
    user_id = ctx.author.id
    user = get_or_create_user(user_id)
    
    # Vérification si le membre est gendarme (pour l'exemple)
    gendarme_role = ctx.guild.get_role(ROLE_GENDARME_ID)
    en_service_role = ctx.guild.get_role(ROLE_EN_SERVICE_ID)
    
    if gendarme_role not in ctx.author.roles:
        await ctx.send("❌ Vous ne faites partie d'aucun métier de service public.")
        return

    if action.lower() == "start":
        if user_id in db_services:
            await ctx.send("⚠️ Vous êtes déjà en service !")
            return
        
        db_services[user_id] = time.time()
        if en_service_role:
            await ctx.author.add_roles(en_service_role)
        await ctx.send("🚔 **Prise de service validée.** Bon courage en patrouille !")

    elif action.lower() == "end":
        if user_id not in db_services:
            await ctx.send("⚠️ Vous n'étiez pas en service.")
            return
        
        debut = db_services.pop(user_id)
        fin = time.time()
        temps_minutes = int((fin - debut) / 60) # En prod, calculer à la minute.
        
        # Exemple de barème : 10$ et 5 XP par minute en service
        salaire = temps_minutes * 10
        xp_gagne = temps_minutes * 5
        
        user["argent"] += salaire
        user["xp_gendarme"] += xp_gagne
        
        if en_service_role:
            await ctx.author.remove_roles(en_service_role)
            
        embed = discord.Embed(title="🧾 RAPPORT DE FIN DE SERVICE", color=discord.Color.gold())
        embed.add_field(name="Temps effectué", value=f"{temps_minutes} minutes", inline=False)
        embed.add_field(name="Salaire versé", value=f"{salaire}$", inline=True)
        embed.add_field(name="XP Métier", value=f"+{xp_gagne} XP", inline=True)
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
        await ctx.send("❌ Cet individu n'a même pas le permis de conduire.")
        return
        
    user["points"] -= points
    msg = f"👮 Le Gendarme {ctx.author.display_name} a retiré **{points} points** à {member.mention}.\n**Raison :** {raison}\n"
    
    if user["points"] <= 0:
        user["points"] = 0
        user["suspendu_jusqua"] = datetime.now() + timedelta(days=7) # Suspendu 7 jours par défaut si 0pt
        msg += "🛑 **Le permis a été automatiquement SUSPENDU (Solde de points nul) !**"
        
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
    
    embed = discord.Embed(title="🛑 SAISIE IMMÉDIATE DU PERMIS", color=discord.Color.dark_red())
    embed.add_field(name="Contrevenant", value=member.mention, inline=True)
    embed.add_field(name="Agent verbalisateur", value=ctx.author.display_name, inline=True)
    embed.add_field(name="Durée", value=f"{jours} jours", inline=True)
    embed.add_field(name="Motif", value=raison, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name="donner-permis")
async def donner_permis(ctx, member: discord.Member):
    """Commande de test (Auto-école) pour donner le permis à quelqu'un."""
    user = get_or_create_user(member.id)
    user["permis"] = True
    user["points"] = 12
    user["suspendu_jusqua"] = None
    await ctx.send(f"🚗 Le permis de conduire de {member.mention} a été validé (12/12 pts).")

# ==============================================================================
# 📜 L'INDEX DES COMMANDES (/cmds)
# ==============================================================================

@bot.command(name="cmds")
async def liste_commandes(ctx):
    """Affiche l'aide de toutes les commandes disponibles."""
    embed = discord.Embed(
        title="📜 INDEX DES COMMANDES DE L'ADMINISTRATION RP", 
        description="Voici la liste complète des interactions disponibles classées par pôle.",
        color=discord.Color.blurple()
    )
    
    embed.add_field(
        name="👤 Pôle Citoyen", 
        value="`/creer-identite [Prenom] [Nom]` • Enregistre ton identité\n`/carte-identite` • Présente tes papiers\n`/permis` • Montre ton solde de points et tes permis", 
        inline=False
    )
    
    embed.add_field(
        name="💼 Pôle Métiers & Service", 
        value="`/service start` • Prise de service (génère ton salaire/XP)\n`/service end` • Fin de service et encaissement\n`/carriere` • Regarde ton grade et ton XP accumulée", 
        inline=False
    )
    
    embed.add_field(
        name="🚔 Pôle Gendarmerie", 
        value="`/donner-permis [@joueur]` • (Moniteur) Délivre le permis\n`/enlever-points [@joueur] [nb] [raison]` • Retire des points\n`/suspendre-permis [@joueur] [jours] [raison]` • Rétention immédiate", 
        inline=False
    )
    
    embed.set_footer(text="Système automatisé • Hébergé en continu.")
    await ctx.send(embed=embed)

# ==============================================================================
# 🚀 LANCEMENT DU BOT
# ==============================================================================
# Récupère le token stocké dans les variables d'environnement de Render
token = os.environ.get("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ Erreur : La variable DISCORD_TOKEN n'est pas configurée dans l'environnement.")
