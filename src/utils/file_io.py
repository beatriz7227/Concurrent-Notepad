import json
from tkinter import filedialog, messagebox
from PIL import ImageGrab

def exportar_png(app):
    # abre a janela do SO para nome do arquivo/caminho
    arquivo = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
    if arquivo:
        app.root.update()
        canvas = app.board_ui.canvas
        # mapeia as coordenadas do quadro para delimitar a captura
        bbox = (canvas.winfo_rootx(), canvas.winfo_rooty(), canvas.winfo_rootx() + canvas.winfo_width(), canvas.winfo_rooty() + canvas.winfo_height())
        ImageGrab.grab(bbox=bbox).save(arquivo)

# serializa todos os elementos ativos do quadro em um arquivo JSON 
def exportar_json(app):
    arquivo = filedialog.asksaveasfile(defaultextension=".json", filetypes=[("JSON", "*.json")])
    if arquivo:
        dados = []
        canvas = app.board_ui.canvas
        # percorre todos os itens guardados na memória global do cliente
        for note_id, ui_ref in app.notas_ui.items():
            tipo = ui_ref["type"]
            # extrai a cor de contorno ou de preenchimento segundo elemento 
            cor = canvas.itemcget(f"id_{note_id}", "fill" if tipo in ["pen", "seta", "text"] else "outline") if tipo != "postit" else ""

            # extrai as coordenadas e propriedades específicas de cada tipo de objeto e empacota num dicionário
            if tipo == "postit":
                c = canvas.coords(ui_ref["winote_id"])
                dados.append({"id": note_id, "type": tipo, "dados": [c[0], c[1]], "texto": ui_ref["texto_guardado"]})
            elif tipo == "text":
                c = canvas.coords(f"id_{note_id}")
                dados.append({"id": note_id, "type": tipo, "dados": [c[0], c[1], canvas.itemcget(f"id_{note_id}", "text"), cor]})
            elif tipo == "pen":
                dados.append({"id": note_id, "type": tipo, "dados": [",".join(map(str, canvas.coords(f"id_{note_id}"))), cor]})
            elif tipo in ["shape_rect", "shape_oval", "shape_tri", "seta"]:
                c = canvas.coords(f"id_{note_id}")
                dados.append({"id": note_id, "type": tipo, "dados": [c[0], c[1], c[2], c[3], cor]})

        # joga em uma lista do JSON
        json.dump(dados, arquivo, indent=4, ensure_ascii=False)
        arquivo.close()

# lê um arquivo JSON e reconstrói os elementos no quadro e joga eles com TCP
def carregar_json(app):
    arquivo = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
    if arquivo:
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                for item in json.load(f):
                    note_id, tipo = item['id'], item['type']
                    # renderiza o item localmente e envia de imediato a ordem de criação para a rede
                    app.renderizar_item(note_id, tipo, *item['dados'])
                    app.rede.enviar("CREATE_ITEM", note_id, tipo, *item['dados'])

                    # se o item for um postit, repõe também o seu texto e estado guardado
                    if tipo == 'postit':
                        app.postit_mgr.alterar_estado(note_id, "SALVO")
                        if item.get('texto'):
                            app.postit_mgr.sincronizar_texto(note_id, item['texto'])
                            app.rede.enviar("TEXT_SYNC", note_id, item['texto'])
        except Exception as e:
            #se o arquivo for corrompido ou mal formatado, exibe um aviso gráfico sem fechar
            messagebox.showerror("Erro", f"O arquivo pode estar corrompido: {e}")