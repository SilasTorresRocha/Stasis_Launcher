import sqlite3
import os
from datetime import datetime

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
            data_atualizacao TEXT
        )
    """)
    conexao.commit()
    conexao.close()

def listar_jogos():
    conexao = sqlite3.connect(ARQUIVO_BANCO)
    # Row factory para retornar dicionários em vez de tuplas
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
    conexao.commit()
    conexao.close()

def atualizar_jogo(id_jogo, dados):
    conexao = sqlite3.connect(ARQUIVO_BANCO)
    cursor = conexao.cursor()
    
    dados['data_atualizacao'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    set_clause = ', '.join([f"{k} = ?" for k in dados.keys()])
    valores = tuple(dados.values()) + (id_jogo,)
    
    cursor.execute(f"UPDATE jogos SET {set_clause} WHERE id = ?", valores)
    conexao.commit()
    conexao.close()

def deletar_jogo(id_jogo):
    conexao = sqlite3.connect(ARQUIVO_BANCO)
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM jogos WHERE id = ?", (id_jogo,))
    conexao.commit()
    conexao.close()
