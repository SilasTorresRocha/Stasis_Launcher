import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger("banco_dados")
ARQUIVO_BANCO = "banco_saves.db"

def inicializar_banco():
    conexao = sqlite3.connect(ARQUIVO_BANCO)
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jogos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            desenvolvedor TEXT,
            versao TEXT,
            status TEXT,
            notas TEXT,
            tags TEXT,
            link_loja TEXT,
            link_oficial TEXT,
            caminho_save TEXT,
            pasta_appdata TEXT,
            caminho_capa TEXT,
            caminho_executavel TEXT,
            ultima_vez_jogado TEXT,
            data_atualizacao TEXT
        )
    """)
    conexao.close()
    logger.info("Banco de dados SQLite inicializado com sucesso.")

def listar_jogos():
    conexao = sqlite3.connect(ARQUIVO_BANCO)
    conexao.row_factory = sqlite3.Row
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM jogos ORDER BY data_atualizacao DESC")
    jogos = [dict(linha) for linha in cursor.fetchall()]
    conexao.close()
    return jogos

def adicionar_jogo(dados):
    conexao = sqlite3.connect(ARQUIVO_BANCO)
    cursor = conexao.cursor()
    
    dados['data_atualizacao'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    colunas = ', '.join(dados.keys())
    placeholders = ', '.join(['?'] * len(dados))
    valores = tuple(dados.values())
    
    cursor.execute(f"INSERT INTO jogos ({colunas}) VALUES ({placeholders})", valores)
    novo_id = cursor.lastrowid
    conexao.commit()
    conexao.close()
    return novo_id

def atualizar_jogo(id_jogo, dados):
    conexao = sqlite3.connect(ARQUIVO_BANCO)
    cursor = conexao.cursor()
    
    dados['data_atualizacao'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    set_clause = ', '.join([f"{k} = ?" for k in dados.keys()])
    valores = tuple(dados.values()) + (id_jogo,)
    
    cursor.execute(f"UPDATE jogos SET {set_clause} WHERE id = ?", valores)
    conexao.commit()
    conexao.close()

def registrar_execucao(id_jogo):
    """Atualiza a data e hora da última vez que o jogo foi aberto"""
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    conexao = sqlite3.connect(ARQUIVO_BANCO)
    cursor = conexao.cursor()
    cursor.execute("UPDATE jogos SET ultima_vez_jogado = ? WHERE id = ?", (agora, id_jogo))
    conexao.commit()
    conexao.close()
    return agora

def deletar_jogo(id_jogo):
    conexao = sqlite3.connect(ARQUIVO_BANCO)
    conexao.row_factory = sqlite3.Row
    cursor = conexao.cursor()
    
    # Recupera caminhos para limpar arquivos orfaos do disco
    cursor.execute("SELECT caminho_capa, caminho_save FROM jogos WHERE id = ?", (id_jogo,))
    jogo = cursor.fetchone()
    if jogo:
        for caminho in [jogo['caminho_capa'], jogo['caminho_save']]:
            if caminho and os.path.exists(caminho) and "dados_stasis" in os.path.abspath(caminho):
                try:
                    os.remove(caminho)
                    logger.info(f"Arquivo orfao removido do Stasis: {caminho}")
                except Exception as e:
                    logger.warning(f"Erro ao remover arquivo orfao {caminho}: {e}")
                    
    cursor.execute("DELETE FROM jogos WHERE id = ?", (id_jogo,))
    conexao.commit()
    conexao.close()
    logger.info(f"Jogo {id_jogo} deletado do banco e do Stasis.")
