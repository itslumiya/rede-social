const zmq = require("zeromq");
const msgpack = require("msgpack-lite");
const fs = require('fs');
const path = require('path');

const languages = [
    "Python", "JavaScript", "C++", "Java", "C#",
    "Go", "Rust", "TypeScript", "Ruby", "Kotlin",
    "Swift", "PHP", "Haskell", "Elixir", "Scala",
    "Perl", "Lua", "Dart", "Objective-C", "R"
];

function randomLanguage() {
    const index = Math.floor(Math.random() * languages.length);
    return languages[index];
}

function getFormattedTimestamp() {
    const now = new Date();
    const day = String(now.getDate()).padStart(2, '0');
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const year = now.getFullYear();
    const hour = String(now.getHours()).padStart(2, '0');
    const minute = String(now.getMinutes()).padStart(2, '0');
    const second = String(now.getSeconds()).padStart(2, '0');

    return `${day}/${month}/${year} ${hour}:${minute}:${second}`;
}

function recordLog(message, timestamp) {
    const logDir = path.join(__dirname, 'Logs', 'Clients');

    if (!fs.existsSync(logDir)) {
        fs.mkdirSync(logDir, { recursive: true });
    }

    const today = new Date();
    const day = String(today.getDate()).padStart(2, '0');
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const year = today.getFullYear();
    const dateToday = `${day}-${month}-${year}`;

    const logPath = path.join(logDir, `client-programming-languages-log-${dateToday}.txt`);
    const logEntry = `${timestamp} => ${message}\n`;

    fs.appendFileSync(logPath, logEntry, { encoding: 'utf-8' });
}

async function sendToServer(socket, msg) {
    const msgPacked = msgpack.encode(msg);
    await socket.send(msgPacked);

    const [replyPacked] = await socket.receive();
    const reply = msgpack.decode(replyPacked);
    return reply;
}

async function runClient() {
    const socket = new zmq.Request();
    await socket.connect("tcp://localhost:5555");

    while (true) {
        const language = randomLanguage();
        const timestamp = getFormattedTimestamp();

        const message = {
            Function: "PublishMessage",
            Message: `A linguagem de programação escolhida é "${language}"`,
            Username: "ProgrammingLanguages",
            Timestamp: timestamp
        };

        console.log("Enviando mensagem: ", message.Message);

        try {
            const response = await sendToServer(socket, message);
            console.log("Resposta do servidor:", response);

            recordLog(`[Publicação] Linguagem de Programação (${timestamp}) - ${message.Message}`, timestamp);
        } catch (err) {
            console.error("Erro ao enviar mensagem:", err);
        }

        await new Promise(resolve => setTimeout(resolve, 5000));
    }
}

runClient();