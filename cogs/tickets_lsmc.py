import discord
from discord.ext import commands
from discord.ui import View, Select, Button, Modal, TextInput
from config import LOG_TICKET_LSMC_CHANNEL_ID, CATEGORY_LSMC_MAPPING, MAX_LSMC_TICKETS, LSMC_ROLE_ID, LSMC_ROLE_HAUTGRADE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID
import os
import asyncio
import io

ticket_lsmc_count = {}
ticket_lsmc_authors = {}

async def log_lsmc_ticket_action(action, user, ticket_name, category=None, reason=None, opened_by=None):
    log_channel = discord.utils.get(user.guild.text_channels, id=LOG_TICKET_LSMC_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="Log Ticket Action",
            description=f"{action} - Ticket {ticket_name}",
            color=discord.Color.from_rgb(130, 0, 0) if action == "Ouverture" else discord.Color.red()
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

class TicketLSMCView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketLSMCSelect())

class TicketLSMCSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=key, value=key) for key in CATEGORY_LSMC_MAPPING.keys()
        ]
        super().__init__(placeholder="Sélectionnez une option", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketLSMCReasonModal(self.values[0]))


class TicketLSMCReasonModal(Modal, title="Raison du ticket"):
    def __init__(self, category):
        super().__init__()
        self.category = category
        self.reason = TextInput(label="Décrivez la raison de votre ticket", style=discord.TextStyle.paragraph)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        user_tickets = ticket_lsmc_count.get(interaction.user.id, 0)
        if user_tickets >= MAX_LSMC_TICKETS:
            await interaction.response.send_message("Vous avez atteint le nombre maximum de tickets.", ephemeral=True)
            return
        
        category_id = CATEGORY_LSMC_MAPPING[self.category]
        category = discord.utils.get(interaction.guild.categories, id=category_id)
        if category is None:
            await interaction.response.send_message("Catégorie introuvable.", ephemeral=True)
            return
        
        ticket_name_map = {
            "Recrutement L.S.M.C.": "recrutement",
            "Demande de Rendez-vous": "rendez-vous"
        }

        ticket_prefix = ticket_name_map.get(self.category, "ticket")
        ticket_channel = await interaction.guild.create_text_channel(
            name=f"{ticket_prefix}-{interaction.user.name}", category=category
        )

        ticket_lsmc_count[interaction.user.id] = user_tickets + 1

        await ticket_channel.set_permissions(interaction.guild.default_role, read_messages=False)  # Cache le ticket pour @everyone
        await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)  # Ajoute l'utilisateur qui a ouvert le ticket
        if self.category == "Recrutement L.S.M.C.":
            allowed_roles = [LSMC_ROLE_HAUTGRADE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID]
        elif self.category == "Demande de Rendez-vous":
            allowed_roles = [LSMC_ROLE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID]
        else:
            allowed_roles = []

        # Ajoute les rôles autorisés
        for role_id in allowed_roles:
            role = discord.utils.get(interaction.guild.roles, id=role_id)
            if role:
                await ticket_channel.set_permissions(role, read_messages=True, send_messages=True)

        ticket_type = self.category
        if ticket_type == "Recrutement L.S.M.C.":
            embed = discord.Embed(
            title="<:lsmc:1361294444749656064> - Recrutement L.S.M.C.",
            color=discord.Color.from_rgb(130, 0, 0)
         )
            embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/pdgy9iwbqr9ckqz1gob1m/LSMC.png?rlkey=0xbjwwau2rbo5fs41w0cdwijf&st=qmqddn8z&dl=0&raw=1")
            embed.add_field(
                name="Merci d'indiquer les informations si dessous",
                value="** **\n"
                      "** **",
                inline=False
            )
            embed.add_field(
                name="👤 - Informations du Citoyen",
                value="<a:redarrow:1361296677406900426> Nom est Prénom RP\n"
                      "<a:redarrow:1361296677406900426> Âge RP\n"
                      "<a:redarrow:1361296677406900426> Nationalité RP\n"
                      "<a:redarrow:1361296677406900426> Motivations (quelques lignes)",
                inline=False
            )
            embed.add_field(
                name="<:redpin:1361330101370880154> - Sujet",
                value=f"{self.category}",
                inline=True
            )
            embed.add_field(
                name="<:redpin:1361330101370880154> - Raison",
                value=f"{self.reason.value}",
                inline=True
            )
            embed.add_field(
                name="<:redpin:1361330101370880154> - Date et Heure",
                value=f"{interaction.created_at.strftime('%d/%m/%Y à %H:%M:%S')}",
                inline=True
            )
            embed.set_footer(text="Merci de patienter, un membre du L.S.M.C. vous répondra rapidement !", icon_url="https://www.dropbox.com/scl/fi/pdgy9iwbqr9ckqz1gob1m/LSMC.png?rlkey=0xbjwwau2rbo5fs41w0cdwijf&st=qmqddn8z&dl=0&raw=1")
        elif ticket_type == "Demande de Rendez-vous":
            embed = discord.Embed(
            title="<:lsmc:1361294444749656064> - Demande de Rendez-vous",
            color=discord.Color.from_rgb(130, 0, 0)
         )
            embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/pdgy9iwbqr9ckqz1gob1m/LSMC.png?rlkey=0xbjwwau2rbo5fs41w0cdwijf&st=qmqddn8z&dl=0&raw=1")
            embed.add_field(
                name="Merci d'indiquer les informations si dessous",
                value="** **\n"
                      "** **",
                inline=False
            )
            embed.add_field(
                name="📅 - Description du Rendez-vous",
                value="<a:redarrow:1361296677406900426> Nom est Prénom RP\n"
                      "<a:redarrow:1361296677406900426> Âge RP\n"
                      "<a:redarrow:1361296677406900426> Nationalité RP\n"
                      "<a:redarrow:1361296677406900426> Quel type de rendez-vous ?\n"
                      "<a:redarrow:1361296677406900426> Informations sur le rendez-vous",
                inline=False
            )
            embed.add_field(
                name="<:redpin:1361330101370880154> - Sujet",
                value=f"{self.category}",
                inline=True
            )
            embed.add_field(
                name="<:redpin:1361330101370880154> - Raison",
                value=f"{self.reason.value}",
                inline=True
            )
            embed.add_field(
                name="<:redpin:1361330101370880154> - Date et Heure",
                value=f"{interaction.created_at.strftime('%d/%m/%Y à %H:%M:%S')}",
                inline=True
            )
            embed.set_footer(text="Merci de patienter, un membre du L.S.M.C. vous répondra rapidement !", icon_url="https://www.dropbox.com/scl/fi/pdgy9iwbqr9ckqz1gob1m/LSMC.png?rlkey=0xbjwwau2rbo5fs41w0cdwijf&st=qmqddn8z&dl=0&raw=1")

        close_view = CloseTicketLSMCView(ticket_channel, interaction.user.id)
        await ticket_channel.send(embed=embed, content=f"<@&{LSMC_ROLE_ID}> {interaction.user.mention}", view=close_view)
        
        # Envoi du log pour l'ouverture du ticket
        await log_lsmc_ticket_action("Ouverture", interaction.user, ticket_channel.name, self.category, self.reason.value)
        
        await interaction.response.send_message(f"Votre ticket a été ouvert : {ticket_channel.mention}", ephemeral=True)

        await interaction.message.edit(view=TicketLSMCView())

class CloseTicketLSMCView(View):
    def __init__(self, channel, user_id):
        super().__init__(timeout=None)
        self.channel = channel
        self.user_id = user_id

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CloseTicketLSMCModal(self.channel, self.user_id))

class CloseTicketLSMCModal(Modal, title="Raison de la fermeture du ticket"):
    def __init__(self, channel, user_id, claimed_by=None):  # Ajout de claimed_by
        super().__init__()
        self.channel = channel
        self.user_id = user_id
        self.claimed_by = claimed_by
        self.reason = TextInput(label="Pourquoi fermez-vous ce ticket ?", style=discord.TextStyle.paragraph)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id == self.user_id or any(role.id == LSMC_ROLE_ID for role in interaction.user.roles):
            ticket_name = self.channel.name
            await interaction.response.defer()
            extra_info = f"Claimed par : {self.claimed_by.mention}" if self.claimed_by else None
            opened_by = ticket_lsmc_authors.get(self.channel.id)
            await log_lsmc_ticket_action("Fermeture", interaction.user, ticket_name, reason=self.reason.value, category=extra_info, opened_by=opened_by)

            ticket_lsmc_count[self.user_id] = max(0, ticket_lsmc_count.get(self.user_id, 0) - 1)

            log_channel = discord.utils.get(interaction.guild.text_channels, id=LOG_TICKET_LSMC_CHANNEL_ID)
            if log_channel:
                transcript_file = await generate_transcript(self.channel)
                await log_channel.send(file=transcript_file)

            if self.channel.id in ticket_lsmc_authors:
                del ticket_lsmc_authors[self.channel.id]

            await self.channel.delete()
        else:
            await interaction.response.send_message("Vous n'avez pas la permission de fermer ce ticket.", ephemeral=True)

class TicketsLSMC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def panel_lsmc(self, ctx):
        embed = discord.Embed(
            title="<:lsmc:1361294444749656064> - Ticket L.S.M.C. - Borderlife",
            description="Sélectionnez une option ci-dessous pour ouvrir un ticket. Un membre du L.S.P.D. vous contactera rapidement.",
            color=discord.Color.from_rgb(130, 0, 0)
        )
        embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/pdgy9iwbqr9ckqz1gob1m/LSMC.png?rlkey=0xbjwwau2rbo5fs41w0cdwijf&st=qmqddn8z&dl=0&raw=1")  # Remplace cette URL par l'image de ton choix
        embed.add_field(
            name="<:redpin:1361330101370880154> - Comment ça fonctionne",
            value="Choisissez l'option qui correspond à votre besoin et un membre du L.S.P.D. interviendra rapidement.\n"
                  "** **",
            inline=False
        )
        embed.add_field(
            name="<:ticket:1361330133515894994> - Options de tickets",
            value="<a:redarrow:1361296677406900426> **Recrutement L.S.P.D.** ➜ Si vous souhaitez vous faire recruter\n"
                  "<a:redarrow:1361296677406900426> **P.P.A. (Permis Port d'Armes)** ➜ Pour passer son P.P.A.\n",
        inline=False
    )
        embed.set_footer(text="Sécurité à l'hôpital : la priorité pour des soins sans risques !", icon_url="https://www.dropbox.com/scl/fi/pdgy9iwbqr9ckqz1gob1m/LSMC.png?rlkey=0xbjwwau2rbo5fs41w0cdwijf&st=qmqddn8z&dl=0&raw=1")  # Remplace cette URL par celle de ton choix

        await ctx.send(embed=embed, view=TicketLSMCView())

    @commands.command()
    @commands.has_any_role(LSMC_ROLE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID)
    async def ticket_lsmc_add(self, ctx, member: discord.Member):
        if ctx.channel.category and ctx.channel.category.id in CATEGORY_LSMC_MAPPING.values():
            await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)
            await ctx.send(f"{member.mention} a été ajouté au ticket.")
        else:
            await ctx.send("Cette commande doit être exécutée dans un ticket LSMC.")
    
    @commands.command()
    @commands.has_any_role(LSMC_ROLE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID)
    async def ticket_lsmc_rem(self, ctx, member: discord.Member):
        if ctx.channel.category and ctx.channel.category.id in CATEGORY_LSMC_MAPPING.values():
            await ctx.channel.set_permissions(member, overwrite=None)
            await ctx.send(f"{member.mention} a été retiré du ticket.")
        else:
            await ctx.send("Cette commande doit être exécutée dans un ticket LSMC.")
    
    @commands.command()
    @commands.has_any_role(LSMC_ROLE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID)
    async def ticket_lsmc_claim(self, ctx):
        await ctx.send(f"L'agent {ctx.author.mention} a claim le ticket de {ctx.channel.name}.")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def ticket_lsmc_reset(self, ctx, member: discord.Member):
        ticket_lsmc_count[member.id] = 0
        await ctx.send(f"Le nombre de tickets de {member.mention} a été remis à zéro.")
        
    @commands.command()
    @commands.has_any_role(LSMC_ROLE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID)
    async def ticket_lsmc_rename(self, ctx, new_name: str):
        if ctx.channel.category and ctx.channel.category.id in CATEGORY_LSMC_MAPPING.values():
            await ctx.channel.edit(name=new_name)
            await ctx.send(f"Le ticket a été renommé en : {new_name}")
        else:
            await ctx.send("Cette commande peut seulement être utilisée dans un canal de ticket.")
            
    @commands.command()
    @commands.has_any_role(LSMC_ROLE_ID, OWNER_FDO_ROLE_ID, MANAGER_FDO_ROLE_ID, LEGAL_MANAGER_FDO_ROLE_ID)
    async def ticket_lsmc_close(self, ctx, *, reason: str = "Aucune raison spécifiée."):
        if ctx.channel.category and ctx.channel.category.id in CATEGORY_LSMC_MAPPING.values():
            await log_lsmc_ticket_action("Fermeture (commande)", ctx.author, ctx.channel.name, reason=reason)
            
            # Mise à jour du compteur si l’auteur du ticket est connu
            async for message in ctx.channel.history(limit=50):
                if message.mentions:
                    mentioned_user = message.mentions[0]
                    if mentioned_user.id in ticket_lsmc_count:
                        ticket_lsmc_count[mentioned_user.id] = max(0, ticket_lsmc_count[mentioned_user.id] - 1)
                    break

            await ctx.send("Le ticket sera fermé dans quelques secondes...")
            await asyncio.sleep(3)
            # ✅ Transcript
            log_channel = discord.utils.get(ctx.guild.text_channels, id=LOG_TICKET_LSMC_CHANNEL_ID)
            if log_channel:
                transcript_file = await generate_transcript(ctx.channel)
                await log_channel.send(
                    file=transcript_file
                )

            await ctx.channel.delete()

        else:
            await ctx.send("❌ Cette commande doit être utilisée dans un ticket.")

async def setup(bot):
    await bot.add_cog(TicketsLSMC(bot))