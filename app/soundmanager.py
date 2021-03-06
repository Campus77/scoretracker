from kivy.logger import Logger
import subprocess
import os
from enum import Enum
from threading import Thread
import glob
import random
from collections import deque
from soundissuer import SoundIssuer

class Trigger(Enum):
    MENU = 0
    GAME_START = 1
    GAME_END = 2
    GAME_PAUSE = 3
    GAME_RESUME = 4
    GOAL = 5 # data: goals1, goals2
    DENIED = 6
    RFID = 7
    PLAYER_JOINED = 8 # data: player dict
    PLAYERS_SWITCHED = 9
    PLAYER_MOVED = 10
    BUTTON = 11
    BACK = 12
    EXIT = 13
    OFFSIDE = 14
    PLAYER_SELECTED = 15 # data: player dict
    INTRO = 16
    HOTSPOT_CONNECT = 17
    HOTSPOT_DISCONNECT = 18

class SoundManagerBase(object):

    BASEPATH = './assets/sounds/'
    EXT = '.mp3'

    def __init__(self):
        self.sound_issuer = SoundIssuer()
        #self.queue = Queue()
        self.stopped = False

        self.map_sound_files = {
            'intro':   {'type': 'fixed', 'path': 'intro', 'volume': 0.7},
            'menu':    {'type': 'random', 'path': 'menu/*', 'volume': 0.7},
            'whistle': {'type': 'fixed', 'path': 'whistle_medium', 'volume': 0.8},
            'kickoff': {'type': 'fixed', 'path': 'kickoff', 'volume': 1.0},
            'goal':    {'type': 'random', 'path': 'goal/*', 'volume': 1.0},
            'offside': {'type': 'random', 'path': 'offside/*', 'volume': 1.0},
            'stadium': {'type': 'random', 'path': 'stadium/*', 'volume': 0.5},
            'denied':  {'type': 'fixed', 'path': 'chime_down2', 'volume': 1.0},
            'button':  {'type': 'fixed', 'path': 'chime_medium1', 'volume': 1.0},
            'back':    {'type': 'fixed', 'path': 'chime_low1', 'volume': 1.0},
            'exit':    {'type': 'random', 'path': 'shutdown/*', 'volume': 1.0},
            'rfid':    {'type': 'fixed', 'path': 'chime_up3', 'volume': 1.0},
            'scratch': {'type': 'fixed', 'path': 'scratch', 'volume': 0.8},
            'player':  {'type': 'indexed', 'path': 'players/*', 'volume': 1.0},
            'players_switched': {'type': 'fixed', 'path': 'players_switched', 'volume': 1.0},
            'player_moved': {'type': 'fixed', 'path': 'player_moved', 'volume': 1.0},
            'hotspot_connect':  {'type': 'fixed', 'path': 'hotspot', 'volume': 1.0},
            'hotspot_disconnect':  {'type': 'fixed', 'path': 'no_hotspot', 'volume': 1.0}
        }

        # read sound files
        for key in self.map_sound_files:
            entry = self.map_sound_files[key]
            files = glob.glob(self.BASEPATH + entry['path'] + self.EXT)
            if entry['type'] == 'indexed':
                self.map_sound_files[key]['map'] = {}
                for sound_file in files:
                    (name, ext) = os.path.splitext(os.path.basename(sound_file))
                    self.map_sound_files[key]['map'][int(name)] = sound_file
            else:
                random.shuffle(files)
                self.map_sound_files[key]['files'] = deque(files)

        self.map_trigger = {
            Trigger.INTRO:          [
                                        {'sound': 'intro', 'loop': False},
                                        {'sound': 'menu', 'loop': True, 'delay': 18.0}
                                    ],
            Trigger.MENU:           [
                                        {'sound': 'menu', 'loop': True}
                                    ],
            Trigger.GAME_START:     [
                                        {'sound': 'kickoff'},
                                        {'sound': 'player', 'delay': 0.6},
                                        {'sound': 'whistle', 'delay': 1.5},
                                        {'sound': 'stadium', 'loop': True, 'delay': 1.0}
                                    ],
            Trigger.GAME_END:       [
                                        {'sound': 'whistle'},
                                        {'sound': 'menu', 'loop': True}
                                    ],
            Trigger.GAME_PAUSE:     [
                                        {'stoploop': True},
                                        {'sound': 'scratch'}
                                    ],
            Trigger.GAME_RESUME:    [
                                        {'sound': 'whistle'},
                                        {'sound': 'stadium', 'loop': True}
                                    ],
            Trigger.GOAL:           [
                                        {'sound': 'goal'}
                                    ],
            Trigger.DENIED:         [
                                        {'sound': 'denied'}
                                    ],
            Trigger.RFID:           [
                                        {'sound': 'rfid'}
                                    ],
            Trigger.BUTTON:         [
                                        {'sound': 'button'}
                                    ],
            Trigger.BACK:           [
                                        {'sound': 'back'}
                                    ],
            Trigger.EXIT:           [
                                        {'stoploop': True},
                                        {'sound': 'exit'}
                                    ],
            Trigger.OFFSIDE:        [
                                        {'sound': 'offside'}
                                    ],
            Trigger.PLAYER_JOINED:  [
                                        {'sound': 'rfid'},
                                        {'sound': 'player', 'delay': 0.5}
                                    ],
            Trigger.PLAYERS_SWITCHED: [
                                        {'sound': 'players_switched'}
                                    ],
            Trigger.PLAYER_MOVED:   [
                                        {'sound': 'player_moved'}
                                    ],
            Trigger.PLAYER_SELECTED:  [
                                        {'sound': 'player'}
                                    ],
            Trigger.HOTSPOT_CONNECT: [
                                        {'sound': 'hotspot_connect'},
                                        {'sound': 'player', 'delay': 0.7}
                                    ],
            Trigger.HOTSPOT_DISCONNECT: [
                                        {'sound': 'hotspot_disconnect'}
                                    ]
        }

        self.thread = Thread(target=self.__thread)
        self.thread.start()

    def play(self, trigger, param=None):
        if trigger in self.map_trigger:
            commands = self.map_trigger[trigger]
            for command in commands:
                if 'sound' in command:
                    sound_conf = self.map_sound_files[command['sound']]
                    volume = sound_conf.get('volume', 1.0)
                    loop = command.get('loop', False)
                    delay = command.get('delay', 0.0)
                    path = ''

                    if sound_conf['type'] == 'random':
                        if len(sound_conf['files']):
                            path = sound_conf['files'][0]
                            sound_conf['files'].rotate(1)
                    elif sound_conf['type'] == 'fixed':
                        if len(sound_conf['files']):
                            path = sound_conf['files'][0]
                    elif sound_conf['type'] == 'indexed':
                        # ayayay....
                        if param and 'id' in param and param['id'] in sound_conf['map']:
                            path = sound_conf['map'][param['id']]

                    if path != '':
                        self.sound_issuer.play(path, volume, loop, delay)
                elif 'stoploop' in command:
                    self.sound_issuer.stop_loop()

    def __thread(self):
        pass

    def create_player_sound(self, player):
        if 'id' in player:
            player_id = int(player['id'])
            if player_id not in self.map_sound_files['player']['map']:
                path = "{}players/{}.mp3".format(self.BASEPATH, player_id)
                print path
                if not os.path.isfile(path):
                    # create TTS file
                    cmd = "espeak -s110 -v{} \"{}\" --stdout | " \
                    "sox --norm --type wav - --type mp3 --rate 44100 --channels 2 " \
                    "--compression 192 \"{}\"".format("mb-de7", player['name'], path)
                    subprocess.call(cmd, shell=True)
                    Logger.info("ScoreTracker: TTS file generated: %s" % path)
                    self.map_sound_files['player']['map'][player_id] = path

SoundManager = SoundManagerBase()
