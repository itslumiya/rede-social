import zmq
import msgpack

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.connect("tcp://localhost:5556")

pub = context.socket(zmq.PUB)
pub.connect("tcp://localhost:5558") 

logged_users = []
messages = {}
privateMessages = {}

def ValidateUsername(username):
    if username in logged_users:
        return False
    else:
        logged_users.append(username)
        return True

while True:
    msg_p = socket.recv()
    msg = msgpack.unpackb(msg_p)
    
    function = str(msg["Function"])

    if(function == "ValidateLoggedUser"):
        username = str(msg["Username"])
        usernameIsValid = ValidateUsername(username)
        ans = {"usernameIsValid": usernameIsValid}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
    elif(function == "ShowAllTopics"):
        username = str(msg["Username"])
        allTopics = list(logged_users)
        if username in allTopics:
            allTopics.remove(username)
        ans = {"Topics": allTopics}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
    elif(function == "PublishMessage"):
        username = str(msg["Username"])
        message = str(msg["Message"])
        timestampString = str(msg["Timestamp"])
        dictionaryMessage = f"{timestampString} {username}: {message}"
        if username in messages:
            messages[username].append(message)
        else:
            messages[username] = [message]
        topic = username
        data = f"Username:{username}|Timestamp:{timestampString}|Message:{message}"
        pub.send_string(f"{topic}: " + data)
        ans = {"StatusPublish": "Mensagem publicada"}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
    elif(function == "SendPrivateMessage"):
        messageTo = str(msg["To"])
        messageFrom = str(msg["From"])
        message = str(msg["Message"])
        timestampString = str(msg["Timestamp"])
        messageObj = {
            "Username": messageFrom,
            "Message": message,
            "Timestamp": timestampString,
        }

        if messageFrom in privateMessages:
            chats = privateMessages[messageFrom]
            if any(chat['ChatWith'] == messageTo for chat in chats):
                index = next((i for i, chat in enumerate(chats) if chat['ChatWith'] == messageTo), None)
                messages = privateMessages[messageFrom][index]["Messages"]
                messages.append(messageObj)
            else:
                newChat = {
                    "ChatWith": messageTo,
                    "Messages": [messageObj]
                }
                chats.append(newChat)
        else:
            privateMessages[messageFrom] = [
                {
                    "ChatWith": messageTo,
                    "Messages": [messageObj]
                }   
            ]
        
        if messageTo in privateMessages:
            chats = privateMessages[messageTo]
            if any(chat['ChatWith'] == messageFrom for chat in chats):
                index = next((i for i, chat in enumerate(chats) if chat['ChatWith'] == messageFrom), None)
                messages = privateMessages[messageTo][index]["Messages"]
                messages.append(messageObj)
            else:
                newChat = {
                    "ChatWith": messageFrom,
                    "Messages": [messageObj]
                }
                chats.append(newChat)
        else:
            privateMessages[messageTo] = [
                {
                    "ChatWith": messageFrom,
                    "Messages": [messageObj]
                }   
            ]

        topic = "Private" + messageTo
        data = f"Username:{username}|Timestamp:{timestampString}|Message:{message}"
        pub.send_string(f"{topic}: " + data)
        ans = {"StatusSendMessage": "Mensagem enviada"}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
    elif(function == "GetPrivateMessages"):
        username = str(msg["Username"])
        chatWith = str(msg["ChatWith"])
        messages = []
        status = "Not found"
        if username in privateMessages:
            allChats = privateMessages[username]
            if any(chat['ChatWith'] == chatWith for chat in allChats):
                index = next((i for i, chat in enumerate(allChats) if chat['ChatWith'] == chatWith), None)
                messages = privateMessages[username][index]["Messages"]
                status = "Found"
        ans = {"StatusFoundMessage": status, "Messages": messages}
        ans_p = msgpack.packb(ans)
        socket.send(ans_p)
server.close()
ctx.close()