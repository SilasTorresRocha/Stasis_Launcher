from nicegui import ui
import os
import banco_dados
import utilidades

# Variável global apenas para o contexto do modal de detalhes
dialog_detalhes = None

def obter_cor_status(status):
    cores = {
        'Jogando': 'blue',
        'Aguardando Update': 'warning',
        'Finalizado': 'negative',
        'Dropado': 'orange'
    }
    return cores.get(status, 'gray')

def salvar_jogo(dialog, id_jogo, dados, funcao_atualizar_grid, capa_anterior=None):
    if not dados['nome']:
        ui.notify('O nome do jogo é obrigatório!', color='negative')
        return
        
    dados['caminho_capa'] = utilidades.importar_imagem_para_stasis(dados.get('caminho_capa'), capa_anterior)
        
    if id_jogo:
        banco_dados.atualizar_jogo(id_jogo, dados)
        ui.notify(f'{dados["nome"]} atualizado com sucesso!', color='positive')
    else:
        banco_dados.adicionar_jogo(dados)
        ui.notify(f'{dados["nome"]} cadastrado com sucesso!', color='positive')
        
    dialog.close()
    
    global dialog_detalhes
    if dialog_detalhes:
        dialog_detalhes.close()
        dialog_detalhes = None
        
    funcao_atualizar_grid.refresh()

def abrir_formulario_jogo(jogo=None, funcao_atualizar_grid=None):
    is_edit = jogo is not None
    titulo = 'Editar Jogo' if is_edit else 'Cadastrar Novo Jogo'
    
    if not is_edit:
        jogo = {
            'nome': '', 'desenvolvedor': '', 'versao': '', 'status': 'Jogando',
            'notas': '', 'tags': '', 'link_loja': '', 'link_oficial': '',
            'pasta_appdata': '', 'caminho_capa': '', 'caminho_executavel': '', 'caminho_save': ''
        }
    
    with ui.dialog() as dialog, ui.card().classes('w-full max-w-4xl p-6'):
        ui.label(titulo).classes('text-2xl font-bold mb-4 text-white')
        
        with ui.row().classes('w-full gap-6'):
            # PRIMEIRA COLUNA
            with ui.column().classes('flex-1 gap-2'):
                with ui.row().classes('w-full items-center justify-between no-wrap'):
                    caminho_executavel = ui.input(
                        'Executável do Jogo (.exe)', 
                        value=jogo.get('caminho_executavel', '')
                    ).classes('flex-1')
                    
                    async def acao_buscar_executavel():
                        path = await utilidades.escolher_executavel()
                        if path:
                            caminho_executavel.value = path
                            if not nome.value.strip():
                                nome_base = os.path.splitext(os.path.basename(path))[0]
                                nome.value = nome_base.replace('_', ' ').replace('-', ' ').title()
                            
                            # Detecção inteligente verificando arquivos .save reais
                            pasta_detectada, tem_saves = utilidades.detectar_pasta_saves(path)
                            if pasta_detectada:
                                pasta_save.value = pasta_detectada
                                if tem_saves:
                                    ui.notify('Pasta com saves reais (.save) detectada com sucesso!', color='positive', icon='check_circle')
                                else:
                                    ui.notify('Pasta de saves detectada, mas sem arquivos .save gerados ainda.', color='info', icon='info')
                            else:
                                ui.notify('Nenhuma pasta de saves encontrada automaticamente. Por favor, aponte manualmente.', color='warning')
                                
                    ui.button(icon='sports_esports', on_click=acao_buscar_executavel).props('outline color=accent').classes('mt-2').tooltip('Selecionar .exe do jogo')

                nome = ui.input('Nome do Jogo *', value=jogo.get('nome', '')).classes('w-full')
                versao = ui.input('Versão atual', value=jogo.get('versao', '')).classes('w-full')
                status = ui.select(['Jogando', 'Aguardando Update', 'Finalizado', 'Dropado'], 
                                   label='Status', value=jogo.get('status', 'Jogando')).classes('w-full')
                tags = ui.input('Tags (ex: VN, RenPy, RPG)', value=jogo.get('tags', '')).classes('w-full')
                
            # SEGUNDA COLUNA
            with ui.column().classes('flex-1 gap-2'):
                desenvolvedor = ui.input('Desenvolvedor (Dev/Patreon)', value=jogo.get('desenvolvedor', '')).classes('w-full')
                
                with ui.row().classes('w-full items-center justify-between no-wrap'):
                    caminho_capa = ui.input('Caminho da Capa', value=jogo.get('caminho_capa', '')).classes('flex-1')
                    async def acao_buscar_capa():
                        path = await utilidades.escolher_imagem_capa()
                        if path: caminho_capa.value = path
                    ui.button(icon='image_search', on_click=acao_buscar_capa).props('outline color=primary').classes('mt-2')
                
                with ui.row().classes('w-full items-center justify-between no-wrap'):
                    pasta_save = ui.input('Pasta de Saves (game/saves ou AppData)', value=jogo.get('pasta_appdata', '')).classes('flex-1')
                    async def acao_buscar_pasta():
                        path = await utilidades.escolher_pasta_save()
                        if path: pasta_save.value = path
                    ui.button(icon='folder_open', on_click=acao_buscar_pasta).props('outline color=secondary').classes('mt-2')
                
                link_loja = ui.input('Link Principal (Loja / Patreon)', value=jogo.get('link_loja', '')).classes('w-full')
                link_oficial = ui.input('Link Secundário (opcional)', value=jogo.get('link_oficial', '')).classes('w-full')
                
        notas = ui.textarea('Notas / Onde parei?', value=jogo.get('notas', '')).classes('w-full mt-4')
        
        with ui.row().classes('w-full justify-between mt-6 p-2 bg-gray-900 rounded'):
            if is_edit:
                ui.button('Deletar Jogo', on_click=lambda: (
                    banco_dados.deletar_jogo(jogo['id']), 
                    dialog.close(), 
                    funcao_atualizar_grid.refresh()
                ), color='red').props('flat')
            else:
                ui.label()
                
            with ui.row().classes('gap-2'):
                ui.button('Cancelar', on_click=dialog.close, color='gray')
                ui.button('Salvar', on_click=lambda: salvar_jogo(
                    dialog, 
                    jogo.get('id'), 
                    {
                        'nome': nome.value, 'desenvolvedor': desenvolvedor.value, 'versao': versao.value, 
                        'status': status.value, 'notas': notas.value, 'tags': tags.value,
                        'link_loja': link_loja.value, 'link_oficial': link_oficial.value,
                        'pasta_appdata': pasta_save.value, 'caminho_capa': caminho_capa.value,
                        'caminho_executavel': caminho_executavel.value,
                        'caminho_save': jogo.get('caminho_save', '')
                    },
                    funcao_atualizar_grid,
                    capa_anterior=jogo.get('caminho_capa')
                ), color='green')
    dialog.open()

def abrir_detalhes(jogo, funcao_atualizar_grid):
    global dialog_detalhes
    with ui.dialog() as dialog_detalhes, ui.card().classes('w-full max-w-4xl p-6'):
        
        # Verificações de integridade de caminhos
        exe_path = jogo.get('caminho_executavel')
        exe_existe = exe_path and os.path.exists(exe_path)
        
        save_path = jogo.get('pasta_appdata')
        save_existe = save_path and os.path.exists(save_path)
        
        caminho_zip = jogo.get('caminho_save')
        tem_backup_zip = caminho_zip and os.path.exists(caminho_zip)

        with ui.row().classes('w-full items-start gap-6'):
            
            # Imagem de Capa
            if jogo.get('caminho_capa') and os.path.exists(jogo['caminho_capa']):
                ui.image(jogo['caminho_capa']).classes('w-64 h-80 object-cover rounded shadow-lg')
            else:
                with ui.column().classes('w-64 h-80 bg-gray-800 items-center justify-center rounded border-2 border-dashed border-gray-600'):
                    ui.icon('image', size='4rem', color='gray')
                    ui.label('Sem Capa').classes('text-gray-500 mt-2')
            
            # Informações do Jogo
            with ui.column().classes('flex-1'):
                ui.label(jogo['nome']).classes('text-4xl font-black text-white')
                
                with ui.row().classes('items-center gap-3 mt-2'):
                    ui.badge(jogo['status'], color=obter_cor_status(jogo['status'])).classes('text-sm px-3 py-1 font-bold')
                    ui.label(f"v. {jogo.get('versao', 'N/A')}").classes('text-lg text-gray-400')
                
                with ui.row().classes('items-center gap-2 mt-2 text-sm text-gray-300'):
                    ui.icon('history', size='1.2rem', color='amber')
                    texto_ultimo = jogo.get('ultima_vez_jogado') or 'Nunca jogado pelo Stasis Launcher'
                    ui.label(f"Última vez jogado: {texto_ultimo}").classes('font-medium')
                
                # Alerta se o jogo estiver registrado mas o arquivo não existir mais (ex: PC formatado)
                if exe_path and not exe_existe:
                    with ui.row().classes('items-center gap-2 mt-2 p-2 bg-red-950/50 border border-red-700/60 rounded text-red-300 text-xs'):
                        ui.icon('warning', color='negative')
                        ui.label('Executável não encontrado neste PC.')
                        
                        async def relocalizar_executavel():
                            novo_exe = await utilidades.escolher_executavel()
                            if novo_exe:
                                banco_dados.atualizar_jogo(jogo['id'], {'caminho_executavel': novo_exe})
                                jogo['caminho_executavel'] = novo_exe
                                ui.notify('Executável relocalizado com sucesso!', color='positive')
                                dialog_detalhes.close()
                                funcao_atualizar_grid.refresh()
                                abrir_detalhes(jogo, funcao_atualizar_grid)
                                
                        ui.button('Relocalizar .exe', on_click=relocalizar_executavel).props('size=xs color=negative')

                ui.label(f"Dev: {jogo.get('desenvolvedor', 'Não informado')}").classes('text-md text-gray-400 mt-1')
                
                if jogo.get('tags'):
                    with ui.row().classes('gap-2 mt-3'):
                        for t in jogo['tags'].split(','):
                            if t.strip():
                                ui.badge(t.strip(), color='gray').props('outline')

                ui.separator().classes('my-4 opacity-50')
                
                ui.label('Anotações de Progresso:').classes('font-bold text-xl text-blue-300')
                ui.markdown(jogo.get('notas', '*Nenhuma nota.*')).classes('text-gray-300 text-lg leading-relaxed bg-gray-900 p-4 rounded-lg w-full min-h-[90px]')
                
                with ui.row().classes('gap-6 mt-3'):
                    if jogo.get('link_loja'):
                        ui.link('Link Principal ↗', jogo['link_loja'], new_tab=True).classes('text-blue-400 hover:text-blue-300 transition-colors font-bold')
                    if jogo.get('link_oficial'):
                        ui.link('Link Secundário ↗', jogo['link_oficial'], new_tab=True).classes('text-blue-400 hover:text-blue-300 transition-colors font-bold')

        # BARRA DE AÇÕES (Launcher e Gerenciador de Saves)
        with ui.row().classes('w-full justify-between items-center mt-6 bg-gray-900 p-4 rounded-xl border border-gray-700'):
            with ui.row().classes('items-center gap-3'):
                
                # Ação Jogar
                def acao_jogar():
                    sucesso, msg = utilidades.executar_jogo(jogo.get('caminho_executavel'))
                    if sucesso:
                        data_execucao = banco_dados.registrar_execucao(jogo['id'])
                        jogo['ultima_vez_jogado'] = data_execucao
                        ui.notify(msg, color='positive', icon='sports_esports')
                        funcao_atualizar_grid.refresh()
                        # Minimiza o app para dar foco no jogo aberto
                        utilidades.minimizar_janela_app()
                    else:
                        ui.notify(msg, color='negative')
                
                if exe_existe:
                    ui.button('JOGAR', icon='play_arrow', color='positive', on_click=acao_jogar).classes('px-5 font-bold text-base')
                else:
                    ui.button('JOGAR', icon='play_arrow', color='gray').props('disable').tooltip('Executável não encontrado')
                
                # Ação Backup do Save
                def acao_backup_save():
                    zip_gerado, msg = utilidades.fazer_backup_save(jogo['id'], jogo.get('pasta_appdata'))
                    if zip_gerado:
                        banco_dados.atualizar_jogo(jogo['id'], {'caminho_save': zip_gerado})
                        jogo['caminho_save'] = zip_gerado
                        ui.notify(msg, color='positive')
                        funcao_atualizar_grid.refresh()
                        dialog_detalhes.close()
                        abrir_detalhes(jogo, funcao_atualizar_grid)
                    else:
                        ui.notify(msg, color='warning')

                ui.button('Backup do Save', icon='archive', color='secondary', on_click=acao_backup_save).props('outline').tooltip('Compacta os saves no Stasis')
                
                # Ação Restaurar Save (com suporte inteligente a PC formatado)
                async def acao_restaurar_save():
                    destino = jogo.get('pasta_appdata')
                    
                    # Se a pasta antiga não existir (ex: PC formatado ou jogo recém instalado em outro local)
                    if not destino or not os.path.exists(destino):
                        ui.notify('A pasta original do save não foi encontrada. Selecione onde restaurar!', color='warning')
                        novo_destino = await utilidades.escolher_pasta_save("Selecione onde restaurar o save do jogo")
                        if not novo_destino:
                            ui.notify('Restauração cancelada.', color='info')
                            return
                        destino = novo_destino
                        banco_dados.atualizar_jogo(jogo['id'], {'pasta_appdata': destino})
                        jogo['pasta_appdata'] = destino
                    
                    sucesso, msg = utilidades.restaurar_backup_save(jogo.get('caminho_save'), destino)
                    if sucesso:
                        ui.notify(msg, color='positive')
                        dialog_detalhes.close()
                        funcao_atualizar_grid.refresh()
                        abrir_detalhes(jogo, funcao_atualizar_grid)
                    else:
                        ui.notify(msg, color='negative')
                        
                if tem_backup_zip:
                    ui.button('Restaurar Save', icon='unarchive', color='amber', on_click=acao_restaurar_save).props('outline').tooltip('Extrai os saves do Stasis para a pasta do jogo')

                # Abrir pasta no Explorer
                def acao_abrir_pasta():
                    alvo = jogo.get('pasta_appdata') or jogo.get('caminho_executavel')
                    if alvo and os.path.exists(alvo):
                        utilidades.abrir_pasta_no_explorador(alvo)
                    else:
                        ui.notify('A pasta ainda não existe no disco deste computador.', color='info')
                        
                ui.button(icon='folder_open', on_click=acao_abrir_pasta).props('flat color=gray').tooltip('Abrir pasta no Windows Explorer')

            with ui.row().classes('gap-2'):
                ui.button('Editar', icon='edit', color='primary', on_click=lambda: abrir_formulario_jogo(jogo, funcao_atualizar_grid))
                ui.button('Fechar', on_click=dialog_detalhes.close, color='gray')
            
    dialog_detalhes.open()
