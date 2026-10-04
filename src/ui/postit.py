import tkinter as tk
import uuid

# classe responsável por gerir o ciclo de vida e sincronizar as notas interativas no quadro
class PostitManager:
    def __init__(self, app):
        self.app = app

    # cria um novo postit e avisa o servidor com TCP
    def CriarPostit(self):
        note_id = uuid.uuid4().hex[:8] # gera um identificador único de 8 carateres
        canvas = self.app.board_ui.canvas
        x, y = canvas.canvasx(canvas.winfo_width() / 2), canvas.canvasy(canvas.winfo_height() / 2)
        self.montar_postit(note_id, x, y)
        self.alterar_estado(note_id, "ABERTO") # o criador começa logo a poder editar
        self.app.rede.enviar("CREATE_ITEM", note_id, "postit", x, y) # envia a criação para a rede sincronizar com os outros usuários

    # constrói a estrutura visual
    def montar_postit(self, note_id, x, y):
        canvas = self.app.board_ui.canvas
        frame = tk.Frame(canvas, bg="#FFF59D", bd=0, relief="flat", highlightbackground="#FBC02D", highlightthickness=1)
        header = tk.Frame(frame, bg="#FFF176", pady=2)
        header.pack(fill=tk.X)
        
        note_status = tk.Label(header, bg="#FFF176", fg="#555", font=("Arial", 8, "bold"))
        note_status.pack(side=tk.LEFT, padx=4)
        
        botton_excluir = tk.Button(header, text="✖", bg="#e74c3c", fg="white", bd=0, font=("Arial", 7), command=lambda: (self.app.apagar_item(note_id), self.app.rede.enviar("DELETE_ITEM", note_id)))
        botton_excluir.pack(side=tk.RIGHT, padx=4)
        
        botton_acao = tk.Button(header, fg="white", bd=0, font=("Arial", 8, "bold"))
        botton_acao.pack(side=tk.RIGHT, padx=2)

        txt_box = tk.Text(frame, width=20, height=5, fg="#333", font=("Arial", 11), bd=0, wrap="word")
        txt_box.pack(padx=5, pady=5)
        
        winote_id = canvas.create_window(x, y, window=frame, anchor="nw", tags=(f"id_{note_id}",))
        botton_acao.config(command=lambda: self.clique_botao(note_id))

        # associa os eventos de arrastar o postit pelo cabeçalho
        header.bind("<Button-1>", lambda e, id=note_id: self.iniciar_arrasto(e, id))
        header.bind("<B1-Motion>", lambda e, id=note_id: self.arrastar_postit(e, id))

        # registra na memória global compartilhada
        self.app.notas_ui[note_id] = {
            "type": "postit", "text": txt_box, "status": note_status, 
            "btn": botton_acao, "winote_id": winote_id, "texto_guardado": ""
        }

    # altera visualmente o comportamento de acordo com o estado de concorrência do momento
    def alterar_estado(self, note_id, estado, dono=""):
        if note_id not in self.app.notas_ui: return
        ui = self.app.notas_ui[note_id]
        
        if estado == "ABERTO": 
            ui["text"].config(state=tk.NORMAL, bg="#FFF9C4")
            ui["btn"].config(text="Salvar", bg="#2ecc71")
            ui["status"].config(text="Editando", fg="#555")
            
        elif estado == "SALVO": 
            ui["text"].config(state=tk.DISABLED, bg="#F0F0F0")
            ui["btn"].config(text="Editar", bg="#3498db")
            ui["status"].config(text="Salvo", fg="#aaa")
            ui["text"].config(state=tk.NORMAL)
            ui["text"].delete("1.0", tk.END)
            ui["text"].insert("1.0", ui["texto_guardado"])
            ui["text"].config(state=tk.DISABLED)
            
        elif estado == "TRANCADO": 
            ui["text"].config(state=tk.NORMAL)
            ui["text"].delete("1.0", tk.END)
            ui["text"].config(state=tk.DISABLED, bg="#F0F0F0")
            
            ui["btn"].config(text="Trancado", bg="#95a5a6")
            ui["status"].config(text=f"Em uso: {dono}", fg="#e74c3c")

    # 
    def clique_botao(self, note_id):
        botton_txt = self.app.notas_ui[note_id]["btn"]['text']
        if botton_txt == "Salvar":
            texto = self.app.notas_ui[note_id]["text"].get("1.0", "end-1c")
            self.app.notas_ui[note_id]["texto_guardado"] = texto
            self.alterar_estado(note_id, "SALVO")
            self.app.rede.enviar("TEXT_SYNC", note_id, texto)
        elif botton_txt == "Editar":
            self.app.rede.enviar("LOCK_REQ", note_id)

    # responde às ordens de lock vindas do servidor por TCP
    def atualizar_estado(self, note_id, status, dono):
        if status == "ACK":
            self.alterar_estado(note_id, "ABERTO")
        elif status == "DENIED":
            self.alterar_estado(note_id, "TRANCADO", dono)
        elif status == "UNLOCK":
            self.alterar_estado(note_id, "SALVO")

    # atualiza o texto quando outro usuário envia alterações pela rede
    def sincronizar_texto(self, note_id, texto):
        if note_id in self.app.notas_ui and self.app.notas_ui[note_id]["type"] == "postit":
            self.app.notas_ui[note_id]["texto_guardado"] = texto
            if self.app.notas_ui[note_id]["btn"]['text'] != "Trancado":
                self.alterar_estado(note_id, "SALVO")

    # egista a posição inicial ao agarrar o cabeçalho para mover
    def iniciar_arrasto(self, event, note_id):
        if self.app.ferramenta_atual == "select":
            self.app.notas_ui[note_id]["drag_px"] = event.x_root
            self.app.notas_ui[note_id]["drag_py"] = event.y_root
            self.app.board_ui.canvas.tag_raise(f"id_{note_id}")

    # calcula o deslocamento e sincroniza o movimento
    def arrastar_postit(self, event, note_id):
        if self.app.ferramenta_atual == "select":
            dx = event.x_root - self.app.notas_ui[note_id]["drag_px"]
            dy = event.y_root - self.app.notas_ui[note_id]["drag_py"]
            self.app.board_ui.canvas.move(self.app.notas_ui[note_id]["winote_id"], dx, dy)
            self.app.rede.enviar("MOVE_ITEM", note_id, dx, dy)
            self.app.notas_ui[note_id]["drag_px"] = event.x_root
            self.app.notas_ui[note_id]["drag_py"] = event.y_root