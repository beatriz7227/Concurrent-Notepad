import socket
import threading
import time
from protocol import receber_tcp, enviar_tcp, enviar_udp

# configurações de rede do servidor
HOST = '0.0.0.0'      
PORTA_TCP = 8080 # porta para o tráfego mais pesado e persistente
PORTA_UDP = 8081 # porta para o tráfego mais temporário
LIMITE_USUARIOS = 3    

class Servidor:
    def __init__(self, senha_sala):
        # autenticação básica da sala
        self.senha_sala = str(senha_sala)
        self.memoria_board = {}  # guarda todos os objetos desenhados
        
        # relação de quem está conectado
        self.clientes_conectados = {} # guarda o objeto socket da conexão
        self.usuarios_online = {}     # guarda os nomes de exibição amigáveis
        
        # mutex fazendo cada cliente roda na sua própria thread, evitandoo que dois clientes modifiquem a memoria no mesmo ms
        self.memoria_lock = threading.Lock()

    # inicia o servidor, configura as portas e fica no aguardo dos clientes
    def iniciar(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind((HOST, PORTA_TCP))
        srv.listen()
        
        # inicia a thread que vai disparar a lista de utilizadores por UDP
        threading.Thread(target=self.broadcast_udp, daemon=True).start()
        
        print(f"Servidor escuta na porta {PORTA_TCP}")
        print(f"Limite de sala: {LIMITE_USUARIOS}")
        
        # thread principal que só aceita usuários e organiza o trabalho
        while True:
            # Bloqueia até alguém tentar conectar
            connection, address = srv.accept()
            
            # alternativa para evitar sobrecarga pelo limite da sala
            if len(self.clientes_conectados) >= LIMITE_USUARIOS:
                print(f"Conexão negada em {address}, pois a sala está cheia.")
                connection.close()
                continue
            
            # joga o cliente para uma nova thread, liberando para aceitar o próximo
            threading.Thread(target=self.tratar_cliente_tcp, args=(connection, address), daemon=True).start()

    # função para fazer o compartilhamento de uma ação TCP para todos os clientes menos quem fez
    def repassar_a_todos(self, tipo_msg, remetente_connection, *dados):
        for j in list(self.clientes_conectados.keys()):
            if j != remetente_connection: 
                enviar_tcp(j, tipo_msg, *dados)

    # organiza a desconexão limpando seu "lastro" quando ele cai/sai da sessão
    def desconectar_cliente(self, connection, addres):
        nome = self.usuarios_online.get(addres, "")
        
        # bloqueia a memória para fazer uma limpeza segura
        with self.memoria_lock:
            self.usuarios_online.pop(addres, None)
            self.clientes_conectados.pop(connection, None)
            
            # passa por todas as notas e se o cliente que caiu estava trancando alguma nota para edição, libera ela
            for note_id, prop in self.memoria_board.items():
                if prop.get('lock') == nome:
                    prop['lock'] = None
                    self.repassar_a_todos("UNLOCK", None, note_id)
                    
        try: connection.close()
        except: pass
        print(f"Cliente desconectado: {addres} ({nome})")

    # thread para enviar a relação do estado da sessão, ou seja, quem está online, a cada 2 segundos
    # usar UDP tem relação com a pouca criticidade de perder pacots devido à repetição da mensagem
    def broadcast_udp(self):
        sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        while True:
            if self.usuarios_online:
                # 255.255.255.255 envia para toda a rede local
                enviar_udp(sock_udp, '255.255.255.255', PORTA_UDP, "ONLINE_USERS", ",".join(self.usuarios_online.values()))
            time.sleep(2)

    # avalia os comandos do protocolo e atualiza o estado principal
    def processar_mensagem(self, connection, address, mensagem):
        if not mensagem or len(mensagem) < 1:
            return True
            
        tipo_msg = mensagem[0]
        nome_usuario = self.usuarios_online.get(address, "Desconhecido")
        
        if tipo_msg == "CONNECT":
            nome = mensagem[1] if len(mensagem) > 1 else "Anónimo"
            senha_tentativa = str(mensagem[2]) if len(mensagem) > 2 else ""
            
            # valida a credencial antes de permitir acesso à memória
            if senha_tentativa != self.senha_sala:
                enviar_tcp(connection, "AUTH_FAIL")
                return False # encerra o loop da thread deste cliente
                
            enviar_tcp(connection, "AUTH_OK")
            self.usuarios_online[address] = nome
            self.clientes_conectados[connection] = address
            
            # quando um cliente entra, o servidor o board inteiro
            with self.memoria_lock:
                for note_id, prop in self.memoria_board.items():
                    enviar_tcp(connection, "CREATE_ITEM", note_id, prop['type'], *prop['dados'])
                    if prop.get('texto'):
                        # pequeno delay gerado em thread concomitante para dar tempo do cliente de renderizar antes de inserir/injetar texto
                        threading.Thread(target=lambda c=connection, i=note_id, t=prop['texto']: (time.sleep(0.1), enviar_tcp(c, "TEXT_SYNC", i, t))).start()
                    if prop.get('lock'): 
                        enviar_tcp(connection, "LOCK_DENIED", note_id, prop['lock'])
            return True
                        
        elif tipo_msg == "CREATE_ITEM":
            if len(mensagem) < 3:
                return True
            note_id, tipo_item = mensagem[1], mensagem[2]
            dados = list(mensagem[3:])
            
            with self.memoria_lock:
                # impede que IDs se conflitem e/ou sobrescrevam itens concretos
                if note_id not in self.memoria_board:
                    self.memoria_board[note_id] = {"type": tipo_item, "dados": dados, "texto": "", "lock": None}
                    self.repassar_a_todos("CREATE_ITEM", connection, note_id, tipo_item, *dados)
            return True

        elif tipo_msg == "DELETE_ITEM":
            if len(mensagem) < 2: return True
            note_id = mensagem[1]
            
            with self.memoria_lock:
                if note_id in self.memoria_board:
                    del self.memoria_board[note_id]
                    self.repassar_a_todos("DELETE_ITEM", connection, note_id)
            return True

        elif tipo_msg == "MOVE_ITEM":
            if len(mensagem) < 4: 
                return True
            try:
                note_id = mensagem[1]
                dx, dy = float(mensagem[2]), float(mensagem[3])
            except ValueError:
                # proteção contra strings no lugar de coordenadas
                return True 
                
            with self.memoria_lock:
                if note_id in self.memoria_board:
                    prop = self.memoria_board[note_id]
                    tipo = prop['type']
                    d = prop['dados']
                    
                    # atualiza matematicamente as coordenadas na memória central
                    try:
                        if tipo in ['postit', 'text']:
                            d[0] = str(float(d[0]) + dx)
                            d[1] = str(float(d[1]) + dy)
                        elif tipo in ['shape_oval', 'shape_rect', 'shape_tri', 'seta']:
                            d[0] = str(float(d[0]) + dx); d[1] = str(float(d[1]) + dy)
                            d[2] = str(float(d[2]) + dx); d[3] = str(float(d[3]) + dy)
                        elif tipo == 'pen':
                            # traços de caneta são uma string concatenada de centenas de pontos
                            pts = [float(p) for p in d[0].split(',')]
                            pts = [p + dx if i%2==0 else p + dy for i, p in enumerate(pts)]
                            d[0] = ",".join(map(str, pts))
                    except ValueError:
                        pass 
                        
                    self.repassar_a_todos("MOVE_ITEM", connection, note_id, dx, dy)
            return True
                    
        elif tipo_msg == "LASER_SYNC":
            # o laser não é guardado na memoria 
            self.repassar_a_todos("LASER_SYNC", connection, *mensagem[1:])
            return True
            
        elif tipo_msg == "LOCK_REQ":
            if len(mensagem) < 2: 
                return True
            note_id = mensagem[1]
            
            with self.memoria_lock: 
                dono = self.memoria_board.get(note_id, {}).get('lock')
                # se o postit está livre ou se o usuário já era o dono
                if dono is None or dono == nome_usuario:
                    if note_id in self.memoria_board:
                        self.memoria_board[note_id]['lock'] = nome_usuario
                    
                    enviar_tcp(connection, "LOCK_ACK", note_id) # avisa o autor que pode editar
                    self.repassar_a_todos("LOCK_DENIED", connection, note_id, nome_usuario) # tranca as janelas dos restantes
                else: 
                    # se outra pessoa foi mais rápida, nega
                    enviar_tcp(connection, "LOCK_DENIED", note_id, dono)
            return True
                    
        elif tipo_msg == "TEXT_SYNC":
            if len(mensagem) < 2: 
                return True
            note_id = mensagem[1]
            novo_texto = mensagem[2] if len(mensagem) > 2 else ""
            
            with self.memoria_lock:
                if note_id in self.memoria_board:
                    self.memoria_board[note_id]['texto'] = novo_texto
                    self.memoria_board[note_id]['lock'] = None # destranca a nota quando recebe o texto
                    self.repassar_a_todos("TEXT_SYNC", connection, note_id, novo_texto)
                    self.repassar_a_todos("UNLOCK", None, note_id)
            return True

        elif tipo_msg == "DISCONNECT":
            self.desconectar_cliente(connection, address)
            return False
            
        return True

    # threada para um único cliente e existe enquanto esse cliente estiver conectado
    def tratar_cliente_tcp(self, connection, address):
        # como fim de 60s, o socket levanta exceção e limpa a memória
        connection.settimeout(60.0) 
        
        while True:
            try:
                # fica travado aqui à espera de dados na rede
                mensagem = receber_tcp(connection)
                
                # se receber none, significa que a conexão foi fechada do outro lado
                if not mensagem:
                    self.desconectar_cliente(connection, address)
                    break
                    
                manter_conexao = self.processar_mensagem(connection, address, mensagem)
                if not manter_conexao:
                    self.desconectar_cliente(connection, address)
                    break
                    
            except socket.timeout:
                print(f"Desconectando cliente inativo: {address}")
                self.desconectar_cliente(connection, address)
                break
            except Exception as e:
                print(f"Erro no cliente {address}: {e}")
                self.desconectar_cliente(connection, address)
                break

if __name__ == "__main__":
    servidor = Servidor()
    servidor.iniciar()