# Concurrent Notepad - Quadro Colaborativo

> Exercício Programa (EP) desenvolvido para a disciplina de Redes de Computadores do curso de Sistemas de Informação da Escola de Artes, Ciências e Humanidades da Universidade de São Paulo (EACH-USP).

Este projeto implementa uma aplicação de um quadro branco colaborativo em tempo real, utilizando python e a API nativa de **sockets**. O sistema adota uma arquitetura cliente-servidor com suporte a concorrência a partir de *threads*, comunicação utilizando os protocolos **TCP** (para dados persistentes e críticos) e **UDP** (para descoberta e presença local), além de uma camada de segurança com criptografia simétrica.

---

## 📑 Sumário

* [Tecnologias Utilizadas](#-tecnologias-utilizadas)
* [Principais Funcionalidades e Impactos](#-principais-funcionalidades-e-impactos)
* [Organização de Arquivos](#-organização-de-arquivos)
* [Como Executar a Aplicação](#-como-executar-a-aplicação)

---

## Tecnologias Utilizadas

O projeto foi desenvolvido inteiramente em **python**, a partir de bibliotecas nativas e externas para garantir performance e segurança:

* **Python 3.10+**: Linguagem principal para toda a lógica de cliente, servidor e interface.
* **Tkinter & Tcl**: Biblioteca gráfica padrão do Python utilizada para a construção de toda a interface visual.
* **Sockets**: API do sistema para a comunicação de rede através dos protocolos TCP e UDP.
* **Concorrência**: Utilizada para gerir múltiplas conexões simultâneas no servidor e escutas assíncronas em segundo plano nos clientes sem bloquear.
* **Criptografia Fernet**: Garante a confidencialidade e integridade dos pacotes de dados trocados na rede através de encriptação simétrica autenticada.
* **Gestor de Ambiente (`python-dotenv`)**: Utilizado para carregar variáveis sensíveis e chaves de segurança ocultas a partir de um arquivo `.env`.
* **Manipulação de Imagem (`Pillow`)**: Responsável pelos eventos de exportação do quadro para capturas de tela em formato PNG.

---

## Principais Funcionalidades e Impactos

A aplicação foi concebida para garantir sincronismo fluído entre múltiplos usuários em rede, resolvendo os desafios clássicos de concorrência e consistência de estado:

* **Controle de Concorrência:** Mecanismo de exclusão mútua nos post-its para evitar conflitos de escrita simultânea entre diferentes clientes.
* **Sincronismo:** Desenhos livres a traço, formas geométricas, caixas de texto e laser refletidos instantaneamente nos quadros dos restantes participantes.
* **Gestão de sessão/limites:** Proteção contra sobrecarga de conexões no servidor através de limites estritos de usuários ativos e gestão de *timeouts* para remoção de clientes inativos.
* **Persistência/Exportação:** Capacidade de exportar o estado do quadro para imagem PNG ou arquivos JSON, assim como carregar arquivos salvos.

---

## Organização de Arquivos

O projeto encontra-se modularizado para garantir coesão e eficiência da seguinte forma:

* **`main.py`**: Atua como o *controller* global gerindo o estado compartilhado e a delegação de eventos para a interface.
* **`host.py`**: O servidor central que gere as conexões TCP, o controle de travamento das notas, a memória central do quadro e a transmissão UDP de presença.
* **`network.py`**: O gestor de rede do cliente que implementa o roteamento de mensagens recebidas de forma segura para a interface gráfica.
* **`protocol.py`**: Define o protocolo de aplicação, tratando o empacotamento, delimitadores de pacotes TCP e a prevenção de fragmentação.
* **`security.py`**: Encriptação e desencriptação dos pacotes utilizando chaves locais.
* **Módulos UI (`ui/`)**: Contém os componentes visuais divididos modularmente (`board.py`, `login.py`, `canvas_ops.py`, `postit.py`).
* **`file_io.py`**: Implementa os procedimentos para leitura e escrita para exportação/importação em JSON e PNG.

### O que é a chave no `.env` e como defini-la?

Para garantir a segurança das comunicações, o projeto utiliza **criptografia dimétrica fernet**. Isto significa que tanto o servidor quanto todos os clientes precisam de compartilhar exatamente a mesma chave para encriptar e desencriptar os pacotes na rede.

* **O arquivo `.env`**: A aplicação lê esta chave de forma segura através de uma variável de ambiente contida num arquivo local `.env` .
* **Como definir a sua própria chave**: 
   Se quiser gerar uma chave nova e totalmente aleatória, execute este pequeno comando no seu terminal python:
   ```python
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
#### Instrução de configuração:
* Crie um arquivo chamado .env na raiz do projeto usando o arquivo de exemplo .env.example como base e insira a chave gerada. Todos os computadores que se conectarem à sala devem possuir exatamente a mesma chave configurada no respetivo arquivo `.env` para que o sistema consiga descodificar as mensagens.

---

## Como Executar a Aplicação

### Pré-requisitos
* Ter o **Python 3.10+** instalado na sua máquina.
* Instalar as dependências necessárias listadas no arquivo `requirements.txt`:
  ```bash
  pip install -r requirements.txt
  ```
### Configuração Inicial
* Certifique-se de que possui o arquivo .env configurado na raiz do projeto com a chave de segurança exigida pelo módulo de criptografia.

### Execução
* Abra o terminal na pasta raiz do projeto.
* Inicie a aplicação executando o arquivo principal:

```bash
python main.py
```

* Na janela inicial, escolha se pretende hospedar uma sala, definindo uma senha de acesso, ou entrar em uma sala existente informando o endereço IP do host, o seu nome de usuário e a senha correspondente.