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

"""
Activity Selection Board

A fun way to select random activities.

This is currently hard coded to work only with a 1920x1080 screen and a 4x3
arrangement of doors. A USB joystick is required.

Command-line parameters:
debug -- print debugging information about all JOYBUTTONDOWN and JOYHATMOTION
    events
debug2 -- print debugging information about all pygame events

For full documentation, see github.com/davidsmakerworks/activity-board

TODO: Move configuration options to a configuration file.

TODO: Generalize size and resolution of door grid.

TODO: Implement alternative control schemes.
"""


import random
import sys
import time

from enum import Enum, unique

import pygame
import buttons

from pygame.locals import *


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
    """
    Enumeration to define states for the finite state machine in the main
    loop.

    States:
    START -- Read activities and initialize door list
    STARTING -- Animated startup (draw one door at a time)
    DRAW -- Draw all doors on screen
    SELECT -- Interactive selection of door to open
    DISPLAY -- Displaying activity in full screen
    REVEAL_ALL -- Revealing all doors to show what was behind them
    SHUTDOWN -- Shutting down
    """
    START = 0
    STARTING = 1
    DRAW = 2
    SELECT = 3
    DISPLAY = 4
    REVEAL_ALL = 5
    SHUTDOWN = 6

class ActivityBoard:
    """
    Class representing the entire activity board.

    Normally will be used to render onyo a PyGame display surface but
    can render onto any PyGame Surface obect
    """

    @property
    def num_doors(self):
        return self.doors_horiz * self.doors_vert

    @property
    def door_width(self):
        return self.surface.get_width() // self._doors_horiz

    @property
    def door_height(self):
        return self.surface.get_height() // self._doors_vert


    @property
    def screen_x(self):
        """
        Calculate and return the screen X coordinate (in pixels) of the door.
        """
        return (self.index % DOORS_HORIZ) * DOOR_WIDTH


    @property
    def screen_y(self):
        """
        Calculate and return the screen Y coordinate (in pixels) of the door.
        """
        return (self.index // DOORS_HORIZ) * DOOR_HEIGHT

    def __init__(
            self, surface, doors_horiz, doors_vert, activities=None):

        if surface.get_width() % doors_horiz != 0:
            raise RuntimeError('surface width must be an integer '
                    'multiple of doors_horiz')

        if surface.get_height() % doors_vert != 0:
            raise RuntimeError('surface height must be an integer '
                    'multiple of doors_vert')

        self.surface = surface

        self._doors_horiz = doors_horiz
        self._doors_vert = doors_vert

class TextRender:
    """
    Class representing a text object that can be rendered as a surface.
    """


    def __init__(self, text, font, line_spacing, text_color):
        """
        Create and return a pygame Surface object containing the specified
        text.

        Arguments:
        text -- text string to be rendered with newlines repersented as
            backticks (`)
        font -- pygame Font object to use for rendering text
        line_spacing -- space between lines in pixels
        text_color -- pygame Color object representing text color if the
            default is not used

        TODO: Implement word wrap.
        """
        self.text = text
        self.font = font
        self.line_spacing = line_spacing
        self.text_color = text_color
        

    def render_surface(self):
        text_lines = self.text.split('`')

        text_surfaces = []

        for line in text_lines:
            text_surfaces.append(self.font.render(line, True, self.text_color))

        total_height = 0
        max_width = 0

        for ts in text_surfaces:
            size = ts.get_rect()

            total_height += size.height

            if size.width > max_width:
                max_width = size.width

        total_height += (len(text_surfaces) - 1) * self.line_spacing

        text_surface = pygame.Surface((max_width, total_height))

        y = 0

        for ts in text_surfaces:
            line_rect = ts.get_rect()

            line_rect.center = (max_width // 2, line_rect.height // 2)

            text_surface.blit(ts, ((max_width - line_rect.width) // 2, y))

            y = y + line_rect.height + self.line_spacing

        return text_surface


class Screen:
    """
    Class representing the pyhsical screen where the board is displayed.

    Initializes the pygame display and gets the corresponding surface.
    """
    def __init__(self, width=SCREEN_WIDTH, height=SCREEN_HEIGHT):
        self.width = width
        self.height = height

        self.surface = pygame.display.set_mode(
                (self.width, self.height), flags=FULLSCREEN)

class Door:
    """
    Class representing a single door on the activity board.

    Properties:
    index -- zero-based index of the door (i.e., index 0 = door 1, etc.)
    number_font -- pygame Font object used to render the door number
    activity_font_small -- pygame Font object used to render the activity
        text while the door is opening
    activity_font_full -- pygame Font object used to render the activity
        text when displaying on full screen
    activity -- text of the activity (backticks [`] represent newlines)
    is_selected -- boolean representing whether the door is currently
        selected in the interface (i.e., should be drawn with a box around
        the door)
    is_open -- boolean indicating that the door has already been opened and
        should be rendered as an X
    is_revealed -- boolean indicating that the door should be revealed
        (i.e., endgame display showing what was behind all doors)
    is_hidden -- boolean representing if door is hidden (i.e., not rendered
        when calling draw(); used for animated startup routine )
    """
    


    def __init__(
            self, index=None, number_font=None, activity_small_font=None,
            activity_full_font=None, activity=None, is_selected=False,
            is_open=False, is_revealed=False, is_hidden=False):
        """Initialize all object properties as shown in class documentation."""
        self.index = index
        self.number_font = number_font
        self.activity_small_font = activity_small_font
        self.activity_full_font = activity_full_font
        self.activity = activity
        self.is_selected = is_selected
        self.is_open = is_open
        self.is_revealed = is_revealed
        self.is_hidden = is_hidden


    def _get_door_surface(self):
        """
        Build and return a pygame Surface object representing the door in
        its current state based on the Door object properties.

        TODO: Remove magic numbers related to ellipse size
        and selection rectangle
        """
        surf = pygame.Surface((self.width, self.height))

        if self.is_hidden:
            # Door is hidden - render as blank box
            surf.fill(self.bg_color)
        elif self.is_open and not self.is_revealed:
            # If door has been opened and we are not in the endgame reveal,
            # render door as an X
            if self.is_selected:
                surf.fill(self.sel_color)
            else:
                surf.fill(self.bg_color)

            surf.fill(self.bg_color, Rect(20, 20, 440, 320))

            pygame.draw.line(
                    surf, DOOR_OPENCOLOR, (20, 40),
                    (self.width - 20, self.height - 40), 40)
            pygame.draw.line(
                    surf, self.open_color, (20, self.height - 40),
                    (self.width - 20, 40), 40)
        elif self.is_revealed:
            # Endgame reveal - render with standard text color if the door
            # was opened during the game, otherwise render in a distinctive
            # color to show that the door was not opened during the game.
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
                # If the door is currently selected, render a box around the
                # door to indicate this.
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


    def _create_text_surface(self, text, font, line_spacing, text_color=None):
        """
        Create and return a pygame Surface object containing the specified
        text.

        Arguments:
        text -- text string to be rendered with newlines repersented as
            backticks (`)
        font -- pygame Font object to use for rendering text
        line_spacing -- space between lines in pixels
        text_color -- pygame Color object representing text color if the
            default is not used

        TODO: Implement word wrap.
        """
        if not text_color:
            text_color = TEXT_COLOR

        text_lines = text.split('`')

        text_surfaces = []

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


    def animate_open(self, dest_surface):
        """
        Performs animation of door opening and displays activity in
        full screen after animation is complete.

        Arguments:
        dest_surface -- pygame Surface on which to render the door animation
            and full-screen activity

        TODO: Make this part of _get_door_surface and make revealed
            portion a property of the class
        """
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
    """Calculate and return the door index based on the x and y position."""
    door_index = (y * DOORS_HORIZ) + x

    return door_index


def update_door_selection(x, y, movement):
    """
    Update the selected door in the form (x,y) and return a tuple with
    that new position.

    Arguments:
    x -- x coordinate of currently selected door
    y -- y coordinate of currently selected door
    movement - movement direction as it occurs in the value property of the
        pygame.JOYHATMOTION event
    """
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
    """Read activities from file (one per line). Return list of activities."""
    activities = []

    with open(file_name, 'r') as activity_file:
        for line in activity_file:
            activities.append(line.strip())

    return activities


def build_door_list(activities, doors_hidden=True):
    """Build list of Door objects for use throughout the program.

    Arguments:
    activities -- list of activities that can be behind doors (newlines are
        represented by backticks: `)
    doors_hidden -- boolean that determines if the doors start off hidden
        (i.e., not displayed when calling Door.draw())
    """
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


def main():
    """
    Main loop for activity board.

    This is primarily a finite state machine using the states defined in
    the State class.

    TODO: Evaluate moving pygame event loop outside of state machine loop.
    """
    debug = False
    debug2 = False

    if len(sys.argv) > 1:
        if sys.argv[1].lower() == 'debug':
            debug = True
        elif sys.argv[1].lower() == 'debug2':
            debug = True
            debug2 = True

    # Small buffer size to prevent delays when playing sounds
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
        move_sounds.append(pygame.mixer.Sound(f'sounds/move{i}.wav'))

    open_sound = pygame.mixer.Sound('sounds/opendoor.wav')
    oops_sound = pygame.mixer.Sound('sounds/oops.wav')
    start_sound = pygame.mixer.Sound('sounds/start.wav')
    reveal_all_sound = pygame.mixer.Sound('sounds/revealall.wav')

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

            # Flag indicating if all doors have been revealed (i.e., endgame)
            all_revealed = False

            # Flag indicating if pygame display needs to be updated
            update_needed = True

            state = State.STARTING
        elif state == State.STARTING:
            time.sleep(DOOR_REVEAL_DELAY)

            if show_list:
                # Loop until show_list is empty, i.e., all doors displayed
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

                        # TODO: Simplfy this based on the fact that
                        # selected_door and (sel_x, sel_y) are functionally
                        # identical.
                        (sel_x, sel_y) = update_door_selection(
                                sel_x, sel_y, event.value)
                        selected_door = get_door_index(sel_x, sel_y)

                        doors[selected_door].is_selected = True

                        if selected_door != prev_selected:
                            # Don't play move sound if player has tried to
                            # move off the side of the screen.
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

    # Should never get here
    pygame.quit()

if __name__ == '__main__':
    main()
