from begcla.database import EvoSCDB
import os
import json
import sys

class CmdDataset:
    def __init__(self, args, config, log):
        self.log = log
        self.args = args
        self.config = config
        self.db = EvoSCDB(config, log, 'visits,play_time,finishes,locals,wins,score,rank,record_rank_avg,num_pbs'.split(','))

    def _menu(self):
        while True:
            try:
                print('1. From DB json file')
                print('2. Manual entry')
                print('3. Quit')
                return int(input('> '))
            except KeyboardInterrupt:
                print('Aborting ...')
                return 3
            except Exception:
                print('Invalid option.')

    def addDataPoint(self, login, isBeginner):
        player = self.db.getPlayerStats(login)
        if player is None:
            print("[-] Player '%s' not found." % (login))
            return
        
        self.log.info("Adding datapoint for player '%s'" % (login))

        with open(self.args.dataset_file, 'a+') as f:
            f.write(str(player['id']) + ',')
            f.write(str(player['visits']) + ',')
            f.write(str(player['play_time']) + ',')
            f.write(str(player['finishes']) + ',')
            f.write(str(player['locals']) + ',')
            f.write(str(player['wins']) + ',')
            f.write(str(player['score']) + ',')
            f.write(str(player['rank']) + ',')
            f.write(str(player['record_rank_avg']) + ',')
            f.write(str(player['num_pbs']) + ',')
            f.write(str(1 if isBeginner else 0) + "\n")

    def run(self):
        while True:
            opt = self._menu()

            if opt == 1:
                fname = input('File: ')
                if not os.path.exists(fname):
                    print('[+] File does not exist.')
                with open (fname, 'r') as f:
                    data = json.loads(f.read())
                    totalPlayers = len(data['rows'])
                    print("Total players to check: " + str(totalPlayers))
                    currPlayer = 1
                    for row in data['rows']:
                        sys.stdout.write("Player: %s (%s/%s - %s%%)               \r" % (row['name'], str(currPlayer), str(totalPlayers), str(round(currPlayer/totalPlayers, 2))))
                        sys.stdout.flush()
                        self.addDataPoint(row['name'], True if row['votes'] == 'beginner' else False)
                        currPlayer += 1
                    print("\n[+] Done!")
            elif opt == 2:
                login = input('Player Login: ')
                isBeginner = True if input('Beginner?: ').lower() == 'y' else False
                self.addDataPoint(login, isBeginner)
            elif opt == 3:
                break
