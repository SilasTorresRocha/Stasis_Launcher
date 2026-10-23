# ⏳ Stasis Launcher

> **Stasis** *(do grego στάσις - stásis: "estado de tempo suspenso, imobilização temporária sem perda")*

Gerenciador e Launcher de Jogos Indie com Controle de Versões e Backups Inteligentes de Saves (com foco em jogos Ren'Py, RPGs e Visual Novels).

---

## 💡 A Ideia do Projeto

Jogos indie em desenvolvimento ocupam dezenas de gigabytes com vídeos e assets pesados. Quando você atinge o limite da versão atual, o jogo precisa esperar meses até que o desenvolvedor lance uma nova atualização.

O **Stasis Launcher** coloca o seu jogo em estado de *stasis*:
1. Ele compacta apenas os arquivos leves de save em `.zip` dentro do seu diretório protegido (`dados_stasis/`).
2. Permite que você delete com segurança a pasta pesada de 10 GB+ do jogo sem perder seu progresso.
3. Quando a nova versão sair, você reinstala e restaura o save com apenas 1 clique!

---

## 🚀 Funcionalidades

- **Central de Launcher:** Abra seus jogos com apenas um clique e rastreie a métrica de "Última vez jogado".
- **Auto-Minimizar:** Ao clicar em *Jogar*, o Stasis Launcher se minimiza automaticamente para que você foque no jogo.
- **Detecção Inteligente de Saves:** Identifica automaticamente pastas com arquivos de save reais (`.save`, `.sav`, `.dat`) no diretório do jogo ou no `%APPDATA%/RenPy`.
- **Economia Gigante de Armazenamento:** Preserva notas, status, links de acompanhamento e o save, liberando espaço no SSD.
- **Backup Geral com Checklist:** Exporta todo o catálogo, capas e saves em um único arquivo `.zip`. Avisa se algum jogo ainda não teve seu save compactado e permite zipar em lote.
- **Restauração Inteligente:** Se você formatar o computador ou mudar de pasta, o aplicativo permite relocalizar o executável e aponta onde restaurar o save com seletor nativo do Windows.
- **Diagnóstico em Tempo Real:** Registro detalhado em `app.log`, com botão no menu para abrir o log diretamente no Bloco de Notas.

---

## 📦 Instalação e Execução

### Opção 1: Via Inicializador Rápido (Windows)
Basta dar dois cliques no arquivo:
```cmd
iniciar.bat
```
*(O aplicativo abrirá sem manter nenhuma janela do CMD aberta por baixo!)*

### Opção 2: Instalação via PIP (Modo Pacote / PyPI)
```bash
pip install .
```
Depois de instalado, basta digitar no terminal:
```bash
stasis-launcher
```

---

## 🛠️ Tecnologias Utilizadas

- **[NiceGUI](https://nicegui.io/):** Interface gráfica moderna em modo desktop nativo (`pywebview`).
- **SQLite3:** Banco de dados local em português para armazenamento persistente.
- **Pillow:** Processamento de imagens de capas.
- **Python Standard Library:** `zipfile`, `subprocess`, `socket`, `tkinter`, `logging`.
