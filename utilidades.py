import os
import shutil
import time
import tkinter as tk
from tkinter import filedialog
from nicegui import run

# Estrutura de pastas do nosso "Cofre"
PASTA_DADOS = "dados_cofre"
PASTA_CAPAS = os.path.join(PASTA_DADOS, "capas")
PASTA_BACKUPS = os.path.join(PASTA_DADOS, "backups_saves")

# Garante que as pastas locais existam assim que esse arquivo for importado
os.makedirs(PASTA_CAPAS, exist_ok=True)
os.makedirs(PASTA_BACKUPS, exist_ok=True)

def _abrir_dialogo_arquivo():
    """Função interna síncrona usando o nativo do Windows (Tkinter)"""
    root = tk.Tk()
    root.attributes('-topmost', True) # Traz a janela para a frente
    root.withdraw() # Esconde a janela principal do Tkinter, deixa só a caixa de diálogo
    caminho = filedialog.askopenfilename(
        title="Selecione a Imagem de Capa",
        filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp *.gif"), ("Todos os arquivos", "*.*")]
    )
    root.destroy()
    return caminho

def _abrir_dialogo_pasta():
    """Função interna síncrona para pegar pastas"""
    root = tk.Tk()
    root.attributes('-topmost', True)
    root.withdraw()
    caminho = filedialog.askdirectory(title="Selecione a pasta do jogo ou save")
    root.destroy()
    return caminho

async def escolher_imagem_capa():
    """
    Roda a caixa de diálogo do Windows de forma assíncrona 
    para não travar a interface do NiceGUI.
    """
    return await run.io_bound(_abrir_dialogo_arquivo)

async def escolher_pasta_save():
    return await run.io_bound(_abrir_dialogo_pasta)

def importar_imagem_para_cofre(caminho_original):
    """
    Copia a imagem selecionada pelo usuário para a pasta interna do nosso sistema.
    Retorna o novo caminho interno da imagem salva.
    """
    if not caminho_original or not os.path.exists(caminho_original):
        return caminho_original # Retorna como veio (vazio ou erro)
        
    # Se a imagem já estiver na nossa pasta interna, ignora a cópia
    if PASTA_CAPAS in os.path.abspath(caminho_original):
        return caminho_original
        
    nome_arquivo = os.path.basename(caminho_original)
    # Adicionamos um carimbo de tempo (timestamp) para garantir que nomes repetidos 
    # (ex: "capa.jpg" e "capa.jpg" de jogos diferentes) não sobrescrevam um ao outro.
    nome_unico = f"{int(time.time())}_{nome_arquivo}"
    caminho_destino = os.path.join(PASTA_CAPAS, nome_unico)
    
    shutil.copy2(caminho_original, caminho_destino)
    return caminho_destino
