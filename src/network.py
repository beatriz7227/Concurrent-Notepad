import socket
import threading
from protocol import enviar_tcp, receber_tcp, decodificar_mensagem
from security import desencriptar

PORTA_TCP = 8080
PORTA_UDP = 8081

# classe responsável por toda a comunicação cliente<>servidor e que isola a complexidade dos sockets da interface gráfica

class GerenciadorRede:
    # ref ao main.py para podermos devolver as mensagens recebidas da rede de volta para a interface visual
    def __init__(self, ui_controller):
        self.ui = ui_controller 
        self.sock_tcp = None
        self.nome_usuario = ""

    # estabelece a ligação inicial com o servidor e valida a senha
    def conectar(self, ip, nome, senha):
        self.nome_usuario = nome
        self.sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock_tcp.connect((ip, PORTA_TCP))
        
        # envia a senha junto com o pedido de conexão
        enviar_tcp(self.sock_tcp, "CONNECT", self.nome_usuario, senha)
        
        # esperamos a resposta do servidor para validar a senha
        resposta = receber_tcp(self.sock_tcp)
        
        if resposta and resposta[0] == "AUTH_OK":
            # a senha está certa e se encaminham as threads
            threading.Thread(target=self.escutar_tcp, daemon=True).start()
            threading.Thread(target=self.escutar_udp, daemon=True).start()
            return True
        else:
            # senha errada ou o servidor fechou
            self.sock_tcp.close()
            return False

    # função que o main.py chama para jogar coisas para a rede
    def enviar(self, tipo_msg, *dados):
        if self.sock_tcp:
            enviar_tcp(self.sock_tcp, tipo_msg, *dados)

    # avisa o servidor da intenção de desconectar
    def desconectar(self):
        if self.sock_tcp:
            enviar_tcp(self.sock_tcp, "DISCONNECT", self.nome_usuario)
            self.sock_tcp.close()

    # thread dedicada a ouvir ordens contínuas do servidor.
    def escutar_tcp(self):
        while True:
            msg = receber_tcp(self.sock_tcp)
            if not msg: break
            
            tipo = msg[0]
            
            rotas = {
                "CREATE_ITEM": lambda m: self.ui.root.after(0, self.ui.renderizar_item, m[1], m[2], *m[3:]),
                "DELETE_ITEM": lambda m: self.ui.root.after(0, self.ui.apagar_item, m[1]),
                "MOVE_ITEM":   lambda m: self.ui.root.after(0, self.ui.mover_item, m[1], float(m[2]), float(m[3])),
                "LASER_SYNC":  lambda m: self.ui.root.after(0, self.ui.renderizar_laser, float(m[1]), float(m[2]), float(m[3]), float(m[4])),
                "LOCK_ACK":    lambda m: self.ui.root.after(0, self.ui.atualizar_estado, m[1], "ACK", None),
                "LOCK_DENIED": lambda m: self.ui.root.after(0, self.ui.atualizar_estado, m[1], "DENIED", m[2]),
                "UNLOCK":      lambda m: self.ui.root.after(0, self.ui.atualizar_estado, m[1], "UNLOCK", None),
                "TEXT_SYNC":   lambda m: self.ui.root.after(0, self.ui.sincronizar_texto, m[1], m[2] if len(m)>2 else "")
            }
            
            if tipo in rotas:
                rotas[tipo](msg)

    def escutar_udp(self):
        sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock_udp.bind(('0.0.0.0', PORTA_UDP))
        
        while True:
            try:
                dados, _ = sock_udp.recvfrom(65536)
                msg_texto = desencriptar(dados)
                if not msg_texto: 
                    continue
                
                msg = decodificar_mensagem(msg_texto)
                if msg[0] == "ONLINE_USERS":
                    nomes = msg[1].split(',') if len(msg) > 1 and msg[1] else []
                    self.ui.root.after(0, self.ui.atualizar_usuarios, nomes)
            except: 
                pass