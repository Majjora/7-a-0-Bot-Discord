import sqlite3
import random
import json
import os

# Dicionário mapeando as vagas disponíveis para cada formação tática
FORMACOES = {
    "4-3-3": ["GOL", "LD", "ZAG", "ZAG", "LE", "VOL", "MC", "MC", "PD", "PE", "ATA"],
    "4-4-2": ["GOL", "LD", "ZAG", "ZAG", "LE", "MD", "MC", "MC", "ME", "ATA", "ATA"],
    "4-2-3-1": ["GOL", "LD", "ZAG", "ZAG", "LE", "VOL", "VOL", "MD", "MEI", "ME", "ATA"],
    "3-5-2": ["GOL", "ZAG", "ZAG", "ZAG", "MD", "VOL", "MC", "VOL", "ME", "ATA", "ATA"]
}

def conectar():
    return sqlite3.connect('sete_a_zero.db')

def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()
    
    # Recria as tabelas caso precisemos resetar para a estrutura nova
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jogadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            selecao TEXT NOT NULL,
            ano INTEGER NOT NULL,
            posicao TEXT NOT NULL,
            overall INTEGER NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS times_ativos (
            user_id INTEGER PRIMARY KEY,
            formacao TEXT,
            estilo TEXT
        )
    ''')
    
    # Nova coluna 'posicao_escolhida' adicionada
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS elenco_ativo (
            user_id INTEGER,
            jogador_id INTEGER,
            posicao_escolhida TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def carregar_dados_json():
    """Lê o arquivo jogadores.json e popula o banco de dados"""
    caminho_arquivo = os.path.join('dados', 'jogadores.json')
    
    if not os.path.exists(caminho_arquivo):
        print(f"⚠️ Arquivo {caminho_arquivo} não encontrado!")
        return

    conn = conectar()
    cursor = conn.cursor()
    
    # Verifica se já temos dados. Se o banco estiver vazio, importa do JSON.
    cursor.execute('SELECT COUNT(*) FROM jogadores')
    if cursor.fetchone()[0] == 0:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            
        for j in dados:
            cursor.execute('''
                INSERT INTO jogadores (nome, selecao, ano, posicao, overall)
                VALUES (?, ?, ?, ?, ?)
            ''', (j['nome'], j['selecao'], j['ano'], j['posicao'], j['overall']))
            
        conn.commit()
        print(f"✅ {len(dados)} jogadores carregados do JSON com sucesso!")
        
    conn.close()

def obter_vagas_disponiveis(user_id):
    """Retorna as posições que ainda estão vazias na tática do usuário"""
    conn = conectar()
    cursor = conn.cursor()
    
    cursor.execute('SELECT formacao FROM times_ativos WHERE user_id = ?', (user_id,))
    resultado = cursor.fetchone()
    if not resultado:
        return []
        
    formacao = resultado[0]
    vagas_totais = FORMACOES.get(formacao, []).copy()
    
    cursor.execute('SELECT posicao_escolhida FROM elenco_ativo WHERE user_id = ?', (user_id,))
    posicoes_ocupadas = [row[0] for row in cursor.fetchall()]
    
    # Remove as posições já preenchidas da lista de vagas
    for pos in posicoes_ocupadas:
        if pos in vagas_totais:
            vagas_totais.remove(pos)
            
    conn.close()
    return vagas_totais

def sortear_selecao(user_id):
    conn = conectar()
    cursor = conn.cursor()
    
    cursor.execute('SELECT jogador_id FROM elenco_ativo WHERE user_id = ?', (user_id,))
    ja_escolhidos = [row[0] for row in cursor.fetchall()]
    
    placeholders = ""
    
    if ja_escolhidos:
        placeholders = ','.join('?' * len(ja_escolhidos))
        cursor.execute(f'SELECT DISTINCT selecao, ano FROM jogadores WHERE id NOT IN ({placeholders})', ja_escolhidos)
    else:
        cursor.execute('SELECT DISTINCT selecao, ano FROM jogadores')
        
    combinacoes = cursor.fetchall()
    
    if not combinacoes:
        conn.close()
        return None, []
        
    selecao_sorteada, ano_sorteado = random.choice(combinacoes)
    
    if ja_escolhidos and placeholders:
        cursor.execute(f'''
            SELECT id, nome, posicao, overall 
            FROM jogadores 
            WHERE selecao = ? AND ano = ? AND id NOT IN ({placeholders})
            ORDER BY overall DESC
        ''', (selecao_sorteada, ano_sorteado, *ja_escolhidos))
    else:
        cursor.execute('''
            SELECT id, nome, posicao, overall 
            FROM jogadores 
            WHERE selecao = ? AND ano = ?
            ORDER BY overall DESC
        ''', (selecao_sorteada, ano_sorteado))
        
    jogadores = cursor.fetchall()
    conn.close()
    return (selecao_sorteada, ano_sorteado), jogadores

def limpar_draft(user_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM times_ativos WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM elenco_ativo WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def registrar_tatica(user_id, formacao, estilo):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO times_ativos (user_id, formacao, estilo)
        VALUES (?, ?, ?)
    ''', (user_id, formacao, estilo))
    conn.commit()
    conn.close()

def adicionar_jogador_draft(user_id, jogador_id, posicao_escolhida):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO elenco_ativo (user_id, jogador_id, posicao_escolhida) VALUES (?, ?, ?)', (user_id, jogador_id, posicao_escolhida))
    cursor.execute('SELECT COUNT(*) FROM elenco_ativo WHERE user_id = ?', (user_id,))
    total = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return total

def calcular_forca_time(user_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT j.selecao, j.ano, j.overall, e.posicao_escolhida, j.posicao
        FROM elenco_ativo e
        JOIN jogadores j ON e.jogador_id = j.id
        WHERE e.user_id = ?
    ''', (user_id,))
    jogadores = cursor.fetchall()
    conn.close()

    if not jogadores:
        return 0

    media_ovr = sum(j[2] for j in jogadores) / len(jogadores)
    
    # Bônus de Entrosamento e Penalidade de Posição
    entrosamento = 0
    combos = {}
    for j in jogadores:
        selecao, ano, ovr, pos_escalada, pos_original = j
        chave = f"{selecao} {ano}"
        combos[chave] = combos.get(chave, 0) + 1
        
        # Se escalou um Atacante como Zagueiro, perde força
        if pos_escalada != pos_original:
            entrosamento -= 2 

    for count in combos.values():
        if count > 1:
            entrosamento += (count - 1) * 3

    forca_total = int(media_ovr + entrosamento)
    return max(50, min(forca_total, 99))

def gerar_adversarios_ia():
    adversarios = [
        {"nome": "Alemanha 2014", "forca": 93},
        {"nome": "França 1998", "forca": 91},
        {"nome": "Espanha 2010", "forca": 92},
        {"nome": "Itália 2006", "forca": 90},
        {"nome": "Argentina 1986", "forca": 89},
        {"nome": "Brasil 1970", "forca": 95},
        {"nome": "Holanda 1974", "forca": 88}
    ]
    random.shuffle(adversarios)
    return adversarios