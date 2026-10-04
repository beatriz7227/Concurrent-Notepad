import tkinter as tk
from utils import file_io

# classe responsável pela interface do quadro
class BoardUI:
    def __init__(self, app):
        self.app = app # guarda a referência do main.py para poder integrar ao estado global e puxar ações
        # dicionários para guardar os botões da barra lateral
        self.botoes_ferramentas = {}
        self.botoes_cores = {}

    # constrói e posiciona todos os painéis
    def construir_board(self):

        # barra superior
        self.topbar = tk.Frame(self.app.root, bg="#f1f3f4", pady=5)
        self.topbar.pack(side=tk.TOP, fill=tk.X)
        tk.Button(self.topbar, text="Sair", fg="red", bd=0, font=("Arial", 9, "bold"), command=self.app.encerrar_app).pack(side=tk.RIGHT, padx=10)
        tk.Button(self.topbar, text="Exportar PNG", bd=0, bg="#e8eaed", command=lambda: file_io.exportar_png(self.app)).pack(side=tk.RIGHT, padx=5)
        tk.Button(self.topbar, text="Exportar JSON", bd=0, bg="#e8eaed", command=lambda: file_io.exportar_json(self.app)).pack(side=tk.RIGHT, padx=5)
        tk.Button(self.topbar, text="Importar JSON", bd=0, bg="#e8eaed", command=lambda: file_io.carregar_json(self.app)).pack(side=tk.RIGHT, padx=5)

        self.sidebar = tk.Frame(self.app.root, bg="#ffffff", width=80, relief="flat", bd=0)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        
        ferramentas = [
            ("↖\nCursor", "select"), ("✎\nCaneta", "pen"), ("🎯\nLaser", "laser"),
            ("✖\nBorracha", "eraser"), ("T\nTexto", "text"), ("📝\nPost-it", "postit"),
            ("➔\nSeta", "seta"), ("▭\nRetângulo", "shape_rect"), ("◯\nCírculo", "shape_oval"), ("△\nTriângulo", "shape_tri")
        ]

        # cria os botões usando a lista acima
        for texto, cmd in ferramentas:
            # a ideia do lambda está em evitar late binding
            btn = tk.Button(self.sidebar, text=texto, width=8, pady=2, bg="#ffffff", bd=0, font=("Arial", 9), command=lambda c=cmd: self.app.set_ferramenta(c))
            btn.pack(pady=2, padx=5)
            self.botoes_ferramentas[cmd] = btn

        self.frame_cores = tk.Frame(self.sidebar, bg="#ffffff")
        self.frame_cores.pack(side=tk.BOTTOM, pady=10)
        tk.Label(self.frame_cores, text="Cores", bg="#ffffff", font=("Arial", 8, "bold")).pack(pady=2)
        
        grid_cores = tk.Frame(self.frame_cores, bg="#ffffff")
        grid_cores.pack()
        cores_hex = ["#070707", "#ec3622", "#1496ec", "#2ecc71"] 
        for i, cor in enumerate(cores_hex):
            btn = tk.Button(grid_cores, bg=cor, width=2, height=1, bd=3, relief="sunken" if cor == self.app.cor_atual else "flat", command=lambda c=cor: self.app.set_cor(c))
            btn.grid(row=i//2, column=i%2, padx=2, pady=2)
            self.botoes_cores[cor] = btn

        # quadro 
        self.frame_main = tk.Frame(self.app.root)
        self.frame_main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.vbar = tk.Scrollbar(self.frame_main, orient=tk.VERTICAL)
        self.hbar = tk.Scrollbar(self.frame_main, orient=tk.HORIZONTAL)
        self.vbar.pack(side=tk.RIGHT, fill=tk.Y); self.hbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = tk.Canvas(self.frame_main, bg="#F8F9FA", xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set, scrollregion=(0, 0, 3000, 3000))
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.vbar.config(command=self.canvas.yview); self.hbar.config(command=self.canvas.xview)

        # associa os cliques ao gerenciador
        self.canvas.bind("<Button-1>", self.app.canvas_ops.quadro_click)
        self.canvas.bind("<B1-Motion>", self.app.canvas_ops.canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.app.canvas_ops.canvas_release)

        # delegação de eventos
        self.frame_usuarios = tk.Frame(self.app.root, width=150, bg="#ffffff", relief="flat")
        self.frame_usuarios.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Label(self.frame_usuarios, text="Online", bg="#ffffff", font=("Arial", 10, "bold")).pack(pady=10)
        self.listbox_usuarios = tk.Listbox(self.frame_usuarios, bd=0, font=("Arial", 9), fg="#555")
        self.listbox_usuarios.pack(fill=tk.BOTH, expand=True, padx=10)
        
        self.app.set_ferramenta("select")

    # feedback visual da ferramenta escolhida
    def AtualizarFerramentas(self):
        for cmd, btn in self.botoes_ferramentas.items():
            btn.config(bg="#e8eaed" if cmd == self.app.ferramenta_atual else "#ffffff")

    def AtualizarCores(self):
        for cor, btn in self.botoes_cores.items():
            btn.config(relief="sunken" if cor == self.app.cor_atual else "flat")

    # limpa a lista lateral e reescreve quem está online no momento
    def atualizar_usuarios(self, nomes):
        try:
            self.listbox_usuarios.delete(0, tk.END)
            for n in nomes: 
                self.listbox_usuarios.insert(tk.END, f"● {n}")
        except AttributeError: pass

    # cria a linha no canvas e que deve ser destruida
    def renderizar_laser(self, x1, y1, x2, y2):
        l_id = self.canvas.create_line(x1, y1, x2, y2, fill="#e74c3c", width=4, capstyle=tk.ROUND)
        self.canvas.after(600, lambda: self.canvas.delete(l_id))


    # move uma forma geométrica x pixels para o lado e y pixels para baixo/cima
    def mover_item(self, note_id, dx, dy):
        self.canvas.move(f"id_{note_id}", dx, dy)

    # remove o item e apaga ele da memória global
    def apagar_item(self, note_id):
        self.canvas.delete(f"id_{note_id}")
        if note_id in self.app.notas_ui: del self.app.notas_ui[note_id]
        if note_id in self.app.itens_selecionados: self.app.itens_selecionados.remove(note_id)

    # desenha com base no parâmetro tipo
    def renderizar_item(self, note_id, tipo, *dados, temp=False):
        tag = "tmp_shape" if temp else f"id_{note_id}"
        if not temp and note_id in self.app.notas_ui: return
        
        cor = dados[-1] if len(dados) > 0 and type(dados[-1]) == str and dados[-1].startswith("#") else "#2c3e50"
        
        if tipo == "postit": 
            self.app.postit_mgr.montar_postit(note_id, float(dados[0]), float(dados[1]))
            return 
            
        # dicionário com cada tipo de forma geométrica à sua respetiva função lambda
        desenhos = {
            "pen": lambda: self.canvas.create_line([float(p) for p in dados[0].split(",")], fill=cor, width=3, capstyle=tk.ROUND, smooth=True, tags=(tag,)),
            "shape_rect": lambda: self.canvas.create_rectangle(float(dados[0]), float(dados[1]), float(dados[2]), float(dados[3]), outline=cor, width=2, tags=(tag,)),
            "shape_oval": lambda: self.canvas.create_oval(float(dados[0]), float(dados[1]), float(dados[2]), float(dados[3]), outline=cor, width=2, tags=(tag,)),
            "shape_tri": lambda: self.canvas.create_polygon(float(dados[0]), float(dados[3]), (float(dados[0])+float(dados[2]))/2, float(dados[1]), float(dados[2]), float(dados[3]), outline=cor, fill="", width=2, tags=(tag,)),
            "seta": lambda: self.canvas.create_line(float(dados[0]), float(dados[1]), float(dados[2]), float(dados[3]), fill=cor, arrow=tk.LAST, width=2, tags=(tag,)),
            "text": lambda: self.canvas.create_text(float(dados[0]), float(dados[1]), text=dados[2] if len(dados) > 2 else "", fill=cor, font=("Arial", 14), anchor="nw", tags=(tag,))
        }

        # executa a função correspondente ao tipo de forma de forma limpa e direta
        if tipo in desenhos:
            desenhos[tipo]()
        
        if not temp: 
            self.app.notas_ui[note_id] = {"type": tipo}