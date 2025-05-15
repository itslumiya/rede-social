using System;
using NetMQ;
using NetMQ.Sockets;

class Program
{
    static void Main(string[] args)
    {
        using (var xpubSocket = new XPublisherSocket())
        using (var xsubSocket = new XSubscriberSocket())
        {
            xpubSocket.Bind("tcp://*:5557");
            xsubSocket.Bind("tcp://*:5558");

            Console.WriteLine("Proxy iniciado: XSUB <--> XPUB");

            // Cria o proxy entre XSUB e XPUB
            Proxy proxy = new Proxy(xsubSocket, xpubSocket);

            try
            {
                proxy.Start();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Erro no proxy: {ex.Message}");
            }
        }
    }
}
