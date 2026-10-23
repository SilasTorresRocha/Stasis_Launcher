import sys
import os
import threading
import tkinter as tk

PASTA_DADOS = "dados_stasis"
ARQUIVO_FECHAR = os.path.join(PASTA_DADOS, "splash.close")

class StasisSplash:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True) # Janela moderna sem bordas do Windows
        
        # Dimensões da Splash Screen
        self.largura = 420
        self.altura = 250
        
        # Centraliza na tela do monitor
        largura_tela = self.root.winfo_screenwidth()
        altura_tela = self.root.winfo_screenheight()
        pos_x = (largura_tela - self.largura) // 2
        pos_y = (altura_tela - self.altura) // 2
        self.root.geometry(f"{self.largura}x{self.altura}+{pos_x}+{pos_y}")
        self.root.configure(bg="#12131e")
        self.root.attributes("-topmost", True)

        # Timeout de segurança: fecha em no máximo 8 segundos
        self.root.after(8000, self.fechar)

        # Borda sutil de destaque
        borda = tk.Frame(self.root, bg="#2a2d45", bd=1)
        borda.place(x=0, y=0, width=self.largura, height=self.altura)
        
        painel = tk.Frame(borda, bg="#12131e")
        painel.place(x=1, y=1, width=self.largura - 2, height=self.altura - 2)

        # Cabeçalho da Splash
        titulo = tk.Label(painel, text="STASIS LAUNCHER", font=("Segoe UI", 16, "bold"), fg="#ffffff", bg="#12131e")
        titulo.pack(pady=(22, 2))
        
        subtitulo = tk.Label(painel, text="Inicializando ambiente e componentes...", font=("Segoe UI", 9), fg="#94a3b8", bg="#12131e")
        subtitulo.pack()

        # Canvas do Spinner de Loading (60 FPS)
        self.canvas = tk.Canvas(painel, width=54, height=54, bg="#12131e", highlightthickness=0)
        self.canvas.pack(pady=(12, 10))
        
        self.angulo = 0
        self.animar_spinner()

        # Terminal com efeito de esmaecimento (4 linhas com gradiente)
        frame_logs = tk.Frame(painel, bg="#12131e")
        frame_logs.pack(fill="x", padx=28)
        
        self.cores_opacidade = ["#232738", "#475569", "#94a3b8", "#60a5fa"]
        self.linhas_texto = [
            "",
            "",
            "",
            "> Carregando Stasis Launcher..."
        ]
        self.labels = []
        for i in range(4):
            lbl = tk.Label(
                frame_logs, 
                text=self.linhas_texto[i], 
                font=("Consolas", 8), 
                fg=self.cores_opacidade[i], 
                bg="#12131e", 
                anchor="w"
            )
            lbl.pack(fill="x")
            self.labels.append(lbl)

        # Monitoramento ativo do sinal de fechamento via arquivo (funciona entre múltiplos processos)
        self.verificar_sinal_fechamento()
        
        # Monitoramento via stdin
        threading.Thread(target=self.ouvir_processo_principal, daemon=True).start()

    def verificar_sinal_fechamento(self):
        """Verifica a cada 80ms se o NiceGUI enviou o sinal de fechamento via arquivo"""
        if os.path.exists(ARQUIVO_FECHAR):
            try:
                os.remove(ARQUIVO_FECHAR)
            except Exception:
                pass
            self.fechar()
            return
            
        self.root.after(80, self.verificar_sinal_fechamento)

    def animar_spinner(self):
        """Desenha e rotaciona o anel circular suavemente a 60 FPS"""
        self.canvas.delete("all")
        self.canvas.create_oval(8, 8, 46, 46, outline="#1e2235", width=4)
        self.canvas.create_arc(
            8, 8, 46, 46,
            start=self.angulo,
            extent=90,
            style="arc",
            outline="#3b82f6",
            width=4
        )
        self.angulo = (self.angulo + 12) % 360
        self.root.after(25, self.animar_spinner)

    def adicionar_log(self, mensagem):
        self.linhas_texto.pop(0)
        self.linhas_texto.append(f"> {mensagem}")
        for i in range(4):
            self.labels[i].config(text=self.linhas_texto[i])

    def ouvir_processo_principal(self):
        try:
            for linha in sys.stdin:
                texto = linha.strip()
                if texto == "FECHAR":
                    break
                elif texto.startswith("LOG:"):
                    msg = texto[4:]
                    self.root.after(0, self.adicionar_log, msg)
        except Exception:
            pass
        finally:
            self.root.after(0, self.fechar)

    def fechar(self):
        try:
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)

    def iniciar(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = StasisSplash()
    app.iniciar()
