const zmq = require("zeromq");

// Lista de frutas
const fruits = [
  "Banana", "Maçã", "Morango", "Uva", "Melancia",
  "Laranja", "Abacaxi", "Manga", "Pêssego", "Kiwi",
  "Acerola", "Amora", "Caju", "Carambola", "Cereja",
  "Framboesa", "Goiaba", "Graviola", "Jabuticaba", "Jaca",
  "Limão", "Maracujá", "Mamão", "Nectarina", "Pera",
  "Pitanga", "Romã", "Tamarindo", "Tangerina", "Abiu",
  "Atemóia", "Cupuaçu", "Figo", "Physalis", "Lichia",
  "Cambuci", "Seriguela", "Biribá", "Pequi", "Murici",
  "Jenipapo", "Uvaia", "Sapoti", "Mangostão", "Cabeludinha",
  "Araticum", "Baru", "Cacau", "Zimbro", "Bacaba"
];

// Função para sortear uma fruta aleatória
function randomFruit() {
  const index = Math.floor(Math.random() * fruits.length);
  return fruits[index];
}

async function runPublisher() {
  const pubSocket = new zmq.Publisher();
  await pubSocket.connect("tcp://localhost:5558");

  while (true) {
    const fruit = randomFruit();
    const mensagem = `A fruta escolhida foi ${fruit}`;
    await pubSocket.send([`Fruta: ${mensagem}`]);
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
}

runPublisher();