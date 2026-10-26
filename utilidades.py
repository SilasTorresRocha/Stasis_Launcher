import os
import shutil
import time
import glob
import zipfile
import subprocess
import socket
import logging
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from nicegui import run, app

logger = logging.getLogger("utilidades")

# Estrutura de pastas do Stasis
PASTA_DADOS = "dados_stasis"
PASTA_CAPAS = os.path.join(PASTA_DADOS, "capas")
PASTA_BACKUPS = os.path.join(PASTA_DADOS, "backups_saves")
ARQUIVO_BANCO = "banco_saves.db"

os.makedirs(PASTA_CAPAS, exist_ok=True)
os.makedirs(PASTA_BACKUPS, exist_ok=True)

def encontrar_porta_livre(porta_inicial=8000, max_tentativas=50):
    for porta in range(porta_inicial, porta_inicial + max_tentativas):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', porta))
                logger.info(f"Porta {porta} selecionada e livre para uso.")
                return porta
            except OSError:
                continue
    return porta_inicial

def _abrir_dialogo_arquivo(titulo, tipos):
    root = tk.Tk()
    root.attributes('-topmost', True)
    root.withdraw()
    caminho = filedialog.askopenfilename(title=titulo, filetypes=tipos)
    root.destroy()
    return caminho

def _abrir_dialogo_pasta(titulo):
    root = tk.Tk()
    root.attributes('-topmost', True)
    root.withdraw()
    caminho = filedialog.askdirectory(title=titulo)
    root.destroy()
    return caminho

def _abrir_dialogo_salvar_arquivo(titulo, arquivo_padrao):
    root = tk.Tk()
    root.attributes('-topmost', True)
    root.withdraw()
    caminho = filedialog.asksaveasfilename(
        title=titulo,
        defaultextension=".zip",
        initialfile=arquivo_padrao,
        filetypes=[("Arquivo Zip", "*.zip")]
    )
    root.destroy()
    return caminho

async def escolher_imagem_capa():
    return await run.io_bound(
        _abrir_dialogo_arquivo,
        "Selecione a Imagem de Capa",
        [("Imagens", "*.png *.jpg *.jpeg *.webp *.gif"), ("Todos os arquivos", "*.*")]
    )

async def escolher_executavel():
    return await run.io_bound(
        _abrir_dialogo_arquivo,
        "Selecione o Executavel do Jogo (.exe)",
        [("Executaveis", "*.exe *.bat *.sh *.bin"), ("Todos os arquivos", "*.*")]
    )

async def escolher_pasta_save(titulo="Selecione a pasta de saves"):
    return await run.io_bound(_abrir_dialogo_pasta, titulo)

def importar_imagem_para_stasis(caminho_original, capa_anterior=None):
    """
    Copia a imagem usando apenas identificador numerico puro (timestamp em milissegundos).
    Se houver uma capa anterior e for diferente, exclui a antiga para evitar acumulo de lixo.
    """
    if not caminho_original or not os.path.exists(caminho_original):
        return caminho_original
        
    caminho_abs = os.path.abspath(caminho_original)
    
    # Se ja estiver dentro da pasta de capas e for a mesma, nao faz nada
    if PASTA_CAPAS in caminho_abs:
        return caminho_original
        
    extensao = os.path.splitext(caminho_original)[1].lower()
    if not extensao:
        extensao = ".jpg"
        
    # Nome exclusivamente numerico
    nome_numerico = f"{int(time.time() * 1000)}{extensao}"
    caminho_destino = os.path.join(PASTA_CAPAS, nome_numerico)
    
    shutil.copy2(caminho_original, caminho_destino)
    logger.info(f"Nova capa salva como {nome_numerico}")
    
    # Remove a capa anterior se existir no Stasis
    if capa_anterior and os.path.exists(capa_anterior):
        try:
            if os.path.abspath(PASTA_CAPAS) in os.path.abspath(capa_anterior):
                os.remove(capa_anterior)
                logger.info(f"Capa antiga removida com sucesso: {capa_anterior}")
        except Exception as e:
            logger.warning(f"Nao foi possivel remover capa antiga: {e}")
            
    return caminho_destino

def detectar_pasta_saves(caminho_executavel):
    """
    Procura ativamente por pastas de saves com arquivos reais (.save, .sav, etc.)
    Retorna (caminho_encontrado, tem_arquivos_reais)
    """
    if not caminho_executavel or not os.path.exists(caminho_executavel):
        return None, False
        
    pasta_raiz = os.path.dirname(caminho_executavel)
    nome_pasta_jogo = os.path.basename(pasta_raiz)
    
    pastas_para_testar = [
        os.path.join(pasta_raiz, "game", "saves"),
        os.path.join(pasta_raiz, "saves"),
    ]
    
    # Checa tambem no AppData do RenPy no Windows
    appdata = os.environ.get('APPDATA')
    if appdata:
        pasta_renpy = os.path.join(appdata, "RenPy")
        if os.path.exists(pasta_renpy):
            # Procura por subpastas com nome aproximado do jogo
            for item in os.listdir(pasta_renpy):
                if nome_pasta_jogo.lower() in item.lower():
                    pastas_para_testar.append(os.path.join(pasta_renpy, item))
                    
    extensoes_save = ('*.save', '*.sav', '*.rpy', '*.dat', '*.rvdata2')
    
    for pasta in pastas_para_testar:
        if os.path.exists(pasta):
            # Verifica se existem arquivos com extensao de save dentro dela
            arquivos_save = []
            for ext in extensoes_save:
                arquivos_save.extend(glob.glob(os.path.join(pasta, ext)))
                
            if arquivos_save:
                logger.info(f"Pasta de saves valida com arquivos detectada: {pasta}")
                return pasta, True
            else:
                # A pasta existe (ex: game/saves), mas pode estar vazia ainda
                logger.info(f"Pasta de saves encontrada, mas sem saves gerados ainda: {pasta}")
                return pasta, False
                
    # Se nao existe pasta de saves criada ainda, mas existe subpasta 'game' (padrao Ren'Py)
    pasta_game = os.path.join(pasta_raiz, "game")
    if os.path.exists(pasta_game):
        provavel = os.path.join(pasta_game, "saves")
        logger.info(f"Pasta padrao RenPy sugerida para novos saves: {provavel}")
        return provavel, False
                
    return None, False

def migrar_versao_jogo(id_jogo, caminho_antigo_exe, pasta_antiga_save, novo_executavel, nova_versao, nova_pasta_save=None):
    """
    Executa o fluxo completo de atualização de versão do jogo:
    1. Backup de segurança dos saves atuais em dados_stasis/
    2. Identificação/criação da pasta de saves da nova versão
    3. Cópia dos arquivos de save da versão antiga para a nova versão
    Retorna: (sucesso, nova_pasta_save, pasta_jogo_antigo, total_copiados, mensagem)
    """
    if not novo_executavel or not os.path.exists(novo_executavel):
        return False, None, None, 0, "O executável da nova versão não foi encontrado no disco!"
        
    pasta_jogo_antigo = os.path.dirname(caminho_antigo_exe) if (caminho_antigo_exe and os.path.exists(caminho_antigo_exe)) else None
    
    # 1. Backup de segurança se houver pasta de saves antiga
    caminho_backup_zip = None
    if pasta_antiga_save and os.path.exists(pasta_antiga_save):
        caminho_backup_zip, _ = fazer_backup_save(id_jogo, pasta_antiga_save)
        logger.info(f"Backup de seguranca gerado antes da migracao: {caminho_backup_zip}")
        
    # 2. Determina a pasta de saves da nova versão
    if not nova_pasta_save:
        pasta_detectada, _ = detectar_pasta_saves(novo_executavel)
        if pasta_detectada:
            nova_pasta_save = pasta_detectada
        else:
            pasta_raiz_nova = os.path.dirname(novo_executavel)
            if os.path.exists(os.path.join(pasta_raiz_nova, "game")):
                nova_pasta_save = os.path.join(pasta_raiz_nova, "game", "saves")
            else:
                nova_pasta_save = os.path.join(pasta_raiz_nova, "saves")
                
    total_copiados = 0
    # 3. Copia os saves da versão anterior para a nova se as pastas forem distintas
    if pasta_antiga_save and os.path.exists(pasta_antiga_save):
        norm_antiga = os.path.normcase(os.path.abspath(pasta_antiga_save))
        norm_nova = os.path.normcase(os.path.abspath(nova_pasta_save))
        
        if norm_antiga != norm_nova:
            try:
                os.makedirs(nova_pasta_save, exist_ok=True)
                for raiz, _, arquivos in os.walk(pasta_antiga_save):
                    for arq in arquivos:
                        caminho_orig = os.path.join(raiz, arq)
                        caminho_rel = os.path.relpath(caminho_orig, pasta_antiga_save)
                        caminho_dest = os.path.join(nova_pasta_save, caminho_rel)
                        os.makedirs(os.path.dirname(caminho_dest), exist_ok=True)
                        shutil.copy2(caminho_orig, caminho_dest)
                        total_copiados += 1
                logger.info(f"Migracao: {total_copiados} arquivos de save copiados de {pasta_antiga_save} para {nova_pasta_save}")
            except Exception as e:
                logger.error(f"Erro ao copiar arquivos de save: {e}")
                return False, nova_pasta_save, pasta_jogo_antigo, total_copiados, f"Erro ao copiar saves: {e}"
        else:
            logger.info("A pasta de saves da nova versao e a mesma da versao anterior. Nenhuma copia necessaria.")
            
    return True, nova_pasta_save, pasta_jogo_antigo, total_copiados, "Migração de versão concluída com sucesso!"

def executar_jogo(caminho_executavel):
    """Inicia o jogo sem travar o aplicativo"""
    if not caminho_executavel or not os.path.exists(caminho_executavel):
        return False, "Arquivo executavel nao foi encontrado!"
        
    pasta_jogo = os.path.dirname(caminho_executavel)
    try:
        subprocess.Popen([caminho_executavel], cwd=pasta_jogo)
        logger.info(f"Jogo executado: {caminho_executavel}")
        return True, "Jogo iniciado com sucesso!"
    except Exception as e:
        logger.error(f"Falha ao executar jogo: {e}")
        return False, f"Falha ao iniciar jogo: {e}"

def minimizar_janela_app():
    """Minimiza a janela do Stasis Launcher automaticamente"""
    try:
        if hasattr(app, 'native') and app.native and hasattr(app.native, 'main_window'):
            app.native.main_window.minimize()
    except Exception as e:
        logger.warning(f"Nao foi possivel minimizar a janela nativa: {e}")

def abrir_arquivo_direto(caminho):
    """Abre um arquivo diretamente no programa padrao do Windows (ex: Bloco de Notas)"""
    if not caminho or not os.path.exists(caminho):
        return False, "Arquivo nao encontrado!"
    try:
        os.startfile(os.path.abspath(caminho))
        return True, "Arquivo aberto com sucesso!"
    except Exception as e:
        return False, f"Erro ao abrir arquivo: {e}"

def abrir_pasta_no_explorador(caminho):
    """Abre uma pasta no Windows Explorer"""
    if not caminho or not os.path.exists(caminho):
        return False, "Caminho nao encontrado!"
    try:
        caminho_norm = os.path.normpath(caminho)
        if os.path.isfile(caminho_norm):
            caminho_norm = os.path.dirname(caminho_norm)
        os.startfile(caminho_norm)
        return True, "Pasta aberta!"
    except Exception as e:
        return False, f"Erro ao abrir pasta: {e}"

def fazer_backup_save(id_jogo, pasta_save):
    """Compacta a pasta de save para dados_stasis/backups_saves/jogo_{id_jogo}_save.zip"""
    if not pasta_save or not os.path.exists(pasta_save):
        return None, "A pasta de save indicada nao existe!"
        
    nome_zip = f"jogo_{id_jogo}_save.zip"
    caminho_zip = os.path.join(PASTA_BACKUPS, nome_zip)
    
    try:
        with zipfile.ZipFile(caminho_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for raiz, _, arquivos in os.walk(pasta_save):
                for arquivo in arquivos:
                    caminho_completo = os.path.join(raiz, arquivo)
                    caminho_relativo = os.path.relpath(caminho_completo, pasta_save)
                    zipf.write(caminho_completo, caminho_relativo)
        logger.info(f"Backup do jogo {id_jogo} salvo em {caminho_zip}")
        return caminho_zip, "Backup do save realizado com sucesso no Stasis!"
    except Exception as e:
        logger.error(f"Erro ao zipar save {id_jogo}: {e}")
        return None, f"Erro ao gerar arquivo zip: {e}"

def restaurar_backup_save(caminho_zip, pasta_save):
    """Extrai o zip do save de volta para a pasta de destino"""
    if not caminho_zip or not os.path.exists(caminho_zip):
        return False, "Nenhum arquivo de backup encontrado para este jogo!"
    if not pasta_save:
        return False, "Pasta de destino do save nao foi configurada!"
        
    try:
        os.makedirs(pasta_save, exist_ok=True)
        with zipfile.ZipFile(caminho_zip, 'r') as zipf:
            zipf.extractall(pasta_save)
        logger.info(f"Save restaurado em {pasta_save}")
        return True, "Save restaurado com sucesso na pasta de destino!"
    except Exception as e:
        logger.error(f"Erro ao restaurar save: {e}")
        return False, f"Erro ao restaurar save: {e}"

async def solicitar_caminho_salvar_backup_geral():
    """Abre o diálogo do Windows para o usuário escolher onde salvar o Backup Geral"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_padrao = f"Backup_Stasis_{timestamp}.zip"
    return await run.io_bound(
        _abrir_dialogo_salvar_arquivo,
        "Escolha onde salvar o Backup Geral",
        nome_padrao
    )

def gravar_arquivo_backup_geral(destino_zip):
    """Gera o arquivo zip único contendo o banco de dados e os dados do Stasis (executado em thread separada)"""
    if not destino_zip:
        return False, "Caminho de destino inválido."
        
    try:
        with zipfile.ZipFile(destino_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if os.path.exists(ARQUIVO_BANCO):
                zipf.write(ARQUIVO_BANCO, arcname=ARQUIVO_BANCO)
                
            if os.path.exists(PASTA_DADOS):
                for raiz, _, arquivos in os.walk(PASTA_DADOS):
                    for arq in arquivos:
                        # Ignora arquivos de controle interno
                        if arq.endswith(".close") or arq.endswith(".tmp"):
                            continue
                        caminho_completo = os.path.join(raiz, arq)
                        caminho_rel = os.path.relpath(caminho_completo, start=".")
                        zipf.write(caminho_completo, arcname=caminho_rel)
                        
        logger.info(f"Backup geral gerado em {destino_zip}")
        return True, f"Backup Geral criado: {os.path.basename(destino_zip)}"
    except Exception as e:
        logger.error(f"Erro no backup geral: {e}")
        return False, f"Erro ao gerar Backup Geral: {e}"

async def exportar_backup_geral():
    """Gera o backup geral solicitando o caminho e executando a compactação sem travar a interface"""
    destino_zip = await solicitar_caminho_salvar_backup_geral()
    if not destino_zip:
        return False, "Operação cancelada."
    return await run.io_bound(gravar_arquivo_backup_geral, destino_zip)

def extrair_arquivo_backup_geral(origem_zip):
    """Extrai os dados do backup geral de volta para o diretório raiz"""
    try:
        with zipfile.ZipFile(origem_zip, 'r') as zipf:
            zipf.extractall(".")
        logger.info("Backup geral importado com sucesso.")
        return True, "Backup Geral restaurado com sucesso!"
    except Exception as e:
        logger.error(f"Erro ao importar backup geral: {e}")
        return False, f"Erro ao restaurar Backup Geral: {e}"

async def importar_backup_geral():
    """Restaura o banco e todo o Stasis a partir de um arquivo zip sem travar a interface"""
    origem_zip = await run.io_bound(
        _abrir_dialogo_arquivo,
        "Selecione o arquivo de Backup Geral (.zip)",
        [("Arquivo Zip", "*.zip")]
    )
    
    if not origem_zip:
        return False, "Operação cancelada."
        
    return await run.io_bound(extrair_arquivo_backup_geral, origem_zip)
