import socket
from security import encriptar, desencriptar # importa as funções do security.py

SEPARATOR = "|||" 
ENCODING = "utf-8"
BUFFER_SIZE = 65536
EOF = "<EOF>"
MAX_BUFFER_SIZE = 5 * 1024 * 1024 # limite de 5MB por cliente para evitar instabilidades ou riscos

buffers = {} # dicionário com memória temporária para lidar com a fragmentação TCP

# pega comando/argumentos e transforma tudo numa string
def formatar_mensagem(tipo_msg, *dados):
    dados_limpos = [str(d).replace(SEPARATOR, "---").replace(EOF, "") for d in dados] # o replace substitui as strings erradas de texto por carateres que não causam impacto
    partes = [tipo_msg] + dados_limpos
    return SEPARATOR.join(partes)

# transforma a string recebida de volta numa lista legível
def decodificar_mensagem(mensagem_crua):
    return mensagem_crua.split(SEPARATOR)

# empacota, encripta e envia os dados por TCP
def enviar_tcp(sock, tipo_msg, *dados):
    try:
        msg_texto = formatar_mensagem(tipo_msg, *dados) # converte argumentos na string do protocolo
        msg_encriptada = encriptar(msg_texto) #criptografa o texto inteiro
        msg_final = msg_encriptada.decode(ENCODING) + EOF # marca o fim do nosso protocolo TCP e converte para bytes
        sock.sendall(msg_final.encode(ENCODING))
        return True
    except Exception: 
        return False

# lê o fluxo contínuo do TCP, remonta as mensagens fragmentadas e descriptografa elas
def receber_tcp(sock):
    try:
        if sock not in buffers:
            buffers[sock] = ""

        # puxa dados da rede enquanto não encontrar a marca de fim de pacote
        while EOF not in buffers[sock]:
            msg_bytes = sock.recv(BUFFER_SIZE)
            if not msg_bytes: 
                if sock in buffers: del buffers[sock]
                return None
                
            buffers[sock] += msg_bytes.decode(ENCODING)
            
            # se o cliente enviar uma string infinitasem nunca enviar um EOF
            if len(buffers[sock]) > MAX_BUFFER_SIZE:
                del buffers[sock]
                return None
            
        msg_encriptada64, buffers[sock] = buffers[sock].split(EOF, 1)

        # pacote isolado é desencriptado
        msg_desencriptada = desencriptar(msg_encriptada64.encode(ENCODING))
        if not msg_desencriptada:
            return None
            
        return decodificar_mensagem(msg_desencriptada)
    except Exception: 
        if sock in buffers: del buffers[sock]
        return None

# envia uma mensagem de forma rápida
def enviar_udp(sock, ip_destino, porta, tipo_msg, *dados):
    try:
        msg_texto = formatar_mensagem(tipo_msg, *dados)
        msg_encriptada = encriptar(msg_texto)
        sock.sendto(msg_encriptada, (ip_destino, porta))
    except Exception: 
        pass