# Activity Selection Board
# github.com/davidsmakerworks/activity-board

# MIT License

# Copyright (c) 2020 David Rice

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Sound effects created by Little Robot Sound Factory
# (www.littlerobotsoundfactory.com)
# and licensed under Creative Commons
# (creativecommons.org/licenses/by/3.0/)


import random
import sys
import time

from enum import Enum, unique

import pygame
import buttons

from pygame.locals import *


# TODO: Move these to a configuration file

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

DOOR_WIDTH = 480
DOOR_HEIGHT = 360

DOOR_FONT_SIZE = 260
ACTIVITY_SMALL_FONT_SIZE = 65
ACTIVITY_FULL_FONT_SIZE = 240

DOORS_HORIZ = 4
DOORS_VERT = 3

DOOR_OPEN_DELAY = 0.02
DOOR_REVEAL_DELAY = 0.075

SCREEN_BGCOLOR = Color('black')

DOOR_BGCOLOR = Color('red')
DOOR_OVALCOLOR = Color('yellow')
DOOR_NUMCOLOR = Color('red')
DOOR_SELCOLOR = Color('orange')
DOOR_OPENCOLOR = Color('red')

TEXT_COLOR = Color('white')
REVEAL_COLOR = Color('gray')

@unique
class State(Enum):
    START = 0 # Read activities and initialize door list
    STARTING = 1 # Animated startup (draw one door at a time)
    DRAW = 2 # Draw all doors on screen
    SELECT = 3 # Interactive selection of door to open
    DISPLAY = 4 # Displaying activity in full screen
    REVEAL_ALL = 5 # Revealing all doors to show what was behind them
    SHUTDOWN = 6 # Shutting down


# This is currently hard coded to work only with a 1920x1080 screen and a 4x3
# arrangement of doors.
#
# TODO: Generalize resolution and size of door grid
class Screen:
    def __init__(self, width=SCREEN_WIDTH, height=SCREEN_HEIGHT):
        self.width = width
        self.height = height

        self.surface = pygame.display.set_mode(
                (self.width, self.height), flags=FULLSCREEN)

class Door:
    @property
    def screen_x(self):
        return (self.index % DOORS_HORIZ) * DOOR_WIDTH


    @property
    def screen_y(self):
        return (self.index // DOORS_HORIZ) * DOOR_HEIGHT


    def __init__(
            self, index=None, number_font=None, activity_small_font=None,
            activity_full_font=None, activity=None, is_selected=False,
            is_open=False, is_revealed=False, is_hidden=False):
        self.index = index
        self.number_font = number_font
        self.activity_small_font = activity_small_font
        self.activity_full_font = activity_full_font
        self.activity = activity
        self.is_selected = is_selected
        self.is_open = is_open
        self.is_revealed = is_revealed
        self.is_hidden = is_hidden


    # TODO: Remove magic numbers related to ellipse size
    # and selection rectangle
    def _get_door_surface(self):
        surf = pygame.Surface((DOOR_WIDTH, DOOR_HEIGHT))

        if self.is_hidden:
            surf.fill(SCREEN_BGCOLOR)
        elif self.is_open and not self.is_revealed:
            if self.is_selected:
                surf.fill(DOOR_SELCOLOR)
            else:
                surf.fill(SCREEN_BGCOLOR)

            surf.fill(SCREEN_BGCOLOR, Rect(20, 20, 440, 320))

            pygame.draw.line(
                    surf, DOOR_OPENCOLOR, (20, 40),
                    (DOOR_WIDTH - 20, DOOR_HEIGHT - 40), 40)
            pygame.draw.line(
                    surf, DOOR_OPENCOLOR, (20, DOOR_HEIGHT - 40),
                    (DOOR_WIDTH - 20, 40), 40)
        elif self.is_revealed:
            text_color = TEXT_COLOR if self.is_open else REVEAL_COLOR

            activity_small_surface = self._create_text_surface(
                    self.activity, self.activity_small_font, 8,
                    text_color=text_color)

            small_rect = activity_small_surface.get_rect()

            surf.fill(SCREEN_BGCOLOR)
            surf.blit(
                    activity_small_surface,
                    ((DOOR_WIDTH // 2) - (small_rect.width // 2),
                    (DOOR_HEIGHT // 2) - (small_rect.height // 2)))
        else:
            if self.is_selected:
                surf.fill(DOOR_SELCOLOR)
            else:
                surf.fill(SCREEN_BGCOLOR)

            surf.fill(DOOR_BGCOLOR, Rect(20, 20, 440, 320))

            pygame.draw.ellipse(surf, DOOR_OVALCOLOR, Rect(40, 40, 400, 280))

            number_surface = self.number_font.render(
                    str(self.index + 1), True, DOOR_NUMCOLOR)
            number_rect = number_surface.get_rect()

            surf.blit(
                    number_surface,
                    ((DOOR_WIDTH // 2) - (number_rect.width // 2),
                    (DOOR_HEIGHT // 2) - (number_rect.height // 2) + 10))

        return surf


    # TODO: Implement word wrap
    def _create_text_surface(self, text, font, line_spacing, text_color=None):
        if not text_color:
            text_color = TEXT_COLOR

        text_lines = text.split('`')

        text_surfaces = list()

        for line in text_lines:
            text_surfaces.append(font.render(line, True, text_color))

        total_height = 0
        max_width = 0

        for ts in text_surfaces:
            size = ts.get_rect()

            total_height += size.height

            if size.width > max_width:
                max_width = size.width

        total_height += (len(text_surfaces) - 1) * line_spacing

        text_surface = pygame.Surface((max_width, total_height))

        y = 0

        for ts in text_surfaces:
            line_rect = ts.get_rect()

            line_rect.center = (max_width // 2, line_rect.height // 2)

            text_surface.blit(ts, ((max_width - line_rect.width) // 2, y))

            y = y + line_rect.height + line_spacing

        return text_surface


    def draw(self, dest_surface):
        dest_surface.blit(
                self._get_door_surface(),
                (self.screen_x, self.screen_y))


    # TODO: Make this part of _get_door_surface and
    # make revealed portion a property of the class
    def animate_open(self, dest_surface):
        activity_small_surface = self._create_text_surface(
                self.activity, self.activity_small_font, 8)
        activity_full_surface = self._create_text_surface(
                self.activity, self.activity_full_font, 16)

        small_rect = activity_small_surface.get_rect()

        door_surface = pygame.Surface((DOOR_WIDTH, DOOR_HEIGHT))
        door_surface.fill(SCREEN_BGCOLOR)
        door_surface.blit(
                activity_small_surface,
                ((DOOR_WIDTH // 2) - (small_rect.width // 2),
                (DOOR_HEIGHT // 2) - (small_rect.height // 2)))

        for revealed_width in range(8, DOOR_WIDTH + 1, 8):
            offset = revealed_width // 2
            left = (self.screen_x + (DOOR_WIDTH // 2)) - offset
            area_rect = Rect(
                    (DOOR_WIDTH // 2 - offset), 0,
                    revealed_width, DOOR_HEIGHT)

            dest_surface.blit(door_surface, (left, self.screen_y), area_rect)

            pygame.display.update()

            time.sleep(DOOR_OPEN_DELAY)

        pygame.display.update()

        dest_surface.fill(SCREEN_BGCOLOR)

        full_rect = activity_full_surface.get_rect()
        dest_surface.blit(
                activity_full_surface,
                ((SCREEN_WIDTH // 2) - (full_rect.width // 2),
                (SCREEN_HEIGHT // 2) - (full_rect.height // 2)))

        pygame.display.update()


def get_door_index(x, y):
    door_index = (y * DOORS_HORIZ) + x

    return door_index


def update_door_selection(x, y, movement):
    x = x + movement[0]
    # Y axis is inverted with respect to our coordinate system
    y = y - movement[1]

    if x < 0:
        x = 0
    elif x > (DOORS_HORIZ - 1):
        x = DOORS_HORIZ - 1

    if y < 0:
        y = 0
    elif y > (DOORS_VERT - 1):
        y = DOORS_VERT - 1

    return (x, y)


def read_activities(file_name):
    activities = []

    with open(file_name, 'r') as activity_file:
        for line in activity_file:
            activities.append(line.strip())

    return activities


def build_door_list(activities, doors_hidden=True):
    doors = []

    door_font = pygame.font.Font('freesansbold.ttf', DOOR_FONT_SIZE)
    activity_small_font = pygame.font.Font(
            'freesansbold.ttf', ACTIVITY_SMALL_FONT_SIZE)
    activity_full_font = pygame.font.Font(
            'freesansbold.ttf', ACTIVITY_FULL_FONT_SIZE)

    for i in range(DOORS_HORIZ * DOORS_VERT):
        activity = random.choice(activities)
        activities.remove(activity)

        doors.append(Door(
                index=i,
                number_font=door_font,
                activity_small_font=activity_small_font,
                activity_full_font=activity_full_font,
                activity=activity,
                is_hidden=doors_hidden))

    return doors


# TODO: Evaluate moving pygame event loop outside of state machine loop
def main():
    debug = False
    debug2 = False

    if len(sys.argv) > 1:
        if sys.argv[1].lower() == 'debug':
            debug = True
        elif sys.argv[1].lower() == 'debug2':
            debug = True
            debug2 = True

    pygame.mixer.init(buffer=512)
    pygame.init()

    random.seed()

    pygame.mouse.set_visible(False)

    if pygame.joystick.get_count():
        js = pygame.joystick.Joystick(0)
        js.init()
    else:
        raise RuntimeError('Joystick not found')

    move_sounds = []

    for i in range(1,5): # i.e., integers 1 to 4 due to exclusive stop value
        move_sounds.append(pygame.mixer.Sound(f'move{i}.wav'))

    open_sound = pygame.mixer.Sound('opendoor.wav')
    oops_sound = pygame.mixer.Sound('oops.wav')
    start_sound = pygame.mixer.Sound('start.wav')
    reveal_all_sound = pygame.mixer.Sound('revealall.wav')

    screen = Screen(SCREEN_WIDTH, SCREEN_HEIGHT)

    state = State.START

    while True:
        if state == State.START:
            activities = read_activities('activities.txt')

            doors = build_door_list(activities)

            doors[0].is_selected = True

            sel_x = 0
            sel_y = 0
            selected_door = 0

            # List of all door numbers to track which ones have been
            # shown during startup animation
            show_list = list(range(DOORS_HORIZ * DOORS_VERT))

            start_sound.play()

            all_revealed = False
            update_needed = True

            state = State.STARTING
        elif state == State.STARTING:
            time.sleep(DOOR_REVEAL_DELAY)

            if show_list:
                for d in doors:
                    d.draw(screen.surface)

                show_door = random.choice(show_list)
                doors[show_door].is_hidden = False
                show_list.remove(show_door)

                update_needed = True
            else:
                state = State.DRAW
        elif state == State.DRAW:
            for d in doors:
                d.draw(screen.surface)

            update_needed = True

            if all_revealed:
                state = State.REVEAL_ALL
            else:
                state = State.SELECT
        elif state == State.SELECT:
            for event in pygame.event.get():
                if debug2:
                    print(f'Pygame event type {event.type}')
                if event.type == JOYBUTTONDOWN:
                    if debug:
                        print(f'Joystick button {event.button} pressed')

                    if event.button == buttons.BTN_A:
                        if not doors[selected_door].is_open:
                            open_sound.play()

                            doors[selected_door].is_open = True
                            doors[selected_door].animate_open(screen.surface)

                            state = State.DISPLAY
                        else:
                            oops_sound.play()

                        pygame.event.clear()
                    elif event.button == buttons.BTN_Y:
                        if js.get_button(buttons.BTN_X):
                            reveal_all_sound.play()

                            for d in doors:
                                d.is_revealed = True

                            all_revealed = True

                            state = State.DRAW
                    elif event.button == buttons.BTN_START:
                        state = State.START
                    elif event.button == buttons.BTN_BACK:
                        if (js.get_button(buttons.BTN_RB)
                                and js.get_button(buttons.BTN_LB)):
                            state = State.SHUTDOWN
                elif event.type == JOYHATMOTION:
                    if debug:
                        print(f'Joystick hat motion {event.value}')

                    if event.value[0] or event.value[1]:
                        prev_selected = selected_door

                        doors[selected_door].is_selected = False

                        (sel_x, sel_y) = update_door_selection(
                                sel_x, sel_y, event.value)
                        selected_door = get_door_index(sel_x, sel_y)

                        doors[selected_door].is_selected = True

                        if selected_door != prev_selected:
                            move_sound = random.choice(move_sounds)
                            move_sound.play()

                        state = State.DRAW

                        pygame.event.clear()
                elif event.type == QUIT:
                    state = State.SHUTDOWN
        elif state == State.DISPLAY:
            for event in pygame.event.get():
                if event.type == JOYBUTTONDOWN:
                    if event.button == buttons.BTN_B:
                        screen.surface.fill(SCREEN_BGCOLOR)

                        state = State.DRAW

                        pygame.event.clear()
                    elif event.button == buttons.BTN_BACK:
                        if (js.get_button(buttons.BTN_RB)
                                and js.get_button(buttons.BTN_LB)):
                            state = State.SHUTDOWN
        elif state == State.REVEAL_ALL:
            for event in pygame.event.get():
                if event.type == JOYBUTTONDOWN:
                    if event.button == buttons.BTN_START:
                        state = State.START
                    elif event.button == buttons.BTN_BACK:
                        if (js.get_button(buttons.BTN_RB)
                                and js.get_button(buttons.BTN_LB)):
                            state = State.SHUTDOWN
        elif state == State.SHUTDOWN:
            pygame.quit()
            sys.exit()
        else:
            pygame.quit()
            raise RuntimeError('Invalid state in main loop')

        if update_needed:
            pygame.display.update()
            update_needed = False

    pygame.quit()

if __name__ == '__main__':
    main()
