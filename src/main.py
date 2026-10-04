import tkinter as tk
from network import GerenciadorRede
from ui.login import LoginUI

# class que atua como controlador para guardar o estado global da aplicação e integrar rede <> interface
class AppController:
    def __init__(self, root):
        self.root = root
        self.root.title("Concurrent Notepad")
        self.root.geometry("1200x800")
        self.rede = GerenciadorRede(self) # instancia o gestor de rede passando o próprio AppController como referência
        
        # Todas as variáveis do estado global que precisam ser acedidas por mais arquivos 
        self.notas_ui = {} #referências de todos os widgets desenhados na tela
        self.ferramenta_atual = "select"
        self.cor_atual = "#2c3e50" # cor padrão
        
        # variáveis de controle para a matemática do movimento
        self.id_item_atual = None
        self.pontos_desenho = []
        self.itens_selecionados = []
        self.caixa_selecao_id = None
        self.drag_start_x = 0
        self.drag_start_y = 0

        # módulos referentes ao board de fato
        self.board_ui = None
        self.canvas_ops = None
        self.postit_mgr = None
        self.servidor_thread = None # ref para o servidor local se o usuário for o host
        
        # joga a construção da tela inicial para a classe LoginUI
        self.login_ui = LoginUI(self)
        self.login_ui.construir_tela_inicial()

    # atualiza o estado da ferramente e pede para a interface se atualizar
    def set_ferramenta(self, ferramenta):
        self.ferramenta_atual = ferramenta
        self.board_ui.AtualizarFerramentas()
        
        # dicionário para alterar o cursor conforme a ferramenta
        cursores = {
            "select": "arrow", "pen": "pencil", "laser": "dotbox",
            "eraser": "X_cursor", "text": "xterm",
            "seta": "crosshair", "shape_rect": "crosshair", "shape_oval": "crosshair", "shape_tri": "crosshair"
        }
        
        # aplica a alteração do cursor
        try:
            self.board_ui.canvas.config(cursor=cursores.get(ferramenta, "arrow"))
        except AttributeError:
            pass
                
        if ferramenta == "postit":
            self.postit_mgr.CriarPostit()
            self.set_ferramenta("select")

    # atualiza cor no estado global 
    def set_cor(self, cor_escolhida):
        self.cor_atual = cor_escolhida
        self.board_ui.AtualizarCores()
    
    def renderizar_item(self, note_id, tipo, *dados, temp=False):
        self.board_ui.renderizar_item(note_id, tipo, *dados, temp=temp)
        
    def apagar_item(self, note_id):
        self.board_ui.apagar_item(note_id)

    def mover_item(self, note_id, dx, dy):
        self.board_ui.mover_item(note_id, dx, dy)

    def renderizar_laser(self, x1, y1, x2, y2):
        self.board_ui.renderizar_laser(x1, y1, x2, y2)

    def atualizar_estado(self, note_id, status, dono):
        self.postit_mgr.atualizar_estado(note_id, status, dono)

    def sincronizar_texto(self, note_id, texto):
        self.postit_mgr.sincronizar_texto(note_id, texto)

    def atualizar_usuarios(self, nomes):
        self.board_ui.atualizar_usuarios(nomes)
    
    def encerrar_app(self):
        self.rede.desconectar() # avisa o servidor TCP de que vai sair de forma voluntária
        self.root.quit() # quebra o ciclo do Tkinter
        self.root.destroy() # destrói a janela e limpa a memória

if __name__ == "__main__":
    # inicia o ciclo principal de eventos
    root = tk.Tk()
    app = AppController(root)
    root.mainloop()