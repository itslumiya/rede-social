import zmq
import msgpack
import os
import threading
from datetime import datetime, timedelta
import time

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")

sub = context.socket(zmq.SUB)
sub.connect("tcp://localhost:5557")

messages = []
allMessages = {} 
followedUsers = []
timestampClient = datetime.now()

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
        global timestampClient
        global username

        try:
            partsMsg = sub.recv_multipart()
            
            if(len(partsMsg) == 2):
                topic = partsMsg[0].decode("utf-8")
                dados = partsMsg[1].decode("utf-8")

                campos = dict(item.split(":", 1) for item in dados.split("|"))
                messageFrom = campos.get("Username", "Desconhecido")
                timestamp = datetime.strptime(campos.get("Timestamp", "Desconhecido"), "%d/%m/%Y %H:%M:%S")
                message = campos.get("Message", "Sem mensagem")

                if(timestampClient < timestamp):
                    msg = {"Function": "GetCoordinatorTime"}
                    reply = SendToServer(msg)
                    timestampServer = datetime.strptime(reply["ServerClock"], "%d/%m/%Y %H:%M:%S")
                    timestampClient = timestampServer

                stringTimestamp = timestamp.strftime("%d/%m/%Y %H:%M:%S")

                formatedMessage = f"{messageFrom} ({stringTimestamp}) diz {message}"
                messages.append(formatedMessage)
                RecordLog(f"[Notificação] {messageFrom} ({stringTimestamp}) - {message}", timestampClient.strftime("%d/%m/%Y %H:%M:%S"))
            else:
                topic, dados = partsMsg[0].decode("utf-8").split(":", 1)
                partes = dados.split("|")
                campos = dict((k.strip(), v.strip()) for k, v in (p.split(":", 1) for p in partes))
                messageFrom = campos.get("Username", "Desconhecido")
                timestamp = datetime.strptime(campos.get("Timestamp", "Desconhecido"), "%d/%m/%Y %H:%M:%S")
                message = campos.get("Message", "Sem mensagem")

                if(timestampClient < timestamp):
                    timestampClientBefore = timestampClient.strftime("%d/%m/%Y %H:%M:%S")
                    msg = {"Function": "GetCoordinatorTime"}
                    reply = SendToServer(msg)
                    timestampServer = datetime.strptime(reply["ServerClock"], "%d/%m/%Y %H:%M:%S")
                    timestampClient = timestampServer
                    timestampClientAfter = timestampClient.strftime("%d/%m/%Y %H:%M:%S")
                    RecordLog(f"[Ajuste de Clock] Clock do cliente sincronizado com o relógio do servidor (Tempo antes: {timestampClientBefore} / Tempo depois: {timestampClientAfter})", timestampClient.strftime("%d/%m/%Y %H:%M:%S"))

                stringTimestamp = timestamp.strftime("%d/%m/%Y %H:%M:%S")

                if(topic == "Private" + username):
                    formatedMessage = f"PRIVADO: {messageFrom} ({stringTimestamp}) diz {message}"
                    messages.append(formatedMessage)
                    RecordLog(f"[Recebeu Mensagem Privada] {messageFrom} ({stringTimestamp}) - {message}", timestampClient.strftime("%d/%m/%Y %H:%M:%S"))
                else:
                    formatedMessage = f"{messageFrom} ({stringTimestamp}) diz {message}"
                    messages.append(formatedMessage)
                    RecordLog(f"[Recebeu Notificação] {messageFrom} ({stringTimestamp}) - {message}", timestampClient.strftime("%d/%m/%Y %H:%M:%S"))
        except zmq.Again:
            pass

def Delay():
    global timestampClient
    timestampClientBefore = timestampClient.strftime('%d-%m-%Y %H:%M:%S')
    timestampClient = timestampClient - timedelta(seconds=1)
    timestampClientAfter = timestampClient.strftime('%d-%m-%Y %H:%M:%S')
    RecordLog(f"[Ajuste no Clock] - Atrasado em 1 segundo (Tempo antes: {timestampClientBefore} / Tempo depois: {timestampClientAfter})", timestampClient.strftime("%d/%m/%Y %H:%M:%S"))

def Advance():
    global timestampClient
    timestampClientBefore = timestampClient.strftime('%d-%m-%Y %H:%M:%S')
    timestampClient = timestampClient + timedelta(seconds=1)
    timestampClientAfter = timestampClient.strftime('%d-%m-%Y %H:%M:%S')
    RecordLog(f"[Ajuste no Clock] - Adiantado em 1 segundo (Tempo antes: {timestampClientBefore} / Tempo depois: {timestampClientAfter})", timestampClient.strftime("%d/%m/%Y %H:%M:%S"))

def SynchronizeWithServer():
    global timestampClient
    timestampClientBefore = timestampClient.strftime('%d-%m-%Y %H:%M:%S')
    msg = {"Function": "GetCoordinatorTime"}
    reply = SendToServer(msg)
    timestampServer = datetime.strptime(reply["ServerClock"], "%d/%m/%Y %H:%M:%S")
    timestampClient = timestampServer
    timestampClientAfter = timestampClient.strftime('%d-%m-%Y %H:%M:%S')
    RecordLog(f"[Ajuste no Clock] - Sincronizado com o Servidor (Tempo antes: {timestampClientBefore} / Tempo depois: {timestampClientAfter})", timestampClient.strftime("%d/%m/%Y %H:%M:%S"))

def RecordLog(message, timestamp):
    global username
    os.makedirs("Logs/Clients", exist_ok=True)

    dateToday = datetime.today().strftime('%d-%m-%Y')
    path = f"Logs/Clients/client-{username}-log-{dateToday}.txt"
    mode = "a" if os.path.exists(path) else "w"

    with open(path, mode, encoding="utf-8") as f:
        f.write(f"{timestamp} => {message}" + "\n")

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

RecordLog(f"[Login] Usuário {username} logado com sucesso", timestampClient.strftime("%d/%m/%Y %H:%M:%S"))

def Menu():
    while True:
        global timestampClient
        stringTimestampClient = timestampClient.strftime("%d/%m/%Y %H:%M:%S")
        
        print("==================================================================")
        print(f"                                     Horário: {stringTimestampClient}")
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
        print("4 - Visualizar chat privado")
        print("5 - Ver todas as publicações de um usuário específico")
        print("6 - Atrasar 1 segundo")
        print("7 - Adiantar 1 segundo")
        print("8 - Sincronizar com Servidor")
        print("9 - Parar de seguir um usuário")
        print("0 - Sair")
        print("==================================================================")
        userOption = input("Digite a opção desejada: ")

        os.system('cls')
        if userOption == "1":
            print("==================================================================")
            print("                         PUBLICAR MENSAGEM                        ")
            print("==================================================================")
            messageInput = input("Digite a mensagem a ser publicada (para cancelar digite Enter): ")
            if messageInput.strip():
                message = ValidateMessage(messageInput)
                msg = {"Function": "PublishMessage", "Message": message, "Username": username, "Timestamp": timestampClient.strftime("%d/%m/%Y %H:%M:%S")}
                reply = SendToServer(msg)
                os.system('cls')
                print("==================================================================")
                print("                  MENSAGEM PUBLICADA COM SUCESSO                  ")
                print("==================================================================")
                timestampClient = timestampClient + timedelta(seconds=1)
                RecordLog(f"[Publicação] {username} - {message}", timestampClient.strftime("%d/%m/%Y %H:%M:%S"))
            else:
                os.system('cls')
                print("==================================================================")
                print("                       VOLTANDO PARA O MENU                       ")
                print("==================================================================")
            time.sleep(1)
            os.system('cls')
        elif(userOption == "2"):
            msg = {"Function": "ShowAllTopics", "Username": username}
            reply = SendToServer(msg)
            allUsers = reply['Topics']
            users = list(set(allUsers) - set(followedUsers))
            if(len(users) > 0):
                print("==================================================================")
                print("                 USUÁRIOS DISPONÍVEIS PARA SEGUIR                 ")
                print("==================================================================")
                for index, user in enumerate(users, start=1):
                    print(f"{index} - {user}")
                print("==================================================================")
                followUserInput = input("Digite o número do usuário que você deseja seguir (para cancelar digite Enter): ")
                if followUserInput.strip():
                    followUser = ValidateIndexUser(followUserInput, len(users))
                    userToFollow = users[followUser]
                    followedUsers.append(userToFollow)
                    sub.setsockopt_string(zmq.SUBSCRIBE, userToFollow)
                    os.system('cls')
                    print( "------------------------------------------------------------------")
                    print(f"                   USUARIO SEGUIDO COM SUCESSO                    ")
                    print( "------------------------------------------------------------------")
                    timestampClient = timestampClient + timedelta(seconds=1)
                    RecordLog(f"[Follow] {username} seguiu {userToFollow}", timestampClient.strftime("%d/%m/%Y %H:%M:%S"))
                else:
                    os.system('cls')
                    print("==================================================================")
                    print("                       VOLTANDO PARA O MENU                       ")
                    print("==================================================================")
            else:
                os.system('cls')
                print("==================================================================")
                print("             NÃO HÁ USUÁRIOS DISPONÍVEIS PARA SEGUIR              ")
                print("==================================================================")
            time.sleep(1)
            os.system('cls')
        elif userOption == "3":
            print("==================================================================")
            print("                           CHAT PRIVADO                           ")
            print("==================================================================")
            msg = {"Function": "ShowAllTopics", "Username": username}
            reply = SendToServer(msg)
            allUsers = reply['Topics']
            allUsers.remove("Fruta")
            allUsers.remove("ShortNSweet")
            allUsers.remove("ProgrammingLanguages")
            if(len(allUsers) > 0):
                for index, user in enumerate(allUsers, start=1):
                    print(f"{index} - {user}")
                print("==================================================================")
                beginChatWithInput = input("Digite o número do usuário que você deseja abrir o chat privado (para cancelar digite Enter): ")
                if beginChatWithInput.strip():
                    beginChatWith = ValidateIndexUser(beginChatWithInput, len(allUsers))
                    usernameChat = allUsers[beginChatWith]
                    os.system('cls')
                    print("==================================================================")
                    print("                    CONVERSAR PELO CHAT PRIVADO                   ")
                    print("==================================================================")
                    print(f"CONVERSANDO COM {usernameChat}")
                    print("==================================================================")
                    msg = {"Function": "GetPrivateMessages", "Username": username, "ChatWith": usernameChat}
                    reply = SendToServer(msg)
                    messagesFound = reply['StatusFoundMessage']
                    if(messagesFound == "Found"):
                        chatMessages = reply['Messages']
                        sortedMessages = sorted(chatMessages, key=lambda msg: datetime.strptime(msg["Timestamp"], "%d/%m/%Y %H:%M:%S"))
                        for message in sortedMessages:
                            print(f"{message['Username']}: {message['Message']}")
                            print(f"{message['Timestamp']}")
                            print( "------------------------------------------------------------------")
                    print("==================================================================")
                    messageInput = input(f"Digite a mensagem a ser enviada para {usernameChat} (para cancelar digite Enter): ")
                    if messageInput.strip():
                        message = ValidateMessage(messageInput)
                        timestamp = timestampClient
                        msg = {"Function": "SendPrivateMessage", "Message": message, "From": username, "Timestamp": timestamp.strftime("%d/%m/%Y %H:%M:%S"), "To": usernameChat}
                        reply = SendToServer(msg)
                        os.system('cls')
                        print("------------------------------------------------------------------")
                        print("               MENSAGEM PRIVADA ENVIADA COM SUCESSO               ")
                        print("------------------------------------------------------------------")
                        timestampClient = timestampClient + timedelta(seconds=1)
                        RecordLog(f"[Enviou Mensagem Privada] {username} para {usernameChat} - {message}", timestampClient.strftime("%d/%m/%Y %H:%M:%S"))
                    else:
                        os.system('cls')
                        print("==================================================================")
                        print("                       VOLTANDO PARA O MENU                       ")
                        print("==================================================================")
                else:
                    os.system('cls')
                    print("==================================================================")
                    print("                       VOLTANDO PARA O MENU                       ")
                    print("==================================================================")
            else:
                os.system('cls')
                print("==================================================================")
                print("      NÃO HÁ USUÁRIOS DISPONÍVEIS PARA ABRIR UM CHAT PRIVADO      ")
                print("==================================================================")
            time.sleep(1)
            os.system('cls')
        elif userOption == "4":
            print("==================================================================")
            print("                      VISUALIZAR CHAT PRIVADO                     ")
            print("==================================================================")
            msg = {"Function": "ShowAllTopics", "Username": username}
            reply = SendToServer(msg)
            allUsers = reply['Topics']
            allUsers.remove("Fruta")
            allUsers.remove("ShortNSweet")
            allUsers.remove("ProgrammingLanguages")
            if(len(allUsers) > 0):
                for index, user in enumerate(allUsers, start=1):
                    print(f"{index} - {user}")
                print("==================================================================")
                beginChatWithInput = input("Digite o número do usuário que você deseja visualizar o chat privado (para cancelar digite Enter): ")
                if beginChatWithInput.strip():
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
                        sortedMessages = sorted(chatMessages, key=lambda msg: datetime.strptime(msg["Timestamp"], "%d/%m/%Y %H:%M:%S"))
                        for message in sortedMessages:
                            print(f"{message['Username']}: {message['Message']}")
                            print(f"{message['Timestamp']}")
                            print( "------------------------------------------------------------------")
                    else:
                        print("Nenhuma mensagem encontrada!")
                    print("==================================================================")
                    input("Pressione ENTER para voltar para o menu...")
                    timestampClient = timestampClient + timedelta(seconds=1)
                else:
                    os.system('cls')
                    print("==================================================================")
                    print("                       VOLTANDO PARA O MENU                       ")
                    print("==================================================================")
            else:
                os.system('cls')
                print("==================================================================")
                print("      NÃO HÁ USUÁRIOS DISPONÍVEIS PARA ABRIR UM CHAT PRIVADO      ")
                print("==================================================================")
            time.sleep(1)
            os.system('cls')
        elif userOption == "5":
            print("==================================================================")
            print("              VER TODAS AS PUBLICAÇÕES DE UM USUÁRIO              ")
            print("==================================================================")
            msg = {"Function": "ShowAllTopics", "Username": username}
            reply = SendToServer(msg)
            allUsers = reply['Topics']
            if(len(allUsers) > 0):
                for index, user in enumerate(allUsers, start=1):
                    print(f"{index} - {user}")
                print("==================================================================")
                showAllPostsInput = input("Digite o número do usuário que você deseja ver todas as publicações (para cancelar digite Enter): ")
                if showAllPostsInput.strip():
                    showAllPosts = ValidateIndexUser(showAllPostsInput, len(allUsers))
                    usernamePost = allUsers[showAllPosts]
                    os.system('cls')
                    print("==================================================================")
                    print("              VER TODAS AS PUBLICAÇÕES DE UM USUÁRIO              ")
                    print("==================================================================")
                    print(f"VISUALIZANDO POSTS DE {usernamePost.upper()}")
                    print("==================================================================")
                    msg = {"Function": "GetAllPosts", "Username": usernamePost}
                    reply = SendToServer(msg)
                    postsFound = reply['StatusFoundPosts']
                    if(postsFound == "Found"):
                        posts = reply['Posts']
                        for post in posts:
                            print(post)
                            print( "------------------------------------------------------------------")
                    else:
                        print("Nenhuma mensagem encontrada!")
                    print("==================================================================")
                    input("Pressione ENTER para voltar para o menu...")
                else:
                    os.system('cls')
                    print("==================================================================")
                    print("                       VOLTANDO PARA O MENU                       ")
                    print("==================================================================")
            else:
                os.system('cls')
                print("==================================================================")
                print("       NÃO HÁ USUÁRIOS DISPONÍVEIS PARA VISUALIZAR OS POSTS       ")
                print("==================================================================")
            time.sleep(1)
            os.system('cls')
            timestampClient = timestampClient + timedelta(seconds=1)
        elif userOption == "6":
            Delay()
            os.system('cls')
        elif userOption == "7":
            Advance()
            os.system('cls')
        elif userOption == "8":
            SynchronizeWithServer()
            os.system('cls')
        elif userOption == "9":
            if(len(followedUsers) > 0):
                print("==================================================================")
                print("                      USUÁRIOS QUE VOCÊ SEGUE                     ")
                print("==================================================================")
                for index, user in enumerate(followedUsers, start=1):
                    print(f"{index} - {user}")
                print("==================================================================")
                unfollowUserInput = input("Digite o número do usuário que você deseja parar de seguir (para cancelar digite Enter): ")
                if unfollowUserInput.strip():
                    unfollowUser = ValidateIndexUser(unfollowUserInput, len(followedUsers))
                    userToUnfollow = followedUsers[unfollowUser]
                    followedUsers.remove(userToUnfollow)
                    sub.setsockopt_string(zmq.UNSUBSCRIBE, userToUnfollow)
                    os.system('cls')
                    print( "------------------------------------------------------------------")
                    print(f"               USUÁRIO DEIXADO DE SEGUIR COM SUCESSO              ")
                    print( "------------------------------------------------------------------")
                    RecordLog(f"[Unollow] {username} parou de seguir {userToUnfollow}", timestampClient.strftime("%d/%m/%Y %H:%M:%S"))
                    timestampClient = timestampClient + timedelta(seconds=1)
                else:
                    os.system('cls')
                    print("==================================================================")
                    print("                       VOLTANDO PARA O MENU                       ")
                    print("==================================================================")
            else:
                os.system('cls')
                print("==================================================================")
                print("         NÃO HÁ USUÁRIOS DISPONÍVEIS PARA PARAR DE SEGUIR         ")
                print("==================================================================")
            time.sleep(1)
            os.system('cls')
        elif userOption == "0":
            print("Saindo do sistema...")
            break
        else:
            os.system('cls')

t = threading.Thread(target=ReceiveNotifications, daemon=True)
t.start()

Menu()