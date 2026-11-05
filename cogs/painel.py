import discord
from discord.ext import commands
from discord import app_commands
import database
import random

# Funções matemáticas isoladas para limpar o código da interface
def simular_jogo(forca_a, forca_b, permite_empate=True):
    des_a = random.randint(forca_a - 5, forca_a + 5)
    des_b = random.randint(forca_b - 5, forca_b + 5)

    if not permite_empate and des_a == des_b:
        des_a += random.choice([-1, 1]) # Desempate forçado (Pênaltis simulados)

    if des_a > des_b:
        gols_a = max(1, (des_a - des_b) // 3)
        gols_b = random.randint(0, gols_a - 1)
    elif des_b > des_a:
        gols_b = max(1, (des_b - des_a) // 3)
        gols_a = random.randint(0, gols_b - 1)
    else:
        if permite_empate:
            gols_a = gols_b = random.randint(0, 3)
        else:
            gols_a = random.randint(1, 3)
            gols_b = gols_a - 1
            
    return gols_a, gols_b, des_a, des_b

def atualizar_tabela(tabela, time_a, gols_a, time_b, gols_b):
    tabela[time_a]["gp"] += gols_a
    tabela[time_a]["sg"] += (gols_a - gols_b)
    tabela[time_b]["gp"] += gols_b
    tabela[time_b]["sg"] += (gols_b - gols_a)

    if gols_a > gols_b:
        tabela[time_a]["pts"] += 3
    elif gols_b > gols_a:
        tabela[time_b]["pts"] += 3
    else:
        tabela[time_a]["pts"] += 1
        tabela[time_b]["pts"] += 1

# --- 5. View do Torneio (Copa do Mundo: Grupos + Mata-Mata Longo) ---
class TorneioView(discord.ui.View):
    def __init__(self, user_id, adversarios, estado=None):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.adversarios = adversarios
        
        if not estado:
            forca_user = database.calcular_forca_time(user_id)
            self.estado = {
                "fase": "Grupos 1",
                "adv_grupo": [adversarios.pop(0), adversarios.pop(0), adversarios.pop(0)],
                "tabela": {
                    "Sua Seleção": {"pts": 0, "sg": 0, "gp": 0, "forca": forca_user}
                }
            }
            for i in range(3):
                nome_ia = self.estado["adv_grupo"][i]["nome"]
                self.estado["tabela"][nome_ia] = {"pts": 0, "sg": 0, "gp": 0, "forca": self.estado["adv_grupo"][i]["forca"]}
        else:
            self.estado = estado

    @discord.ui.button(label="SIMULAR PARTIDA ⚽", style=discord.ButtonStyle.success)
    async def botao_simular(self, interaction: discord.Interaction, button: discord.ui.Button):
        fase_atual = self.estado["fase"]

        if fase_atual.startswith("Grupos"):
            rodada = int(fase_atual.split(" ")[1])
            advs = self.estado["adv_grupo"]
            
            if rodada == 1:
                meu_adv, outro_a, outro_b = advs[0]["nome"], advs[1]["nome"], advs[2]["nome"]
            elif rodada == 2:
                meu_adv, outro_a, outro_b = advs[1]["nome"], advs[0]["nome"], advs[2]["nome"]
            else:
                meu_adv, outro_a, outro_b = advs[2]["nome"], advs[0]["nome"], advs[1]["nome"]

            gu, ga, du, da = simular_jogo(self.estado["tabela"]["Sua Seleção"]["forca"], self.estado["tabela"][meu_adv]["forca"], True)
            goa, gob, _, _ = simular_jogo(self.estado["tabela"][outro_a]["forca"], self.estado["tabela"][outro_b]["forca"], True)

            atualizar_tabela(self.estado["tabela"], "Sua Seleção", gu, meu_adv, ga)
            atualizar_tabela(self.estado["tabela"], outro_a, goa, outro_b, gob)

            times_ord = sorted(self.estado["tabela"].items(), key=lambda x: (x[1]["pts"], x[1]["sg"], x[1]["gp"]), reverse=True)
            
            embed = discord.Embed(title=f"📊 FASE DE GRUPOS - RODADA {rodada}/3", color=discord.Color.blue())
            embed.add_field(name="O Seu Jogo", value=f"**Sua Seleção** {gu} x {ga} **{meu_adv}**", inline=False)
            embed.add_field(name="Outro Jogo do Grupo", value=f"**{outro_a}** {goa} x {gob} **{outro_b}**", inline=False)

            tabela_txt = ""
            for i, (nome, stats) in enumerate(times_ord, 1):
                tabela_txt += f"`{i}º` **{nome[:12]}** | {stats['pts']} pts | SG: {stats['sg']}\n"
            embed.add_field(name="Classificação Atualizada", value=tabela_txt, inline=False)

            if rodada < 3:
                self.estado["fase"] = f"Grupos {rodada + 1}"
                embed.description = "A tabela foi atualizada! Clique para ir à próxima rodada."
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                # MENSAGENS PERSONALIZADAS DE CLASSIFICAÇÃO
                if times_ord[0][0] == "Sua Seleção":
                    self.estado["fase"] = "16-avos de Final" # NOVO MATA-MATA
                    embed.description = "🥇 **LÍDER ABSOLUTO!** Você dominou o grupo e avançou para os 16-avos de Final!"
                    embed.color = discord.Color.green()
                    await interaction.response.edit_message(embed=embed, view=self)
                elif times_ord[1][0] == "Sua Seleção":
                    self.estado["fase"] = "16-avos de Final" # NOVO MATA-MATA
                    embed.description = "🥈 **CLASSIFICADO EM 2º LUGAR!** Foi suado, mas você está nos 16-avos de Final!"
                    embed.color = discord.Color.green()
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    embed.description = "❌ **ELIMINADO!** Você caiu na Fase de Grupos.\nUse `/painel` para recomeçar."
                    embed.color = discord.Color.red()
                    database.limpar_draft(self.user_id)
                    await interaction.response.edit_message(embed=embed, view=None)

        else:
            # --- MATA-MATA (16-avos, Oitavas, Quartas, Semi, Final) ---
            adversario = self.adversarios.pop(0)
            forca_ia, nome_ia = adversario["forca"], adversario["nome"]
            forca_user = database.calcular_forca_time(self.user_id)

            gu, gia, du, da = simular_jogo(forca_user, forca_ia, False)
            vitoria = gu > gia

            cor_embed = discord.Color.green() if vitoria else discord.Color.red()
            embed = discord.Embed(title=f"🏟️ {fase_atual.upper()} - RESULTADO", color=cor_embed)
            embed.add_field(name="Sua Seleção", value=f"Força Base: {forca_user}\nDesempenho: **{du}**\n## ⚽ {gu}", inline=True)
            embed.add_field(name="vs", value="⚔️", inline=True)
            embed.add_field(name=nome_ia, value=f"Força Base: {forca_ia}\nDesempenho: **{da}**\n## ⚽ {gia}", inline=True)

            if vitoria:
                # PROGRESSÃO ATUALIZADA
                if fase_atual == "16-avos de Final":
                    self.estado["fase"] = "Oitavas de Final"
                    embed.description = "🎉 **AVANÇOU!** O seu time chegou nas Oitavas de Final!"
                    await interaction.response.edit_message(embed=embed, view=self)
                elif fase_atual == "Oitavas de Final":
                    self.estado["fase"] = "Quartas de Final"
                    embed.description = "🔥 **AVANÇOU!** Você está nas Quartas de Final!"
                    await interaction.response.edit_message(embed=embed, view=self)
                elif fase_atual == "Quartas de Final":
                    self.estado["fase"] = "Semifinal"
                    embed.description = "⚡ **AVANÇOU!** Você chegou à Semifinal!"
                    await interaction.response.edit_message(embed=embed, view=self)
                elif fase_atual == "Semifinal":
                    self.estado["fase"] = "Grande Final"
                    embed.description = "🏆 **VITÓRIA ÉPICA!** Você está na Grande Final do Mundo!"
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    embed.description = "🌎 🏆 **CAMPEÃO DO MUNDO!** Você venceu o torneio 7 a 0!"
                    database.limpar_draft(self.user_id)
                    await interaction.response.edit_message(embed=embed, view=None)
            else:
                embed.description = "❌ **ELIMINADO.** A sua seleção caiu no mata-mata.\nUse `/painel` para iniciar nova run."
                database.limpar_draft(self.user_id)
                await interaction.response.edit_message(embed=embed, view=None)


# --- 4. View de Escolha da Posição na Tática ---
class EscolhaPosicaoView(discord.ui.View):
    def __init__(self, user_id, jogador_id, nome_jogador, posicoes_do_jogador, formacao, estilo):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.jogador_id = jogador_id
        self.formacao = formacao
        self.estilo = estilo

        vagas_livres = database.obter_vagas_disponiveis(user_id)
        posicoes_aceitas = [p.strip() for p in posicoes_do_jogador.split('/')]
        vagas_validas = [vaga for vaga in vagas_livres if vaga in posicoes_aceitas]

        opcoes = []
        for index, vaga in enumerate(vagas_validas[:25]):
            opcoes.append(discord.SelectOption(
                label=f"Escalar como: {vaga} (#{index + 1})",
                value=f"{vaga}_{index}",
                description=f"Ocupar vaga de {vaga}",
                emoji="📍"
            ))

        if not opcoes:
            opcoes.append(discord.SelectOption(label="Nenhuma vaga compatível!", value="erro_0"))

        select = discord.ui.Select(
            placeholder=f"Onde quer colocar {nome_jogador}?",
            min_values=1, max_values=1, options=opcoes
        )

        async def select_callback(interaction: discord.Interaction):
            valor_selecionado = select.values[0]
            if valor_selecionado == "erro_0":
                await interaction.response.send_message("❌ Erro: Nenhuma vaga compatível encontrada.", ephemeral=True)
                return

            posicao_escolhida = valor_selecionado.split('_')[0]
            total_draftados = database.adicionar_jogador_draft(self.user_id, self.jogador_id, posicao_escolhida)

            if total_draftados < 11:
                embed_sucesso = discord.Embed(
                    title="✅ Jogador Escalado com Sucesso!",
                    description=f"Progresso da equipe: **{total_draftados}/11 jogadores**.\n\nClique abaixo para sortear a próxima seleção.",
                    color=discord.Color.green()
                )
                await interaction.response.edit_message(embed=embed_sucesso, view=ContinuarDraftView(self.formacao, self.estilo))
            else:
                adversarios_ia = database.gerar_adversarios_ia()
                forca_user = database.calcular_forca_time(self.user_id)

                embed_torneio = discord.Embed(
                    title="🏆 11 JOGADORES ESCALADOS!",
                    description=f"O Sorteio da Copa do Mundo foi realizado! Seu time tem **{forca_user} de Força Total**!\n\nVocê caiu em um grupo com 3 IAs históricas. Clique abaixo para iniciar a Fase de Grupos!",
                    color=discord.Color.dark_theme()
                )
                await interaction.response.edit_message(embed=embed_torneio, view=TorneioView(self.user_id, adversarios_ia))

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
        self.jogadores_dados = jogadores
        
        opcoes = []
        for jogador in jogadores[:25]:
            id_jog, nome, pos, ovr = jogador
            opcoes.append(discord.SelectOption(label=f"{nome} ({pos})", description=f"Overall: {ovr}", value=str(id_jog), emoji="👕"))
            
        select = discord.ui.Select(placeholder=f"Escolha 1 jogador de {selecao} {ano}...", min_values=1, max_values=1, options=opcoes)
        
        async def select_callback(interaction: discord.Interaction):
            id_escolhido = int(select.values[0])
            jogador_info = next((j for j in self.jogadores_dados if j[0] == id_escolhido), None)
            
            if not jogador_info:
                await interaction.response.send_message("❌ Erro ao localizar os dados do jogador.", ephemeral=True)
                return
                
            nome_escolhido, posicoes_do_jogador = jogador_info[1], jogador_info[2] 
            
            embed_pos = discord.Embed(
                title=f"📍 ESCOLHER POSIÇÃO PARA {nome_escolhido.upper()}",
                description=f"Este atleta joga nas posições: **{posicoes_do_jogador}**\nSelecione abaixo a vaga:",
                color=discord.Color.blue()
            )
            await interaction.response.edit_message(
                embed=embed_pos, 
                view=EscolhaPosicaoView(interaction.user.id, id_escolhido, nome_escolhido, posicoes_do_jogador, formacao, estilo)
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
            embed_aviso = discord.Embed(title="🏆 7 A 0 • MONTE SUA SELEÇÃO", description="Configure sua tática antes de iniciar.", color=discord.Color.red())
            embed_aviso.set_footer(text="⚠️ Erro: Selecione a Formação e o Estilo antes de rolar!")
            await interaction.response.edit_message(embed=embed_aviso, view=self)
            return
        
        database.limpar_draft(interaction.user.id)
        database.registrar_tatica(interaction.user.id, self.formacao, self.estilo)
        info_selecao, jogadores = database.sortear_selecao(interaction.user.id)
        
        if not info_selecao:
            embed_erro = discord.Embed(title="🏆 7 A 0", description="O banco está vazio ou esgotou.", color=discord.Color.red())
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
        embed = discord.Embed(title="🏆 7 A 0 • MONTE SUA SELEÇÃO", description="Configure sua tática antes de iniciar o sorteio dos jogadores históricos.", color=discord.Color.dark_theme())
        await interaction.response.send_message(embed=embed, view=PainelPrincipal())

async def setup(bot):
    await bot.add_cog(PainelCog(bot))