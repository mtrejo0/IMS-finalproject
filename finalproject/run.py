from re import L, S
import sys, os
from tkinter import Button
sys.path.insert(0, os.path.abspath('..'))

from imslib.core import BaseWidget, run, lookup
from imslib.audio import Audio
from imslib.mixer import Mixer
from imslib.wavegen import WaveGenerator
from imslib.wavesrc import WaveBuffer, WaveFile

from kivy.graphics.instructions import InstructionGroup
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.core.window import Window
from kivy import metrics
from kivy.core.image import Image
from kivy.properties import ObjectProperty, ListProperty


from imslib.gfxutil import topleft_label, CEllipse, CRectangle, CLabelRect

from random import choice, randint, random


# configuration parameters:
nowbar_w = 0.025        
nowbar_laser = .15
nowbar_h_margin = 0.1 # margin on either side of the nowbar (as proportion of window width)
time_span = 2.0       # time (in seconds) that spans the full vertical height of the Window
beat_marker_len = 0.2 # horizontal length of beat marker (as a proportion of window width)
px = metrics.dp(1) 

def time_to_xpos(time):
    now_x = Window.width * nowbar_laser
    return (Window.width)/time_span * time + now_x


def get_lane_y(lane):
    wh = Window.height

    margin = wh / 6

    origin = 0

    return origin + (lane+1) * margin
def get_lane(y):
    wh = Window.height
    margin = wh/5

    return int(y//margin)



class MainWidget(BaseWidget):
    # fire / trigger axis
    FIRE = (2, 5)
    STOP_FIRE = -32767

    # min value for user to actually trigger axis
    OFFSET = 15000

    # current values + event instance
    VALUES = ListProperty([])
    HOLD = ObjectProperty(None)

    def __init__(self):
        super(MainWidget, self).__init__()

        # bind all the controller input
        Window.bind(on_joy_hat=self.on_joy_hat)
        Window.bind(on_joy_ball=self.on_joy_ball)
        Window.bind(on_joy_axis=self.on_joy_axis)
        Window.bind(on_joy_button_up=self.on_joy_button_up)
        Window.bind(on_joy_button_down=self.on_joy_button_down)


        gems_file = '../data/starfox_melody_gems_firstdraft.txt'

        barlines_file = '../data/barline.txt'

        base = "corneria-2"

        self.song_data  = SongData(gems_file)
        self.audio_ctrl = AudioController(base)

        self.barlines_data  = BarlineData(barlines_file)
        

        self.display1 = GameDisplay(self.song_data, self.barlines_data, self.audio_ctrl, 1)
        self.display2 = GameDisplay(self.song_data, self.barlines_data, self.audio_ctrl, 2)
        
        self.canvas.add(self.display1)
        self.canvas.add(self.display2)

        self.info = topleft_label()
        self.add_widget(self.info)

        # state varaible for movement

        self.player1 = Player(self.song_data, self.audio_ctrl, self.display1, 1, self.boss_incoming, self.boss_outgoing, self.boss_flip)
        self.player2 = Player(self.song_data, self.audio_ctrl, self.display2, 2, self.boss_incoming, self.boss_outgoing, self.boss_flip)

    # functions for reading gamepad inputs 
    # show values in console
    def print_values(self, *args):
        print(self.VALUES)

    def joy_motion(self, event, id, axis, value):
        # HAT first, returns max values
        if isinstance(value, tuple):
            if not value[0] and not value[1]:
                Clock.unschedule(self.HOLD)
            else:
                self.VALUES = [event, id, axis, value]
                self.HOLD = Clock.schedule_interval(self.print_values, 0)
            
            return

        # unschedule if at zero or at minimum (FIRE)
        if axis in self.FIRE and value < self.STOP_FIRE or abs(value) < self.OFFSET:
            Clock.unschedule(self.HOLD)
            self.player1.on_button_action_up('down')
            self.player1.on_button_action_up('up')
            return
        elif abs(value) < self.OFFSET or self.HOLD:
            Clock.unschedule(self.HOLD)

        # schedule if over OFFSET (to prevent accidental event with low value)
        if (axis in self.FIRE and value > self.STOP_FIRE or
                axis not in self.FIRE and abs(value) >= self.OFFSET):
            self.VALUES = [event, id, axis, value]
            self.HOLD = Clock.schedule_interval(self.print_values, 0)
            if value > 15000:
                self.player1.on_button_action_down('down')
            elif value < -15000:
                self.player1.on_button_action_down('up')

    # replace window instance with identifier
    def on_joy_axis(self, win, stickid, axisid, value):
        self.joy_motion('axis', stickid, axisid, value)

    def on_joy_ball(self, win, stickid, ballid, xvalue, yvalue):
        self.joy_motion('ball', stickid, ballid, (xvalue, yvalue))

    def on_joy_hat(self, win, stickid, hatid, value):
        self.joy_motion('hat', stickid, hatid, value)

    def on_joy_button_down(self, win, stickid, buttonid):
        self.player1.on_button_action_down('spacebar')

    def on_joy_button_up(self, win, stickid, buttonid):
        self.player1.on_button_action_up('spacebar')

    def on_key_down(self, keycode, modifiers):
        # play / pause toggle
        if keycode[1] == 'p':
            self.audio_ctrl.toggle()

        if keycode[1] == 'down':
            self.player2.on_button_action_down(keycode[1])

        if keycode[1] == 'up':
            self.player2.on_button_action_down(keycode[1])
        
        if keycode[1] == 'spacebar':
            self.player2.on_button_action_down(keycode[1])
            

    def on_key_up(self, keycode):
        # button up
        if keycode[1] == 'spacebar':
            self.player2.on_button_action_up(keycode[1])
        if keycode[1] == 'up':
            self.player2.on_button_action_up(keycode[1])
        if keycode[1] == 'down':
            self.player2.on_button_action_up(keycode[1])

    # handle changing displayed elements when window size changes
    # This function should call GameDisplay.on_resize 
    def on_resize(self, win_size):
        self.display1.on_resize(win_size)
        self.display2.on_resize(win_size)
		
    def on_update(self):
        self.audio_ctrl.on_update()

        # Note that in this system, on_update() is called with the song's current time. It does
        # NOT use dt (delta time).
        now = self.audio_ctrl.get_time()  # time of song in seconds.
        self.display1.on_update(now)
        self.display2.on_update(now)


        self.player1.on_update(now)
        self.player2.on_update(now)

        self.info.text = 'p: pause/unpause song\n'
        self.info.text += f'song time: {now:.2f}\n'
        self.info.text += f'P1: {self.player1.score}\n'
        self.info.text += f'P2: {self.player2.score}\n'

    def boss_incoming(self):
        self.display1.remove_beats()
        self.display1.goat.hide()
        self.display2.boss_incoming()

    def boss_flip(self):
        if len(self.display1.beats):
            self.display1.remove_beats()
            self.display1.goat.hide()
            self.display2.goat.show()
            self.display2.playback(self.display1.playback_gems)
        else:
            self.display2.remove_beats()
            self.display2.goat.hide()
            self.display1.goat.show()
            self.display1.playback(self.display2.playback_gems)

    def boss_outgoing(self):
        self.display1.boss_outgoing()
        self.display2.boss_outgoing()


# Handles everything about Audio.
#   creates the main Audio object
#   load and plays solo and bg audio tracks
#   creates audio buffers for sound-fx (miss sound)
#   functions as the clock (returns song time elapsed)
class AudioController(object):
    def __init__(self, song_path):
        super(AudioController, self).__init__()
        self.audio = Audio(2)
        self.mixer = Mixer()
        self.audio.set_generator(self.mixer)


        solo = f'../data/{song_path}-bass'

        bg = f'../data/{song_path}-melody'

        rest = f'../data/{song_path}-rest'

        # song
        self.track = WaveGenerator(WaveFile(solo + ".wav"))

        self.bg = WaveGenerator(WaveFile(bg + ".wav"))

        self.rest = WaveGenerator(WaveFile(rest + ".wav"))


        self.mixer.add(self.track)
        self.mixer.add(self.bg)
        self.mixer.add(self.rest)

        self.miss = WaveBuffer(f"../data/miss.wav", int(Audio.sample_rate * 0), int(Audio.sample_rate * .5))

        self.laser = WaveBuffer(f"../data/laser.wav", int(Audio.sample_rate * .5), int(Audio.sample_rate * .1))

        # start paused
        self.track.pause()
        self.bg.pause()
        self.rest.pause()

    # start / stop the song
    def toggle(self):
        self.track.play_toggle()
        self.bg.play_toggle()
        self.rest.play_toggle()
    # mute / unmute the solo track
    def set_mute(self, mute):
        pass

    # play a sound-fx (miss sound)
    def play_miss(self):
        self.mixer.add(WaveGenerator(self.miss))
        self.track.set_gain(0)

    def play_laser(self):
        self.mixer.add(WaveGenerator(self.laser))

    # return current time (in seconds) of song
    def get_time(self):
        return self.track.frame/44100

    # needed to update audio
    def reset(self):
        self.track.reset()
        self.bg.reset()
        self.rest.reset()

    # needed to update audio
    def on_update(self):
        self.audio.on_update()


# for parsing gem text file: return (time, lane) from a single line of text
def beat_from_line(line):
    time, beat = line.strip().split('\t')
    return (float(time), int(beat) - 1)

# Holds data beats
class SongData(object):
    def __init__(self, filepath):
        super(SongData, self).__init__()
        self.beats = []

        lines = open(filepath).readlines()
        self.beats = [beat_from_line(l) for l in lines]

    def get_beats(self):
        return self.beats


    # TODO: figure out how gem and barline data should be represented and accessed...

class BarlineData(object):
    def __init__(self, filepath):
        super(BarlineData, self).__init__()

        # self.barlines = regions_from_file(filepath)

        guess_distance = 0.922465470909

        guess = [guess_distance*i for i in range(100)]

        self.barlines = []

        for i in range(len(guess)):
            self.barlines.append((guess[i],i))
        

    def get_barlines(self):
        return self.barlines
        

# Display for a single gem at a position with a hue or color
class GemDisplay(InstructionGroup):
    def __init__(self, time, lane, id = 0):
        super(GemDisplay, self).__init__()


        self.lane = int(lane)

        self.time = time

        self.id = id

        if self.id == 0:
            self.color = Color(1,1,1)
        elif self.id == 1:
            self.color = Color(1,.5,.5)
        elif self.id == 2:
            self.color = Color(.5,.5,1)
        self.add(self.color)
        
        y = get_lane_y(self.lane)
        x = 0

        pos = (x,y)
        img = choice(['../data/piano.png', '../data/drums.png'])

        self.gem = CRectangle(cpos=pos, csize=(50*px, 50*px), texture=Image(img).texture)
        
        self.add(self.gem)
        self.hit = False


    # change to display this gem being hit
    def on_hit(self):
        self.color.rgb = (0,0,0)
        self.hit = True

    # change to display a passed or missed gem
    def on_pass(self):
        self.color.rgb = (1,0,0)
        if self.color.a == 1:
            self.color.a = .5

    # animate gem (position and animation) based on current time
    def on_update(self, now_time):
        xpos = time_to_xpos(self.time-now_time)

        _,y = self.gem.cpos
        self.gem.cpos = xpos,y

        return xpos > 0 and xpos < Window.width

    def on_resize(self,win_size):
        x,_ = self.gem.cpos
        y = get_lane_y(self.lane)
        pos = (x,y)
        self.gem.cpos = pos




# Displays a single beat marker on screen
class BarlineDisplay(InstructionGroup):
    def __init__(self, time, beat_num):
        super(BarlineDisplay, self).__init__()

        self.time = time  # the timestamp (in seconds) of this beat in the song (ie, when does this beat occur?)
        self.color = Color(hsv=(.1, .8, 1)) # color of this beat line
        self.line = Line(width = 1) # line object to be drawn / animated in on_update()

        self.add(self.color)
        self.add(self.line)

    # animate barline (position) based on current time. The value now_time is in seconds
    # and is an absolute time position (not a delta time)
    def on_update(self, now_time):


        xpos = time_to_xpos(self.time-now_time)

        self.line.points = [xpos, 0, xpos, Window.height]

        return xpos > 0 and xpos < Window.width

# Displays one button on the nowbar
class ButtonDisplay(InstructionGroup):
    def __init__(self, lane):
        super(ButtonDisplay, self).__init__()
        self.lane = lane

        x = nowbar_w* Window.width
        y = get_lane_y(self.lane)


        pos = (x,y)

        self.color = Color(1,1,1)
        self.color.a = 0
        self.add(self.color)

        self.button = CRectangle(cpos=pos, csize=(50,50))

        self.add(self.button)
        
        self.linecolor = Color(1,0,0)
        self.linecolor.a = 0
        self.add(self.linecolor)
        self.line = Line(points = [Window.width*nowbar_laser,y,Window.width*nowbar_w,y], width = 3)
        self.add(self.line)


        self.linecolor2 = Color(1,1,1)
        self.linecolor2.a = 0
        self.add(self.linecolor2)
        self.line2 = Line(points = [Window.width*nowbar_laser,y,Window.width*nowbar_w,y], width = 1.5)
        self.add(self.line2)


    # displays when button is pressed down
    def on_down(self,y):
        self.linecolor.a = 1
        self.linecolor2.a = 1
        self.line2.points = (Window.width*nowbar_laser,y,Window.width*nowbar_w,y)
        self.line.points = (Window.width*nowbar_laser,y,Window.width*nowbar_w,y)

    # back to normal state
    def on_up(self,):
        self.linecolor.a = 0
        self.linecolor2.a = 0

    # modify object positions based on new window size
    def on_resize(self, win_size):

        x = nowbar_w* Window.width
        y = get_lane_y(self.lane)

        pos = (x,y)

        self.button.cpos = pos

        self.line.points = [Window.width*nowbar_laser,y,Window.width*nowbar_w,y]
        self.line2.points = [Window.width*nowbar_laser,y,Window.width*nowbar_w,y]


class Goat(InstructionGroup):
    def __init__(self, id):
        super(Goat, self).__init__()

        self.id = id
        self.lane = 0

        x = nowbar_w* Window.width
        self.y = Window.height/2

        self.color = self.goat_color(self.id)

        self.add(self.color)
        self.avatar = CRectangle(cpos=(x,self.y), csize=(50*px, 50*px), texture=Image('../data/goat.png').texture)
        
        self.add(self.avatar)

        # self.cross_color = None
        # if self.id == 1:
        #     self.cross_color = Color(1,0,0)
        # if self.id == 2:
        #     self.cross_color = Color(0,0,1)

        # self.add(self.cross_color)

        self.cross = CRectangle(cpos=(nowbar_laser* Window.width,Window.height/2), csize=(10*px, 10*px))

        self.add(self.cross)

        self.move = "n"

    def goat_color(self, id):
        if id == 1:
            return Color(1,.5,.5)
        if id == 2:
            return Color(.5,.5,1)
        
    def on_update(self):
        x = nowbar_w* Window.width
        # move based on state
        if self.move == "u":
            self.y = self.y + 20
        elif self.move == "d":
            self.y = self.y-20
        elif self.move == "n":
            self.y = self.y

        # loop around the screen
        if self.y < 0:
            self.y = Window.height
        elif self.y > Window.height:
            self.y = 0

        # define the lane to hit the gem
        self.lane = get_lane(self.y)

        # set position of goat and target
        self.avatar.cpos = (x,self.y)
        self.cross.cpos = (nowbar_laser* Window.width,self.y)
        
    

    def on_button_down(self, keycode):
        if keycode == "down":
            self.move = "d"

        if keycode == "up":
            self.move = "u"


    def on_button_up(self, keycode):
        self.move = "n"

    def hide(self):
        self.color.a = 0
    
    def show(self):
        self.color.a = 1

        


class GameDisplay(InstructionGroup):
    def __init__(self, song_data, barline_data, audio_ctrl, id):
        super(GameDisplay, self).__init__()


        self.id = id

        self.stars = []
        for i in range(500):

            color = Color(1,1,1)
            color.a = random()
            size = randint(0,3)
            pos = (randint(0,Window.width), randint(0,Window.height))

            star = CEllipse(cpos=pos, csize=(size*px, size*px))

            self.add(color)
            self.add(star)

            self.stars.append([star, color.a])


        self.beat_data = song_data.get_beats()

        self.barline_data = barline_data.get_barlines()

        


        self.buttons = []

        for i in range(5):
            button = ButtonDisplay(i)
            self.buttons.append(button)
            self.add(button)


        self.goat = Goat(self.id)

        self.add(self.goat)

        self.state = "normal"

        self.label = None
        self.boss_count = 0

        self.now_time = 0

        self.add(Color(1,1,1))
        self.boss = CRectangle(cpos=(10000,10000), csize=(100*px, 100*px), texture=Image('../data/dog.png').texture)
        self.add(self.boss)


        self.audio_ctrl = audio_ctrl



        self.add_normal_beats()

        self.barlines = [BarlineDisplay(*b) for b in self.barline_data]
        for b in self.barlines:
            self.add(b)

        self.playback_gems = []

    # when the window size changes:
    def on_resize(self, win_size):
        
        for each in self.beats:
            each.on_resize(win_size)

        for each in self.buttons:
            each.on_resize(win_size)

        for each in self.stars:
            if random() < .2:
                each[0].cpos = (randint(0,Window.width), randint(0,Window.height))


    def get_num_object(self):
        return len(self.children)
    
    def remove_beats(self):
        beats = self.beats.copy()
        self.beats = []
        for b in beats:
            self.remove(b)
            if b in self.children:
                self.children.remove(b)
    
    def add_boss_beats(self):
        self.beats = []
        for b in self.beat_data:
            time, lane = b

            for i in range(5):
                if int(lane) == i:
                    # skip the current gem
                    continue
                beat = GemDisplay(time, i, self.id)
                self.beats.append(beat)

    def add_normal_beats(self):

        self.beats = []
        for b in self.beat_data:
            time, lane = b
            time = time + self.now_time
            beat = GemDisplay(time, lane, self.id)
            self.beats.append(beat)

    

    def boss_incoming(self):
        self.state = "boss_incoming"
        self.remove_beats()
        self.incoming_color = Color(1,0,0)
        self.add(self.incoming_color)
        self.label = CLabelRect(text="BOSS INCOMING", cpos=(Window.width/2,Window.height/2), font_size=21)
        self.add(self.label)


        if self.goat.id == 1:
            self.add(self.goat.goat_color(2))
        else:
            self.add(self.goat.goat_color(1))

        self.taken = CRectangle(cpos=(Window.width - Window.width/8, Window.height/4), csize=(50*px, 50*px), texture=Image('../data/goat_reflected.png').texture)
        
        self.add(self.taken)

    def boss_start(self):
        self.state = "boss"
        self.remove(self.label)
        self.add_boss_beats()

        self.audio_ctrl.reset()
        self.audio_ctrl.toggle()

    def boss_outgoing(self):
        self.state = "boss_outgoing"
        # remove boss
        self.boss.set_cpos((10000,10000))

        # remove boss gems
        self.remove_beats()

        self.end_color = Color(1,0,0)
        self.add(self.incoming_color)

        self.label = CLabelRect(text="BOSS DEAFEATED", cpos=(Window.width/2,Window.height/2), font_size=21)
        self.add(self.label)

    def boss_end(self):
        self.remove(self.label)
        self.add_normal_beats()
        self.state = "normal"

    def playback(self, beats):

        self.state = "playback"

        self.remove_beats()
        self.audio_ctrl.reset()
        self.audio_ctrl.toggle()
        self.beats = []
        for b in beats:
            beat = GemDisplay(b.time, b.lane, self.id)
            self.beats.append(beat)
        

    # call every frame to handle animation needs. The value now_time is in seconds
    # and is an absolute time position (not a delta time)
    def on_update(self, now_time):

        self.now_time = now_time

        beats = self.beats.copy()
        for b in beats:
            vis = b.on_update(now_time)

            if not vis and b in self.children:
                self.children.remove(b)
            if vis and b not in self.children:
                self.children.append(b)
        

        barlines = self.barlines.copy()
        for b in barlines:
            vis = b.on_update(now_time)
            if not vis and b in self.children:
                self.children.remove(b)
            if vis and b not in self.children:
                self.children.append(b)

        self.goat.on_update()

        for each in self.stars:
            x,y = each[0].cpos
            x -= each[1]
            each[0].cpos = x,y

            if x < 0:
                each[0].cpos = (Window.width, randint(0,Window.height))
            
        if self.state == "boss_incoming":
            
            if self.boss_count % 10 == 0:
                self.incoming_color.rgb = choice([(1,1,1), (1,0,0)])
            
            if self.boss_count > 300:
                self.boss_start()
                self.boss_count = 0
            else:
                self.boss_count += 1

        if self.state == "boss_outgoing":
            
            if self.boss_count % 10 == 0:
                self.incoming_color.rgb = choice([(1,1,1), (1,0,0)])
            
            if self.boss_count > 300:
                self.boss_end()
                self.boss_count = 0
            else:
                self.boss_count += 1
        
        if self.state == "boss":
            
            # show the boss
            self.boss.set_cpos((Window.width - Window.width/8,Window.height/2))


    # called by Player when succeeded in hitting this gem.
    def gem_hit(self, gem_idx):
        pass

    # called by Player on pass or miss.
    def gem_pass(self, gem_idx):
        pass

    # called by Player on button down
    def on_button_down(self, lane, y):
        self.buttons[lane].on_down(y)

        for each in self.children:
            if each in self.beats and each.lane == lane:

                gem_x,_ = each.gem.cpos

                if abs(gem_x - Window.width*nowbar_laser) < 50:
                    each.on_hit()

                    beats = self.beats
                    for b in beats:
                        if b.time == each.time:
                            b.color.a = 0
                    self.playback_gems.append(each)
                    return True
        
        return False


    # called by Player on button up
    def on_button_up(self, lane):
        self.buttons[lane].on_up()

    # called by Player to update score
    def set_score(self, score):
        pass
        


# Handles game logic and keeps track of score.
# Controls the GameDisplay and AudioCtrl based on what happens
class Player(object):
    def __init__(self, song_data, audio_ctrl, display, id, boss_incoming, boss_outgoing, boss_flip):
        super(Player, self).__init__()

        self.display = display
        self.audio_ctrl = audio_ctrl
        self.song_data = song_data
        self.score = 0
        self.state = 'normal'
        self.id = id
        self.boss_incoming = boss_incoming
        self.boss_outgoing = boss_outgoing
        self.boss_flip = boss_flip
        

    # called by MainWidget
    def on_button_down(self, lane):
        if self.display.on_button_down(lane):
            self.audio_ctrl.track.set_gain(1)
            self.score += 1
        
    # called by MainWidget
    def on_button_up(self, lane):
        self.display.on_button_up()

    def on_button_action_down(self, keycode):
        self.display.goat.on_button_down(keycode)

        if keycode == "spacebar":
            self.audio_ctrl.play_laser()

            if self.display.on_button_down(self.display.goat.lane, self.display.goat.y):
                self.audio_ctrl.track.set_gain(1)
                self.score += 1
        
    def on_button_action_up(self, keycode):
        self.display.goat.on_button_up(keycode)

        if keycode == "spacebar":
            self.display.on_button_up(self.display.goat.lane)
        for each in self.display.buttons:
            each.on_up()

    # needed to check for pass gems (ie, went past the slop window)
    def on_update(self, time):

        for each in self.display.children:
            if each in self.display.beats:
                gem_x,_ = each.gem.cpos

                if Window.width*nowbar_laser - gem_x > 50 and each.hit == False:
                    if each.color.a == 1:
                        each.on_pass()
                        self.audio_ctrl.play_miss()
        
        if self.display.state == "normal":
            if self.score == 1:
                self.boss_incoming()
                self.score = 0
        
        if self.display.state == "boss":
            if self.score == 2:
                self.score = 0
                self.boss_flip()


            

if __name__ == "__main__":
    run(MainWidget())

# change to explosions after hitting the target
# animate the goat moving through space
# repeat the sequence played by the first player
# add in the health bar for the main level
# add in a display for the bosses health bar
# penalty for spamming
