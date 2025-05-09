import zmq
import msgpack
import os
import threading
from datetime import datetime
import time

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")

sub = context.socket(zmq.SUB)
sub.connect("tcp://localhost:5557")

messages = []
allMessages = {} 
followedUsers = []

def ValidateUsername(name):
    while True:
        try:
            username = str(name)
            return username
        except ValueError:
            name = input("O nome não pode ser vazio. Por favor, insira um nome válido: ")

def ValidateMessage(message):
    while True:
        try:
            msg = str(message)
            return msg
        except ValueError:
            message = input("A mensagem não pode ser vazia. Por favor, insira uma mensagem válida: ")

def ValidateIndexUser(followUserInput, usersLength):
    while True:
        try:
            followUser = int(followUserInput)
            if 1 <= followUser <= usersLength:
                return followUser - 1
            else:
                followUserInput = input(f"Valor inválido. Digite um número entre 1 e {usersLength}.")
        except ValueError:
                followUserInput = input(f"Entrada inválida. Por favor, insira um número inteiro entre 1 e {usersLength}.")

def SendToServer(msg):
    msg_p = msgpack.packb(msg)
    socket.send(msg_p)
    reply_p = socket.recv()
    return msgpack.unpackb(reply_p)

def ReceiveNotifications():
    while True:
        try:
            msg = sub.recv_string()
            topic, dados = msg.split(" ", 1)

            partes = dados.split("|")
            campos = dict(p.split(":", 1) for p in partes)

            username = campos.get("Username", "Desconhecido")
            timestamp = campos.get("Timestamp", "Desconhecido")
            message = campos.get("Message", "Sem mensagem")

            if(topic == ("Private" + username)):
                formatedMessage = (f"PRIVADO: {username} ({timestamp}) diz {message}")
            else:
                formatedMessage = (f"{username} ({timestamp}) diz {message}")
            messages.append(formatedMessage)
        except zmq.Again:
            pass

print("==================================================================")
print("                       BEM VINDO A REDE SOCIAL                    ")
print("==================================================================")

usernameInput = input("Digite o seu username para se logar: ")
username = ValidateUsername(usernameInput)

msg = {"Function": "ValidateLoggedUser", "Username": username,}
reply = SendToServer(msg)
usernameIsValid = reply['usernameIsValid'] 

while(usernameIsValid != True):
    usernameInput = input("Ops, este usuario já está logado. Por favor, insira outro username: ")
    username = ValidateUsername(usernameInput)
    msg = {"Function": "ValidateLoggedUser", "Username": username}
    reply = SendToServer(msg)
    usernameIsValid = reply['usernameIsValid'] 

privateTopic = "Private" + username
sub.setsockopt_string(zmq.SUBSCRIBE, privateTopic)

os.system('cls') 
print("------------------------------------------------------------------")
print("                    Usuario logado com sucesso                    ")
print("------------------------------------------------------------------")
time.sleep(1)
os.system('cls')


def Menu():
    while True:
        if messages:
            print("==================================================================")
            print("                           NOTIFICAÇÕES                           ")
            print("==================================================================")
            for msg in messages:
                print(msg)
            messages.clear()

        print("==================================================================")
        print("                               MENU                               ")
        print("==================================================================")
        print("1 - Publicar um texto")
        print("2 - Seguir um usuário")
        print("3 - Enviar uma mensagem privada")
        print("4 - Atualizar notificações")
        print("5 - Ver todas as publicações de um usuário específico")
        print("0 - Sair")
        print("==================================================================")
        userOption = input("Digite a opção desejada: ")

        os.system('cls')
        if userOption == "1":
            messageInput = input("Digite a mensagem a ser publicada: ")
            message = ValidateMessage(messageInput)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            msg = {"Function": "PublishMessage", "Message": message, "Username": username, "Timestamp": timestamp}
            reply = SendToServer(msg)
            time.sleep(1)
            os.system('cls')
        elif(userOption == "2"):
            msg = {"Function": "ShowAllTopics", "Username": username}
            reply = SendToServer(msg)
            allUsers = reply['Topics']
            users = list(set(allUsers) - set(followedUsers))
            print("==================================================================")
            print("                 USUÁRIOS DISPONÍVEIS PARA SEGUIR                 ")
            print("==================================================================")
            for index, user in enumerate(users, start=1):
                print(f"{index} - {user}")
            print("==================================================================")
            followUserInput = input("Digite o número do usuário que você deseja seguir: ")
            followUser = ValidateIndexUser(followUserInput, len(users))
            topic = users[followUser]
            followedUsers.append(topic)
            sub.setsockopt_string(zmq.SUBSCRIBE, topic)
            print( "------------------------------------------------------------------")
            print(f"               Usuario {topic} seguido com sucesso                ")
            print( "------------------------------------------------------------------")
            time.sleep(1)
            os.system('cls')
        elif userOption == "3":
            print("==================================================================")
            print("                           CHAT PRIVADO                           ")
            print("==================================================================")
            msg = {"Function": "ShowAllTopics", "Username": username}
            reply = SendToServer(msg)
            allUsers = reply['Topics']
            for index, user in enumerate(allUsers, start=1):
                print(f"{index} - {user}")
            print("==================================================================")
            beginChatWithInput = input("Digite o número do usuário que você deseja abrir o chat privado: ")
            beginChatWith = ValidateIndexUser(beginChatWithInput, len(allUsers))
            usernameChat = allUsers[beginChatWith]
            os.system('cls')
            print("==================================================================")
            print("                           CHAT PRIVADO                           ")
            print("==================================================================")
            print(f"CONVERSANDO COM {usernameChat}")
            print("==================================================================")
            msg = {"Function": "GetPrivateMessages", "Username": username, "ChatWith": usernameChat}
            reply = SendToServer(msg)
            messagesFound = reply['StatusFoundMessage']
            if(messagesFound == "Found"):
                chatMessages = reply['Messages']
                sortedMessages = sorted(chatMessages, key=lambda msg: datetime.strptime(msg["Timestamp"], '%Y-%m-%d %H:%M:%S'))
                for message in sortedMessages:
                    print(f"{message['Username']}: {message['Message']}")
                    print(f"{message['Timestamp']}")
                    print( "------------------------------------------------------------------")
            messageInput = input(f"Digite a mensagem a ser enviada para {usernameChat}: ")
            message = ValidateMessage(messageInput)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            msg = {"Function": "SendPrivateMessage", "Message": message, "From": username, "Timestamp": timestamp, "To": usernameChat}
            reply = SendToServer(msg)
            time.sleep(1)
            os.system('cls')
        elif userOption == "6":
            os.system('cls')
        elif userOption == "0":
            print("Saindo do sistema...")
            break
        else:
            os.system('cls')

t = threading.Thread(target=ReceiveNotifications, daemon=True)
t.start()

Menu()