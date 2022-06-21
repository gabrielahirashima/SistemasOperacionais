import socket
from threading import Thread
from turtle import update
from unicodedata import name
from tcp_latency import measure_latency
import time
import copy
import sys

#**********************************************  VARIAVEIS  *********************************************#

client_ip = "191.52.64.154"
client_port = 8900
client_port_bind = client_port + 1

server_ip = "191.52.64.154"
server_port = 8091

Clients = {}
directClients = {}
directClientAux = {}
serverClients = {}
allClients = "" #String para armazenar todas as infos dos clients
clientsNumber = 0
isConnectedToOriginalServer = 0 #Variavel para verificar se esta conectado no server original, se 0, o server original ainda eh o principal se 1, outro cliente eh o pricipal
thisName = ""
isMainServer = 0 #Identifica se virou o main server
isTempServer = 0 #Identifica um main server temporario (Para receber votos)

mainServerReconn = 0 #Identifica quantas reconexoes ao server principal houveram
serverReconn = 0 #Identifica quantas reconexoes ao server do cliente houveram
electionStart = 0 #Flag para identificar se a eleicao esta em andamento ou nao
totalVotos = 0
totalClientsElection = 0
electionEnd = 0

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((client_ip, client_port_bind))
sock.listen(30) #Socket para aguardar novas conexoes

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((server_ip, server_port)) #Socket para bindar o server do client

new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
new_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

#*********************************************** CLIENT-PART ***********************************************#

#Funcao para aceitar a conexao dos clientes
def accept_client_connection():
    global isTempServer
    global totalClientsElection
    global serverClients
    while True:  #Loop para aceitar conexoes
        client_conn, client_address = sock.accept()
        msg = client_conn.recv(1024).decode("utf8")
        
        if isMainServer == 0:
            if "new-conn" in msg:  
                clientInfo = msg.split('@')
                directClients[client_conn] = clientInfo[1]
                print(clientInfo[1] + " se conectou. Endereco: " + "(" + clientInfo[2] + "," + (str(clientInfo[3])) + "): ")
                Thread(target=handle_clients, args=(client_conn, client_address, clientInfo[1])).start() #Inicia uma thread para o cliente aceito
            elif isTempServer == 1:
                if 'voto-' in msg:
                    clientInfo = msg.split("@")
                    totalClientsElection = totalClientsElection + 1
                    client_info = clientInfo[0].split("-")
                    serverClients[client_conn] = client_info[1]
                    Thread(target=handle_election, args=(msg,)).start() #Inicia uma thread para o cliente aceito
        elif isMainServer == 1:
            if "client-connection" in msg:
                client_conn.send(bytes("Digite seu nome para continuar:", "utf8"))
                print(client_address, " se conectou")
                Thread(target=handle_server_clients, args=(client_conn, client_address)).start() #Inicia uma thread para o cliente aceito
            elif "new-conn" in msg:  
                clientInfo = msg.split('@')
                directClients[client_conn] = clientInfo[1]
                print(clientInfo[1] + " se conectou. Endereco: " + "(" + clientInfo[2] + "," + (str(clientInfo[3])) + "): ")
                Thread(target=handle_clients, args=(client_conn, client_address, clientInfo[1])).start() #Inicia uma thread para o cliente aceito
        else:
            print(">>> Teste de ping")    

#Funcao para gerenciar cada cliente conectado
def handle_clients(client_conn, client_address, name):
    global s
    global new_sock
    global allClients
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
                    forward_message(x[1], y[1], x[0], directClients)
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
                msg = client_conn.recv(1024).decode("utf8")
                if 'is-conn-alive' in msg:
                    pass
                elif 'client_message:' in msg: 
                    client_message = msg.split("@")
                    y = client_message[0].split(":")
                    x = client_message[1].split(":")
                    new_msg = name + ": " + x[1]
                    print(new_msg)
                    server_msg = "client_message:" + thisName + "@" + x[0] + ":" + x[1]
                    forward_message(x[1], y[1], x[0], directClients)
                    if isMainServer == 0:
                        new_sock.send(bytes(server_msg, "utf8"))
                else:
                    msg = client_conn.recv(1024).decode("utf8")
                    if isMainServer == 0 or isTempServer == 0:
                        new_sock.send(bytes(msg, "utf8"))
                    send_message_directClients(new_msg, directClients)
                    print(msg)
                
            except Exception:
                pass


#Funcao para lidar com clientes - recebe o nome do cliente e dados da conexao
def handle_server_clients(conn, client_address):
    global allClients
    client_ip = ""
    client_port = 0
    client_port_bind = 0
    
    name = conn.recv(1024).decode("utf8")

    welcome = f"Bem-vindo(a) {name} :" #Mensagem de boas vindas 
    conn.send(bytes(welcome, "utf8"))
    
    msg = name + " se juntou ao chat" #Mensagem para avisar outros clientes
    send_message_directClients(msg, directClients) #Avisa todos os clientes
    
    serverClients[conn] = name #Adiciona cliente ao dicionario
    
    conn.send(bytes("testar-conexao", "utf8"))

    while True: #Loop para receber mensagens do cliente e transmiti-las
        try:
            msg = conn.recv(1024).decode("utf8")
            if 'clients-list' in msg: #Envia a lista de enderecos para o cliente
                print("Enviando lista de enderecos")
                conn.send(bytes(allClients, "utf8"))
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
                send_directClients(msg, name, directClients)
        except:
            serverClients.pop(conn)
            if name in directClients.values():
                directClients.pop(conn)
            print(allClients)
            delete_element_clientsListAddresses(client_ip, client_port)
            sys.exit()



#Funcao que faz a conexao servidor-clientes
def connect(clientsList):
    global isConnectedToOriginalServer
    global thisName
    global new_sock
    global serverReconn
    
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
            if serverReconn > 0:
                print("\nFechando conexao anterior... Reabrindo conexao.....")
                new_sock.close()
                new_sock = "new_sock" + (str(serverReconn))
                new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            new_sock.connect((ipMenorPing, portMenorPing))
            print(">> Conectado a (" +ipMenorPing + "," + (str(portMenorPing)) + ")")
            msg = "new-conn@" + thisName + "@" + client_ip + "@" + (str(client_port))
            new_sock.send(bytes(msg, "utf8"))
            isConnectedToOriginalServer = 1
            serverReconn = serverReconn + 1

#Funcao que recebe as mensagens do servidor
def receive_from_server():
    global allClients
    global clientsList
    global directClients
    global new_sock
    global s
    global clientsNumber
    while isMainServer == 0: #Loop para receber mensagens
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
                    count_list_elements()
                elif 'start-election@' in msg:
                    print(">>> Server principal desconectado... Iniciando eleicao de um novo server principal")
                    election(msg)
                elif 'new-server@' in msg:
                    msg = msg.split("@")
                    serverInfo = msg[1].split("-")
                    print(">>> Novo server principal eleito. (" + serverInfo[0] + ", " + (str(serverInfo[1])) + ")")
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
                elif 'start-election@' in msg:
                    print(">>> Server principal desconectado... Iniciando eleicao de um novo server principal")
                    election(msg)
                elif 'new-server@' in msg:
                    msg = msg.split("@")
                    serverInfo = msg[1].split("-")
                    print(">>> Novo server principal eleito. (" + serverInfo[0] + ", " + (str(serverInfo[1])) + ")")
                else:
                    send_message_directClients(msg, directClients)
                    print(msg)
            
            except Exception:
                pass
            
#*********************************************** MESSAGE-SENDING ***********************************************#

#Funcao que envia mensagem do cliente atual para os clientes diretamente conectados a ele
def send_directClients(msg, name, directClients):
    new_msg = name + ": " + msg
    directClients = directClientAux
    for client_conn, client_name in directClients.items():  #Dict que contem infos de conexao
        if client_name == name:
            pass
        else:
            client_conn.send(bytes(new_msg, "utf8"))

#Funcao que manda mensagem para os clientes incluidos na lista
def send_message_directClients(msg, directClients):
    for client in directClients:  #Dict que contem infos de conexao
        client.send(bytes(msg, "utf8"))

#Funcao que manda mensagem formatada para os clientes da lista
def forward_message(msg, sender_name, message_sender_name, directClients):
    new_msg = message_sender_name + ":" + msg
    for client_conn, client_name in directClients.items():  #Dict que contem infos de conexao
        if client_name == sender_name:
            pass
        else:
            client_conn.send(bytes(new_msg, "utf8"))

#Funcao em loop que aguarda input do usuario e os envia em formato de mensagem
def send_server():
    global thisName
    global directClients
    global directClientAux
    global new_sock
    global isTempServer
    while True:
        msg = input("") #Aguarda input
        if isMainServer == 0:
            if isTempServer == 1:
                send_directClients(msg, thisName, directClients)
                
            elif isConnectedToOriginalServer == 0: 
                s.send(bytes(msg, "utf8")) #Envia mensagem
                send_directClients(msg, thisName, directClients)
                    
            elif isConnectedToOriginalServer == 1:
                new_msg = "client_message:"+ thisName + "@" + thisName + ":" + msg
                new_sock.send(bytes(new_msg, "utf8")) #Envia mensagem
                send_directClients(msg, thisName, directClients)
        else:
            send_directClients(msg, thisName, directClients)

            
#*********************************************** LISTS MANAGEMENT ***********************************************#

#Deleta elemento da lista de enderecos de clientes por IP e PORT
def delete_element_clientsListAddresses(ip, port):
    global allClients
    auxList = "0" #Inicializa nova string com lista de clientes.
    List = allClients.split("@")
    
    for x in List:
        clientInfo = x.split("-")
        ipAtual = clientInfo[0]
        portAtual = (int(clientInfo[1]))
        portBindAtual = clientInfo[2]
        if ip == ipAtual and port == portAtual:
            print("Cliente (" + ip + "," + (str(portAtual)) + ") se desconectou")
        else:
            if auxList == "0":
                auxList = ipAtual + "-" + (str(portAtual)) + "-" + portBindAtual + "-" + clientInfo[3]
            else: 
                auxList = auxList + "@" + ipAtual + "-" + (str(portAtual)) + "-" + portBindAtual + "-" + clientInfo[3]
    
    allClients = auxList
    count_list_elements()
    msg = "updated-client-list@" + allClients
    send_message_directClients(msg, directClients)
    
def count_list_elements():
    global allClients
    global clientsNumber
    List = allClients.split("@")
    
    clientsNumber = len(List)

def add_address(client_info, name):
    global allClients
    new_address = "@" + client_info[1] + "-" + (str(client_info[2])) + "-" + (str(client_info[3])) + "-" + name
    allClients = allClients + new_address
    msg = "updated-client-list@" + allClients
    send_message_directClients(msg, directClients)
    
#*********************************************** CONNECTION TESTS ***********************************************#

def test_server_conn():
    global allClients
    global isConnectedToOriginalServer
    global isMainServer#Se o server for o novo principal, isMainServer = 1
    global new_sock
    global electionStart
    global isTempServer
    global serverReconn
    global server_ip
    global server_port
    time.sleep(20)
    while isMainServer == 0:
        if isConnectedToOriginalServer == 0:
            if isTempServer == 1:
                if electionStart == 0:
                    print("Aguarde um momento...")
                    time.sleep(20)
                    delete_element_clientsListAddresses(server_ip, server_port)
                    print("Iniciando eleicao...")
                    msg = "start-election@" + client_ip + "-" + (str(client_port_bind))
                    send_message_directClients(msg, directClients)
                    electionStart = 1
                else:
                    pass
            else:
                try:
                    s.send(bytes("is-conn-alive", "utf8"))
                except:
                    print(">>> Server raiz se desconectou.")
                    allClientsList = allClients.split("@")
                    clientInfo = allClientsList[1].split("-")
                    if clientInfo[0] == client_ip and clientInfo[1] == (str(client_port)):
                        isTempServer = 1
                        print(">>> Novo server temporario")
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
                        serverReconn = serverReconn + 1
                        isConnectedToOriginalServer = 1
        else:
            if isTempServer == 1 :
                if electionStart == 0:
                    print("Aguarde um momento...")
                    time.sleep(20)
                    temp_port = server_port - 1
                    delete_element_clientsListAddresses(server_ip, temp_port)
                    print("Iniciando eleicao...")
                    msg = "start-election@" + client_ip + "-" + (str(client_port_bind))
                    send_message_directClients(msg, directClients)
                    electionStart = 1
                else:
                    pass
            else:
                try:
                    new_sock.send(bytes("is-conn-alive", "utf8"))
                except:
                    print(">>> Server se desconectou")
                    allClientsList = allClients.split("@")
                    clientInfo = allClientsList[1].split("-")
                    if clientInfo[0] == client_ip and clientInfo[1] == (str(client_port)):
                        isTempServer = 1
                        print(">>> Novo server temporario")
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
                        if serverReconn > 0:
                            new_sock.close()
                            new_sock = "new_sock" + (str(serverReconn))
                            new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            new_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                            new_sock.connect((ipMenorPing, portMenorPing))
                        print(">> Conectado a (" +ipMenorPing + "," + (str(portMenorPing)) + ")")
                        msg = "new-conn@" + thisName + "@" + client_ip + "@" + (str(client_port))
                        new_sock.send(bytes(msg, "utf8"))
                        serverReconn = serverReconn + 1
                        isConnectedToOriginalServer = 1
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

#*********************************************** ELECTION PROCEDURE ***********************************************#

def election(msg): #"start-election@" + client_ip + "-" + (str(client_port_bind))
    global s
    global mainServerReconn
    global server_ip
    global server_port
    global allClients
    
    msg = msg.split("@")
    temp_server = msg[1].split("-")
    server_ip = temp_server[0]
    server_port = (int(temp_server[1]))
    
    s.close()
    
    s = "s" + (str(mainServerReconn))
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.connect((server_ip, server_port)) #Socket para bindar o server do client
    
    allClientsList = allClients.split("@")
    clientInfo = allClientsList[0].split("-")
    
    print("\nVoto em: (" + clientInfo[0] + "-" + (str(clientInfo[2]) + ")"))
    
    msg = "voto-" + thisName + "@" + clientInfo[0] + "-" + (str(clientInfo[2]))
    s.send(bytes(msg, "utf8"))
    
    mainServerReconn = mainServerReconn + 1

def handle_election(msg):
    
    global totalVotos
    global totalClientsElection
    global electionEnd
    global clientsNumber
    
    msg = msg.split("@")
    clientInfo = msg[0].split("-")
    electionResult = msg[1].split("-")
    
    print("Voto de " + clientInfo[1] + ": Ip:" + electionResult[0] + "- Port:" + electionResult[1])
    
    if electionResult[0] == client_ip and (int(electionResult[1])) == client_port_bind:
        totalVotos = totalVotos + 1
        print(">>> Tudo certo ate aqui - Votos contados: "+ (str(totalVotos)) + " Votos esperados: " + (str(clientsNumber - 1)))
    else:
        print("Voto de " +clientInfo[1] + " diferente do esperado :(")
        electionEnd = 1
        
    if totalVotos == (clientsNumber - 1):
        electionEnd = 1
    

def election_thread():
    global isTempServer
    global isMainServer
    global clientsNumber
    global totalVotos
    global serverClients
    global electionEnd
    while isMainServer == 0:
        if electionEnd == 1:
            if totalVotos == (clientsNumber - 1):
                print(">>> Eleicao concluida com sucesso.")
                print(">>> Novo server principal - IP:" + client_ip + " PORT:" + (str(client_port_bind)))
                isTempServer = 0
                isMainServer = 1
                msg = "new-server@" + client_ip + "-" + (str(client_port_bind))
                send_message_directClients(msg, directClients)
            else: 
                print(">>> Falha na eleicao.")
        time.sleep(5)


#************************************************* MAIN *************************************************#
if __name__ == "__main__":
    try:
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
        
        election_test = Thread(target=election_thread)
        election_test.start()
        
        t = Thread(target=accept_client_connection) #A thread aceita multiplos clientes

        t.start()  # start thread
        t.join()  # thread wait for main thread to exit.
        
    except:
        print("Encerrando programa")
        sock.close()
        s.close()
        new_sock.close()