import socket
from threading import Thread, RLock
import numpy
import os
import time
from struct import pack, unpack
from begcla.classifier import Classifier
from begcla.database import EvoSCDB
import json

class Packet:
    def __init__(self, data):
        self.data = data
    
    def makePacket(self):
        body = json.dumps(self.data)
        size = len(body)

        bdata = pack('<I', size)
        bdata += body.encode('utf8')

        return bdata

    @staticmethod
    def Parse(dataBytes):
        datastr = dataBytes.decode('utf8')
        data = json.loads(datastr)
        return Packet(data)

class Client:
    ERROR_UNKNOWN = 1
    ERROR_INVALID_REQUEST = 2
    ERROR_INVALID_BODY = 4
    ERROR_DATABASE = 8

    def __init__(self, socket, addr, server, blockSize):
        self.server = server
        self.socket = socket
        self.addr = addr
        self.id = None
        self.blockSize = blockSize
    
    def awaitPacket(self):
        """Recieve a packet from the client.
        
        Returns:
            Packet -- Packet recieved.
        """
        try:
            chunks = []
            nread = 0
            
            # get packet size
            sized = self.socket.recv(4)
            size = unpack('<I', sized)[0]

            self.server.log.debug("packet size: " + str(size))
            self.server.log.debug("packet size bytes: " + str(sized))

            # read the packet contents
            while nread < size:
                bytesLeft = size - nread
                chunk = self.socket.recv(min(bytesLeft, self.blockSize))

                if chunk == b'':
                    self.server.log.error('Connection to client %d is interrupted while recieving.' % (self.id))
                    return None
                
                nread += len(chunk)
                chunks.append(chunk)
            
            # parse the packet data
            dataBytes = b''.join(chunks)
            self.server.log.debug("recv bytes: " + str(dataBytes))
            packet = Packet.Parse(dataBytes)

            return packet

        except Exception as e:
            self.server.log.error('Recv failed: ' + str(e), stack_info=e)
            return None
    
    def sendError(self, errno):
        """Send a error packet back to the client
        
        Arguments:
            errno {int} -- Error number.
        """
        errStr = ''

        if errno == Client.ERROR_INVALID_REQUEST:
            errStr = 'Invalid request'
        elif errno == Client.ERROR_INVALID_BODY:
            errStr = 'Invalid body.'
        elif errno == Client.ERROR_DATABASE:
            errStr = 'Database error.'
        else:
            errStr = 'Unknonw error.'

        packet = Packet({
            'error': errStr,
            'errno': Client.ERROR_INVALID_REQUEST
        })

        self.sendPacket(packet)
    
    def sendPacket(self, packet):
        """Send a packet to the client.
        
        Arguments:
            packet {Packet} -- Packet object containing the data.
        """
        try:
            data = packet.makePacket()
            totalBytes = len(data)

            nsent = 0
            while nsent < totalBytes:
                sent = self.socket.send(data[nsent:])

                if sent == 0:
                    self.server.log.error('Connection to client %d is interrupted while sending.' % (self.id))
                    return False
                
                nsent += sent
            
            return True
        except Exception as e:
            self.server.log.error('Send failed: %s' % (str(e)), stack_info=e)
            return False

    def _client_handle_thread(self):
        try:
            # handle client ...
            packet = self.awaitPacket()

            if packet is None:
                self.server.log.debug('Packet is null, aborting ...')
                return

            # check if request option exists
            if 'request' not in packet.data:
                self.sendError(Client.ERROR_INVALID_REQUEST)
                self.server.log.debug('Client %d sent an invalid request.' % (self.id))
                return

            # check for valid requests
            if packet.data['request'] == 'predict':
                if 'logins' not in packet.data or type(packet.data['logins']) is not list:
                    self.sendError(Client.ERROR_INVALID_BODY)
                    self.server.log.debug('Client %d sent an invalid body.' % (self.id))
                    return

                result = {
                    'errno': 0,
                    'predictions': []
                }

                if len(packet.data['logins']) > 0:
                # make a prediction on each login
                    for login in packet.data['logins']:
                        prediction = None
                        try:
                            prediction = self.server.classify(login)
                        except ConnectionRefusedError as e:
                            self.sendError(Client.ERROR_DATABASE)
                            return

                        pred_result = {}

                        if prediction is None:
                            self.server.log.debug('Prediction failed; check error log msg.')
                            pred_result = {
                                'login': login,
                                'success': False,
                                'error': 'Player '+login+' not found.'
                            }
                        else:
                            pred_result = {
                                'login': login,
                                'success': True,
                                'experienced': float(prediction[0][0]),
                                'beginner': float(prediction[0][1]),
                            }
                        
                        result['predictions'].append(pred_result)
                
                    if len(result['predictions']) == 0:
                        self.sendError(Client.ERROR_UNKNOWN)
                        return
                
                resultPacket = Packet(result)
                self.sendPacket(resultPacket)
            else:
                self.sendError(Client.ERROR_INVALID_REQUEST)
                self.server.log.debug('Client %d sent an invalid request.' % (self.id))
        finally:
            self.server.log.debug('Client %d finished.' % (self.id))
            self.socket.close()
            self.server.removeClient(self.id)

    def handleAsync(self):
        """Handle a client in a new thread
        """
        t = Thread(target=self._client_handle_thread)
        t.start()

class PredictionServer:
    def __init__(self, config, log, model, args):
        self.config = config
        self.log = log
        self.model = model
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clientId = 0
        self.clientLock = RLock()
        self.clients = {}
        self.db = EvoSCDB(config, log, args.dt_values.split(','))
        self.args = args
        self.classifier = Classifier(self.db, model, args.dt_values.split(','))
        self.classifierLock = RLock()

    def classify(self, login):
        try:
            self.classifierLock.acquire()
            prediction = self.classifier.classify(login)
            return prediction
        except Exception as e:
            self.log.error('Failed to classify player: ' + str(e), stack_info=e)
            return None
        except ConnectionRefusedError as e:
            self.log.error('Failed to connect to database: ' + str(e), stack_info=e)
            raise e
        finally:
            self.classifierLock.release()

    def addClient(self, client):
        try:
            self.clientLock.acquire()

            clientId = self.clientId
            self.clientId += 1

            return clientId
        finally:
            self.clientLock.release()
    
    def removeClient(self, clientId):
        try:
            self.clientLock.acquire()

            if clientId in self.clients:
                del self.clients[clientId]
        finally:
            self.clientLock.release()
    
    def getNumClients(self):
        try:
            self.clientLock.acquire()
            return len(self.clients)
        finally:
            self.clientLock.release()
    
    def serve(self):
        address = self.config['Server']['ListenAddress']
        port = int(self.config['Server']['ListenPort'])
        rejectOnMaxClients = self.config['Server']['RejectOnMaxClients']
        maxClientsRetryInterval = int(self.config['Server']['MaxClientsRetryInterval'])
        maxClients = int(self.config['Server']['MaxClients'])
        dataBlockSize = int(self.config['Server']['DataBlockSize'])

        # setup socket
        self.log.debug('Binding socket to: %s:%d' % (address, port))
        self.socket.bind((address, port))

        self.log.debug('Start listen ...')
        self.socket.listen(int(self.config['Server']['Backlog']))

        self.log.debug('Waiting for connections ...')

        # wait and accept clients
        try:
            while True:
                while self.getNumClients() >= maxClients and not rejectOnMaxClients:
                    self.log.warn('Max clients exceeded, waiting %d milliseconds ...' % (maxClientsRetryInterval))
                    time.sleep(maxClientsRetryInterval/1000)
                
                # accept client
                (csocket, caddress) = self.socket.accept()
                self.log.debug('Accept client: %s' % (str(caddress)))

                if rejectOnMaxClients and self.getNumClients() >= maxClients:
                    # reject client instead of waiting for available slots
                    self.log.warn('Max clients exceeded, rejecting client.')
                    csocket.close()
                    continue
                
                # handle client
                client = Client(csocket, caddress, self, dataBlockSize)
                client.id = self.addClient(client)
                self.log.debug('Handling client ...')
                client.handleAsync()
        except (KeyboardInterrupt, SystemExit):
            self.log.info('KeyboardInterrupt, closing down ...')
        except Exception as e:
            self.log.error('Error: ' + str(e), stack_info=e)
        
        # close all clients still connected
        self.log.debug('Closing all client connections ...')
        for clientId in self.clients:
            try:
                self.clients[clientId].socket.close()
                self.log.debug('Closed client with id %d' % (clientId))
            except Exception as e:
                self.log.error('Failed closing client connection: ' + str(e), stack_info=e)

class CmdServer:
    def __init__(self, args, config, log):
        self.log = log
        self.args = args
        self.config = config
        self.server = None

    def run(self):
        modelfile = self.config['Classifier']['Model']
        if not os.path.exists(modelfile):
            self.log.error('Could not load model: %s' % (modelfile))
            return

        # load and initialize model
        from keras.models import load_model

        self.log.debug('Loading model file %s' % (modelfile))

        model = load_model(modelfile)
        model._make_predict_function() # initialize model so that it is thread-safe

        # initialize and start server
        self.server = PredictionServer(self.config, self.log, model, self.args)
        self.log.info('Starting up prediction server.')
        self.server.serve()
