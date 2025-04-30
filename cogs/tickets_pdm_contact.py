import discord
from discord.ext import commands
from discord.ui import View, Select, Button, Modal, TextInput
from config import LOG_TICKET_PDM_CHANNEL_ID, CATEGORY_PDM_CONTACT_MAPPING, MAX_PDM_TICKETS, PDM_ROLE_ID, OWNER_ENTREPRISES_ROLE_ID, MANAGER_ENTREPRISES_ROLE_ID, LEGAL_MANAGER_ENTREPRISES_ROLE_ID
import os

ticket_lspd_count = {}

async def log_lspd_ticket_action(action, user, ticket_name, category=None, reason=None):
    log_channel = discord.utils.get(user.guild.text_channels, id=LOG_TICKET_PDM_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="Log Ticket Action",
            description=f"{action} - Ticket {ticket_name}",
            color=discord.Color.from_rgb(0, 68, 214) if action == "Ouverture" else discord.Color.red()
        )
        embed.add_field(name="Utilisateur", value=user.mention, inline=False)
        embed.add_field(name="Ticket", value=ticket_name, inline=False)
        if category:
            embed.add_field(name="Catégorie", value=category, inline=False)
        if reason:
            embed.add_field(name="Raison", value=reason, inline=False)
        embed.set_footer(text=f"Action effectuée le {user.guild.me.created_at.strftime('%d/%m/%Y à %H:%M:%S')}")
        await log_channel.send(embed=embed)

class TicketPDMContactView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketPDMContactSelect())

class TicketPDMContactSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=key, value=key) for key in CATEGORY_PDM_CONTACT_MAPPING.keys()
        ]
        super().__init__(placeholder="Sélectionnez une option", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketPDMContactReasonModal(self.values[0]))


class TicketPDMContactReasonModal(Modal, title="Raison du ticket"):
    def __init__(self, category):
        super().__init__()
        self.category = category
        self.reason = TextInput(label="Décrivez la raison de votre ticket", style=discord.TextStyle.paragraph)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        user_tickets = ticket_lspd_count.get(interaction.user.id, 0)
        if user_tickets >= MAX_PDM_TICKETS:
            await interaction.response.send_message("Vous avez atteint le nombre maximum de tickets.", ephemeral=True)
            return
        
        category_id = CATEGORY_PDM_CONTACT_MAPPING[self.category]
        category = discord.utils.get(interaction.guild.categories, id=category_id)
        if category is None:
            await interaction.response.send_message("Catégorie introuvable.", ephemeral=True)
            return
        
        ticket_name_map = {
            "Contact Direction P.D.M.": "contact"
        }

        ticket_prefix = ticket_name_map.get(self.category, "ticket")
        ticket_channel = await interaction.guild.create_text_channel(
            name=f"{ticket_prefix}-{interaction.user.name}", category=category
        )

        ticket_lspd_count[interaction.user.id] = user_tickets + 1

        await ticket_channel.set_permissions(interaction.guild.default_role, read_messages=False)
        await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        roles = [
            discord.utils.get(interaction.guild.roles, id=PDM_ROLE_ID),
            discord.utils.get(interaction.guild.roles, id=OWNER_ENTREPRISES_ROLE_ID),
            discord.utils.get(interaction.guild.roles, id=MANAGER_ENTREPRISES_ROLE_ID),
            discord.utils.get(interaction.guild.roles, id=LEGAL_MANAGER_ENTREPRISES_ROLE_ID)
        ]

        for role in roles:
            await ticket_channel.set_permissions(role, read_messages=True, send_messages=True)

        ticket_type = self.category
        if ticket_type == "Contact Direction P.D.M.":
            embed = discord.Embed(
            title="<:pdm:1358014852802805821> **- Contact Direction P.D.M.**",
            color=discord.Color.from_rgb(0, 68, 214)
         )
            embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/rw2tk45r8vxt9i368a9zf/PDM.png?rlkey=fep1z8abfe8vzj84vzdpwyrth&st=pirbsyoa&dl=0&raw=1")
            embed.add_field(
                name="Merci d'indiquer les informations si dessous",
                value="** **\n"
                      "** **",
                inline=False
            )
            embed.add_field(
                name="👤 - Informations de l'ouverture du ticket",
                value="<a:bluearrow:1358065377468219483> Nom est Prénom RP\n"
                      "<a:bluearrow:1358065377468219483> Pourquoi ouvrez-vous un ticket ?",
                inline=False
            )
            embed.add_field(
                name="Sujet",
                value=f"{self.category}",
                inline=True
            )
            embed.add_field(
                name="Raison",
                value=f"{self.reason.value}",
                inline=True
            )
            embed.add_field(
                name="Date et Heure",
                value=f"{interaction.created_at.strftime('%d/%m/%Y à %H:%M:%S')}",
                inline=True
            )
            embed.set_footer(text="Merci de patienter, un membre de la direction du P.D.M. vous répondra rapidement !", icon_url="https://www.dropbox.com/scl/fi/rw2tk45r8vxt9i368a9zf/PDM.png?rlkey=fep1z8abfe8vzj84vzdpwyrth&st=pirbsyoa&dl=0&raw=1")

        close_view = CloseTicketPDMContactView(ticket_channel, interaction.user.id)
        await ticket_channel.send(embed=embed, content=f"<@&{PDM_ROLE_ID}> {interaction.user.mention}", view=close_view)
        
        # Envoi du log pour l'ouverture du ticket
        await log_lspd_ticket_action("Ouverture", interaction.user, ticket_channel.name, self.category, self.reason.value)
        
        await interaction.response.send_message(f"Votre ticket a été ouvert : {ticket_channel.mention}", ephemeral=True)

        await interaction.message.edit(view=TicketPDMContactView())

class CloseTicketPDMContactView(View):
    def __init__(self, channel, user_id):
        super().__init__(timeout=None)
        self.channel = channel
        self.user_id = user_id

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CloseTicketPDMContactModal(self.channel, self.user_id))

class CloseTicketPDMContactModal(Modal, title="Raison de la fermeture du ticket"):
    def __init__(self, channel, user_id):
        super().__init__()
        self.channel = channel
        self.user_id = user_id
        self.reason = TextInput(label="Pourquoi fermez-vous ce ticket ?", style=discord.TextStyle.paragraph)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id == self.user_id or any(role.id == PDM_ROLE_ID for role in interaction.user.roles):
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

class TicketsPDMContact(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def panel_pdm1(self, ctx):
        embed = discord.Embed(
            title="<:pdm:1358014852802805821> **- Ticket Contact Direction P.D.M. - Borderlife**",
            description="Sélectionnez une option ci-dessous pour ouvrir un ticket. Un membre de la direction du P.D.M. vous contactera rapidement.",
            color=discord.Color.from_rgb(0, 68, 214)
        )
        embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/rw2tk45r8vxt9i368a9zf/PDM.png?rlkey=fep1z8abfe8vzj84vzdpwyrth&st=pirbsyoa&dl=0&raw=1")  # Remplace cette URL par l'image de ton choix
        embed.add_field(
            name="<:bluepin:1358014322147721226> **- Comment ça fonctionne**",
            value="Choisissez l'option qui correspond à votre besoin et un membre de la direction du P.D.M. vous répondra rapidement.\n"
                  "** **",
            inline=False
        )
        embed.add_field(
            name="<:ticket:1358014740802306048> **- Options de tickets**",
            value="<a:bluearrow:1358065377468219483> **Contacter le Direction** - Si vous souhaitez contacter la direction",
        inline=False
    )
        embed.set_footer(text="Of course you are !", icon_url="https://www.dropbox.com/scl/fi/rw2tk45r8vxt9i368a9zf/PDM.png?rlkey=fep1z8abfe8vzj84vzdpwyrth&st=pirbsyoa&dl=0&raw=1")  # Remplace cette URL par celle de ton choix

        await ctx.send(embed=embed, view=TicketPDMContactView())

async def setup(bot):
    await bot.add_cog(TicketsPDMContact(bot))