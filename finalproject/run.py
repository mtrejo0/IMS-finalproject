#pset6.py


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
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.core.window import Window
from kivy import metrics
from kivy.core.image import Image


from imslib.gfxutil import topleft_label, CEllipse, CRectangle, CLabelRect

from random import choice, randint



# configuration parameters:
nowbar_h = 0.2        # height of nowbar from the bottom of screen (as proportion of window height)
nowbar_w_margin = 0.1 # margin on either side of the nowbar (as proportion of window width)
time_span = 2.0       # time (in seconds) that spans the full vertical height of the Window
beat_marker_len = 0.2 # horizontal length of beat marker (as a proportion of window width)
px = metrics.dp(1) 

# convert a time value to a y-pixel value (where time==0 is on the nowbar)
def time_to_ypos(time):
    now_y = Window.height * nowbar_h
    return (Window.height)/time_span * time + now_y

def get_lane_x(lane):
    ww = Window.width

    margin = beat_marker_len * ww / 6 * 2

    origin = ww/2 - ww * beat_marker_len

    return origin + (lane+1) * margin



class MainWidget(BaseWidget):
    def __init__(self):
        super(MainWidget, self).__init__()


        gems_file = '../data/gems.txt'

        barlines_file = '../data/barline.txt'

        base = "IronMan"

        self.song_data  = SongData(gems_file)
        self.audio_ctrl = AudioController(base)

        self.barlines_data  = BarlineData(barlines_file)
        

        self.display = GameDisplay(self.song_data, self.barlines_data)

        self.canvas.add(self.display)

        self.info = topleft_label()
        self.add_widget(self.info)


        self.player = Player(self.song_data, self.audio_ctrl, self.display)

    def on_key_down(self, keycode, modifiers):
        # play / pause toggle
        if keycode[1] == 'p':
            self.audio_ctrl.toggle()

        # button down
        button_idx = lookup(keycode[1], '12345', (0,1,2,3,4))
        if button_idx != None:
            print('down', button_idx)
            self.player.on_button_down(button_idx)

        if keycode[1] == 'left':
            self.player.on_button_action_down(keycode[1])

        if keycode[1] == 'right':
            self.player.on_button_action_down(keycode[1])
        
        if keycode[1] == 'spacebar':
            self.player.on_button_action_down(keycode[1])
            

    def on_key_up(self, keycode):
        # button up
        button_idx = lookup(keycode[1], '12345', (0,1,2,3,4))
        if button_idx != None:
            self.player.on_button_up(button_idx)

        if keycode[1] == 'spacebar':
            self.player.on_button_action_up(keycode[1])

    # handle changing displayed elements when window size changes
    # This function should call GameDisplay.on_resize 
    def on_resize(self, win_size):
        self.display.on_resize(win_size)
		
    def on_update(self):
        self.audio_ctrl.on_update()

        # Note that in this system, on_update() is called with the song's current time. It does
        # NOT use dt (delta time).
        now = self.audio_ctrl.get_time()  # time of song in seconds.
        self.display.on_update(now)

        self.player.on_update(now)

        self.info.text = 'p: pause/unpause song\n'
        self.info.text += f'song time: {now:.2f}\n'
        self.info.text += f'Score: {self.player.score}\n'


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


        solo = f'../../GH Audio/{song_path}_solo'

        bg = f'../../GH Audio/{song_path}_bg'

        # song
        self.track = WaveGenerator(WaveFile(solo + ".wav"))

        self.bg = WaveGenerator(WaveFile(bg + ".wav"))


        self.mixer.add(self.track)
        self.mixer.add(self.bg)

        self.miss = WaveBuffer(f"../data/miss.wav", int(Audio.sample_rate * 0), int(Audio.sample_rate * .5))

        # start paused
        self.track.pause()
        self.bg.pause()

    # start / stop the song
    def toggle(self):
        self.track.play_toggle()
        self.bg.play_toggle()
    # mute / unmute the solo track
    def set_mute(self, mute):
        pass

    # play a sound-fx (miss sound)
    def play_miss(self):
        self.mixer.add(WaveGenerator(self.miss))
        self.track.set_gain(0)

    # return current time (in seconds) of song
    def get_time(self):
        return self.track.frame/44100

    # needed to update audio
    def on_update(self):
        self.audio.on_update()


# for parsing gem text file: return (time, lane) from a single line of text
def beat_from_line(line):
    print(line)
    time, beat = line.strip().split('\t')
    return (float(time), beat)

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
    def __init__(self, time, lane):
        super(GemDisplay, self).__init__()


        self.lane = int(lane)

        self.time = time

        self.color = Color(1,1,1)
        self.add(self.color)
        
        y = 0
        x = get_lane_x(self.lane)

        pos = (x,y)
        img = choice(['../data/piano.png', '../data/sax.png', '../data/drums.png'])

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
        self.color.a = .5

    # animate gem (position and animation) based on current time
    def on_update(self, now_time):


        ypos = time_to_ypos(self.time-now_time)

        x,_ = self.gem.cpos
        self.gem.cpos = x,ypos

        return ypos > 0 and ypos < Window.height

    def on_resize(self,win_size):

        _,y = self.gem.cpos
        x = get_lane_x(self.lane)

        
        pos = (x,y)

        self.gem.cpos = pos




# Displays a single beat marker on screen
class BarlineDisplay(InstructionGroup):
    def __init__(self, time, beat_num):
        super(BarlineDisplay, self).__init__()

        self.time = time  # the timestamp (in seconds) of this beat in the song (ie, when does this beat occur?)
        self.color = Color(hsv=(.1, .8, 1)) # color of this beat line
        self.line = Line(width = 3) # line object to be drawn / animated in on_update()

        self.add(self.color)
        self.add(self.line)

    # animate barline (position) based on current time. The value now_time is in seconds
    # and is an absolute time position (not a delta time)
    def on_update(self, now_time):

        ypos = time_to_ypos(self.time-now_time)
        x_left = Window.width /2 - beat_marker_len * Window.width
        x_right = Window.width /2 + beat_marker_len * Window.width

        self.line.points = [x_left, ypos, x_right, ypos]

        return ypos > 0 and ypos < Window.height

# Displays one button on the nowbar
class ButtonDisplay(InstructionGroup):
    def __init__(self, lane):
        super(ButtonDisplay, self).__init__()
        self.lane = lane

        x = get_lane_x(self.lane)
        y = nowbar_h* Window.height
        pos = (x,y)

        self.color = Color(1,1,1)
        self.color.a = .5
        self.add(self.color)

        self.button = CRectangle(cpos=pos, csize=(50,50))

        self.add(self.button)
        
        self.line = Line(points = [x,Window.height,x,0])
        self.add(self.line)


    # displays when button is pressed down
    def on_down(self):
        self.color.a = 1

    # back to normal state
    def on_up(self):
        self.color.a = .5

    # modify object positions based on new window size
    def on_resize(self, win_size):

        x = get_lane_x(self.lane)
        y = nowbar_h * Window.height

        pos = (x,y)

        self.button.cpos = pos

        self.line.points = [x,Window.height,x,0]


class Goat(InstructionGroup):
    def __init__(self):
        super(Goat, self).__init__()
        self.lane = 0

        
        x = get_lane_x(self.lane)
        y = nowbar_h* Window.height

        self.color = Color(1,1,1)
        self.add(self.color)
        self.avatar = CRectangle(cpos=(x,y), csize=(50*px, 50*px), texture=Image('../data/goat.png').texture)

        self.add(self.avatar)


    def on_update(self):
        x = get_lane_x(self.lane)
        y = nowbar_h* Window.height
        self.avatar.cpos = (x,y)
    

    def on_button_down(self, keycode):
        if keycode == "left":
            self.lane -= 1
            self.lane = max(0, self.lane)

        if keycode == "right":

            self.lane += 1
            self.lane = min(4, self.lane)

        if keycode == "spacebar":
            self.color.rgb = (1,0,0)

    def on_button_up(self, keycode):
        if keycode == "spacebar":
            self.color.rgb = (1,1,1)

        


class GameDisplay(InstructionGroup):
    def __init__(self, song_data, barline_data):
        super(GameDisplay, self).__init__()


        self.beat_data = song_data.get_beats()

        self.barline_data = barline_data.get_barlines()

        self.beats = [GemDisplay(*b) for b in self.beat_data]
        for b in self.beats:
            self.add(b)

        self.barlines = [BarlineDisplay(*b) for b in self.barline_data]
        for b in self.barlines:
            self.add(b)

        color = Color(1, 1, 1) # color of this beat line
        left_coord = [nowbar_w_margin*Window.width,nowbar_h* Window.height]
        right_coord = [Window.width - nowbar_w_margin*Window.width,nowbar_h* Window.height]
        
        self.now_bar = Line(points=left_coord+right_coord, width = 3) # line object to be drawn / animated in on_update()
        
        self.add(color)
        self.add(self.now_bar)

        self.buttons = []

        for i in range(5):
            button = ButtonDisplay(i)
            self.buttons.append(button)
            self.add(button)


        self.goat = Goat()

        self.add(self.goat)


        # test: print first 4 beat locations:
        print('Window size is:', Window.size)
        for b in self.beat_data[:4]:
            t = b[0]
            y = time_to_ypos(t)
            print(f'time:{t:.3f}, y-pixel:{y:.0f}')

    # when the window size changes:
    def on_resize(self, win_size):
        left_coord = [nowbar_w_margin*Window.width,nowbar_h* Window.height]
        right_coord = [Window.width - nowbar_w_margin*Window.width,nowbar_h* Window.height]
        self.now_bar.points=left_coord+right_coord

        for each in self.beats:
            each.on_resize(win_size)

        for each in self.buttons:
            each.on_resize(win_size)


    def get_num_object(self):
        return len(self.children)

    # call every frame to handle animation needs. The value now_time is in seconds
    # and is an absolute time position (not a delta time)
    def on_update(self, now_time):

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
        


    # called by Player when succeeded in hitting this gem.
    def gem_hit(self, gem_idx):
        pass

    # called by Player on pass or miss.
    def gem_pass(self, gem_idx):
        pass

    # called by Player on button down
    def on_button_down(self, lane):
        self.buttons[lane].on_down()

        for each in self.children:
            if each in self.beats and each.lane == lane:
                button = self.buttons[lane]

                _,button_y = button.button.cpos

                _,gem_y = each.gem.cpos

                if abs(gem_y - button_y) < 50:
                    each.on_hit()
                    return True
        
        for each in self.children:
            if each in self.beats and each.lane == lane:
                button = self.buttons[lane]

                _,button_y = button.button.cpos

                _,gem_y = each.gem.cpos

                if abs(gem_y - button_y) < 50:
                    each.on_hit()
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
    def __init__(self, song_data, audio_ctrl, display):
        super(Player, self).__init__()

        self.display = display
        self.audio_ctrl = audio_ctrl
        self.song_data = song_data
        self.score = 0

        

    # called by MainWidget
    def on_button_down(self, lane):
        if self.display.on_button_down(lane):
            self.audio_ctrl.track.set_gain(1)
            self.score += 1
        
    # called by MainWidget
    def on_button_up(self, lane):
        self.display.on_button_up(lane)

    def on_button_action_down(self, keycode):
        self.display.goat.on_button_down(keycode)

        if keycode == "spacebar":
            if self.display.on_button_down(self.display.goat.lane):
                self.audio_ctrl.track.set_gain(1)
                self.score += 1
        
    def on_button_action_up(self, keycode):
        self.display.goat.on_button_up(keycode)

        if keycode == "spacebar":
            self.display.on_button_up(self.display.goat.lane)

    # needed to check for pass gems (ie, went past the slop window)
    def on_update(self, time):

        for each in self.display.children:
            if each in self.display.beats:
                button = self.display.buttons[each.lane]

                _,button_y = button.button.cpos

                _,gem_y = each.gem.cpos

                if button_y - gem_y > 50 and each.hit == False:
                    each.on_pass()
                    self.audio_ctrl.play_miss()


if __name__ == "__main__":
    run(MainWidget())
