import discord
from discord.ui import View, Button

class ConfirmView(View):
    def __init__(self, author):
        super().__init__(timeout = 15)
        self.value = None
        self.author = author

    async def interaction_check(self, interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("This is not your interaction!", ephemeral = True)
            return False
        return True
    
    @discord.ui.button(label = "Yes", style = discord.ButtonStyle.green)
    async def yes(self, interaction, button):
        self.value = True
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(content = "Confirmed", view = self)
        self.stop()
    
    @discord.ui.button(label = "No", style = discord.ButtonStyle.red)
    async def no(self, interaction, button):
        self.value = False
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(content = "Cancelled", view = self)
        self.stop()