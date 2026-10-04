import uuid
import tkinter as tk
from tkinter import simpledialog

# classe responsável por toda a lógica de interação com o quadro como clique, movimentos e trancamentos/libertação
class CanvasOps:
    def __init__(self, app):
        self.app = app

    # percorre as tags de um elemento gráfico e extrai o identificador único
    def get_idtag(self, item):
        for tag in self.app.board_ui.canvas.gettags(item):
            if tag.startswith("id_"): return tag[3:]
        return None

    # evento de carregar no botão esquerdo
    def quadro_click(self, event):
        canvas = self.app.board_ui.canvas
        # converte as coordenadas
        cx, cy = canvas.canvasx(event.x), canvas.canvasy(event.y)
        self.app.drag_start_x, self.app.drag_start_y = cx, cy
        
        if self.app.ferramenta_atual == "select":
            item = canvas.find_closest(cx, cy)
            note_id = self.get_idtag(item[0]) if item else None
            
            if note_id and note_id not in self.app.itens_selecionados:
                # se clicou num objeto existente, seleciona e traz para a camada superior do canvas
                self.app.itens_selecionados = [note_id]
                canvas.tag_raise(f"id_{note_id}")
            elif not note_id:
                self.app.itens_selecionados = []
                self.app.caixa_selecao_id = canvas.create_rectangle(cx, cy, cx, cy, dash=(4, 4), outline="#3498db")

        elif self.app.ferramenta_atual == "eraser":
            item = canvas.find_closest(cx, cy)
            if item:
                note_id = self.get_idtag(item[0])
                if note_id: 
                    # apaga na interface e depois joga a ordem de exclusão por TCP para os outros
                    self.app.apagar_item(note_id)
                    self.app.rede.enviar("DELETE_ITEM", note_id)
                
        elif self.app.ferramenta_atual == "laser":
            self.app.last_laser_x, self.app.last_laser_y = cx, cy
                
        elif self.app.ferramenta_atual == "pen":
            # gera um ID exclusivo para o novo risco
            self.app.id_item_atual = uuid.uuid4().hex[:8]
            self.app.pontos_desenho = [cx, cy]
            
        elif self.app.ferramenta_atual in ["shape_rect", "shape_oval", "shape_tri", "seta"]:
            self.app.id_item_atual = uuid.uuid4().hex[:8]
            self.app.pontos_desenho = [cx, cy, cx, cy]
            self.app.renderizar_item(self.app.id_item_atual, self.app.ferramenta_atual, cx, cy, cx, cy, self.app.cor_atual, temp=True)
            
        elif self.app.ferramenta_atual == "text":
            #cria localmente e envia o comando CREATE_ITEM por TCP para a rede
            texto = simpledialog.askstring("Texto", "Escreva:")
            if texto:
                note_id = uuid.uuid4().hex[:8]
                self.app.renderizar_item(note_id, "text", cx, cy, texto, self.app.cor_atual)
                self.app.rede.enviar("CREATE_ITEM", note_id, "text", cx, cy, texto, self.app.cor_atual)
                self.app.set_ferramenta("select")

    def canvas_drag(self, event):
        canvas = self.app.board_ui.canvas
        cx, cy = canvas.canvasx(event.x), canvas.canvasy(event.y)
        
        if self.app.ferramenta_atual == "select":
            if self.app.caixa_selecao_id:
                canvas.coords(self.app.caixa_selecao_id, self.app.drag_start_x, self.app.drag_start_y, cx, cy)
            elif self.app.itens_selecionados:
                # calcula a distância matemática deslocada
                dx, dy = cx - self.app.drag_start_x, cy - self.app.drag_start_y
                for note_id in self.app.itens_selecionados:
                    self.app.mover_item(note_id, dx, dy)
                    self.app.rede.enviar("MOVE_ITEM", note_id, dx, dy) 
                self.app.drag_start_x, self.app.drag_start_y = cx, cy

        elif self.app.ferramenta_atual == "laser":
            if hasattr(self.app, 'last_laser_x'):
                self.app.renderizar_laser(self.app.last_laser_x, self.app.last_laser_y, cx, cy)
                self.app.rede.enviar("LASER_SYNC", self.app.last_laser_x, self.app.last_laser_y, cx, cy)
                self.app.last_laser_x, self.app.last_laser_y = cx, cy

        # se estiver com a caneta, acumula pontos contínuos no vetor para formar o risco 
        elif self.app.ferramenta_atual == "pen" and self.app.id_item_atual:
            if len(self.app.pontos_desenho) >= 2:
                if abs(cx - self.app.pontos_desenho[-2]) > 3 or abs(cy - self.app.pontos_desenho[-1]) > 3:
                    self.app.pontos_desenho.extend([cx, cy])
                    canvas.create_line(self.app.pontos_desenho[-4:], width=3, fill=self.app.cor_atual, tags=f"id_{self.app.id_item_atual}", capstyle=tk.ROUND, smooth=True)
            
        elif self.app.ferramenta_atual in ["shape_rect", "shape_oval", "shape_tri", "seta"] and self.app.id_item_atual:
            canvas.delete("tmp_shape")
            self.app.renderizar_item(self.app.id_item_atual, self.app.ferramenta_atual, self.app.pontos_desenho[0], self.app.pontos_desenho[1], cx, cy, self.app.cor_atual, temp=True)

    def canvas_release(self, event):
        canvas = self.app.board_ui.canvas
        cx, cy = canvas.canvasx(event.x), canvas.canvasy(event.y)
        
        if self.app.ferramenta_atual == "select":
            if self.app.caixa_selecao_id:
                # verifica quais os objetos que ficaram dentro da área da caixa de seleção tracejada
                x1, y1, x2, y2 = canvas.coords(self.app.caixa_selecao_id)
                for item in canvas.find_enclosed(x1, y1, x2, y2):
                    note_id = self.get_idtag(item)
                    if note_id and note_id not in self.app.itens_selecionados: self.app.itens_selecionados.append(note_id)
                canvas.delete(self.app.caixa_selecao_id)
                self.app.caixa_selecao_id = None
                
        elif self.app.ferramenta_atual == "laser" and hasattr(self.app, 'last_laser_x'):
            del self.app.last_laser_x; del self.app.last_laser_y

        # quando solta o botão ao desenhar com a caneta, empacota todos os pontos acumulados e envia para a rede
        elif self.app.ferramenta_atual == "pen" and self.app.id_item_atual:
            self.app.rede.enviar("CREATE_ITEM", self.app.id_item_atual, "pen", ",".join(map(str, self.app.pontos_desenho)), self.app.cor_atual)
            self.app.id_item_atual = None

        # quando solta o botão, apaga o rascunho temporário e materializa o objeto definitivo na rede
        elif self.app.ferramenta_atual in ["shape_rect", "shape_oval", "shape_tri", "seta"] and self.app.id_item_atual:
            canvas.delete("tmp_shape")
            self.app.renderizar_item(self.app.id_item_atual, self.app.ferramenta_atual, self.app.pontos_desenho[0], self.app.pontos_desenho[1], cx, cy, self.app.cor_atual)
            self.app.rede.enviar("CREATE_ITEM", self.app.id_item_atual, self.app.ferramenta_atual, self.app.pontos_desenho[0], self.app.pontos_desenho[1], cx, cy, self.app.cor_atual)
            self.app.id_item_atual = None