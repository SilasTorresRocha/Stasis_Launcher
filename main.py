import os
import sys
import subprocess
import logging
import asyncio

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
    
    async def exibir_modal_progresso(destino_zip, modo, jogos_alvo):
        with ui.dialog().props('persistent') as dialog_progresso, ui.card().classes('w-full max-w-xl p-6 bg-gray-900 border border-blue-500/40 shadow-2xl'):
            with ui.row().classes('items-center gap-3 mb-2'):
                container_icone = ui.row().classes('items-center justify-center')
                with container_icone:
                    ui.spinner(size='md', color='primary')
                    
                with ui.column().classes('gap-0 flex-1'):
                    titulo_progresso = ui.label('Executando Backup Geral...').classes('text-xl font-bold text-white')
                    subtitulo_progresso = ui.label('Inicializando processo...').classes('text-xs text-blue-400')
                    
            barra_progresso = ui.linear_progress(value=0.0).props('rounded stripe animate size=10px color=primary').classes('w-full mt-3')
            
            with ui.row().classes('w-full justify-between items-center text-xs mt-1 text-gray-400 font-mono'):
                texto_porcentagem = ui.label('0%').classes('font-bold text-cyan-400')
                texto_contador = ui.label('Preparando ambiente...')

            ui.label('Console de Execução:').classes('text-xs font-bold text-gray-500 uppercase mt-4')
            with ui.column().classes('w-full bg-black/90 rounded-lg p-3 font-mono text-xs border border-gray-800 gap-1 min-h-[110px] justify-end'):
                linha_0 = ui.label('').classes('text-gray-600 truncate w-full')
                linha_1 = ui.label('').classes('text-gray-500 truncate w-full')
                linha_2 = ui.label('').classes('text-gray-300 truncate w-full')
                linha_3 = ui.label('> Aguardando início...').classes('text-cyan-300 font-semibold truncate w-full')
                
            logs_buffer = ['', '', '', '> Aguardando início...']
            
            def push_log(mensagem):
                logs_buffer.pop(0)
                logs_buffer.append(mensagem)
                linha_0.text = logs_buffer[0]
                linha_1.text = logs_buffer[1]
                linha_2.text = logs_buffer[2]
                linha_3.text = logs_buffer[3]

            container_botoes = ui.row().classes('w-full justify-end items-center gap-3 mt-4')

        dialog_progresso.open()
        await asyncio.sleep(0.08)

        total_jogos = len(jogos_alvo)
        total_etapas = total_jogos + 1
        
        if modo == 'completo' and total_jogos > 0:
            push_log(f'[*] Atualizando saves de {total_jogos} jogos...')
            for idx, j in enumerate(jogos_alvo, 1):
                nome = j['nome']
                subtitulo_progresso.text = f'Compactando ({idx}/{total_jogos}): {nome}'
                texto_contador.text = f'{idx} de {total_jogos} jogos'
                barra_progresso.value = (idx - 0.5) / total_etapas
                texto_porcentagem.text = f'{int(barra_progresso.value * 100)}%'
                push_log(f'[{idx}/{total_jogos}] Salvando saves de: {nome}...')
                await asyncio.sleep(0.01)

                caminho_zip, msg = await run.io_bound(utilidades.fazer_backup_save, j['id'], j['pasta_appdata'])
                if caminho_zip:
                    banco_dados.atualizar_jogo(j['id'], {'caminho_save': caminho_zip})
                    push_log(f'[+] {nome}: save salvo com sucesso.')
                else:
                    push_log(f'[!] {nome}: {msg}')

                barra_progresso.value = idx / total_etapas
                texto_porcentagem.text = f'{int(barra_progresso.value * 100)}%'
                await asyncio.sleep(0.01)

        subtitulo_progresso.text = 'Gerando arquivo compactado do Backup Geral (.zip)...'
        push_log('[*] Compactando banco de dados SQLite e dados do Stasis...')
        await asyncio.sleep(0.01)

        sucesso, msg = await run.io_bound(utilidades.gravar_arquivo_backup_geral, destino_zip)

        barra_progresso.value = 1.0
        texto_porcentagem.text = '100%'
        barra_progresso.props('color=positive')
        container_icone.clear()
        with container_icone:
            ui.icon('check_circle', color='positive', size='md')

        if sucesso:
            titulo_progresso.text = 'Backup Geral Concluído!'
            subtitulo_progresso.text = f'Arquivo salvo: {os.path.basename(destino_zip)}'
            push_log(f'[OK] Arquivo gerado: {os.path.basename(destino_zip)}')
            push_log('[OK] Todos os saves e cadastros foram preservados.')
            carregar_grid_jogos.refresh()
            ui.notify('Backup Geral criado com sucesso!', color='positive', icon='check_circle')
        else:
            titulo_progresso.text = 'Falha no Backup Geral'
            subtitulo_progresso.text = msg
            push_log(f'[ERRO] {msg}')
            ui.notify(msg, color='negative')

        with container_botoes:
            ui.button('Abrir Pasta no Explorer', icon='folder_open', on_click=lambda: utilidades.abrir_pasta_no_explorador(destino_zip)).props('outline color=secondary')
            ui.button('Concluir', on_click=dialog_progresso.close, color='positive' if sucesso else 'gray')

    async def acao_backup_geral():
        jogos = banco_dados.listar_jogos()
        if not jogos:
            ui.notify('Nenhum jogo cadastrado no Stasis para realizar backup.', color='warning')
            return

        jogos_com_saves = [
            j for j in jogos 
            if j.get('pasta_appdata') and os.path.exists(j.get('pasta_appdata'))
        ]

        with ui.dialog() as dialog_opcoes, ui.card().classes('w-full max-w-lg p-6 bg-gray-900 border border-blue-600/40 shadow-2xl'):
            with ui.row().classes('items-center gap-3 mb-2'):
                ui.icon('archive', size='2.2rem', color='primary')
                with ui.column().classes('gap-0'):
                    ui.label('Backup Geral do Stasis').classes('text-xl font-bold text-white')
                    ui.label(f'{len(jogos)} jogos no catálogo • {len(jogos_com_saves)} prontos para atualizar saves').classes('text-xs text-gray-400')
                    
            ui.markdown(
                'O **Backup Geral** empacota todo o banco de dados, capas e saves em um único arquivo `.zip`.\n\n'
                '• **Backup Completo (Recomendado):** Varre cada um dos seus jogos instalados e atualiza todos os saves para o estado atual antes de gerar o arquivo.\n'
                '• **Exportar Rápido:** Gera o backup imediatamente utilizando os arquivos já guardados no Stasis (sem re-compactar os jogos instalados).'
            ).classes('text-xs text-gray-300 bg-gray-800/80 p-3 rounded-lg border border-gray-700 my-3')
            
            async def iniciar_processamento(modo='completo'):
                dialog_opcoes.close()
                destino_zip = await utilidades.solicitar_caminho_salvar_backup_geral()
                if not destino_zip:
                    ui.notify('Operação de backup cancelada.', color='info')
                    return
                await exibir_modal_progresso(destino_zip, modo=modo, jogos_alvo=jogos_com_saves if modo == 'completo' else [])

            with ui.row().classes('w-full justify-between items-center mt-3'):
                ui.button('Cancelar', on_click=dialog_opcoes.close, color='gray').props('flat')
                with ui.row().classes('gap-2'):
                    ui.button('Exportar Rápido', icon='bolt', color='secondary', on_click=lambda: iniciar_processamento('rapido')).props('outline').tooltip('Exporta usando apenas os zips existentes')
                    ui.button('Backup Completo', icon='cloud_sync', color='primary', on_click=lambda: iniciar_processamento('completo')).classes('font-bold').tooltip('Atualiza saves de todos os jogos instalados e exporta')

        dialog_opcoes.open()

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
