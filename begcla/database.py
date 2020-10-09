import mysql.connector

class EvoSCDB:
    def __init__(self, config, log, datavalues):
        self.config = config
        self.log = log
        self.datavalues = datavalues

        try:
            self.db = mysql.connector.connect(
                host=config['Database']['Host'],
                port=int(config['Database']['Port']),
                user=config['Database']['Username'],
                passwd=config['Database']['Password'],
                database=config['Database']['Database']
            )
        except Exception as e:
            log.error("Failed connecting to database.", stack_info=e)
            raise e
    
    def getPlayerStats(self, login):
        """Get stats used in the classifier of the given player.
        
        Arguments:
            login {string} -- Login name of player.
        
        Returns:
            dict -- Stats of player.
        """

        if not self.db.is_connected():
            self.log.error('Database not connected, attempting reconnection ...')
            self.db.reconnect()

        try:
            self.log.debug("Getting stats of player '%s'" % (login))

            cursor = self.db.cursor()

            # get stats
            cursor.execute('SELECT * FROM players INNER JOIN stats ON players.id=stats.Player WHERE players.Login=%s LIMIT 1', (login,))
            statsRes = cursor.fetchall()

            if len(statsRes) == 0:
                return None

            playerId = statsRes[0][0]

            self.log.debug("Got stats of '%s'" % (login))

            # get local records
            rankAvg = 0
            if 'record_rank_avg' in self.datavalues:
                cursor.execute('SELECT Rank FROM `local-records` where Player=%s', (playerId,))
                localRecords = cursor.fetchall()
                if len(localRecords) > 0:
                    for rec in localRecords:
                        rankAvg += rec[0]
                    rankAvg /= len(localRecords)
                
                self.log.debug("Got local-records avg of '%s'" % (login))

            # get pbs
            npbs = 0
            if 'num_pbs' in self.datavalues:
                cursor.execute('SELECT count(*) FROM pbs where player_id=%s', (playerId,))
                pbs = cursor.fetchall()
                npbs = len(pbs[0])
                self.log.debug("Got pb count of '%s' count: %d" % (login, npbs))

            return {
                'id': playerId,
                'visits': statsRes[0][12],
                'play_time': statsRes[0][13],
                'finishes': statsRes[0][14],
                'locals': statsRes[0][15],
                'wins': statsRes[0][17],
                'score': statsRes[0][19],
                'rank': statsRes[0][20],
                'record_rank_avg': rankAvg,
                'num_pbs': npbs
            }

        except Exception as e:
            self.log.error("Could not retrieve player data for login %s" % (login), stack_info=e)
        
        return None
