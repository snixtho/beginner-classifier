import numpy as np
import os
import json
import sys
from begcla.database import EvoSCDB
from begcla.classifier import Classifier
from begcla.commands.cmd_server import Client, Packet, PredictionServer
import socket

class CmdClassify:
    def __init__(self, args, config, log):
        self.log = log
        self.args = args
        self.config = config
        self.db = None
        self.log.name = "BeginnerClassifierClient"

    def run(self):
        result = {}

        self.log.debug('Classify start.')

        if self.args.use_server:
            self.log.debug('Using server.')
            address = self.config['Server']['ListenAddress']
            port = int(self.config['Server']['ListenPort'])
            dataBlockSize = int(self.config['Server']['DataBlockSize'])

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((address, port))
                client = Client(sock, address, PredictionServer(self.config, self.log, None, self.args), dataBlockSize)

                packet = Packet({
                    'request': 'predict',
                    'logins': self.args.player_logins
                })
                client.sendPacket(packet)

                response = client.awaitPacket()
                if response.data['errno'] > 0:
                    if self.args.json:
                        print(json.dumps(response.data))
                    else:
                        print('[-] Error: ' + str(response.data['error']))
                    return
                
                sock.close()
                result['predictions'] = response.data['predictions']
            except Exception as e:
                if self.args.json:
                    print(json.dumps({
                        'errno': 1,
                        'error': 'Server connection failed: ' + str(e)
                    }))
                else:
                    print('Server connection failed: ' + str(e))
                return

        elif os.path.exists(self.args.model_file):
            self.log.debug('Don\'t use server.')
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '10'
            stderr = sys.stderr
            sys.stderr = open(os.devnull, 'w')
            from keras.models import load_model
            sys.stderr = stderr

            data_values = self.args.dt_values.split(',')
            self.db = EvoSCDB(self.config, self.log, data_values)

            self.log.info("Loading model %s" % (self.args.model_file))
            model = load_model(self.args.model_file)
            result['predictions'] = []
            
            classifier = Classifier(self.db, model, data_values)

            for login in self.args.player_logins:
                prediction = classifier.classify(login)
                
                if prediction is None:
                    print("[-] Failed to classify player '%s'. Player probably doesn't exist." % (login))
                    return

                result['predictions'].append({
                    'login': login,
                    'experienced': float(prediction[0][0]),
                    'beginner': float(prediction[0][1]),
                })
        else:
            print("[-] The model file '%s' does not exist." % (self.args.model_file))
            return

        self.log.debug('Got prediction.')

        if self.args.json:
            print(json.dumps(result))
            self.log.debug('Printed json.')
        else:
            for prediction in result['predictions']:
                if 'success' in prediction and prediction['success'] == False:
                    print("[-] Error: " + prediction['error'])
                    continue

                if prediction['beginner'] > 0.5:
                    print("[+] %s is a beginner (%s%% sure)" % (prediction['login'], round(prediction['beginner']*100, 2)))
                else:
                    print("[+] %s is experienced (%s%% sure)" % (prediction['login'], round(prediction['experienced']*100, 2)))
            self.log.debug('Printed user-friendly output.')
