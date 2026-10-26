import os
import sys
import subprocess
import logging

PASTA_DADOS = "dados_stasis"
ARQUIVO_FECHAR = os.path.join(PASTA_DADOS, "splash.close")
os.makedirs(PASTA_DADOS, exist_ok=True)

# Remove resquício de sinal de execução anterior
if os.path.exists(ARQUIVO_FECHAR):
    try:
        os.remove(ARQUIVO_FECHAR)
    except Exception:
        pass

# Dispara a Splash Screen apenas UMA vez no processo raiz
processo_splash = None
primeira_execucao = "STASIS_ROOT_STARTED" not in os.environ
if primeira_execucao and __name__ == "__main__":
    os.environ["STASIS_ROOT_STARTED"] = "1"
    caminho_splash = os.path.join(os.path.dirname(__file__), "splash.py")
    try:
        processo_splash = subprocess.Popen(
            [sys.executable, caminho_splash],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1
        )
    except Exception:
        pass

def log_splash(msg):
    if processo_splash and processo_splash.stdin:
        try:
            processo_splash.stdin.write(f"LOG:{msg}\n")
            processo_splash.stdin.flush()
        except Exception:
            pass

def fechar_splash():
    global processo_splash
    # Cria o arquivo de sinal instantâneo (funciona entre diferentes processos no Windows)
    try:
        with open(ARQUIVO_FECHAR, "w") as f:
            f.write("1")
    except Exception:
        pass

    if processo_splash:
        try:
            if processo_splash.stdin:
                try:
                    processo_splash.stdin.write("FECHAR\n")
                    processo_splash.stdin.flush()
                    processo_splash.stdin.close()
                except Exception:
                    pass
            processo_splash.terminate()
            processo_splash.kill()
        except Exception:
            pass
        processo_splash = None

# Garante compatibilidade de caracteres no console do Windows
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Configuração central de log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8", mode="a")
    ]
)
logger = logging.getLogger("main")

# Registra o cabeçalho no log apenas uma vez
if primeira_execucao:
    logger.info("=" * 40)
    logger.info("INICIANDO STASIS LAUNCHER")
    logger.info("=" * 40)

log_splash("Carregando interface e módulos do sistema...")

from nicegui import ui, app
import banco_dados
import interface_modais
import utilidades

# Fecha a splash screen assim que a engine principal iniciar
app.on_startup(fechar_splash)

# Inicializa o banco de dados apenas no processo raiz
if primeira_execucao:
    log_splash("Verificando banco de dados SQLite...")
    logger.info("Inicializando componentes do banco de dados...")
    banco_dados.inicializar_banco()

# Aloca a porta uma única vez e compartilha com subprocessos via variável de ambiente
if "STASIS_PORT" not in os.environ:
    log_splash("Verificando portas de rede disponíveis...")
    porta_livre = utilidades.encontrar_porta_livre(8000)
    os.environ["STASIS_PORT"] = str(porta_livre)
    logger.info(f"Porta {porta_livre} alocada para o servidor nativo.")
else:
    porta_livre = int(os.environ["STASIS_PORT"])

log_splash(f"Porta {porta_livre} pronta. Abrindo janela...")

ordem_catalogo = {'valor': 'recente'}

@ui.refreshable
def carregar_grid_jogos():
    """Lê os jogos do banco e monta os cards principais na tela"""
    jogos = banco_dados.listar_jogos(ordem=ordem_catalogo['valor'])
    
    if not jogos:
        with ui.column().classes('w-full items-center justify-center p-12 text-center'):
            ui.icon('sports_esports', size='5rem', color='gray')
            ui.label('Nenhum jogo salvo ainda.').classes('text-gray-400 mt-2 text-2xl font-bold')
            ui.label('Adicione seus jogos ou use o seletor de executavel para cadastra-los!').classes('text-gray-500 mt-1')
            ui.button('Adicionar Meu Primeiro Jogo', icon='add', 
                      on_click=lambda: interface_modais.abrir_formulario_jogo(None, carregar_grid_jogos)).props('color=primary').classes('mt-4')
        return

    with ui.grid(columns=4).classes('w-full gap-6 mt-4'):
        for jogo in jogos:
            with ui.card().classes('w-full cursor-pointer hover:scale-[1.02] hover:shadow-xl transition-all duration-200 border border-transparent hover:border-blue-500 p-0 overflow-hidden bg-gray-900').on('click', lambda j=jogo: interface_modais.abrir_detalhes(j, carregar_grid_jogos)):
                
                # Capa com Badge de Status
                with ui.element('div').classes('relative w-full h-48'):
                    caminho_capa = jogo.get('caminho_capa')
                    if caminho_capa and os.path.exists(caminho_capa):
                        ui.image(caminho_capa).classes('w-full h-48 object-cover')
                    else:
                        with ui.column().classes('w-full h-48 bg-gray-800 items-center justify-center'):
                            ui.icon('videogame_asset', size='4rem', color='gray')
                    
                    ui.badge(
                        jogo.get('status', 'Sem status'), 
                        color=interface_modais.obter_cor_status(jogo.get('status'))
                    ).classes('absolute top-2 right-2 text-xs font-bold shadow-md')

                # Informações no Card
                with ui.column().classes('p-3 w-full gap-1'):
                    ui.label(jogo['nome']).classes('text-lg font-bold truncate w-full text-white').tooltip(jogo['nome'])
                    
                    with ui.row().classes('w-full justify-between items-center text-xs text-gray-400'):
                        ui.label(f"v. {jogo.get('versao') or '1.0'}")
                        
                        ultimo = jogo.get('ultima_vez_jogado')
                        if ultimo:
                            ui.label(f"Jogado: {ultimo.split()[0]}").classes('text-amber-400')
                        else:
                            ui.label('Nunca jogado').classes('text-gray-500')
                    
                    # Botão rápido de Iniciar caso possua executável válido
                    exe_path = jogo.get('caminho_executavel')
                    if exe_path and os.path.exists(exe_path):
                        def play_rapido(e, j=jogo):
                            e.stop_propagation()
                            sucesso, msg = utilidades.executar_jogo(j.get('caminho_executavel'))
                            if sucesso:
                                banco_dados.registrar_execucao(j['id'])
                                ui.notify(f"Iniciando {j['nome']}...", color='positive', icon='sports_esports')
                                carregar_grid_jogos.refresh()
                                utilidades.minimizar_janela_app()
                            else:
                                ui.notify(msg, color='negative')
                                
                        with ui.row().classes('w-full justify-end mt-1'):
                            ui.button('JOGAR', icon='play_arrow', on_click=play_rapido).props('size=sm color=positive flat').classes('font-bold')

# --- CONFIGURAÇÃO DO LAYOUT PRINCIPAL ---

with ui.header(elevated=True).style('background-color: #1a1a2e').classes('items-center justify-between px-6 py-2'):
    with ui.row().classes('items-center gap-2'):
        ui.label('Stasis Launcher').classes('text-2xl font-bold tracking-wider text-white')
        ui.badge('Version & Saves', color='primary').classes('text-xs')
        
    ui.button('Adicionar Jogo', icon='add', on_click=lambda: interface_modais.abrir_formulario_jogo(None, carregar_grid_jogos)).props('color=primary rounded')

with ui.left_drawer(elevated=True).props('show-if-above width=260').style('background-color: #16213e; color: white'):
    ui.label('Ferramentas').classes('text-lg font-bold mb-6 mt-4 ml-4 text-gray-300 uppercase tracking-widest')
    
    async def acao_backup_geral():
        jogos = banco_dados.listar_jogos()
        pendentes = []
        for j in jogos:
            pasta = j.get('pasta_appdata')
            zip_save = j.get('caminho_save')
            tem_zip = zip_save and os.path.exists(zip_save)
            if pasta and os.path.exists(pasta) and not tem_zip:
                pendentes.append(j)
                
        if not pendentes:
            sucesso, msg = await utilidades.exportar_backup_geral()
            if sucesso:
                ui.notify(msg, color='positive', icon='check_circle')
            else:
                ui.notify(msg, color='warning')
            return

        with ui.dialog() as dialog_pendentes, ui.card().classes('w-full max-w-lg p-5'):
            ui.label('Saves Pendentes de Backup').classes('text-xl font-bold text-amber-400')
            ui.label('Estes jogos possuem pasta de saves mas ainda nao estao no Stasis. Deseja zipar antes do backup geral?').classes('text-sm text-gray-300 mt-1')
            
            checks = {}
            with ui.column().classes('w-full mt-3 gap-2 max-h-60 overflow-y-auto'):
                for pj in pendentes:
                    with ui.row().classes('w-full items-center justify-between p-2 bg-gray-800 rounded'):
                        checks[pj['id']] = ui.checkbox(pj['nome'], value=True).classes('text-white')
                        ui.label(os.path.basename(pj['pasta_appdata'])).classes('text-xs text-gray-400 font-mono')
                        
            async def processar_e_exportar():
                dialog_pendentes.close()
                total_zipados = 0
                for pj in pendentes:
                    if checks.get(pj['id']) and checks[pj['id']].value:
                        caminho_zip, _ = utilidades.fazer_backup_save(pj['id'], pj['pasta_appdata'])
                        if caminho_zip:
                            banco_dados.atualizar_jogo(pj['id'], {'caminho_save': caminho_zip})
                            total_zipados += 1
                if total_zipados > 0:
                    ui.notify(f'{total_zipados} save(s) compactado(s) com sucesso!', color='positive')
                    carregar_grid_jogos.refresh()
                sucesso, msg = await utilidades.exportar_backup_geral()
                if sucesso:
                    ui.notify(msg, color='positive', icon='check_circle')
                else:
                    ui.notify(msg, color='warning')
                    
            async def exportar_direto():
                dialog_pendentes.close()
                sucesso, msg = await utilidades.exportar_backup_geral()
                if sucesso:
                    ui.notify(msg, color='positive', icon='check_circle')
                else:
                    ui.notify(msg, color='warning')
                    
            with ui.row().classes('w-full justify-between items-center mt-5'):
                ui.button('Ignorar e Exportar', on_click=exportar_direto, color='gray').props('flat size=sm')
                with ui.row().classes('gap-2'):
                    ui.button('Cancelar', on_click=dialog_pendentes.close, color='gray').props('flat')
                    ui.button('Compactar & Exportar', on_click=processar_e_exportar, color='primary')
                    
        dialog_pendentes.open()

    async def acao_restaurar_geral():
        sucesso, msg = await utilidades.importar_backup_geral()
        if sucesso:
            ui.notify(msg, color='positive', icon='check_circle')
            carregar_grid_jogos.refresh()
        else:
            ui.notify(msg, color='warning')

    ui.button('Backup Geral', icon='archive', color='secondary', on_click=acao_backup_geral).classes('w-full mb-3 justify-start px-4').props('flat').tooltip('Exporta banco + Stasis em um único zip')
    ui.button('Restaurar Backup', icon='unarchive', color='secondary', on_click=acao_restaurar_geral).classes('w-full mb-3 justify-start px-4').props('flat').tooltip('Importa e restaura o zip do Backup Geral')
    
    def abrir_arquivo_log():
        if os.path.exists("app.log"):
            utilidades.abrir_arquivo_direto("app.log")
        else:
            ui.notify("Arquivo de log ainda não foi criado.", color='info')
            
    ui.button('Ver Logs', icon='receipt_long', color='secondary', on_click=abrir_arquivo_log).classes('w-full mb-3 justify-start px-4').props('flat').tooltip('Abre o arquivo app.log no Bloco de Notas')
    
    ui.separator().classes('my-4 opacity-30')
    
    ui.label('Informações').classes('text-sm font-bold mb-2 mt-2 ml-4 text-gray-500 uppercase')
    ui.label('Gerenciador e Launcher de Jogos em Stasis.').classes('text-xs text-gray-400 ml-4 mr-4')
    ui.label('Versão 1.4.0').classes('text-xs text-gray-500 ml-4 mt-2 font-mono')

with ui.column().classes('w-full max-w-[1400px] mx-auto p-6'):
    with ui.row().classes('w-full justify-between items-center mb-2'):
        with ui.column().classes('gap-0'):
            ui.label('Meu Catálogo').classes('text-3xl font-bold text-white')
            ui.label('Clique em um card para detalhes e saves.').classes('text-gray-400 text-sm')
            
        with ui.row().classes('items-center gap-2'):
            ui.icon('sort', color='primary').classes('text-xl')
            def mudar_ordenacao(e):
                ordem_catalogo['valor'] = e.value
                carregar_grid_jogos.refresh()
                
            ui.select(
                {
                    'recente': 'Mais Recentes (Jogados)',
                    'atualizacao': 'Últimos Adicionados',
                    'alfabetica': 'Nome (A-Z)',
                    'status': 'Por Status'
                },
                value=ordem_catalogo['valor'],
                label='Ordenar por',
                on_change=mudar_ordenacao
            ).props('dense outlined options-dense').classes('w-56 text-sm bg-gray-900')
        
    carregar_grid_jogos()

# Fecha a splash screen assim que a interface do usuário carrega no pywebview
ui.timer(0.2, fechar_splash, once=True)

def iniciar():
    ui.run(
        native=True, 
        port=porta_livre, 
        title="Stasis Launcher", 
        window_size=(1280, 800), 
        dark=True, 
        reload=False
    )

if __name__ == "__main__":
    iniciar()
