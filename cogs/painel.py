import discord
from discord.ext import commands
from discord import app_commands
import database
import random

# --- 5. View do Torneio (A Chave de Mata-Mata e Simulação) ---
class TorneioView(discord.ui.View):
    def __init__(self, user_id, adversarios, fase="Quartas de Final"):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.adversarios = adversarios
        self.fase = fase

    @discord.ui.button(label="SIMULAR PARTIDA ⚽", style=discord.ButtonStyle.success)
    async def botao_simular(self, interaction: discord.Interaction, button: discord.ui.Button):
        adversario = self.adversarios.pop(0)
        forca_ia = adversario["forca"]
        nome_ia = adversario["nome"]

        forca_user = database.calcular_forca_time(self.user_id)

        desempenho_user = random.randint(forca_user - 5, forca_user + 5)
        desempenho_ia = random.randint(forca_ia - 5, forca_ia + 5)

        if desempenho_user == desempenho_ia:
            desempenho_user += random.choice([-1, 1])

        vitoria = desempenho_user > desempenho_ia

        if vitoria:
            gols_user = max(1, (desempenho_user - desempenho_ia) // 3)
            gols_ia = random.randint(0, gols_user - 1)
        else:
            gols_ia = max(1, (desempenho_ia - desempenho_user) // 3)
            gols_user = random.randint(0, gols_ia - 1)

        cor_embed = discord.Color.green() if vitoria else discord.Color.red()
        embed_resultado = discord.Embed(
            title=f"🏟️ {self.fase.upper()} - RESULTADO",
            color=cor_embed
        )
        embed_resultado.add_field(name="Sua Seleção", value=f"Força Base: {forca_user}\nDesempenho: **{desempenho_user}**\n## ⚽ {gols_user}", inline=True)
        embed_resultado.add_field(name="vs", value="⚔️", inline=True)
        embed_resultado.add_field(name=nome_ia, value=f"Força Base: {forca_ia}\nDesempenho: **{desempenho_ia}**\n## ⚽ {gols_ia}", inline=True)

        if vitoria:
            if self.fase == "Quartas de Final":
                proxima_fase = "Semifinal"
                embed_resultado.description = "🎉 **VITÓRIA!** Avançaste para a Semifinal!"
                await interaction.response.edit_message(embed=embed_resultado, view=TorneioView(self.user_id, self.adversarios, proxima_fase))
            elif self.fase == "Semifinal":
                proxima_fase = "Grande Final"
                embed_resultado.description = "🔥 **VITÓRIA ÉPICA!** Estás na Grande Final!"
                await interaction.response.edit_message(embed=embed_resultado, view=TorneioView(self.user_id, self.adversarios, proxima_fase))
            else:
                embed_resultado.description = "🏆 **CAMPEÃO!** Venceste o torneio 7 a 0!"
                database.limpar_draft(self.user_id)
                await interaction.response.edit_message(embed=embed_resultado, view=None)
        else:
            embed_resultado.description = "❌ **DERROTA.** A tua equipa foi eliminada.\nUsa `/painel` para iniciar uma nova run."
            database.limpar_draft(self.user_id)
            await interaction.response.edit_message(embed=embed_resultado, view=None)


# --- 4. View de Escolha da Posição na Tática ---
# --- 4. View de Escolha da Posição na Tática ---
class EscolhaPosicaoView(discord.ui.View):
    def __init__(self, user_id, jogador_id, nome_jogador, formacao, estilo):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.jogador_id = jogador_id
        self.formacao = formacao
        self.estilo = estilo

        # Puxa apenas as vagas que ainda estão vazias na formação do utilizador
        vagas_livres = database.obter_vagas_disponiveis(user_id)

        opcoes = []
        # Usamos enumerate para garantir que cada 'value' enviado ao Discord seja absolutamente único (ex: 'ZAG_0', 'ZAG_1')
        for index, vaga in enumerate(vagas_livres[:25]):
            opcoes.append(discord.SelectOption(
                label=f"Escalar na posição: {vaga} (#{index + 1})",
                value=f"{vaga}_{index}",  # Valor único evita o erro do Discord
                description=f"Alocar vaga de {vaga}",
                emoji="📍"
            ))

        if not opcoes:
            opcoes.append(discord.SelectOption(label="Sem vagas", value="nenhuma_0"))

        select = discord.ui.Select(
            placeholder=f"Onde quer colocar {nome_jogador}?",
            min_values=1,
            max_values=1,
            options=opcoes
        )

        async def select_callback(interaction: discord.Interaction):
            # Recupera apenas o nome real da posição (ex: 'ZAG_0' vira 'ZAG')
            valor_selecionado = select.values[0]
            posicao_escolhida = valor_selecionado.split('_')[0]
            
            total_draftados = database.adicionar_jogador_draft(self.user_id, self.jogador_id, posicao_escolhida)

            if total_draftados < 11:
                embed_sucesso = discord.Embed(
                    title="✅ Jogador Escalado com Sucesso!",
                    description=f"Progresso da equipa: **{total_draftados}/11 jogadores**.\n\nClica abaixo para sortear a próxima seleção.",
                    color=discord.Color.green()
                )
                await interaction.response.edit_message(embed=embed_sucesso, view=ContinuarDraftView(self.formacao, self.estilo))
            else:
                adversarios_ia = database.gerar_adversarios_ia()
                forca_user = database.calcular_forca_time(self.user_id)

                embed_torneio = discord.Embed(
                    title="🏆 11 JOGADORES ESCALADOS!",
                    description=f"A tua equipa está pronta com **{forca_user} de Força Total**!\n\nO torneio de Quartas de Final foi gerado. Clica abaixo para simular!",
                    color=discord.Color.dark_theme()
                )
                await interaction.response.edit_message(embed=embed_torneio, view=TorneioView(self.user_id, adversarios_ia, "Quartas de Final"))

        select.callback = select_callback
        self.add_item(select)


# --- 3. View da Ponte (Para rolar o 2º ao 11º jogador) ---
class ContinuarDraftView(discord.ui.View):
    def __init__(self, formacao, estilo):
        super().__init__(timeout=None)
        self.formacao = formacao
        self.estilo = estilo

    @discord.ui.button(label="PRÓXIMO ROLAR 🎲", style=discord.ButtonStyle.danger)
    async def botao_rolar(self, interaction: discord.Interaction, button: discord.ui.Button):
        info_selecao, jogadores = database.sortear_selecao(interaction.user.id)
        
        if not info_selecao:
            return
            
        selecao, ano = info_selecao
        
        embed = discord.Embed(
            title=f"🎲 SAIU: {selecao} {ano}",
            description="Escolhe **UM** jogador desta seleção e define a posição dele.",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Formação: {self.formacao} | Estilo: {self.estilo}")
        
        view_escolha = EscolhaJogadorView(selecao, ano, jogadores, self.formacao, self.estilo)
        await interaction.response.edit_message(embed=embed, view=view_escolha)


# --- 2. View de Escolha da Carta ---
class EscolhaJogadorView(discord.ui.View):
    def __init__(self, selecao, ano, jogadores, formacao, estilo):
        super().__init__(timeout=None)
        
        opcoes = []
        for jogador in jogadores[:25]:
            id_jog, nome, pos, ovr = jogador
            opcoes.append(discord.SelectOption(
                label=f"{nome} ({pos})", 
                description=f"Overall: {ovr}", 
                value=str(id_jog),
                emoji="👕"
            ))
            
        select = discord.ui.Select(
            placeholder=f"Escolha 1 jogador de {selecao} {ano}...", 
            min_values=1, 
            max_values=1, 
            options=opcoes
        )
        
        async def select_callback(interaction: discord.Interaction):
            id_escolhido = int(select.values[0])
            
            # Descobre o nome do jogador escolhido para mostrar no menu de posições
            nome_escolhido = next((j[1] for j in jogadores if j[0] == id_escolhido), "Jogador")
            
            # Em vez de salvar direto, abre o menu para escolher a posição na tática
            embed_pos = discord.Embed(
                title=f"📍 ESCOLHER POSIÇÃO PARA {nome_escolhido.upper()}",
                description="Seleciona em qual vaga da tua formação pretendes encaixar este atleta:",
                color=discord.Color.blue()
            )
            await interaction.response.edit_message(
                embed=embed_pos, 
                view=EscolhaPosicaoView(interaction.user.id, id_escolhido, nome_escolhido, formacao, estilo)
            )
            
        select.callback = select_callback
        self.add_item(select)


# --- 1. O Painel Inicial (Primeiro Rolar) ---
class PainelPrincipal(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.formacao = None
        self.estilo = None

    @discord.ui.select(
        placeholder="Escolha a Formação",
        options=[
            discord.SelectOption(label="4-3-3", description="Padrão", emoji="⚔️"),
            discord.SelectOption(label="4-4-2", description="Equilibrado", emoji="⚖️"),
            discord.SelectOption(label="4-2-3-1", description="Controle de meio", emoji="🛡️"),
            discord.SelectOption(label="3-5-2", description="Alargamento de campo", emoji="🏃")
        ]
    )
    async def select_formacao(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.formacao = select.values[0]
        await interaction.response.defer()

    @discord.ui.select(
        placeholder="Escolha o Estilo",
        options=[
            discord.SelectOption(label="Ofensivo", emoji="🔥"),
            discord.SelectOption(label="Equilibrado", emoji="☯️"),
            discord.SelectOption(label="Defensivo", emoji="🧱")
        ]
    )
    async def select_estilo(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.estilo = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="INICIAR DRAFT 🎲", style=discord.ButtonStyle.danger, row=2)
    async def botao_rolar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.formacao or not self.estilo:
            embed_aviso = discord.Embed(
                title="🏆 7 A 0 • MONTE SUA SELEÇÃO",
                description="Configure sua tática antes de iniciar o sorteio dos jogadores históricos.",
                color=discord.Color.red()
            )
            embed_aviso.set_footer(text="⚠️ Erro: Selecione a Formação e o Estilo antes de rolar!")
            await interaction.response.edit_message(embed=embed_aviso, view=self)
            return
        
        database.limpar_draft(interaction.user.id)
        database.registrar_tatica(interaction.user.id, self.formacao, self.estilo)
        
        info_selecao, jogadores = database.sortear_selecao(interaction.user.id)
        
        if not info_selecao:
            embed_erro = discord.Embed(
                title="🏆 7 A 0 • MONTE SUA SELEÇÃO",
                description="Configure sua tática antes de iniciar o sorteio dos jogadores históricos.",
                color=discord.Color.red()
            )
            embed_erro.set_footer(text="❌ O banco de dados está vazio ou esgotaste os jogadores!")
            await interaction.response.edit_message(embed=embed_erro, view=self)
            return
            
        selecao, ano = info_selecao
        
        embed = discord.Embed(
            title=f"🎲 SAIU: {selecao} {ano}",
            description="Escolha **UM** jogador desta seleção e defina a posição dele.",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Formação: {self.formacao} | Estilo: {self.estilo}")
        
        view_escolha = EscolhaJogadorView(selecao, ano, jogadores, self.formacao, self.estilo)
        await interaction.response.edit_message(embed=embed, view=view_escolha)


class PainelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="painel", description="Abre o centro de comando do 7 a 0")
    async def painel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏆 7 A 0 • MONTE SUA SELEÇÃO",
            description="Configure sua tática antes de iniciar o sorteio dos jogadores históricos.",
            color=discord.Color.dark_theme()
        )
        await interaction.response.send_message(embed=embed, view=PainelPrincipal())

async def setup(bot):
    await bot.add_cog(PainelCog(bot))