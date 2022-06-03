from concurrent.futures import thread
import ipaddress
import socket
from threading import Thread
import sys


#**********************************************  VARIAVEIS  *********************************************#
ip_server = "191.52.64.135"
port_server = 8080

clients = {}
directClients = {}
clientsList = ip_server + "-" + (str(port_server)) + "-server" #Inicializa uma string que armazenara os clientes no formato (@ip-port-nome)
clientsListAddresses = ip_server + "-" + (str(port_server)) + "-" + (str(port_server)) #Inicializa uma string que armazenara os enderecos dos clientes no formato (@ip-port_cliente-port_servidor])


#******************************************* SERVER PRINCIPAL *******************************************#

def delete_element_clientsList(name):
    global clientsList
    auxList = "" #Inicializa nova string com lista de clientes.
    List = clientsList.split("@")
    
    for x in List:
        clientInfo = x.split("-")
        ipAtual = clientInfo[0]
        portAtual = (int(clientInfo[1]))
        nameAtual = clientInfo[2]
        if name == nameAtual:
            print("Cliente " + name + " se desconectou")
        else:
            auxList = auxList + "@" + ipAtual + "-" + (str(portAtual)) + "-" + nameAtual
    
    clientsList = auxList
    print(clientsList)
    
def delete_element_clientsListAddresses(ip, port):
    global clientsListAddresses
    auxList = "0" #Inicializa nova string com lista de clientes.
    List = clientsListAddresses.split("@")
    
    for x in List:
        clientInfo = x.split("-")
        ipAtual = clientInfo[0]
        portAtual = (int(clientInfo[1]))
        portBindAtual = clientInfo[2]
        if ip == ipAtual and port == portAtual:
            print("Cliente (" + ip + "," + (str(portAtual)) + " se desconectou")
        else:
            if auxList == "0":
                auxList = ipAtual + "-" + (str(portAtual)) + "-" + portBindAtual   
            else: 
                auxList = auxList + "@" + ipAtual + "-" + (str(portAtual)) + "-" + portBindAtual
    
    clientsListAddresses = auxList
    msg = "updated-client-list@" + clientsListAddresses
    send_info(msg, directClients)
    
def add_address(client_info, name):
    global clientsListAddresses
    new_address = "@" + client_info[1] + "-" + (str(client_info[2])) + "-" + (str(client_info[3])) + "-" + name
    clientsListAddresses = clientsListAddresses + new_address
    msg = "updated-client-list@" + clientsListAddresses
    send_info(msg, directClients)

#Funcao para lidar com clientes - recebe o nome do cliente e dados da conexao
def handle_clients(conn, client_address):
    global clientsListAddresses
    client_ip = ""
    client_port = 0
    client_port_bind = 0
    
    name = conn.recv(1024).decode("utf8")

    welcome = f"Bem-vindo(a) {name} :)" #Mensagem de boas vindas 
    conn.send(bytes(welcome, "utf8"))
    
    msg = name + " se juntou ao chat" #Mensagem para avisar outros clientes
    send_info(msg, clients) #Avisa todos os clientes
    
    clients[conn] = name #Adiciona cliente ao dicionario
    
    conn.send(bytes("testar-conexao", "utf8"))

    while True: #Loop para receber mensagens do cliente e transmiti-las
        try:
            msg = conn.recv(1024).decode("utf8")
            if 'clients-list' in msg: #Envia a lista de enderecos para o cliente
                print("Enviando lista de enderecos")
                conn.send(bytes(clientsListAddresses, "utf8"))
            elif 'client-info' in msg: #Recebe info do cliente conectado e adiciona a lista de enderecos
                this_client_info = msg.split("@")
                client_ip = this_client_info[1]
                client_port = (int(this_client_info[2]))
                client_port_bind = (int(this_client_info[3]))
                add_address(this_client_info, name)
            elif 'server-conn' in msg:
                 directClients[conn] = name #Adiciona cliente ao dicionario
            elif 'client_message:' in msg: 
                client_message = msg.split("@")
                y = client_message[0].split(":")
                x = client_message[1].split(":")
                forward_message(x[1], y[1], x[0], directClients)
            elif 'is-conn-alive' in msg:
                pass
            else:
                send_message(msg, name, directClients)
        except socket.timeout:
            print("Conexao derrubada")
        except:
            clients.pop(conn)
            print(clientsListAddresses)
            delete_element_clientsListAddresses(client_ip, client_port)
            sys.exit()

#Envia infos para os clients
def send_info(msg, Clients):
    for client in Clients:  #Dict que contem infos de conexao
        client.send(bytes(msg, "utf8"))

#Envia mensagem para todos os clientes da lista
def send_message(msg, name, directClients):
    new_msg = name + ":" + msg
    for client_conn, client_name in directClients.items():  #Dict que contem infos de conexao
        if client_name == name:
            pass
        else:
            client_conn.send(bytes(new_msg, "utf8"))

def forward_message(msg, sender_name, message_sender_name, directClients):
    new_msg = message_sender_name + ":" + msg
    for client_conn, client_name in directClients.items():  #Dict que contem infos de conexao
        if client_name == sender_name:
            pass
        else:
            client_conn.send(bytes(new_msg, "utf8"))

#Funcao para aceitar a conexao dos clientes
def accept_client_connection():
    while True:  #Loop para aceitar conexoes
        client_conn, client_address = sock.accept()  
        print(client_address, " se conectou")

        teste = client_conn.recv(1024).decode("utf8")
        
        if "client-connection" in teste:
            client_conn.send(bytes("Digite seu nome para continuar:", "utf8"))
            Thread(target=handle_clients, args=(client_conn, client_address)).start() #Inicia uma thread para o cliente aceito
        elif "is-conn-alive" in teste:
            pass
        else:
            print("Teste de ping...")


#************************************************* MAIN *************************************************#
if __name__ == "__main__":
    print("** Inicializando servidor .....")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((ip_server, port_server))
    sock.listen(20)
    print("Servidor inicializado em: (" + ip_server+ " ," +(str(port_server))+ ")......")

    t = Thread(target=accept_client_connection) #A thread aceita multiplos clientes

    t.start()  # start thread
    t.join()  # thread wait for main thread to exit.