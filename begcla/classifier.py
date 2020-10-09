import numpy as np

class Classifier:
    def __init__(self, db, model, dataValues):
        self.db = db
        self.model = model
        self.dataValues = dataValues
    
    def classify(self, login):
        stats = self.db.getPlayerStats(login)

        if stats == None:
            return None

        point = []

        if "visits" in self.dataValues:
            point.append(float(stats['visits']))
        if "play_time" in self.dataValues:
            point.append(float(stats['play_time']))
        if "finishes" in self.dataValues:
            point.append(float(stats['finishes']))
        if "locals" in self.dataValues:
            point.append(float(stats['locals']))
        if "wins" in self.dataValues:
            point.append(float(stats['wins']))
        if "score" in self.dataValues:
            point.append(float(stats['score']))
        if "rank" in self.dataValues:
            point.append(float(stats['rank']))
        if "record_rank_avg" in self.dataValues:
            point.append(float(stats['record_rank_avg']))
        if "num_pbs" in self.dataValues:
            point.append(float(stats['num_pbs']))
        
        return self.model.predict(np.array([point]))
