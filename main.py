import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import database

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class Bot7a0(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        # O prefixo '!' é mantido por padrão, mas focaremos nos slash commands
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # Carrega o arquivo painel.py que está dentro da pasta cogs
        await self.load_extension('cogs.painel')
        
        # Sincroniza os comandos com os servidores do Discord
        await self.tree.sync()
        print('🔄 Comandos de barra sincronizados com sucesso.')

    async def on_ready(self):
        database.criar_tabelas()
        database.carregar_dados_json() # Alteração feita aqui
        
        if self.user:
            print(f'✅ O bot {self.user.name} conectou e está pronto!')

# Instancia e roda o bot
bot = Bot7a0()

if __name__ == '__main__':
    bot.run(str(TOKEN))