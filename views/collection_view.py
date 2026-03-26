import discord
from helpers.util import card_list_embed, card_info_embed

class CardSelect(discord.ui.Select):
    def __init__(self, cards, page, allowed_user):
        start = page * 10
        end = start + 10
        pages = cards[start:end]

        options = [
            discord.SelectOption(label = f"{card["fd_display"]}", value = card["fd_display"])
            for card in pages
        ]

        super().__init__(
            placeholder = "Select a card...",
            min_values = 1,
            max_values = 1,
            options = options
        )

        self.cards = cards
        self.allowed_user = allowed_user

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.allowed_user:
            return await interaction.response.send_message("This is not your interaction!", ephemeral = True)

        selected_id = self.values[0]
        card = next(c for c in self.cards if c["fd_display"] == selected_id)

        embed, file = card_info_embed(card)
        await interaction.response.send_message(embed = embed, file = file)


class CardView(discord.ui.View):
    def __init__(self, viewer, target, cards):
        super().__init__(timeout = 180)
        self.viewer = viewer
        self.target = target
        self.cards = cards
        self.page = 0
        self.total = (len(cards) - 1) // 10 + 1

        self.update_view()

    def update_view(self):
        self.clear_items()

        self.add_item(CardSelect(self.cards, self.page, self.viewer))

        prev_button = discord.ui.Button(label = "⬅️", disabled = self.page == 0)
        prev_button.callback = self.prev_page
        self.add_item(prev_button)
        next_button = discord.ui.Button(label = "➡️", disabled = self.page >= self.total - 1)
        next_button.callback = self.next_page
        self.add_item(next_button)

    async def prev_page(self, interaction: discord.Interaction):
        if interaction.user != self.viewer:
            return await interaction.response.send_message("This is not your interaction!", ephemeral = True)

        self.page -= 1
        self.update_view()

        embed = card_list_embed(self.target, self.cards, self.page, self.total)
        await interaction.response.edit_message(embed  =embed, view = self)

    async def next_page(self, interaction: discord.Interaction):
        if interaction.user != self.viewer:
            return await interaction.response.send_message("This is not your interaction!", ephemeral = True)

        self.page += 1
        self.update_view()

        embed = card_list_embed(self.target, self.cards, self.page, self.total)
        await interaction.response.edit_message(embed = embed, view = self)