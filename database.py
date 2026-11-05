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
    """Lê o arquivo jogadores.json e força a sincronização com o banco de dados"""
    caminho_arquivo = os.path.join('dados', 'jogadores.json')
    
    if not os.path.exists(caminho_arquivo):
        print(f"⚠️ Arquivo {caminho_arquivo} não encontrado!")
        return

    conn = conectar()
    cursor = conn.cursor()
    
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        dados = json.load(f)
        
    # 1. Apaga a lista antiga de jogadores para atualizar com o novo JSON
    cursor.execute('DELETE FROM jogadores')
    
    # 2. Reseta os IDs para não virarem números gigantes
    cursor.execute('DELETE FROM sqlite_sequence WHERE name="jogadores"')
    
    for j in dados:
        # 3. O PULO DO GATO: Se você digitar com espaço sem querer no JSON (ex: "ATA / PD / PE"), 
        # o bot limpa automaticamente para "ATA/PD/PE" para não quebrar a busca do SQL!
        posicao_limpa = "/".join([p.strip() for p in j['posicao'].split('/')])
        
        cursor.execute('''
            INSERT INTO jogadores (nome, selecao, ano, posicao, overall)
            VALUES (?, ?, ?, ?, ?)
        ''', (j['nome'], j['selecao'], j['ano'], posicao_limpa, j['overall']))
        
    conn.commit()
    print(f"✅ Sincronização Perfeita! {len(dados)} jogadores carregados do JSON para o banco.")
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
    
    # 1. Pega os IDs dos jogadores já escolhidos
    cursor.execute('SELECT jogador_id FROM elenco_ativo WHERE user_id = ?', (user_id,))
    ja_escolhidos = [row[0] for row in cursor.fetchall()]
    
    # 2. Descobre QUAIS POSIÇÕES ainda estão vazias
    vagas_livres = obter_vagas_disponiveis(user_id)
    posicoes_necessarias = list(set(vagas_livres))
    
    if not posicoes_necessarias:
        conn.close()
        return None, []
        
    # 3. CORREÇÃO DO BUG "ME" x "MEI":
    # Em vez de um LIKE simples, verificamos 4 cenários exatos para ignorar falsos positivos:
    # 1) É exatamente 'ME'
    # 2) Começa com 'ME/' (ex: ME/ATA)
    # 3) Está no meio '/ME/' (ex: PE/ME/ATA)
    # 4) Termina com '/ME' (ex: PE/ME)
    clausulas_posicao = []
    params_posicao = []
    
    for pos in posicoes_necessarias:
        clausulas_posicao.append("(posicao = ? OR posicao LIKE ? OR posicao LIKE ? OR posicao LIKE ?)")
        params_posicao.extend([pos, f"{pos}/%", f"%/{pos}/%", f"%/{pos}"])
        
    filtro_posicoes = " OR ".join(clausulas_posicao)
    
    placeholders_esc = ""
    query_sel = f"SELECT DISTINCT selecao, ano FROM jogadores WHERE ({filtro_posicoes})"
    params_sel = params_posicao.copy()
    
    if ja_escolhidos:
        placeholders_esc = ','.join('?' * len(ja_escolhidos))
        query_sel += f" AND id NOT IN ({placeholders_esc})"
        params_sel.extend(ja_escolhidos)
        
    cursor.execute(query_sel, params_sel)
    combinacoes = cursor.fetchall()
    
    if not combinacoes:
        conn.close()
        return None, []
        
    selecao_sorteada, ano_sorteado = random.choice(combinacoes)
    
    # 4. Busca APENAS os jogadores que servem para as vagas abertas
    query_jog = f'''
        SELECT id, nome, posicao, overall 
        FROM jogadores 
        WHERE selecao = ? AND ano = ? AND ({filtro_posicoes})
    '''
    params_jog = [selecao_sorteada, ano_sorteado] + params_posicao
    
    if ja_escolhidos:
        query_jog += f' AND id NOT IN ({placeholders_esc})'
        params_jog.extend(ja_escolhidos)
        
    query_jog += ' ORDER BY overall DESC'
    
    cursor.execute(query_jog, params_jog)
    jogadores = cursor.fetchall()
    
    conn.close()
    return (selecao_sorteada, ano_sorteado), jogadores
    
    # 4. Busca APENAS os jogadores que servem para as vagas abertas
    query_jog = f'''
        SELECT id, nome, posicao, overall 
        FROM jogadores 
        WHERE selecao = ? AND ano = ? AND ({like_clauses})
    '''
    params_jog = [selecao_sorteada, ano_sorteado] + like_params
    
    if ja_escolhidos:
        query_jog += f' AND id NOT IN ({placeholders_esc})'
        params_jog.extend(ja_escolhidos)
        
    query_jog += ' ORDER BY overall DESC'
    
    cursor.execute(query_jog, params_jog)
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
    
    entrosamento = 0
    combos = {}
    for j in jogadores:
        selecao, ano, ovr, pos_escalada, pos_original = j
        chave = f"{selecao} {ano}"
        combos[chave] = combos.get(chave, 0) + 1
        
        # Agora divide as posições múltiplas separadas por barra para verificar
        posicoes_permitidas = [p.strip() for p in pos_original.split('/')]
        
        # Penalidade só acontece se por algum bug bizarro ele jogar fora da posição nativa
        if pos_escalada not in posicoes_permitidas:
            entrosamento -= 2 

    for count in combos.values():
        if count > 1:
            entrosamento += (count - 1) * 3

    forca_total = int(media_ovr + entrosamento)
    return max(50, min(forca_total, 99))

def gerar_adversarios_ia():
    # Forças DEFINIDAS e justas! Sem Japão overpower aleatório.
    pool_ia = [
        {"nome": "Brasil 1970", "forca": 96},
        {"nome": "Brasil 2002", "forca": 94},
        {"nome": "Espanha 2010", "forca": 93},
        {"nome": "França 1998", "forca": 92},
        {"nome": "França 2018", "forca": 91},
        {"nome": "Alemanha 2014", "forca": 93},
        {"nome": "Alemanha 1990", "forca": 90},
        {"nome": "Itália 2006", "forca": 91},
        {"nome": "Itália 1982", "forca": 89},
        {"nome": "Argentina 2022", "forca": 92},
        {"nome": "Argentina 1986", "forca": 91},
        {"nome": "Holanda 1974", "forca": 92},
        {"nome": "Holanda 1988", "forca": 89},
        {"nome": "Inglaterra 1966", "forca": 88},
        {"nome": "Inglaterra 2018", "forca": 86},
        {"nome": "Uruguai 1950", "forca": 87},
        {"nome": "Croácia 2018", "forca": 86},
        {"nome": "Bélgica 2018", "forca": 87},
        {"nome": "Portugal 2006", "forca": 88},
        {"nome": "Portugal 2016", "forca": 87},
        {"nome": "Japão 2022", "forca": 82},
        {"nome": "Marrocos 2022", "forca": 83},
        {"nome": "Senegal 2002", "forca": 82},
        {"nome": "Colômbia 2014", "forca": 84},
        {"nome": "Chile 2015", "forca": 85},
        {"nome": "Grécia 2004", "forca": 81},
        {"nome": "Camarões 1990", "forca": 82},
        {"nome": "Turquia 2002", "forca": 84},
        {"nome": "Coreia do Sul 2002", "forca": 81},
        {"nome": "Suécia 1958", "forca": 85}
    ]
    # Sorteia 8 times únicos para a Run (3 Grupos + 16-avos + Oitavas + Quartas + Semi + Final)
    adversarios = random.sample(pool_ia, 8)
    return adversarios