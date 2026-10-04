import tkinter as tk
from tkinter import messagebox
import threading
from host import Servidor

# UI do quadro
from ui.board import BoardUI
from ui.canvas_ops import CanvasOps
from ui.postit import PostitManager

# classe responsável pela tela inicial de login e a validação do acesso à sala.
class LoginUI:
    def __init__(self, app):
        self.app = app
        self.frame_login = None
        self.frame_form = None

    def construir_tela_inicial(self):
        self.frame_login = tk.Frame(self.app.root, pady=80)
        self.frame_login.pack()
        
        tk.Label(self.frame_login, text="Bem-vindo ao Quadro Colaborativo!", font=("Arial", 16, "bold")).pack(pady=10)

        # botões de escolha
        frame_botoes = tk.Frame(self.frame_login)
        frame_botoes.pack(pady=15)
        
        tk.Button(frame_botoes, text="Criar Sala (Hospedar)", bg="#3498db", fg="white", font=("Arial", 10, "bold"), width=20, command=self.mostrar_hospedar).grid(row=0, column=0, padx=10)
        tk.Button(frame_botoes, text="Entrar numa Sala", bg="#2ecec0", fg="white", font=("Arial", 10, "bold"), width=20, command=self.mostrar_conectar).grid(row=0, column=1, padx=10)

        # formulários dinâmicos
        self.frame_form = tk.Frame(self.frame_login)
        self.frame_form.pack(pady=10)

    # tira os elementos do formulário para limpar a tela antes de desenhar os novos campos
    def limpar_form(self):
        for widget in self.frame_form.winfo_children():
            widget.destroy()

    # renderiza os campos necessários para criar sala
    def mostrar_hospedar(self):
        self.limpar_form()
        tk.Label(self.frame_form, text="Defina uma senha para a sala:", font=("Arial", 10)).pack(pady=5)
        self.entry_senha_host = tk.Entry(self.frame_form, font=("Arial", 12), show="*")
        self.entry_senha_host.pack(pady=5)
        tk.Button(self.frame_form, text="Iniciar Servidor", bg="#20df3a", fg="white", font=("Arial", 10, "bold"), command=self.iniciar_servidor).pack(pady=15)

    # renderiza os campos necessários para entrar numa sala existente
    def mostrar_conectar(self):
        self.limpar_form()
        tk.Label(self.frame_form, text="IP do Servidor:", font=("Arial", 10)).pack()
        self.entry_ip = tk.Entry(self.frame_form, font=("Arial", 12))
        # preenche por padrão com o IP local para facilitar testes na mesma máquina
        self.entry_ip.insert(0, "127.0.0.1")
        self.entry_ip.pack(pady=5)
        
        tk.Label(self.frame_form, text="Seu Nome:", font=("Arial", 10)).pack()
        self.entry_nome = tk.Entry(self.frame_form, font=("Arial", 12))
        self.entry_nome.pack(pady=5)
        
        tk.Label(self.frame_form, text="Senha da Sala:", font=("Arial", 10)).pack()
        self.entry_senha_client = tk.Entry(self.frame_form, font=("Arial", 12), show="*")
        self.entry_senha_client.pack(pady=5)
        
        tk.Button(self.frame_form, text="Conectar", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), command=self.iniciar_conexao).pack(pady=15)

    # instancia o servidor local e coloca numa thread paralela, preparando o atalho para o host entrar
    def iniciar_servidor(self):
        senha = self.entry_senha_host.get()
        if not senha:
            messagebox.showwarning("Aviso", "Por favor, defina uma senha.")
            return
            
        try:
            # instancia o servidor passando a senha escolhida pelo utilizador
            servidor = Servidor(senha_sala=senha)
            self.app.servidor_thread = threading.Thread(target=servidor.iniciar, daemon=True)
            self.app.servidor_thread.start()
            
            messagebox.showinfo("Sucesso", "Servidor iniciado com sucesso!\nPeça aos seus amigos para se conectarem com o seu IP.")
            
            self.mostrar_conectar()
            self.entry_ip.delete(0, tk.END)
            self.entry_ip.insert(0, "127.0.0.1")
            self.entry_senha_client.insert(0, senha)
            self.entry_nome.insert(0, "Host")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível iniciar o servidor: {e}")

    # valida os campos de entrada e tenta conectar à rede por TCP
    def iniciar_conexao(self):
        ip = self.entry_ip.get()
        nome = self.entry_nome.get()
        senha = self.entry_senha_client.get()
        
        if not nome or not senha:
            messagebox.showwarning("Aviso", "Preencha o nome e a senha.")
            return
            
        try:
            # tenta a conexão gerida pelo network.py
            if not self.app.rede.conectar(ip, nome, senha):
                messagebox.showerror("Erro", "Conexão recusada. Averigue a senha ou se o servidor está ativo.")
                return
                
            self.frame_login.destroy()
            
            # instancia os módulos visuais e funcionais do quadro
            self.app.board_ui = BoardUI(self.app)
            self.app.canvas_ops = CanvasOps(self.app)
            self.app.postit_mgr = PostitManager(self.app)
            
            self.app.board_ui.construir_board()
        except Exception as e: 
            messagebox.showerror("Erro de Rede", f"Falha na conexão: {e}")