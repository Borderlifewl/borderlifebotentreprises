import discord
from discord.ext import commands
from discord.ui import View, Select, Button, Modal, TextInput
from config import LOG_TICKET_LSPD_CHANNEL_ID, CATEGORY_LSPD_SUPERVISOR_MAPPING, MAX_LSPD_TICKETS, LSPD_ROLE_SUPERVISOR_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID
import os

ticket_lspd_count = {}

async def log_lspd_ticket_action(action, user, ticket_name, category=None, reason=None):
    log_channel = discord.utils.get(user.guild.text_channels, id=LOG_TICKET_LSPD_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="Log Ticket Action",
            description=f"{action} - Ticket {ticket_name}",
            color=discord.Color.from_rgb(2, 39, 81) if action == "Ouverture" else discord.Color.red()
        )
        embed.add_field(name="Utilisateur", value=user.mention, inline=False)
        embed.add_field(name="Ticket", value=ticket_name, inline=False)
        if category:
            embed.add_field(name="Catégorie", value=category, inline=False)
        if reason:
            embed.add_field(name="Raison", value=reason, inline=False)
        embed.set_footer(text=f"Action effectuée le {user.guild.me.created_at.strftime('%d/%m/%Y à %H:%M:%S')}")
        await log_channel.send(embed=embed)

class TicketLSPDSupervisorView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketLSPDSupervisorSelect())

class TicketLSPDSupervisorSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=key, value=key) for key in CATEGORY_LSPD_SUPERVISOR_MAPPING.keys()
        ]
        super().__init__(placeholder="Sélectionnez une option", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketLSPDSupervisorReasonModal(self.values[0]))


class TicketLSPDSupervisorReasonModal(Modal, title="Raison du ticket"):
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
        
        category_id = CATEGORY_LSPD_SUPERVISOR_MAPPING[self.category]
        category = discord.utils.get(interaction.guild.categories, id=category_id)
        if category is None:
            await interaction.response.send_message("Catégorie introuvable.", ephemeral=True)
            return
        
        ticket_name_map = {
            "Supervisor Team": "supervisor"
        }

        ticket_prefix = ticket_name_map.get(self.category, "ticket")
        ticket_channel = await interaction.guild.create_text_channel(
            name=f"{ticket_prefix}-{interaction.user.name}", category=category
        )

        ticket_lspd_count[interaction.user.id] = user_tickets + 1

        await ticket_channel.set_permissions(interaction.guild.default_role, read_messages=False)  # Cache le ticket pour @everyone
        await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)  # Ajoute l'utilisateur qui a ouvert le ticket
        roles = [
            discord.utils.get(interaction.guild.roles, id=LSPD_ROLE_SUPERVISOR_ID),
            discord.utils.get(interaction.guild.roles, id=OWNER_FDO_ROLE_ID),
            discord.utils.get(interaction.guild.roles, id=MANAGER_FDO_ROLE_ID),
            discord.utils.get(interaction.guild.roles, id=LEGAL_MANAGER_FDO_ROLE_ID)
        ]

        for role in roles:
            await ticket_channel.set_permissions(role, read_messages=True, send_messages=True)

        ticket_type = self.category
        if ticket_type == "Supervisor Team":
            embed = discord.Embed(
            title="Contact Supervisor Team",
            color=discord.Color.from_rgb(2, 39, 81)
         )
            embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/7noftydvgoqkqsv1d99vj/Logo_lspd.png?rlkey=093qq9nltl5qtdppgj40dyvbu&st=978muzlm&dl=0&raw=1")
            embed.add_field(
                name="Merci d'indiquer ces informations avant tout :",
                value="- Nom et Prénom\n"
                      "- Matricule\n"
                      "- Raison détaillée de l'ouverture du ticket",
                inline=False
            )
            embed.add_field(
                name="🏷️ Sujet",
                value=f"{self.category}",
                inline=True
            )
            embed.add_field(
                name="🔎 Raison",
                value=f"{self.reason.value}",
                inline=True
            )
            embed.add_field(
                name="📅 Date et Heure",
                value=f"{interaction.created_at.strftime('%d/%m/%Y à %H:%M:%S')}",
                inline=True
            )
            embed.set_footer(text="Merci de patienter, un membre du Supervisor Team vous répondra rapidement !", icon_url="https://www.dropbox.com/scl/fi/7noftydvgoqkqsv1d99vj/Logo_lspd.png?rlkey=093qq9nltl5qtdppgj40dyvbu&st=978muzlm&dl=0&raw=1")

        close_view = CloseTicketLSPDSupervisorView(ticket_channel, interaction.user.id)
        await ticket_channel.send(embed=embed, content=f"<@&{LSPD_ROLE_SUPERVISOR_ID}> {interaction.user.mention}", view=close_view)
        
        # Envoi du log pour l'ouverture du ticket
        await log_lspd_ticket_action("Ouverture", interaction.user, ticket_channel.name, self.category, self.reason.value)
        
        await interaction.response.send_message(f"Votre ticket a été ouvert : {ticket_channel.mention}", ephemeral=True)

        await interaction.message.edit(view=TicketLSPDSupervisorView())

class CloseTicketLSPDSupervisorView(View):
    def __init__(self, channel, user_id):
        super().__init__(timeout=None)
        self.channel = channel
        self.user_id = user_id

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CloseTicketLSPDSupervisorModal(self.channel, self.user_id))

class CloseTicketLSPDSupervisorModal(Modal, title="Raison de la fermeture du ticket"):
    def __init__(self, channel, user_id):
        super().__init__()
        self.channel = channel
        self.user_id = user_id
        self.reason = TextInput(label="Pourquoi fermez-vous ce ticket ?", style=discord.TextStyle.paragraph)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id == self.user_id or any(role.id == LSPD_ROLE_SUPERVISOR_ID for role in interaction.user.roles):
            ticket_name = self.channel.name

            # Défer la réponse pour éviter une erreur de timeout
            await interaction.response.defer()

            # Envoyer le log de fermeture avec la raison
            await log_lspd_ticket_action("Fermeture", interaction.user, ticket_name, reason=self.reason.value)

            # Mettre à jour le compteur de tickets de l'utilisateur
            ticket_lspd_count[self.user_id] = max(0, ticket_lspd_count.get(self.user_id, 0) - 1)

            # Fermer le ticket après avoir envoyé la raison
            await self.channel.delete()
        else:
            await interaction.response.send_message("Vous n'avez pas la permission de fermer ce ticket.", ephemeral=True)

class TicketsLSPDSupervisor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def panel_lspd3(self, ctx):
        embed = discord.Embed(
            title="Ticket L.S.P.D. Supervisor Team - Borderlife",
            description="Pour contacter les Supervisor Team merci d'ouvrir un ticket dans cette catégorie.\n"
                        "Un membre du Supervisor Team vous contactera rapidement.",
            color=discord.Color.from_rgb(2, 39, 81)
        )
        embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/7noftydvgoqkqsv1d99vj/Logo_lspd.png?rlkey=093qq9nltl5qtdppgj40dyvbu&st=978muzlm&dl=0&raw=1")  # Remplace cette URL par l'image de ton choix
        embed.set_footer(text="Protéger et Servir !", icon_url="https://www.dropbox.com/scl/fi/7noftydvgoqkqsv1d99vj/Logo_lspd.png?rlkey=093qq9nltl5qtdppgj40dyvbu&st=978muzlm&dl=0&raw=1")  # Remplace cette URL par celle de ton choix

        await ctx.send(embed=embed, view=TicketLSPDSupervisorView())

    @commands.command()
    @commands.has_any_role(LSPD_ROLE_SUPERVISOR_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID)
    async def ticket_lspd3_add(self, ctx, member: discord.Member):
        if ctx.channel.category and ctx.channel.category.id in CATEGORY_LSPD_SUPERVISOR_MAPPING.values():
            await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)
            await ctx.send(f"{member.mention} a été ajouté au ticket.")
        else:
            await ctx.send("Cette commande doit être exécutée dans un ticket LSPD.")
    
    @commands.command()
    @commands.has_any_role(LSPD_ROLE_SUPERVISOR_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID)
    async def ticket_lspd3_rem(self, ctx, member: discord.Member):
        if ctx.channel.category and ctx.channel.category.id in CATEGORY_LSPD_SUPERVISOR_MAPPING.values():
            await ctx.channel.set_permissions(member, overwrite=None)
            await ctx.send(f"{member.mention} a été retiré du ticket.")
        else:
            await ctx.send("Cette commande doit être exécutée dans un ticket LSPD.")
    
    @commands.command()
    @commands.has_any_role(LSPD_ROLE_SUPERVISOR_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID)
    async def ticket_lspd3_claim(self, ctx):
        await ctx.send(f"L'agent {ctx.author.mention} a claim le ticket de {ctx.channel.name}.")

async def setup(bot):
    await bot.add_cog(TicketsLSPDSupervisor(bot))