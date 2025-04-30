import discord
from discord.ext import commands
from discord.ui import View, Select, Button, Modal, TextInput
from config import LOG_TICKET_VIGNERON_CHANNEL_ID, CATEGORY_VIGNERON_MAPPING, CATEGORY_VIGNERON_CONTACT_MAPPING, MAX_VIGNERON_TICKETS, VIGNERON_ROLE_ID, VIGNERON_OUVRIER_ID, OWNER_ENTREPRISES_ROLE_ID, MANAGER_ENTREPRISES_ROLE_ID, LEGAL_MANAGER_ENTREPRISES_ROLE_ID
import os
import asyncio

ticket_vigneron_count = {}

async def log_vigneron_ticket_action(action, user, ticket_name, category=None, reason=None):
    log_channel = discord.utils.get(user.guild.text_channels, id=LOG_TICKET_VIGNERON_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="Log Ticket Action",
            description=f"{action} - Ticket {ticket_name}",
            color=discord.Color.from_rgb(103, 26, 48) if action == "Ouverture" else discord.Color.red()
        )
        embed.add_field(name="Utilisateur", value=user.mention, inline=False)
        embed.add_field(name="Ticket", value=ticket_name, inline=False)
        if category:
            embed.add_field(name="Catégorie", value=category, inline=False)
        if reason:
            embed.add_field(name="Raison", value=reason, inline=False)
        embed.set_footer(text=f"Action effectuée le {user.guild.me.created_at.strftime('%d/%m/%Y à %H:%M:%S')}")
        await log_channel.send(embed=embed)

class TicketVigneronView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketVigneronSelect())

class TicketVigneronSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=key, value=key) for key in CATEGORY_VIGNERON_MAPPING.keys()
        ]
        super().__init__(placeholder="Sélectionnez une option", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketVigneronReasonModal(self.values[0]))


class TicketVigneronReasonModal(Modal, title="Raison du ticket"):
    def __init__(self, category):
        super().__init__()
        self.category = category
        self.reason = TextInput(label="Décrivez la raison de votre ticket", style=discord.TextStyle.paragraph)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        user_tickets = ticket_vigneron_count.get(interaction.user.id, 0)
        if user_tickets >= MAX_VIGNERON_TICKETS:
            await interaction.response.send_message("Vous avez atteint le nombre maximum de tickets.", ephemeral=True)
            return
        
        category_id = CATEGORY_VIGNERON_MAPPING[self.category]
        category = discord.utils.get(interaction.guild.categories, id=category_id)
        if category is None:
            await interaction.response.send_message("Catégorie introuvable.", ephemeral=True)
            return
        
        ticket_name_map = {
            "Recrutement Vigneron": "recrutement",
            "Demande d'achat de vins": "achat"
        }

        ticket_prefix = ticket_name_map.get(self.category, "ticket")
        ticket_channel = await interaction.guild.create_text_channel(
            name=f"{ticket_prefix}-{interaction.user.name}", category=category
        )

        ticket_vigneron_count[interaction.user.id] = user_tickets + 1

        await ticket_channel.set_permissions(interaction.guild.default_role, read_messages=False)
        await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        if self.category == "Recrutement Vigneron":
            allowed_roles = [VIGNERON_ROLE_ID, OWNER_ENTREPRISES_ROLE_ID, MANAGER_ENTREPRISES_ROLE_ID, LEGAL_MANAGER_ENTREPRISES_ROLE_ID]
        elif self.category == "Demande d'achat de vins":
            allowed_roles = [VIGNERON_OUVRIER_ID, OWNER_ENTREPRISES_ROLE_ID, MANAGER_ENTREPRISES_ROLE_ID, LEGAL_MANAGER_ENTREPRISES_ROLE_ID]
        else:
            allowed_roles = []

        # Ajoute les rôles autorisés
        for role_id in allowed_roles:
            role = discord.utils.get(interaction.guild.roles, id=role_id)
            if role:
                await ticket_channel.set_permissions(role, read_messages=True, send_messages=True)

        ticket_type = self.category
        if ticket_type == "Recrutement Vigneron":
            embed = discord.Embed(
            title="<:vigneron:1360559757076725842> **- Recrutement Vigneron**",
            color=discord.Color.from_rgb(103, 26, 48)
         )
            embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/azpgw4n9xit65b49bp80t/vigneron.webp?rlkey=k2rveoqkllqqe6kiqd8zy8348&st=bjhg3rz5&dl=0&raw=1")
            embed.add_field(
                name="Merci d'indiquer les informations si dessous",
                value="** **",
                inline=False
            )
            embed.add_field(
                name="👤 - Informations du Citoyen",
                value="<a:redarrow:1358065181049229538> Nom est Prénom RP\n"
                      "<a:redarrow:1358065181049229538> Âge RP\n"
                      "<a:redarrow:1358065181049229538> Nationalité RP\n"
                      "<a:redarrow:1358065181049229538> Motivations (quelques lignes)",
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
            embed.set_footer(text="Merci de patienter, un membre du Vigneron vous répondra rapidement !", icon_url="https://www.dropbox.com/scl/fi/azpgw4n9xit65b49bp80t/vigneron.webp?rlkey=k2rveoqkllqqe6kiqd8zy8348&st=bjhg3rz5&dl=0&raw=1")
        elif ticket_type == "Demande d'achat de vins":
            embed = discord.Embed(
            title="<:vigneron:1360559757076725842> **- Demande d'achat de vins Vigneron**",
            color=discord.Color.from_rgb(103, 26, 48)
         )
            embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/azpgw4n9xit65b49bp80t/vigneron.webp?rlkey=k2rveoqkllqqe6kiqd8zy8348&st=bjhg3rz5&dl=0&raw=1")
            embed.add_field(
                name="Merci d'indiquer les informations si dessous",
                value="** **",
                inline=False
            )
            embed.add_field(
                name="🛒 - Informations sur l'achat",
                value="<a:redarrow:1358065181049229538> Nom est Prénom RP\n"
                      "<a:redarrow:1358065181049229538> Pour une entreprise ou pour vous ?\n"
                      "<a:redarrow:1358065181049229538> Quelle(s) vin(s) et quelle quantité ?",
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
            embed.set_footer(text="Merci de patienter, un membre du Vigneron vous répondra rapidement !", icon_url="https://www.dropbox.com/scl/fi/azpgw4n9xit65b49bp80t/vigneron.webp?rlkey=k2rveoqkllqqe6kiqd8zy8348&st=bjhg3rz5&dl=0&raw=1")


        close_view = CloseTicketVigneronView(ticket_channel, interaction.user.id)
        await ticket_channel.send(embed=embed, content=f"<@&{VIGNERON_OUVRIER_ID}> {interaction.user.mention}", view=close_view)
        
        # Envoi du log pour l'ouverture du ticket
        await log_vigneron_ticket_action("Ouverture", interaction.user, ticket_channel.name, self.category, self.reason.value)
        
        await interaction.response.send_message(f"Votre ticket a été ouvert : {ticket_channel.mention}", ephemeral=True)

        await interaction.message.edit(view=TicketVigneronView())

class CloseTicketVigneronView(View):
    def __init__(self, channel, user_id):
        super().__init__(timeout=None)
        self.channel = channel
        self.user_id = user_id

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CloseTicketVigneronModal(self.channel, self.user_id))

class CloseTicketVigneronModal(Modal, title="Raison de la fermeture du ticket"):
    def __init__(self, channel, user_id):
        super().__init__()
        self.channel = channel
        self.user_id = user_id
        self.reason = TextInput(label="Pourquoi fermez-vous ce ticket ?", style=discord.TextStyle.paragraph)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id == self.user_id or any(role.id == VIGNERON_OUVRIER_ID for role in interaction.user.roles):
            ticket_name = self.channel.name

            # Défer la réponse pour éviter une erreur de timeout
            await interaction.response.defer()

            # Envoyer le log de fermeture avec la raison
            await log_vigneron_ticket_action("Fermeture", interaction.user, ticket_name, reason=self.reason.value)

            # Mettre à jour le compteur de tickets de l'utilisateur
            ticket_vigneron_count[self.user_id] = max(0, ticket_vigneron_count.get(self.user_id, 0) - 1)

            # Fermer le ticket après avoir envoyé la raison
            await self.channel.delete()
        else:
            await interaction.response.send_message("Vous n'avez pas la permission de fermer ce ticket.", ephemeral=True)

class TicketsVigneron(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def panel_vigneron(self, ctx):
        embed = discord.Embed(
            title="<:vigneron:1360559757076725842> **- Ticket Vigneron - Borderlife**",
            description="Sélectionnez une option ci-dessous pour ouvrir un ticket. Un membre du Vigneron vous contactera rapidement.",
            color=discord.Color.from_rgb(103, 26, 48)
        )
        embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/azpgw4n9xit65b49bp80t/vigneron.webp?rlkey=k2rveoqkllqqe6kiqd8zy8348&st=bjhg3rz5&dl=0&raw=1")  # Remplace cette URL par l'image de ton choix
        embed.add_field(
            name="<:redpin:1358014382633910443> **- Comment ça fonctionne**",
            value="Choisissez l'option qui correspond à votre besoin et un membre du Vigneron vous répondra rapidement.\n"
                  "** **",
            inline=False
        )
        embed.add_field(
            name="<:ticket:1358014740802306048> **- Options de tickets**",
            value="<a:redarrow:1358065181049229538> **Recrutement Vigneron** - Si vous souhaitez vous faire recruter\n"
                  "<a:redarrow:1358065181049229538> **Demande d'achat de vins** - Si vous souhaitez passer une commande",
        inline=False
    )
        embed.set_footer(text="Boire un canon c'est sauver un vigneron !", icon_url="https://www.dropbox.com/scl/fi/azpgw4n9xit65b49bp80t/vigneron.webp?rlkey=k2rveoqkllqqe6kiqd8zy8348&st=bjhg3rz5&dl=0&raw=1")  # Remplace cette URL par celle de ton choix

        await ctx.send(embed=embed, view=TicketVigneronView())

    @commands.command()
    @commands.has_any_role(VIGNERON_ROLE_ID, OWNER_ENTREPRISES_ROLE_ID, MANAGER_ENTREPRISES_ROLE_ID, LEGAL_MANAGER_ENTREPRISES_ROLE_ID)
    async def ticket_vigneron_add(self, ctx, member: discord.Member):
        if ctx.channel.category and ctx.channel.category.id in CATEGORY_VIGNERON_MAPPING.values() or ctx.channel.category.id in CATEGORY_VIGNERON_CONTACT_MAPPING.values():
            await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)
            await ctx.send(f"{member.mention} a été ajouté au ticket.")
        else:
            await ctx.send("Cette commande doit être exécutée dans un ticket Vigneron.")
    
    @commands.command()
    @commands.has_any_role(VIGNERON_ROLE_ID, OWNER_ENTREPRISES_ROLE_ID, MANAGER_ENTREPRISES_ROLE_ID, LEGAL_MANAGER_ENTREPRISES_ROLE_ID)
    async def ticket_vigneron_rem(self, ctx, member: discord.Member):
        if ctx.channel.category and ctx.channel.category.id in CATEGORY_VIGNERON_MAPPING.values() or ctx.channel.category.id in CATEGORY_VIGNERON_CONTACT_MAPPING.values():
            await ctx.channel.set_permissions(member, overwrite=None)
            await ctx.send(f"{member.mention} a été retiré du ticket.")
        else:
            await ctx.send("Cette commande doit être exécutée dans un ticket Vigneron.")
    
    @commands.command()
    @commands.has_any_role(VIGNERON_ROLE_ID, OWNER_ENTREPRISES_ROLE_ID, MANAGER_ENTREPRISES_ROLE_ID, LEGAL_MANAGER_ENTREPRISES_ROLE_ID)
    async def ticket_vigneron_claim(self, ctx):
        if ctx.channel.category and ctx.channel.category.id in CATEGORY_VIGNERON_MAPPING.values() or ctx.channel.category.id in CATEGORY_VIGNERON_CONTACT_MAPPING.values():
            await ctx.send(f"L'ouvrier {ctx.author.mention} a claim le ticket de {ctx.channel.name}.")
        else:
            await ctx.send("Cette commande doit être exécutée dans un ticket Vigneron.")

    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def ticket_vigneron_reset(self, ctx, member: discord.Member):
        ticket_vigneron_count[member.id] = 0
        await ctx.send(f"Le nombre de tickets de {member.mention} a été remis à zéro.")

    @commands.command()
    @commands.has_any_role(VIGNERON_ROLE_ID, OWNER_ENTREPRISES_ROLE_ID, MANAGER_ENTREPRISES_ROLE_ID, LEGAL_MANAGER_ENTREPRISES_ROLE_ID)
    async def ticket_vigneron_rename(self, ctx, new_name: str):
        if ctx.channel.category and ctx.channel.category.id in CATEGORY_VIGNERON_MAPPING.values():
            await ctx.channel.edit(name=new_name)
            await ctx.send(f"Le ticket a été renommé en : {new_name}")
        else:
            await ctx.send("Cette commande peut seulement être utilisée dans un canal de ticket.")

    @commands.command()
    @commands.has_role(VIGNERON_OUVRIER_ID)
    async def ticket_vigneron_close(self, ctx, *, reason: str = "Aucune raison spécifiée."):
        if ctx.channel.category and ctx.channel.category.id in CATEGORY_VIGNERON_MAPPING.values() or ctx.channel.category.id in CATEGORY_VIGNERON_CONTACT_MAPPING.values():
            await log_vigneron_ticket_action("Fermeture (commande)", ctx.author, ctx.channel.name, reason=reason)
            
            # Mise à jour du compteur si l’auteur du ticket est connu
            async for message in ctx.channel.history(limit=50):
                if message.mentions:
                    mentioned_user = message.mentions[0]
                    if mentioned_user.id in ticket_vigneron_count:
                        ticket_vigneron_count[mentioned_user.id] = max(0, ticket_vigneron_count[mentioned_user.id] - 1)
                    break

            await ctx.send("Le ticket sera fermé dans quelques secondes...")
            await asyncio.sleep(3)
            await ctx.channel.delete()

        else:
            await ctx.send("❌ Cette commande doit être utilisée dans un ticket.")

async def setup(bot):
    await bot.add_cog(TicketsVigneron(bot))