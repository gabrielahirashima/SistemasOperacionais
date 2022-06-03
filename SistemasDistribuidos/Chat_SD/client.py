import socket
from threading import Thread
from turtle import update
from unicodedata import name
from tcp_latency import measure_latency
import re
import subprocess
import time
import copy
from client1 import send_message_directClients

from server import send_message


#**********************************************  VARIAVEIS  *********************************************#

client_ip = "191.52.64.135"
client_port = 8000
client_port_bind = client_port + 1

server_ip = "191.52.64.135"
server_port = 8080

directClients = {}
directClientAux = {}
allClients = ""
clientsNumber = 0
isConnectedToOriginalServer = 0 #Variavel para verificar se esta conectado no server original, se 0, o server original ainda eh o principal se 1, outro cliente eh o pricipal
thisName = ""
isMainServer = 0

#*********************************************** CLIENTE ***********************************************#
def connect(clientsList):
    global isConnectedToOriginalServer
    global thisName
    
    for clients in clientsList:
            clientInfo = clients.split("-")
            ipAtual = clientInfo[0]
            portAtual = (int(clientInfo[2]))
            if ipAtual == client_ip and portAtual == client_port_bind:
                thisName = clientInfo[3]
    
    if len(clientsList) == 2: #Caso a lista de enderecos retorne 2 elementos, quer dizer que ha somente o server e o cliente atual disponiveis. Conexao e feita ao server
        print(">>> Conectado ao servidor")
        s.send(bytes("server-conn", "utf8"))
    elif len(clientsList) == 3:
        clientInfo = clientsList[1].split("-")
        ipAtual = clientInfo[0]
        portAtual = (int(clientInfo[2]))
        new_sock.connect((ipAtual, portAtual))
        msg = "new-conn@" + thisName + "@" + client_ip + "@" + (str(client_port))
        new_sock.send(bytes(msg, "utf8"))
        isConnectedToOriginalServer = 1
        print(">> Conectado a: (" + ipAtual + "," + (str(portAtual)) + ")")
    else:
        print("** Testando ping...")
        menorPing = 10000.0
        ipMenorPing = ""
        portMenorPing = 0
        
        for clients in clientsList:
            clientInfo = clients.split("-")
            ipAtual = clientInfo[0]
            portAtual = (int(clientInfo[2]))
            if ipAtual == client_ip and portAtual == client_port_bind:
                print("Pulando...")
            else:
                ping = measure_latency(host = ipAtual, port = portAtual, runs=1, timeout=2.5)
                
                if len(ping) == 1:
                    if ping[0] < menorPing:
                        menorPing = ping[0]
                        ipMenorPing = ipAtual
                        portMenorPing = portAtual
                        
        print(">> Melhor conexao com: " +(str(portMenorPing))+ " de " + ipMenorPing)
        if ipMenorPing == server_ip and portMenorPing == server_port:
            print(">> Conectado ao servidor")
            s.send(bytes("server-conn", "utf8"))
        else:
            new_sock.connect((ipMenorPing, portMenorPing))
            print(">> Conectado a (" +ipMenorPing + "," + (str(portMenorPing)) + ")")
            msg = "new-conn@" + thisName + "@" + client_ip + "@" + (str(client_port))
            new_sock.send(bytes(msg, "utf8"))
            isConnectedToOriginalServer = 1

def receive_from_server():
    global allClients
    global clientsList
    global directClients
    while True: #Loop para receber mensagens
        if isConnectedToOriginalServer == 0:
            try:
                msg = s.recv(1024).decode("utf8") 
                if 'testar-conexao' in msg: #Parte que ira testar os pings com as conexoes
                    this_client_info = "client-info" + "@" + client_ip + "@"+ (str(client_port)) + "@" + (str(client_port_bind))
                    s.send(bytes(this_client_info, "utf8"))
                    time.sleep(1)
                    s.send(bytes("clients-list", "utf8"))
                    msg = s.recv(1024).decode("utf8") 
                    
                    allClients = msg
                    clientsList = msg.split('@')
                    connect(clientsList)
                elif 'client_message:' in msg: 
                    client_message = msg.split("@")
                    y = client_message[0].split(":") #Parte da mensagem no formato: client_message : Nome_de_quem_repassou_msg
                    x = client_message[1].split(":") #Parte da mensagem no formato: Nome_do_cliente_msg: Msg
                    send_directClients(x[1], x[0], directClients)
                elif 'is-conn-alive' in msg:
                    pass
                elif 'updated-client-list@' in msg:
                    send_message_directClients(msg, directClients)
                    updated_list = msg.removeprefix("updated-client-list@")
                    allClients = updated_list
                else:
                    send_message_directClients(msg, directClients)
                    print(msg)
            
            except Exception:
                pass
        else:
            try:
                msg = new_sock.recv(1024).decode("utf8") 
                if 'testar-conexao' in msg: #Parte que ira testar os pings com as conexoes
                    this_client_info = "client-info" + "@" + client_ip + "@"+ (str(client_port)) + "@" + (str(client_port_bind))
                    new_sock.send(bytes(this_client_info, "utf8"))
                    time.sleep(1)
                    new_sock.send(bytes("clients-list", "utf8"))
                    msg = new_sock.recv(1024).decode("utf8") 
                    
                    allClients = msg
                    clientsList = msg.split('@')
                    connect(clientsList)
                elif 'client_message:' in msg: 
                    client_message = msg.split("@")
                    y = client_message[0].split(":") #Parte da mensagem no formato: client_message : Nome_de_quem_repassou_msg
                    x = client_message[1].split(":") #Parte da mensagem no formato: Nome_do_cliente_msg: Msg
                    send_directClients(x[1], x[0], directClients)
                elif 'is-conn-alive' in msg:
                    pass
                elif 'updated-client-list@' in msg:
                    send_message_directClients(msg, directClients)
                    updated_list = msg.removeprefix("updated-client-list@")
                    allClients = updated_list
                else:
                    send_message_directClients(msg, directClients)
                    print(msg)
                    isConnected = 1
            
            except Exception:
                pass

def send_server():
    global thisName
    global directClients
    global directClientAux
    while True:
        msg = input("") #Aguarda input
        if isMainServer == 0:
            if isConnectedToOriginalServer == 0: 
                s.send(bytes(msg, "utf8")) #Envia mensagem
                send_directClients(msg, thisName, directClients)
                    
            elif isConnectedToOriginalServer == 1:
                new_msg = "client_message:"+ thisName + "@" + thisName + ":" + msg
                new_sock.send(bytes(new_msg, "utf8")) #Envia mensagem
                send_directClients(msg, thisName, directClients)
        else:
            send_directClients(msg, thisName, directClients)

def send_directClients(msg, name, directClients):
    new_msg = name + ": " + msg
    directClients = directClientAux
    for client_conn, client_name in directClients.items():  #Dict que contem infos de conexao
        if client_name == name:
            pass
        else:
            client_conn.send(bytes(new_msg, "utf8"))

def send_message_directClients(msg, directClients):
    for client in directClients:  #Dict que contem infos de conexao
        client.send(bytes(msg, "utf8"))

def forward_message(msg, sender_name, message_sender_name, directClients):
    new_msg = message_sender_name + ":" + msg
    for client_conn, client_name in directClients.items():  #Dict que contem infos de conexao
        if client_name == sender_name:
            pass
        else:
            client_conn.send(bytes(new_msg, "utf8"))

def handle_clients(client_conn, client_address, name):
    if isConnectedToOriginalServer == 0:
        while True: #Loop para receber mensagens
            try:
                msg = client_conn.recv(1024).decode("utf8")
                if 'client_message:' in msg: 
                    client_message = msg.split("@")
                    y = client_message[0].split(":")
                    x = client_message[1].split(":")
                    new_msg = name + ": " + x[1]
                    print(new_msg)
                    server_msg = "client_message:" + thisName + "@" + x[0] + ":" + x[1]
                    forward_message(x[1], thisName, y[1], directClients)
                    if isMainServer == 0:
                        s.send(bytes(server_msg, "utf8"))
                elif 'is-conn-alive' in msg:
                    pass
                else:
                    if isMainServer == 0:
                        s.send(bytes(msg, "utf8"))
                    print(msg)
            except Exception:
                pass
                
    elif isConnectedToOriginalServer == 1:
        while True: #Loop para receber mensagens
            try:
                if 'is-conn-alive' in msg:
                    pass
                elif 'client_message:' in msg: 
                    client_message = msg.split("@")
                    y = client_message[0].split(":")
                    x = client_message[1].split(":")
                    new_msg = name + ": " + x[1]
                    print(new_msg)
                    server_msg = "client_message:" + thisName + "@" + x[0] + ":" + x[1]
                    forward_message(x[1], thisName, y[1], directClients)
                    if isMainServer == 0:
                        new_sock.send(bytes(server_msg, "utf8"))
                else:
                    msg = client_conn.recv(1024).decode("utf8")
                    new_sock.send(bytes(msg, "utf8"))
                    send_message_directClients(new_msg, directClients)
                    print(msg)
                
            except Exception:
                pass

def test_server_conn():
    global allClients
    global isConnectedToOriginalServer
    global isMainServer#Se o server for o novo principal, isMainServer = 1
    time.sleep(20)
    while isMainServer == 0:
        if isConnectedToOriginalServer == 0:
            try:
                s.send(bytes("is-conn-alive", "utf8"))
            except:
                print(">>> Server raiz se desconectou.")
                allClientsList = allClients.split("@")
                clientInfo = allClientsList[1].split("-")
                if clientInfo[0] == client_ip and clientInfo[1] == (str(client_port)):
                    isMainServer = 1
                    print(">>> Novo server raiz")
                else:
                    print(">>> Reconectando....")
                    print("** Testando ping...")
                    menorPing = 10000.0
                    ipMenorPing = ""
                    portMenorPing = 0
                    
                    for clients in allClientsList:
                        clientInfo = clients.split("-")
                        ipAtual = clientInfo[0]
                        portAtual = (int(clientInfo[2]))
                        if ipAtual == client_ip and portAtual == client_port_bind:
                            print("Pulando...")
                        else:
                            ping = measure_latency(host = ipAtual, port = portAtual, runs=1, timeout=2.5)
                            
                            if len(ping) == 1:
                                if ping[0] < menorPing:
                                    menorPing = ping[0]
                                    ipMenorPing = ipAtual
                                    portMenorPing = portAtual
                                    
                    print(">> Melhor conexao com: " +(str(portMenorPing))+ " de " + ipMenorPing)
                    new_sock.connect((ipMenorPing, portMenorPing))
                    print(">> Conectado a (" +ipMenorPing + "," + (str(portMenorPing)) + ")")
                    msg = "new-conn@" + thisName + "@" + client_ip + "@" + (str(client_port))
                    new_sock.send(bytes(msg, "utf8"))
                    isConnectedToOriginalServer = 1
        else:
            try:
                new_sock.send(bytes("is-conn-alive", "utf8"))
            except:
                print(">>> Server se desconectou")
        time.sleep(5)

def test_clients_conn():
    global directClients
    global directClientAux
    while True:
        directClients = directClientAux
        for client_conn, client_name in directClients.items():  #Dict que contem infos de conexao
            try:
                client_conn.send(bytes("is-conn-alive", "utf8"))
            except:
                directClientsCopy = copy.copy(directClients)
                del directClientsCopy[client_conn]
                directClientAux = directClientsCopy
                print(">>> Cliente " + client_name + " se desconectou.")
        time.sleep(5)

#Funcao para aceitar a conexao dos clientes
def accept_client_connection():
    global clientsNumber
    while True:  #Loop para aceitar conexoes
        client_conn, client_address = sock.accept()
        msg = client_conn.recv(1024).decode("utf8")
        
        if "new-conn" in msg:  
            clientInfo = msg.split('@')
            directClients[client_conn] = clientInfo[1]
            clientsNumber = clientsNumber + 1
            print(clientInfo[1] + " se conectou. Endereco: " + "(" + clientInfo[2] + "," + (str(clientInfo[3])) + "): ")
            Thread(target=handle_clients, args=(client_conn, client_address, clientInfo[1])).start() #Inicia uma thread para o cliente aceito
        else:
            print(">>> Teste de ping")    


#************************************************* MAIN *************************************************#
if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((client_ip, client_port_bind))
    sock.listen(20) #Socket para aguardar novas conexoes
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((server_ip, server_port)) #Socket para bindar o server do client
    
    new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    print(">>> Endereco do cliente (" + client_ip + ", " + (str(client_port)) + ")")    
    print(">>> Escutando no port : "+ (str(client_port_bind)) + "......")
    
    s.send(bytes("client-connection", "utf8"))
    
    receive_thread = Thread(target=receive_from_server)
    receive_thread.start()

    send_thread = Thread(target=send_server)
    send_thread.start()
    
    client_conn_test = Thread(target=test_clients_conn)
    client_conn_test.start()
    
    server_conn_test = Thread(target=test_server_conn)
    server_conn_test.start()
    
    t = Thread(target=accept_client_connection) #A thread aceita multiplos clientes

    t.start()  # start thread
    t.join()  # thread wait for main thread to exit.