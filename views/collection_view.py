import discord
from helpers.util import card_list_embed, card_info_embed

BINI_ORDER = ["Aiah", "Colet", "Maloi", "Gwen", "Stacey", "Mikha", "Jhoanna", "Sheena", "OT8"]

class CardSelect(discord.ui.Select):
    def __init__(self, cards, page, allowed_user):
        start = page * 9
        end = start + 9
        pages = cards[start:end]

        options = [
            discord.SelectOption(label = f"{card['o']['fd_display']}: {card['c']['fd_bundle']} {card['c']['fd_member']}", value = card['o']['fd_display'])
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
        card = next(c for c in self.cards if c["o"]["fd_display"] == selected_id)

        embed, file = await card_info_embed(card)
        await interaction.response.send_message(embed = embed, file = file)

class MemberFilter(discord.ui.Select):
    def __init__(self, view):
        source = view.cards if view.cards else view.all_cards
        members = sorted({
            card["c"]["fd_member"] for card in source}, 
            key = lambda m: BINI_ORDER.index(m) if m in BINI_ORDER else 999
        )
        options = [discord.SelectOption(label = "All", value = "all")]
        options += [
            discord.SelectOption(label = m, value = m) 
            for m in members
        ]

        super().__init__(placeholder = "Filter by member", options = options[:25])
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.view_ref.viewer:
            return await interaction.response.send_message("This is not your interaction!", ephemeral = True)
        
        val = self.values[0]
        self.view_ref.filters["member"] = None if val == "all" else val

        self.view_ref.apply_filters()
        self.view_ref.update_view()

        embed = card_list_embed(self.view_ref.target, self.view_ref.cards, self.view_ref.page, self.view_ref.total)
        await interaction.response.edit_message(embed = embed, view = self.view_ref)

class SearchModal(discord.ui.Modal):
    query = discord.ui.TextInput(label = "Series name (\"all\" for no filter)", placeholder = "Type to search")

    def __init__(self, view):
        super().__init__(title = "Search series")
        self.view_ref = view

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user != self.view_ref.viewer:
            return await interaction.response.send_message("This is not your interaction!", ephemeral = True)
        
        value = self.query.value.strip().lower()
        self.view_ref.filters["series"] = None if value in ("", "all") else value
        self.view_ref.apply_filters()
        self.view_ref.update_view()

        embed = card_list_embed(self.view_ref.target, self.view_ref.cards, self.view_ref.page, self.view_ref.total)
        await interaction.response.edit_message(embed = embed, view = self.view_ref)

class SearchButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(label = "🔍 Search series", style = discord.ButtonStyle.primary)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.view_ref.viewer:
            return await interaction.response.send_message("This is not your interaction!", ephemeral = True)
        
        await interaction.response.send_modal(SearchModal(self.view_ref))

class CardView(discord.ui.View):
    def __init__(self, viewer, target, cards):
        super().__init__(timeout = 180)
        self.viewer = viewer
        self.target = target
        self.all_cards = cards
        self.cards = cards
        self.page = 0
        self.total = max(1, (len(cards) - 1) // 9 + 1)

        self.filters = {"member": None, "series": None}

        self.update_view()

    def update_view(self):
        self.clear_items()

        self.add_item(CardSelect(self.cards, self.page, self.viewer))
        self.add_item(MemberFilter(self))

        prev_button = discord.ui.Button(label = "⬅️", disabled = self.page == 0)
        prev_button.callback = self.prev_page
        self.add_item(prev_button)
        next_button = discord.ui.Button(label = "➡️", disabled = self.page >= self.total - 1)
        next_button.callback = self.next_page
        self.add_item(next_button)
        
        self.add_item(SearchButton(self))

    def apply_filters(self):
        cards = self.all_cards

        if self.filters["member"]:
            cards = [card for card in cards if card["c"]["fd_member"] == self.filters["member"]]

        if self.filters["series"]:
            query = self.filters["series"].lower()
            cards = [card for card in cards if query in card["c"]["fd_bundle"].lower()]

        self.cards = cards
        self.page = 0
        self.total = max(1, (len(cards) - 1) // 9 + 1)

    async def prev_page(self, interaction: discord.Interaction):
        if interaction.user != self.viewer:
            return await interaction.response.send_message("This is not your interaction!", ephemeral = True)

        self.page -= 1
        self.update_view()

        embed = card_list_embed(self.target, self.cards, self.page, self.total)
        await interaction.response.edit_message(embed = embed, view = self)

    async def next_page(self, interaction: discord.Interaction):
        if interaction.user != self.viewer:
            return await interaction.response.send_message("This is not your interaction!", ephemeral = True)

        self.page += 1
        self.update_view()

        embed = card_list_embed(self.target, self.cards, self.page, self.total)
        await interaction.response.edit_message(embed = embed, view = self)