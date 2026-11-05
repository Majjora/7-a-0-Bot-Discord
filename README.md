# ⚽ Bot 7 a 0 — Simulação de Seleções Históricas no Discord

Bot interativo para Discord inspirado no jogo *7 a 0*, desenvolvido em Python. O bot permite aos usuários montar táticas, realizar drafts de jogadores históricos de Copas do Mundo sem repetição e disputar torneios de mata-mata com simulação probabilística ponderada por Overall e Entrosamento.

## 🚀 Funcionalidades
- **Interface 100% Visual:** Construído com botões e menus suspensos (`discord.ui`), dispensando comandos de texto poluídos.
- **Configuração Tática:** Escolha de formações (4-3-3, 4-4-2, 3-5-2, etc.) e estilos de jogo.
- **Draft de Jogadores:** Sorteio dinâmico de seleções históricas alimentado por um banco de dados em JSON.
- **Alocação por Posição:** Validação tática para escalar cada atleta em sua respectiva vaga na formação.
- **Simulação Matemático-Estatística:** Algoritmo de partida que considera a média de Overall do elenco e bônus de entrosamento para calcular probabilidades reais de vitória.
- **Modo Torneio:** Disputa de mata-mata (Quartas, Semifinal e Final) contra seleções controladas por IA.

## 🛠️ Tecnologias Utilizadas
- **Linguagem:** Python 3.10+
- **Biblioteca Discord:** `discord.py` (v2.0+) utilizando a arquitetura modular de **Cogs**
- **Banco de Dados:** SQLite3
- **Estruturação de Dados:** JSON

## 🔧 Como Executar Localmente
1. Clone o repositório:
   ```bash
   git clone https://github.com/Majjora/7-a-0-Bot-Discord.git
   cd 7-a-0-Bot-Discord


## Depedências

Instale: 

pip install discord.py python-dotenv

------------------------

Configure as variáveis de ambiente criando um arquivo .env na raiz:

DISCORD_TOKEN=seu_token_aqui

------------------------

Iniciar o bot:

python main.py
