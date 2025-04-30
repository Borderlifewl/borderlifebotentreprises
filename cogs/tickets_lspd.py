import discord
from discord.ext import commands
from discord.ui import View, Select, Button, Modal, TextInput
from config import LOG_TICKET_LSPD_CHANNEL_ID, CATEGORY_LSPD_MAPPING, MAX_LSPD_TICKETS, LSPD_ROLE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID, LSPD_RECRUITMENT_ROLE_ID, LSPD_PPA_ROLE_ID, LSPD_PPL_ROLE_ID, LSPD_DDP_ROLE_ID
import os
import asyncio
import io

ticket_lspd_count = {}
ticket_lspd_authors = {}

async def log_lspd_ticket_action(action, user, ticket_name, category=None, reason=None, opened_by=None):
    log_channel = discord.utils.get(user.guild.text_channels, id=LOG_TICKET_LSPD_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="Log Ticket Action",
            description=f"{action} - Ticket {ticket_name}",
            color=discord.Color.from_rgb(2, 39, 81) if action == "Ouverture" else discord.Color.red()
        )
        embed.add_field(name="Utilisateur", value=user.mention, inline=False)
        embed.add_field(name="Ticket", value=ticket_name, inline=False)
        if opened_by and opened_by != user:
            embed.add_field(name="Ouvert par", value=opened_by.mention, inline=False)
        if category:
            embed.add_field(name="Catégorie ou Info", value=category, inline=False)
        if reason:
            embed.add_field(name="Raison", value=reason, inline=False)
        embed.set_footer(text=f"Action effectuée le {user.guild.me.created_at.strftime('%d/%m/%Y à %H:%M:%S')}")
        await log_channel.send(embed=embed)
        
async def generate_transcript(channel: discord.TextChannel):
    transcript = io.StringIO()
    async for message in channel.history(limit=None, oldest_first=True):
        timestamp = message.created_at.strftime('%d/%m/%Y %H:%M:%S')
        author = message.author
        content = message.content or "[Embed ou Fichier]"
        transcript.write(f"[{timestamp}] {author}: {content}\n")
    transcript.seek(0)
    return discord.File(fp=transcript, filename=f"transcript_{channel.name}.txt")

class TicketLSPDView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketLSPDSelect())

class TicketLSPDSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=key, value=key) for key in CATEGORY_LSPD_MAPPING.keys()
        ]
        super().__init__(placeholder="Sélectionnez une option", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketLSPDReasonModal(self.values[0]))


class TicketLSPDReasonModal(Modal, title="Raison du ticket"):
    def __init__(self, category):
        super().__init__()
        self.category = category
        self.reason = TextInput(label="Décrivez la raison de votre ticket", style=discord.TextStyle.paragraph)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        user_tickets = ticket_lspd_count.get(interaction.user.id, 0)
        if user_tickets >= MAX_LSPD_TICKETS:
            await interaction.response.send_message("Vous avez atteint le nombre maximum de tickets.", ephemeral=True)
            return
        
        category_id = CATEGORY_LSPD_MAPPING[self.category]
        category = discord.utils.get(interaction.guild.categories, id=category_id)
        if category is None:
            await interaction.response.send_message("Catégorie introuvable.", ephemeral=True)
            return
        
        ticket_name_map = {
            "Recrutement L.S.P.D.": "recrutement",
            "P.P.A. (Permis Port d'Armes)": "ppa",
            "P.P.L. (License Pilote Privé)": "ppl",
            "Dépôt de Plainte": "plainte"
        }

        ticket_prefix = ticket_name_map.get(self.category, "ticket")
        ticket_channel = await interaction.guild.create_text_channel(
            name=f"{ticket_prefix}-{interaction.user.name}", category=category
        )

        ticket_lspd_count[interaction.user.id] = user_tickets + 1

        await ticket_channel.set_permissions(interaction.guild.default_role, read_messages=False)  # Cache le ticket pour @everyone
        await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)  # Ajoute l'utilisateur qui a ouvert le ticket
        if self.category == "Recrutement L.S.P.D.":
            allowed_roles = [LSPD_RECRUITMENT_ROLE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID]
        elif self.category == "P.P.A. (Permis Port d'Armes)":
            allowed_roles = [LSPD_PPA_ROLE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID]
        elif self.category == "P.P.L. (License Pilote Privé)":
            allowed_roles = [LSPD_PPL_ROLE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID]
        elif self.category == "Dépôt de Plainte":
            allowed_roles = [LSPD_DDP_ROLE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID]
        else:
            allowed_roles = []

        # Ajoute les rôles autorisés
        for role_id in allowed_roles:
            role = discord.utils.get(interaction.guild.roles, id=role_id)
            if role:
                await ticket_channel.set_permissions(role, read_messages=True, send_messages=True)

        ticket_type = self.category
        if ticket_type == "Recrutement L.S.P.D.":
            embed = discord.Embed(
            title="<:lspd:1361294728389328906> - Recrutement L.S.P.D.",
            color=discord.Color.from_rgb(2, 39, 81)
         )
            embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/gqhj7dk2r7dwrorq91bop/Logo_recrutement_lspd.png?rlkey=x4iaarf8lhdbyja4xpcvj7awj&st=thqro6gl&dl=0&raw=1")
            embed.add_field(
                name="Merci d'indiquer les informations si dessous",
                value="** **\n"
                      "** **",
                inline=False
            )
            embed.add_field(
                name="👤 - Informations du Citoyen",
                value="<a:bluearrow:1361296701935190228>< Nom est Prénom RP\n"
                      "<a:bluearrow:1361296701935190228>< Âge RP\n"
                      "<a:bluearrow:1361296701935190228>< Nationalité RP\n"
                      "<a:bluearrow:1361296701935190228>< Motivations (quelques lignes)",
                inline=False
            )
            embed.add_field(
                name="<:bluepin:1361330078448881674> - Sujet",
                value=f"{self.category}",
                inline=True
            )
            embed.add_field(
                name="<:bluepin:1361330078448881674> - Raison",
                value=f"{self.reason.value}",
                inline=True
            )
            embed.add_field(
                name="<:bluepin:1361330078448881674> - Date et Heure",
                value=f"{interaction.created_at.strftime('%d/%m/%Y à %H:%M:%S')}",
                inline=True
            )
            embed.set_footer(text="Merci de patienter, un membre du L.S.P.D. vous répondra rapidement !", icon_url="https://www.dropbox.com/scl/fi/7noftydvgoqkqsv1d99vj/Logo_lspd.png?rlkey=093qq9nltl5qtdppgj40dyvbu&st=978muzlm&dl=0&raw=1")
        elif ticket_type == "P.P.A. (Permis Port d'Armes)":
            embed = discord.Embed(
            title="<:lspd:1361294728389328906> - Demande de P.P.A. (Permis Port d'Armes)",
            color=discord.Color.from_rgb(2, 39, 81)
         )
            embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/7noftydvgoqkqsv1d99vj/Logo_lspd.png?rlkey=093qq9nltl5qtdppgj40dyvbu&st=978muzlm&dl=0&raw=1")
            embed.add_field(
                name="<:bluepin:1361330078448881674> - Sujet",
                value=f"{self.category}",
                inline=True
            )
            embed.add_field(
                name="<:bluepin:1361330078448881674> - Raison",
                value=f"{self.reason.value}",
                inline=True
            )
            embed.add_field(
                name="<:bluepin:1361330078448881674> - Date et Heure",
                value=f"{interaction.created_at.strftime('%d/%m/%Y à %H:%M:%S')}",
                inline=True
            )
            embed.set_footer(text="Merci de patienter, un membre du L.S.P.D. vous répondra rapidement !", icon_url="https://www.dropbox.com/scl/fi/7noftydvgoqkqsv1d99vj/Logo_lspd.png?rlkey=093qq9nltl5qtdppgj40dyvbu&st=978muzlm&dl=0&raw=1")
        elif ticket_type == "P.P.L. (License Pilote Privé)":
            embed = discord.Embed(
            title="<:lspd:1361294728389328906> - Demande de P.P.L. (License Pilote Privé)",
            color=discord.Color.from_rgb(2, 39, 81)
         )
            embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/7noftydvgoqkqsv1d99vj/Logo_lspd.png?rlkey=093qq9nltl5qtdppgj40dyvbu&st=978muzlm&dl=0&raw=1")
            embed.add_field(
                name="<:bluepin:1361330078448881674> - Sujet", 
                value=f"{self.category}", 
                inline=False
            )
            embed.add_field(
                name="<:bluepin:1361330078448881674> - Raison", 
                value=f"{self.reason.value}", 
                inline=False
            )
            embed.add_field(
                name="<:bluepin:1361330078448881674> - Date et Heure",
                value=f"{interaction.created_at.strftime('%d/%m/%Y à %H:%M:%S')}",
                inline=False
            )
            embed.set_footer(text="Merci de patienter, un membre du L.S.P.D. vous répondra rapidement !", icon_url="https://www.dropbox.com/scl/fi/7noftydvgoqkqsv1d99vj/Logo_lspd.png?rlkey=093qq9nltl5qtdppgj40dyvbu&st=978muzlm&dl=0&raw=1")
        elif ticket_type == "Dépôt de Plainte":
            embed = discord.Embed(
             title="<:lspd:1361294728389328906> - Dépôt de Plainte",
             color=discord.Color.from_rgb(2, 39, 81)
         )
            embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/7noftydvgoqkqsv1d99vj/Logo_lspd.png?rlkey=093qq9nltl5qtdppgj40dyvbu&st=978muzlm&dl=0&raw=1")
            embed.add_field(
                name="Merci d'indiquer les informations si dessous",
                value="** **\n"
                      "** **",
                inline=False
            )
            embed.add_field(
                name="👤 - Informations sur le plaignant",
                value="<a:bluearrow:1361296701935190228>< Nom est Prénom RP\n"
                      "<a:bluearrow:1361296701935190228>< Numéro de Télephone\n"
                      "<a:bluearrow:1361296701935190228>< Adresse",
                inline=False
            )
            embed.add_field(
                name="⚠️ - Informations sur l'incident",
                value="<a:bluearrow:1361296701935190228>< Date et Heure\n"
                      "<a:bluearrow:1361296701935190228>< Lieu\n"
                      "<a:bluearrow:1361296701935190228>< Type d'incident (Vol, Trafic, Agression, ...)\n"
                      "<a:bluearrow:1361296701935190228>< Nom(s) et Prénom(s) ou Pseudonyme(s) de l'auteur(s) de l'incident (si connu)\n"
                      "<a:bluearrow:1361296701935190228>< Description physique ou élèments distinctifs de/des auteur(s) (Couleur de cheveux, Taille, Vêtements, Véhicule(s), ...)",
                inline=False
            )
            embed.add_field(
                name="💬 - Description de l'incident",
                value="<a:bluearrow:1361296701935190228>< Décrivez l'incident dans les moindres détails (Déroulé des évenements, Vos actions, Les actions des autres personnes impliquées)",
                inline=False
            )
            embed.add_field(
                name="📝 - Autres Informations",
                value="<a:bluearrow:1361296701935190228>< Témoins, Préjudices, Pertes matérielles, Preuve(s), ...",
                inline=False
            )
            embed.add_field(
                name="<:bluepin:1361330078448881674> - Sujet",
                value=f"{self.category}",
                inline=True
            )
            embed.add_field(
                name="<:bluepin:1361330078448881674> - Raison",
                value=f"{self.reason.value}",
                inline=True
            )
            embed.add_field(
                name="<:bluepin:1361330078448881674> - Date et Heure",
                value=f"{interaction.created_at.strftime('%d/%m/%Y à %H:%M:%S')}",
                inline=True
            )
            embed.set_footer(text="Merci de patienter, un membre du L.S.P.D. vous répondra rapidement !", icon_url="https://www.dropbox.com/scl/fi/7noftydvgoqkqsv1d99vj/Logo_lspd.png?rlkey=093qq9nltl5qtdppgj40dyvbu&st=978muzlm&dl=0&raw=1")

        close_view = CloseTicketLSPDView(ticket_channel, interaction.user.id)
        await ticket_channel.send(embed=embed, content=f"<@&{LSPD_ROLE_ID}> {interaction.user.mention}", view=close_view)
        
        # Envoi du log pour l'ouverture du ticket
        await log_lspd_ticket_action("Ouverture", interaction.user, ticket_channel.name, self.category, self.reason.value)
        
        await interaction.response.send_message(f"Votre ticket a été ouvert : {ticket_channel.mention}", ephemeral=True)

        await interaction.message.edit(view=TicketLSPDView())

class CloseTicketLSPDView(View):
    def __init__(self, channel, user_id):
        super().__init__(timeout=None)
        self.channel = channel
        self.user_id = user_id

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CloseTicketLSPDModal(self.channel, self.user_id))

class CloseTicketLSPDModal(Modal, title="Raison de la fermeture du ticket"):
    def __init__(self, channel, user_id, claimed_by=None):  # Ajout de claimed_by
        super().__init__()
        self.channel = channel
        self.user_id = user_id
        self.claimed_by = claimed_by
        self.reason = TextInput(label="Pourquoi fermez-vous ce ticket ?", style=discord.TextStyle.paragraph)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id == self.user_id or any(role.id == LSPD_ROLE_ID for role in interaction.user.roles):
            ticket_name = self.channel.name
            await interaction.response.defer()
            extra_info = f"Claimed par : {self.claimed_by.mention}" if self.claimed_by else None
            opened_by = ticket_lspd_authors.get(self.channel.id)
            await log_lspd_ticket_action("Fermeture", interaction.user, ticket_name, reason=self.reason.value, category=extra_info, opened_by=opened_by)

            ticket_lspd_count[self.user_id] = max(0, ticket_lspd_count.get(self.user_id, 0) - 1)

            log_channel = discord.utils.get(interaction.guild.text_channels, id=LOG_TICKET_LSPD_CHANNEL_ID)
            if log_channel:
                transcript_file = await generate_transcript(self.channel)
                await log_channel.send(file=transcript_file)

            if self.channel.id in ticket_lspd_authors:
                del ticket_lspd_authors[self.channel.id]

            await self.channel.delete()
        else:
            await interaction.response.send_message("Vous n'avez pas la permission de fermer ce ticket.", ephemeral=True)

class TicketsLSPD(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def panel_lspd(self, ctx):
        embed = discord.Embed(
            title="<:lspd:1361294728389328906> - Ticket L.S.P.D. - Borderlife",
            description="Sélectionnez une option ci-dessous pour ouvrir un ticket. Un membre du L.S.P.D. vous contactera rapidement.",
            color=discord.Color.from_rgb(2, 39, 81)
        )
        embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/7noftydvgoqkqsv1d99vj/Logo_lspd.png?rlkey=093qq9nltl5qtdppgj40dyvbu&st=978muzlm&dl=0&raw=1")  # Remplace cette URL par l'image de ton choix
        embed.add_field(
            name="<:bluepin:1361330078448881674> - Comment ça fonctionne",
            value="Choisissez l'option qui correspond à votre besoin et un membre du L.S.P.D. interviendra rapidement.\n"
                  "** **",
            inline=False
        )
        embed.add_field(
            name="<:ticket:1361330133515894994> - Options de tickets",
            value="<a:bluearrow:1361296701935190228> **Recrutement L.S.P.D.**\n"
                  "➜ Si vous souhaitez vous faire recruter\n"
                  "<a:bluearrow:1361296701935190228> **P.P.A. (Permis Port d'Armes)**\n"
                  "➜ Pour passer son P.P.A.\n"
                  "<a:bluearrow:1361296701935190228> **P.P.L. (License Pilote Privé)**\n"
                  "➜ Pour passer son P.P.L.\n"
                  "<a:bluearrow:1361296701935190228> **Dépôt de Plainte**\n"
                  "➜ Si vous souhaitez déposer une plainte",
        inline=False
    )
        embed.set_footer(text="Protéger et Servir !", icon_url="https://www.dropbox.com/scl/fi/7noftydvgoqkqsv1d99vj/Logo_lspd.png?rlkey=093qq9nltl5qtdppgj40dyvbu&st=978muzlm&dl=0&raw=1")  # Remplace cette URL par celle de ton choix

        await ctx.send(embed=embed, view=TicketLSPDView())

    @commands.command()
    @commands.has_any_role(LSPD_ROLE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID)
    async def ticket_lspd_add(self, ctx, member: discord.Member):
        if ctx.channel.category and ctx.channel.category.id in CATEGORY_LSPD_MAPPING.values():
            await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)
            await ctx.send(f"{member.mention} a été ajouté au ticket.")
        else:
            await ctx.send("Cette commande doit être exécutée dans un ticket LSPD.")
    
    @commands.command()
    @commands.has_any_role(LSPD_ROLE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID)
    async def ticket_lspd_rem(self, ctx, member: discord.Member):
        if ctx.channel.category and ctx.channel.category.id in CATEGORY_LSPD_MAPPING.values():
            await ctx.channel.set_permissions(member, overwrite=None)
            await ctx.send(f"{member.mention} a été retiré du ticket.")
        else:
            await ctx.send("Cette commande doit être exécutée dans un ticket LSPD.")
    
    @commands.command()
    @commands.has_any_role(LSPD_ROLE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID)
    async def ticket_lspd_claim(self, ctx):
        await ctx.send(f"L'agent {ctx.author.mention} a claim le ticket de {ctx.channel.name}.")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def ticket_lspd_reset(self, ctx, member: discord.Member):
        ticket_lspd_count[member.id] = 0
        await ctx.send(f"Le nombre de tickets de {member.mention} a été remis à zéro.")
        
    @commands.command()
    @commands.has_any_role(LSPD_ROLE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID)
    async def ticket_lspd_rename(self, ctx, new_name: str):
        if ctx.channel.category and ctx.channel.category.id in CATEGORY_LSPD_MAPPING.values():
            await ctx.channel.edit(name=new_name)
            await ctx.send(f"Le ticket a été renommé en : {new_name}")
        else:
            await ctx.send("Cette commande peut seulement être utilisée dans un canal de ticket.")
            
    @commands.command()
    @commands.has_any_role(LSPD_ROLE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID)
    async def ticket_lspd_close(self, ctx, *, reason: str = "Aucune raison spécifiée."):
        if ctx.channel.category and ctx.channel.category.id in CATEGORY_LSPD_MAPPING.values():
            await log_lspd_ticket_action("Fermeture (commande)", ctx.author, ctx.channel.name, reason=reason)
            
            # Mise à jour du compteur si l’auteur du ticket est connu
            async for message in ctx.channel.history(limit=50):
                if message.mentions:
                    mentioned_user = message.mentions[0]
                    if mentioned_user.id in ticket_lspd_count:
                        ticket_lspd_count[mentioned_user.id] = max(0, ticket_lspd_count[mentioned_user.id] - 1)
                    break

            await ctx.send("Le ticket sera fermé dans quelques secondes...")
            await asyncio.sleep(3)
            # ✅ Transcript
            log_channel = discord.utils.get(ctx.guild.text_channels, id=LOG_TICKET_LSPD_CHANNEL_ID)
            if log_channel:
                transcript_file = await generate_transcript(ctx.channel)
                await log_channel.send(
                    file=transcript_file
                )

            await ctx.channel.delete()

        else:
            await ctx.send("❌ Cette commande doit être utilisée dans un ticket.")

async def setup(bot):
    await bot.add_cog(TicketsLSPD(bot))