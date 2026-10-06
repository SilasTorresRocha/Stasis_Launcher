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

def salvar_jogo(dialog, id_jogo, dados, funcao_atualizar_grid):
    if not dados['nome']:
        ui.notify('O nome do jogo é obrigatório!', color='negative')
        return
        
    # Quando o usuário salva, importamos a imagem para o nosso cofre
    # Assim o sistema não perde a imagem se o usuário deletá-la da pasta de Downloads
    dados['caminho_capa'] = utilidades.importar_imagem_para_cofre(dados['caminho_capa'])
        
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
        jogo = {k: '' for k in ['nome', 'desenvolvedor', 'versao', 'notas', 'tags', 'link_loja', 'link_oficial', 'pasta_appdata', 'caminho_capa', 'caminho_save']}
        jogo['status'] = 'Jogando'
    
    with ui.dialog() as dialog, ui.card().classes('w-full max-w-4xl'):
        ui.label(titulo).classes('text-2xl font-bold mb-4 text-white')
        
        with ui.row().classes('w-full gap-4'):
            # PRIMEIRA COLUNA
            with ui.column().classes('flex-1'):
                nome = ui.input('Nome do Jogo *', value=jogo['nome']).classes('w-full')
                desenvolvedor = ui.input('Desenvolvedor', value=jogo['desenvolvedor']).classes('w-full')
                versao = ui.input('Versão atual', value=jogo['versao']).classes('w-full')
                status = ui.select(['Jogando', 'Aguardando Update', 'Finalizado', 'Dropado'], 
                                   label='Status', value=jogo['status']).classes('w-full')
                tags = ui.input('Tags (ex: RPG, VN)', value=jogo['tags']).classes('w-full')
                
            # SEGUNDA COLUNA
            with ui.column().classes('flex-1 gap-2'):
                link_loja = ui.input('Link Principal', value=jogo['link_loja']).classes('w-full')
                link_oficial = ui.input('Link Secundário (opcional)', value=jogo['link_oficial']).classes('w-full')
                
                # Input de Capa com Botão de Buscar Arquivo nativo
                with ui.row().classes('w-full items-center justify-between no-wrap'):
                    caminho_capa = ui.input('Caminho da Capa', value=jogo['caminho_capa']).classes('flex-1')
                    
                    async def acao_buscar_capa():
                        path = await utilidades.escolher_imagem_capa()
                        if path: caminho_capa.value = path
                        
                    ui.button(icon='image_search', on_click=acao_buscar_capa).props('outline color=primary').classes('mt-2')
                
                # Input de Pasta com Botão de Buscar Diretório
                with ui.row().classes('w-full items-center justify-between no-wrap'):
                    pasta_appdata = ui.input('Pasta do Appdata/Save', value=jogo['pasta_appdata']).classes('flex-1')
                    
                    async def acao_buscar_pasta():
                        path = await utilidades.escolher_pasta_save()
                        if path: pasta_appdata.value = path
                        
                    ui.button(icon='folder_open', on_click=acao_buscar_pasta).props('outline color=secondary').classes('mt-2')
                
                caminho_save = ui.input('Caminho do Backup Zip (futuro)', value=jogo['caminho_save']).classes('w-full')
                
        notas = ui.textarea('Notas / Onde parei?', value=jogo['notas']).classes('w-full mt-4')
        
        # BARRA INFERIOR DO FORMULÁRIO
        with ui.row().classes('w-full justify-between mt-4 p-2 bg-gray-900 rounded'):
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
                        'pasta_appdata': pasta_appdata.value, 'caminho_capa': caminho_capa.value,
                        'caminho_save': caminho_save.value
                    },
                    funcao_atualizar_grid
                ), color='green')
    dialog.open()

def abrir_detalhes(jogo, funcao_atualizar_grid):
    global dialog_detalhes
    with ui.dialog() as dialog_detalhes, ui.card().classes('w-full max-w-4xl p-6'):
        with ui.row().classes('w-full items-start gap-6'):
            
            # Coluna da imagem
            if jogo.get('caminho_capa') and os.path.exists(jogo['caminho_capa']):
                ui.image(jogo['caminho_capa']).classes('w-64 h-80 object-cover rounded shadow-lg')
            else:
                with ui.column().classes('w-64 h-80 bg-gray-800 items-center justify-center rounded border-2 border-dashed border-gray-600'):
                    ui.icon('image', size='4rem', color='gray')
                    ui.label('Sem Capa').classes('text-gray-500 mt-2')
            
            # Coluna de Informações
            with ui.column().classes('flex-1'):
                ui.label(jogo['nome']).classes('text-4xl font-black text-white')
                
                with ui.row().classes('items-center gap-3 mt-2'):
                    ui.badge(jogo['status'], color=obter_cor_status(jogo['status'])).classes('text-sm px-3 py-1 font-bold')
                    ui.label(f"v. {jogo.get('versao', 'N/A')}").classes('text-lg text-gray-400')
                
                ui.label(f"Dev: {jogo.get('desenvolvedor', 'Não informado')}").classes('text-md text-gray-400 mt-2')
                
                if jogo.get('tags'):
                    with ui.row().classes('gap-2 mt-3'):
                        for t in jogo['tags'].split(','):
                            if t.strip():
                                ui.badge(t.strip(), color='gray').props('outline')

                ui.separator().classes('my-4 opacity-50')
                
                ui.label('Anotações de Progresso:').classes('font-bold text-xl text-blue-300')
                ui.markdown(jogo.get('notas', '*Nenhuma nota.*')).classes('text-gray-300 text-lg leading-relaxed bg-gray-900 p-4 rounded-lg w-full min-h-[100px]')
                
                with ui.row().classes('gap-6 mt-4'):
                    if jogo.get('link_loja'):
                        ui.link('Link Principal ↗', jogo['link_loja'], new_tab=True).classes('text-blue-400 hover:text-blue-300 transition-colors font-bold')
                    if jogo.get('link_oficial'):
                        ui.link('Link Secundário ↗', jogo['link_oficial'], new_tab=True).classes('text-blue-400 hover:text-blue-300 transition-colors font-bold')

        # Barra inferior
        with ui.row().classes('w-full justify-between items-center mt-8 bg-gray-900 p-4 rounded-xl border border-gray-700'):
            with ui.row().classes('gap-3'):
                ui.button('Editar Jogo', icon='edit', color='primary', on_click=lambda: abrir_formulario_jogo(jogo, funcao_atualizar_grid))
                ui.button('Abrir Diretório', icon='folder_open', color='secondary', 
                          on_click=lambda: ui.notify('Em breve')).props('outline')
            ui.button('Fechar', icon='close', on_click=dialog_detalhes.close, color='gray')
            
    dialog_detalhes.open()
