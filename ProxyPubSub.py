import zmq

ctx = zmq.Context()

xpub = ctx.socket(zmq.XPUB)
xpub.bind("tcp://*:5557")

xsub = ctx.socket(zmq.XSUB)
xsub.bind("tcp://*:5556")

zmq.proxy(xsub, xpub)

xpub.close()
xsub.close()
ctx.term()