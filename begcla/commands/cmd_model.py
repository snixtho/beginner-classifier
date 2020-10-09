import numpy as np
import os

class CmdModel:
    def __init__(self, args, config, log):
        self.log = log
        self.args = args
        self.config = config

    def run(self):
        import keras
        from keras.models import Sequential
        from keras.layers import Dense, Activation

        if not os.path.exists(self.args.dataset_file):
            print("[+] The dataset file '%' can't be found." % (self.args.dataset_file))

        # print configuration
        print("[+] Dataset: " + str(self.args.dataset_file))
        print("[+] Training Batch Size: " + str(self.args.batch_size))
        print("[+] Training Epochs: " + str(self.args.epochs))
        print("[+] Output Layer Activation: " + str(self.args.outlayer_activation))
        print("[+] Inner Layers: " + str(self.args.inner_layers))
        print("[+] Datapoint values: " + str(self.args.db_values))
        print("[+] Input Layer Size: " + str(self.args.inlayer_size))
        print("[+] Input Layer Activation: " + str(self.args.inlayer_activation))
        print("[+] Optimizer: " + str(self.args.optimizer))
        print("[+] Loss Function: " + str(self.args.loss))
        print("[+] Training Metrics: " + str(self.args.metrics))
        print("[+] Output File: " + str(self.args.out_file))

        # form training data
        data_values = self.args.db_values.split(',')

        datapoints = np.array([])
        labels = np.array([])

        with open(self.args.dataset_file) as f:
            for line in f.readlines():
                entries = line.split(',')
                point = []

                if "visits" in data_values:
                    point.append(float(entries[1]))
                if "play_time" in data_values:
                    point.append(float(entries[2]))
                if "finishes" in data_values:
                    point.append(float(entries[3]))
                if "locals" in data_values:
                    point.append(float(entries[4]))
                if "wins" in data_values:
                    point.append(float(entries[5]))
                if "score" in data_values:
                    point.append(float(entries[6]))
                if "rank" in data_values:
                    point.append(float(entries[7]))
                if "record_rank_avg" in data_values:
                    point.append(float(entries[8]))
                if "num_pbs" in data_values:
                    point.append(float(entries[9]))
                
                npPoint = np.array([np.array(point)])

                if len(datapoints) == 0:
                    datapoints = npPoint
                else:
                    datapoints = np.concatenate((datapoints, npPoint))
                
                labels = np.append(labels, entries[10])
        
        labels = keras.utils.to_categorical(labels, num_classes=2)

        # build model
        model = Sequential()
        model.add(Dense(self.args.inlayer_size, input_dim=len(data_values)))
        model.add(Activation(self.args.inlayer_activation))

        for layer in self.args.inner_layers:
            info = layer.split(':')
            size = int(info[0])
            activation = info[1]

            model.add(Dense(size))
            model.add(Activation(activation))
        
        model.add(Dense(2))
        model.add(Activation(self.args.outlayer_activation))

        model.compile(
            optimizer=self.args.optimizer,
            loss=self.args.loss,
            metrics=self.args.metrics
        )

        # train the model
        model.fit(datapoints, labels, epochs=int(self.args.epochs), batch_size=int(self.args.batch_size))
        model.save(self.args.out_file)
