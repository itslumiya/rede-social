import zmq
import msgpack
from datetime import datetime
import redis
import json
import os
import signal
import atexit
import sys

# ---------------------------
# Função para remover servidor
# ---------------------------

def cleanup():
    global idServer
    print(f"Removendo servidor {idServer} da lista de ativos...")
    r.srem('active_servers', str(idServer))
    print("Servidor removido. Saindo...")
    RecordLog(f"[Desconectando Servidor] Servidor {idServer} desconectado", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    
atexit.register(cleanup)

def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ---------------------------
# Funções Redis para dados compartilhados
# ---------------------------

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

def add_logged_user(username):
    if not r.sismember('logged_users', username):
        r.sadd('logged_users', username)
        return True
    return False

def get_logged_users(exclude_username=None):
    users = list(r.smembers('logged_users'))
    if exclude_username and exclude_username in users:
        users.remove(exclude_username)
    return users

def save_post(username, message):
    key = f"posts:{username}"
    r.rpush(key, message)

def get_posts(username):
    key = f"posts:{username}"
    return r.lrange(key, 0, -1)

def save_private_message(sender, receiver, message_obj):
    key_from = f"private:{sender}:{receiver}"
    key_to = f"private:{receiver}:{sender}"
    msg_str = json.dumps(message_obj)
    r.rpush(key_from, msg_str)
    r.rpush(key_to, msg_str)

def get_private_messages(user, chat_with):
    key = f"private:{user}:{chat_with}"
    return [json.loads(m) for m in r.lrange(key, 0, -1)]

# ---------------------------
# Funções Redis para dados compartilhados
# ---------------------------

def add_active_server(server_id):
    if not r.sismember('active_servers', server_id):
        r.sadd('active_servers', server_id)
        return True
    return False

def get_active_servers():
    servers_bytes = r.smembers('active_servers')
    # Converter de bytes para string
    servers = [server.decode('utf-8') for server in servers_bytes]
    return servers

# ---------------------------
# ZMQ setup
# ---------------------------

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.connect("tcp://localhost:5556")

pub = context.socket(zmq.PUB)
pub.connect("tcp://localhost:5558") 

# ---------------------------
# Lógica do servidor
# ---------------------------

def ValidateUsername(username):
    return add_logged_user(username)

def RecordLog(message, timestamp):
    global idServer
    os.makedirs("Logs/Servers", exist_ok=True)

    dateToday = datetime.today().strftime('%d-%m-%Y')
    path = f"Logs/Servers/server-{idServer}-log-{dateToday}.txt"
    mode = "a" if os.path.exists(path) else "w"

    with open(path, mode, encoding="utf-8") as f:
        f.write(f"{timestamp} => {message}" + "\n")

add_logged_user("Fruta")

while True:
    idServerString = input("Digite qual o número deste servidor: ")
    if idServerString.isdigit():
        active_servers = get_active_servers()
        if idServerString in active_servers:
            print(f"O servidor {idServerString} já está ativo. Por favor, escolha outro número: ")
        else:
            idServer = int(idServerString)
            break
    else:
        print("Por favor, digite um número válido.")

add_active_server(idServer)
print("Servidor conectado!")
stringDatetime = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
RecordLog(f"[Conectando Servidor] Servidor {idServer} conectado em {stringDatetime}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

atexit.register(cleanup)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

while True:
    msg_p = socket.recv()
    msg = msgpack.unpackb(msg_p)
    
    function = str(msg["Function"])
    RecordLog(f"[Requisição recebida - {function}] Requisição recebida - {msg}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    if function == "ValidateLoggedUser":
        username = str(msg["Username"])
        usernameIsValid = ValidateUsername(username)
        ans = {"usernameIsValid": usernameIsValid}
        if usernameIsValid:
            RecordLog(f"[ValidateLoggedUser] {username} é válido (não logado ainda)", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            RecordLog(f"[Usuário Logado] {username} logado no servidor", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        else:
            RecordLog(f"[ValidateLoggedUser] {username} não é válido (já existe um usuário logado com esse nome)", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
        RecordLog(f"[ValidateLoggedUser] Retorno enviado para o usuário - {ans}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    elif function == "ShowAllTopics":
        username = str(msg["Username"])
        allTopics = get_logged_users(exclude_username=username)
        RecordLog(f"[ShowAllTopics] Usuários obtidos com sucesso {allTopics}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        ans = {"Topics": allTopics}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
        RecordLog(f"[ShowAllTopics] Retorno enviado para o usuário - {ans}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    elif function == "PublishMessage":
        username = str(msg["Username"])
        message = str(msg["Message"])
        timestampString = str(msg["Timestamp"])
        dictionaryMessage = f"{username} ({timestampString}): {message}"

        save_post(username, dictionaryMessage)
        RecordLog(f"[PublishMessage] Publicação registrada na lista de publicações do usuário {username}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

        data = f"Username:{username}|Timestamp:{timestampString}|Message:{message}"
        pub.send_string(f"{username}: " + data)
        RecordLog(f"[PublishMessage] Publicação de {username} enviada para os subscribers - {dictionaryMessage}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        ans = {"StatusPublish": "Mensagem publicada"}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
        RecordLog(f"[PublishMessage] Retorno enviado para o usuário - {ans}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    elif function == "SendPrivateMessage":
        messageTo = str(msg["To"])
        messageFrom = str(msg["From"])
        message = str(msg["Message"])
        timestampString = str(msg["Timestamp"])

        messageObj = {
            "Username": messageFrom,
            "Message": message,
            "Timestamp": timestampString,
        }

        save_private_message(messageFrom, messageTo, messageObj)
        RecordLog(f"[SendPrivateMessage] Mensagem privada registrada no chat entre {messageTo} e {messageFrom}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

        topic = "Private" + messageTo
        data = f"Username:{messageFrom}|Timestamp:{timestampString}|Message:{message}"
        pub.send_string(f"{topic}: " + data)
        RecordLog(f"[SendPrivateMessage] Mensagem privada de {messageTo} enviada para {messageFrom} - {message}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        ans = {"StatusSendMessage": "Mensagem enviada"}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
        RecordLog(f"[SendPrivateMessage] Retorno enviado para o usuário - {ans}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    elif function == "GetPrivateMessages":
        username = str(msg["Username"])
        chatWith = str(msg["ChatWith"])
        messages = get_private_messages(username, chatWith)
        status = "Found" if messages else "Not found"
        if status == "Found":
            RecordLog(f"[GetPrivateMessages] Mensagens privadas entre {username} e {chatWith} obtidas - {messages}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        else:
            RecordLog(f"[GetPrivateMessages] Mensagens privadas entre {username} e {chatWith} não encontradas", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        ans = {"StatusFoundMessage": status, "Messages": messages}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
        RecordLog(f"[GetPrivateMessages] Retorno enviado para o usuário - {ans}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    elif function == "GetCoordinatorTime":
        serverDatetime = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        RecordLog(f"[GetCoordinatorTime] Obtido timestamp do servidor {serverDatetime}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        ans = {"ServerClock": serverDatetime}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
        RecordLog(f"[GetCoordinatorTime] Retorno enviado para o usuário - {ans}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    elif function == "GetAllPosts":
        username = str(msg["Username"])
        messages = get_posts(username)
        RecordLog(f"[GetCoordinatorTime] Posts obtidos com sucesso - {messages} ", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        status = "Found" if messages else "Not found"
        ans = {"StatusFoundPosts": status, "Posts": messages}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
        RecordLog(f"[GetAllPosts] Retorno enviado para o usuário - {ans}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
