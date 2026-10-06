from nicegui import ui
import banco_dados
import interface_modais
import os

# Garante que o banco exista na inicialização
banco_dados.inicializar_banco()

@ui.refreshable
def carregar_grid_jogos():
    """Lê os jogos do banco e monta os cards principais na tela"""
    jogos = banco_dados.listar_jogos()
    
    if not jogos:
        ui.label('Nenhum jogo salvo ainda. Vamos começar adicionando um!').classes('text-gray-400 mt-8 text-xl text-center w-full')
        return

    with ui.grid(columns=4).classes('w-full gap-6 mt-4'):
        for jogo in jogos:
            # Card clicável que abre o Modal de Detalhes da nova interface_modais.py
            with ui.card().classes('w-full cursor-pointer hover:scale-105 hover:shadow-lg transition-all duration-200 border border-transparent hover:border-blue-500 p-0 overflow-hidden').on('click', lambda j=jogo: interface_modais.abrir_detalhes(j, carregar_grid_jogos)):
                
                caminho_capa = jogo.get('caminho_capa')
                if caminho_capa and os.path.exists(caminho_capa):
                    ui.image(caminho_capa).classes('w-full h-48 object-cover')
                else:
                    with ui.column().classes('w-full h-48 bg-gray-800 items-center justify-center'):
                        ui.icon('videogame_asset', size='4rem', color='gray')
                
                with ui.column().classes('p-3 w-full'):
                    ui.label(jogo['nome']).classes('text-lg font-bold truncate w-full').tooltip(jogo['nome'])
                    with ui.row().classes('w-full justify-between items-center mt-1'):
                        ui.label(f"v. {jogo.get('versao', 'N/A')}").classes('text-sm text-gray-400')
                        ui.badge(jogo['status'], color=interface_modais.obter_cor_status(jogo['status'])).classes('text-xs')

# --- CONFIGURAÇÃO DO LAYOUT PRINCIPAL ---

with ui.header(elevated=True).style('background-color: #1a1a2e').classes('items-center justify-between px-6 py-2'):
    ui.label('🎮 Cofre Indie').classes('text-2xl font-bold tracking-wider')
    # Botão de adicionar chama o modal repassando a função de recarregar a grid
    ui.button('Adicionar Jogo', icon='add', on_click=lambda: interface_modais.abrir_formulario_jogo(None, carregar_grid_jogos)).props('color=primary rounded')

with ui.left_drawer(elevated=True).props('show-if-above width=250').style('background-color: #16213e; color: white'):
    ui.label('Ferramentas').classes('text-lg font-bold mb-6 mt-4 ml-4 text-gray-300 uppercase tracking-widest')
    
    ui.button('Backup Geral', icon='archive', color='secondary').classes('w-full mb-3 justify-start px-4').props('flat')
    ui.button('Restaurar Backup', icon='unarchive', color='secondary').classes('w-full mb-3 justify-start px-4').props('flat')
    
    ui.separator().classes('my-4 opacity-30')
    
    ui.label('Informações').classes('text-sm font-bold mb-2 mt-2 ml-4 text-gray-500 uppercase')
    ui.label('Gerenciador modular de saves e jogos Indie.').classes('text-xs text-gray-400 ml-4 mr-4')

with ui.column().classes('w-full max-w-[1400px] mx-auto p-6'):
    ui.label('Meu Catálogo').classes('text-3xl font-bold mb-2 text-white')
    ui.label('Clique em um card para ver detalhes, notas e links.').classes('text-gray-400 mb-4')
    
    carregar_grid_jogos()

# Inicia o app em modo Desktop
ui.run(native=True, title="Cofre Indie", window_size=(1280, 800), dark=True, reload=False)
