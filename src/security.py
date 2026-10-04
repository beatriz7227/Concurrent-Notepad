import os
from cryptography.fernet import Fernet 
from dotenv import load_dotenv


load_dotenv() # carrega as variáveis do arquivo .env para a memória

chave_str = os.getenv("CHAVE")
if not chave_str:
    exit(1)

# converte a string do .env de volta para bytes, como o Fernet exige
CHAVE = chave_str.encode('utf-8')

try:
    # o fernet garante a confidencialidade, ocultando a mensagem, mas também assina o pacote com um hash por fins de integridade
    #se um pacote for modificado no meio, a assinatura é quebrada e a mensagem é rejeitada
    cifra = Fernet(CHAVE)
except Exception as e:
    print(f"Chave inválida: {e}")
    exit(1)

# recebe a mensagem em texto gerada pelo protocolo e converte para bytes para cifrar ela num pacote seguro
def encriptar(texto: str) -> bytes:
    try:
        texto_bytes = texto.encode('utf-8')
        return cifra.encrypt(texto_bytes)
    except Exception as e:
        print(f"Erro {e}")
        return b""

# recebe o pacote vindo da rede, valida a sua autenticidade e devolve o texto original para o protocolo ler
def desencriptar(pacote_criptografado: bytes) -> str:
    try:
        texto_bytes = cifra.decrypt(pacote_criptografado)
        return texto_bytes.decode('utf-8')
    except Exception as e:
        print(f"Pacote corrompido: {e}")
        return ""