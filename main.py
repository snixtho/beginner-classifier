import configparser
import os
import logging
import argparse

from begcla.commands import cmd_classify, cmd_dataset, cmd_model, cmd_server
from begcla.pidfile import PidFile, PidFileException

###################################################

CONFIG_FILE = 'conf.cfg'

###################################################

# read config
if not os.path.exists(CONFIG_FILE):
    print("Failed to find config file 'conf.cfg'.")
    exit(-1)

config = configparser.ConfigParser(allow_no_value=True)
config.read(CONFIG_FILE)

# setup logging
log = logging.getLogger('BeginnerClassifier')
log.setLevel({
    'noset': logging.NOTSET,
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}[config['Logging']['Level'].lower()])

if config['FileLog']['Enabled'].lower() == 'true':
    _filelogHandler = logging.FileHandler(config['FileLog']['File'])
    _filelogHandler.setFormatter(logging.Formatter(config['FileLog']['Format']))
    log.addHandler(_filelogHandler)

if config['Graylog']['Enabled'].lower() == 'true':
    import graypy
    _graylogHandler = graypy.GELFTCPHandler(
        config['Graylog']['Host'],
        config['Graylog']['Port']
    )
    _graylogHandler.setFormatter(logging.Formatter(config['Graylog']['Format']))
    log.addHandler(_graylogHandler)

# cmd arguments
cmdParser = argparse.ArgumentParser(description='EvoSC Beginner Classifier.')
cmdSubParsers = cmdParser.add_subparsers(dest='cmd')

datasetCmdParser = cmdSubParsers.add_parser("dataset", help='Create datasets model generator.')
datasetCmdParser.add_argument('--out', dest='dataset_file', help='CSV-file to output the dataset to (will append).', required=True)

modelCmdParser = cmdSubParsers.add_parser("model", help='Generate classifier models.')
modelCmdParser.add_argument('--dataset', dest='dataset_file', help='CSV-file containing data points used for training.', required=True)
modelCmdParser.add_argument('--batch-size', dest='batch_size', help='Size of training batches.', default=100)
modelCmdParser.add_argument('--epochs', dest='epochs', help='Number of training epochs.', default=32)
modelCmdParser.add_argument('--out-layer-activation', dest='outlayer_activation', help='Activation function on output layer.', default='softmax')
modelCmdParser.add_argument('--inner-layers', dest='inner_layers', help='List of hidden layers (format size:activation).', default=["50:sigmoid"], nargs='+')
modelCmdParser.add_argument('--dt-values', dest='db_values', help='Data-point values to use (visits,play_time,finishes,locals,wins,score,rank,record_rank_avg,num_pbs).', default="finishes,locals,wins,score,rank")
modelCmdParser.add_argument('--in-layer-size', dest='inlayer_size', help='Size of the input layer.', default=32)
modelCmdParser.add_argument('--in-layer-activation', dest='inlayer_activation', help='Activation function of the input layer', default='relu')
modelCmdParser.add_argument('--optimizer', dest='optimizer', help='Model compilation optimizer.', default='rmsprop')
modelCmdParser.add_argument('--loss', dest='loss', help='Model compilation loss function.', default='binary_crossentropy')
modelCmdParser.add_argument('--metrics', dest='metrics', help='Metrics to use for the training.', default=["accuracy"], nargs='+')
modelCmdParser.add_argument('--out', dest='out_file', help='File to save the model to.', default='model.h5')

serverCmdParser = cmdSubParsers.add_parser("server", help='Serve a classifier prediction server.')
serverCmdParser.add_argument('--dt-values', dest='dt_values', help='Data-point values to use (visits,play_time,finishes,locals,wins,score,rank,record_rank_avg,num_pbs).', default="finishes,locals,wins,score,rank")
serverCmdParser.add_argument('--detach', dest='detach', help='Detach the server process and run it in the background.', default=False, action="store_true")
serverCmdParser.add_argument('--pid', dest='pid', help='Path to pid file.', default=config['Common']['PidFile'])

classifyCmdParser = cmdSubParsers.add_parser("classify", help='Try to classify players beginners or advanced.')
classifyCmdParser.add_argument('--logins', dest='player_logins', help='List of logins of players to check', required=True, nargs='+')
classifyCmdParser.add_argument('--model', dest='model_file', help='Path to the model file to use.', default='model.h5')
classifyCmdParser.add_argument('--json', dest='json', help='Output in json format.', default=False, action="store_true")
classifyCmdParser.add_argument('--server', dest='use_server', help='Run classification through the prediction server (the server must be running).', default=False, action="store_true")
classifyCmdParser.add_argument('--dt-values', dest='dt_values', help='Data-point values to use (visits,play_time,finishes,locals,wins,score,rank,record_rank_avg,num_pbs).', default="finishes,locals,wins,score,rank")

args = cmdParser.parse_args()
cmd = None
fork = False
child = 0
withpid = False

if args.cmd == 'dataset':
    cmd = cmd_dataset.CmdDataset(args, config, log)
elif args.cmd == 'model':
    cmd = cmd_model.CmdModel(args, config, log)
elif args.cmd == 'classify':
    cmd = cmd_classify.CmdClassify(args, config, log)
elif args.cmd == 'server':
    fork = args.detach

    if fork:
        if hasattr(os, 'fork'):
            child = os.fork()
        else:
            log.error('Forking is not supported on this OS, continuing without detach mode ...')
            fork = False

    withpid = True
    cmd = cmd_server.CmdServer(args, config, log)

if fork and child != 0:
    log.info('Running in detatched mode, child pid: ' + str(child))
    exit(0)

if cmd is not None:
    try:
        if withpid:
            with PidFile(config, args):
                cmd.run()
        else:
            cmd.run()
    except PidFileException as e:
        log.debug(str(e))
