# lecture7.py: Screen system demo. See imslib/screen.py

import sys, os
sys.path.insert(0, os.path.abspath('..'))

from imslib.core import BaseWidget, run
from imslib.gfxutil import topleft_label, resize_topleft_label, CEllipse
from imslib.screen import ScreenManager, Screen

from kivy.core.window import Window
from kivy.clock import Clock as kivyClock
from kivy.graphics import Color, Ellipse
from kivy.uix.button import Button
from kivy import metrics

# metrics allows kivy to create screen-density-independent sizes. 
# Here, 20 dp will always be the same physical size on screen regardless of resolution or OS.
# Another option is to use metrics.pt or metrics.sp. See https://kivy.org/doc/stable/api-kivy.metrics.html
font_sz = metrics.dp(20)
button_sz = metrics.dp(100)
px = metrics.dp(1)

# IntroScreen is just like a MainWidget, but it derives from Screen instead of BaseWidget.
# This allows it to work with the ScreenManager system.
class IntroScreen(Screen):
    def __init__(self, **kwargs):
        super(IntroScreen, self).__init__(always_update=True, **kwargs)

        self.info = topleft_label()
        self.info.text = "Intro Screen"
        self.info.text += "->: switch to main\n"
        self.add_widget(self.info)

        self.counter = 0

        # A button is a widget. It must be added with add_widget()
        # button.bind allows you to set up a reaction to when the button is pressed (or released).
        # It takes a function as argument. You can define one, or just use lambda as an inline function.
        # In this case, the button will cause a screen switch
        self.button = Button(text='Main', font_size=font_sz, size = (button_sz, button_sz), pos = (Window.width/2, Window.height/2))
        self.button.bind(on_release= lambda x: self.switch_to('main'))
        self.add_widget(self.button)

    def on_key_down(self, keycode, modifiers):
        if keycode[1] == 'right':
            # tell screen manager to switch from the current screen to some other screen, by name.
            print('IntroScreen next')
            self.switch_to('main')

    # this shows that on_update() gets called when this screen is active.
    # if you want on_update() called when a screen is NOT active, then pass in an extra argument:
    # always_update=True to the screen constructor.
    def on_update(self):
        self.info.text = "Intro Screen\n"
        self.info.text += "->: switch to main\n"
        self.info.text += f'fps:{kivyClock.get_fps():.1f}\n'
        self.info.text += f'counter:{self.counter}\n'
        self.counter += 1

    # on_resize always gets called - even when a screen is not active.
    def on_resize(self, win_size):
        self.button.pos = (Window.width/2, Window.height/2)
        resize_topleft_label(self.info)


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)

        self.info = topleft_label()
        self.info.text = "MainScreen\n"
        self.info.text += "->: switch to end\n"
        self.info.text += "<-: switch to intro\n"
        self.info.text += "Drag mouse to draw\n"

        self.add_widget(self.info)

        # more buttons - one to switch back to the intro screen, and one to switch to the end screen.
        self.button1 = Button(text='Intro', font_size=font_sz, size = (button_sz, button_sz), pos = (Window.width * .4, Window.height/2))
        self.button1.bind(on_release= lambda x: self.switch_to('intro'))
        self.add_widget(self.button1)

        self.button2 = Button(text='End', font_size=font_sz, size = (button_sz, button_sz), pos = (Window.width * .6, Window.height/2))
        self.button2.bind(on_release= lambda x: self.switch_to('end'))
        self.add_widget(self.button2)

        self.objects = []

    def on_key_down(self, keycode, modifiers):
        if keycode[1] == 'right':
            print('MainScreen next')
            self.switch_to('end')

        if keycode[1] == 'left':
            print('MainScreen prev')
            self.switch_to('intro')

    # simple drawing example, which only can happen when this screen is active.
    def on_touch_move(self, touch):
        # some drawing
        obj = CEllipse(cpos=touch.pos, csize=(20,20))
        self.canvas.add(obj)
        self.objects.append(obj)

    # on_enter gets called when a screen is about to enter. You can use this to setup or initialize
    # stuff on this screen. Here, we remove whatever drawing happens to be here already.
    # If you remove this code, then the previous drawing of objects will remain on screen.
    def on_enter(self):
        # this is called when a screen is about to become active.
        for o in self.objects:
            self.canvas.remove(o)
        self.objects = []


class EndScreen(Screen):
    def __init__(self, **kwargs):
        super(EndScreen, self).__init__(**kwargs)

        self.info = topleft_label()
        self.info.text = "EndScreen\n"
        self.info.text += "<-: switch main\n"
        self.add_widget(self.info)

    def on_key_down(self, keycode, modifiers):
        if keycode[1] == 'left':
            print('EndScreen prev')
            self.switch_to('main')

# create the screen manager (this is the replacement for "MainWidget")
sm = ScreenManager()

# add all screens to the manager. By default, the first screen added is the current screen.
# each screen must have a name argument (so that switch_to() will work).
# If screens need to share data between themselves, feel free to pass in additional arguments
# like a shared data class or they can even know directly about each other as needed.
sm.add_screen(IntroScreen(name='intro'))
sm.add_screen(MainScreen(name='main'))
sm.add_screen(EndScreen(name='end'))

run(sm)
