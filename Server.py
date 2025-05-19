import zmq
import msgpack
from datetime import datetime
import redis
import json

# Configuração do Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# ---------------------------
# Funções Redis para dados compartilhados
# ---------------------------

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

while True:
    msg_p = socket.recv()
    msg = msgpack.unpackb(msg_p)
    
    function = str(msg["Function"])

    if function == "ValidateLoggedUser":
        username = str(msg["Username"])
        usernameIsValid = ValidateUsername(username)
        ans = {"usernameIsValid": usernameIsValid}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    elif function == "ShowAllTopics":
        username = str(msg["Username"])
        allTopics = get_logged_users(exclude_username=username)
        ans = {"Topics": allTopics}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    elif function == "PublishMessage":
        username = str(msg["Username"])
        message = str(msg["Message"])
        timestampString = str(msg["Timestamp"])
        dictionaryMessage = f"{username} ({timestampString}): {message}"

        save_post(username, dictionaryMessage)

        data = f"Username:{username}|Timestamp:{timestampString}|Message:{message}"
        pub.send_string(f"{username}: " + data)
        ans = {"StatusPublish": "Mensagem publicada"}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
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

        topic = "Private" + messageTo
        data = f"Username:{messageFrom}|Timestamp:{timestampString}|Message:{message}"
        pub.send_string(f"{topic}: " + data)
        ans = {"StatusSendMessage": "Mensagem enviada"}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    elif function == "GetPrivateMessages":
        username = str(msg["Username"])
        chatWith = str(msg["ChatWith"])
        messages = get_private_messages(username, chatWith)
        status = "Found" if messages else "Not found"
        ans = {"StatusFoundMessage": status, "Messages": messages}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    elif function == "GetCoordinatorTime":
        serverDatetime = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ans = {"ServerClock": serverDatetime}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    elif function == "GetAllPosts":
        username = str(msg["Username"])
        messages = get_posts(username)
        status = "Found" if messages else "Not found"
        ans = {"StatusFoundPosts": status, "Posts": messages}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
