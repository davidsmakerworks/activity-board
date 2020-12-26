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

A PyGame-compatible joystick is required.

Config file is specified on command line or defaults 
to config.json if not specified

For full documentation, see github.com/davidsmakerworks/activity-board

TODO: Implement alternative control schemes.

TODO: Make certain sounds a property of the door for increased variation
"""


import json
import random
import sys
import time

from enum import Enum, unique
from typing import Text

import pygame
import buttons

from pygame.locals import *


DOOR_OPEN_DELAY = 0.02
DOOR_REVEAL_DELAY = 0.075


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


class TextRenderer:
    """
    Class representing a text object that can be rendered as a surface.
    """

    def __init__(self, font, line_spacing, text_color):
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
        self.font = font
        self.line_spacing = line_spacing
        self.text_color = text_color
        

    def render_surface(self, text):
        text_lines = text.split('`')

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


class DoorProperties:
    """
    Class to contain configurable properties of a Door object.

    All color-related properties are PyGame Color objects.

    All font-related properties are PyGame Font objects.

    Properties:
    bg_color -- background color of the underlying activity board surface
    door_color -- overall color of the door surface
    ellipse_color -- color of the ellipse surrounding the door number
    number_color -- color of the door number
    opened_color -- color of the X shown when door has been opened
    selection_color -- color of the selection box around selected door
    activity_color -- color of the acivity text behind the door
    unused_color -- color of activity text when unused activity
            is revealed in endgame
    number_font -- font object used to render the door number
    border_size -- size of selection border in pixels
    ellipse_margin -- margin of ellipse in pixels from edge of door surface
    """
    def __init__(
            self, bg_color, door_color, ellipse_color, number_color,
            cross_color, selection_color, activity_color,
            unused_color, activity_font, line_spacing, number_font,
            border_size, ellipse_margin, cross_width, cross_offset):
            self.bg_color = bg_color
            self.door_color = door_color
            self.ellipse_color = ellipse_color
            self.number_color = number_color
            self.cross_color = cross_color
            self.selection_color = selection_color
            self.activity_color = activity_color
            self.unused_color = unused_color
            self.activity_font = activity_font
            self.line_spacing = line_spacing
            self.number_font = number_font
            self.border_size = border_size
            self.ellipse_margin = ellipse_margin
            self.cross_width = cross_width
            self.cross_offset = cross_offset


class Door:
    """
    Class representing a single door on the activity board.

    Properties:
    index -- zero-based index of the door (i.e., index 0 = door 1, etc.)
    activity -- text of the activity (backticks [`] represent newlines)
    props -- DoorProperties object representing configurable door properties
    is_selected -- boolean representing whether the door is currently
        selected in the interface (i.e., should be drawn with a box around
        the door)
    is_open -- boolean indicating that the door has already been opened and
        should be rendered as an X
    is_revealed -- boolean indicating that the door should be revealed
        (i.e., endgame display showing what was behind all doors)
    is_hidden -- boolean representing if door is hidden (i.e., not rendered
        when calling draw(); used for animated startup routine)

    pct_open -- integer percentage of door that is currently displayed -
        used for door-opening animation routine
    """

    def __init__(
            self, index, height, width, activity, props,
            is_selected=False, is_open=False, is_revealed=False,
            is_hidden=False):
        """Initialize all object properties as shown in class documentation."""
        self.index = index
        self.height = height
        self.width = width
        self.activity = activity
        self.props = props
        self.is_selected = is_selected
        self.is_open = is_open
        self.is_revealed = is_revealed
        self.is_hidden = is_hidden

        self.pct_open = 0

    def _draw_cross(self, surf):
        """
        Draws a cross (X) on the door surface to show that the door has
        already been opened.
        """
        pygame.draw.line(
                    surf,
                    self.props.cross_color,
                    (self.props.cross_offset, self.props.cross_offset * 2),
                    (self.width - self.props.cross_offset,
                            self.height - self.props.cross_offset * 2),
                    self.props.cross_width)
        
        pygame.draw.line(
                surf,
                self.props.cross_color,
                (self.props.cross_offset,
                        self.height - self.props.cross_offset * 2),
                (self.width - self.props.cross_offset,
                        self.props.cross_offset * 2),
                self.props.cross_width)

    def get_door_surface(self):
        """
        Build and return a pygame Surface object representing the door in
        its current state based on the Door object properties.

        TODO: Move some drawing code to separate methods to improve readability.
        """
        surf = pygame.Surface((self.width, self.height))

        interior_rect = pygame.Rect(
                self.props.border_size,
                self.props.border_size, 
                self.width - self.props.border_size * 2, 
                self.height - self.props.border_size * 2)
        
        activity_renderer = TextRenderer(
                    font=self.props.activity_font,
                    line_spacing=self.props.line_spacing,
                    text_color=self.props.activity_color)

        if self.is_hidden:
            # Door is hidden - render as blank box
            surf.fill(self.props.bg_color)
        elif self.is_open and not self.is_revealed:
            # If door has been opened and we are not in the endgame reveal,
            # render door as an X
            if self.is_selected:
                surf.fill(self.props.selection_color)
            else:
                surf.fill(self.props.bg_color)

            surf.fill(self.props.bg_color, interior_rect)

            self._draw_cross(surf)       
        elif self.is_revealed:
            # Endgame reveal - render with standard text color if the door
            # was opened during the game, otherwise render in a distinctive
            # color to show that the door was not opened during the game.        
            activity_surface = activity_renderer.render_surface(self.activity)

            activity_rect = activity_surface.get_rect()

            surf.fill(self.props.bg_color)
            surf.blit(
                    activity_surface,
                    ((self.width // 2) - (activity_rect.width // 2),
                    (self.height // 2) - (activity_rect.height // 2)))
        else:
            if self.is_selected:
                # If the door is currently selected, render a box around the
                # door to indicate this.
                surf.fill(self.props.selection_color)
            else:
                surf.fill(self.props.bg_color)

            surf.fill(self.props.door_color, interior_rect)

            ellipse_rect = pygame.Rect(
                    self.props.ellipse_margin,
                    self.props.ellipse_margin,
                    self.width - self.props.ellipse_margin * 2,
                    self.height - self.props.ellipse_margin * 2)

            pygame.draw.ellipse(
                    surf, self.props.ellipse_color, ellipse_rect)

            number_surface = self.props.number_font.render(
                    str(self.index + 1), True, self.props.number_color)
            number_rect = number_surface.get_rect()

            surf.blit(
                    number_surface,
                    ((self.width // 2) - (number_rect.width // 2),
                    (self.height // 2) - (number_rect.height // 2) + 10))
            
            if self.pct_open > 0:
                activity_small_surface = activity_renderer.render_surface(
                        self.activity)

                small_rect = activity_small_surface.get_rect()

                open_width = int(self.width * (self.pct_open / 100))
                open_height = int(self.height * (self.pct_open / 100))

                open_surface = pygame.Surface((self.width, self.height))
                
                open_surface.fill(self.props.bg_color)
                
                open_surface.blit(
                        activity_small_surface,
                        ((self.width // 2) - (small_rect.width // 2),
                        (self.height // 2) - (small_rect.height // 2)))

                x = (self.width - open_width) // 2
                y = (self.height - open_height) // 2

                open_rect = Rect(x, y, open_width, open_height)

                surf.blit(open_surface, (x, y), open_rect)

        return surf


class ActivityBoard:
    """
    Class representing the entire activity board.

    Normally will be used to render onyo a PyGame display surface but
    can render onto any PyGame Surface obect
    """
    @property
    def num_doors(self):
        return self._doors_horiz * self._doors_vert


    @property
    def door_width(self):
        return self.surface.get_width() // self._doors_horiz


    @property
    def door_height(self):
        return self.surface.get_height() // self._doors_vert


    def door_x_coord(self, index):
        """
        Calculate and return the screen X coordinate (in pixels) of the door.
        """
        return (index % self._doors_horiz) * self.door_width


    def door_y_coord(self, index):
        """
        Calculate and return the screen Y coordinate (in pixels) of the door.
        """
        return (index // self._doors_horiz) * self.door_height


    def _read_activities(self, file_name):
        """Read activities from file (one per line)."""
        self.activities = []

        with open(file_name, 'r') as activity_file:
            for line in activity_file:
                self.activities.append(line.strip())


    def _build_sound_list(self, sound_files):
        """
        Builds a list of PyGame Sound objects given a list of sound file names.
        """
        sound_list = []

        for f in sound_files:
            sound_list.append(pygame.mixer.Sound(f))
        
        return sound_list


    def _build_door_list(self, activities, doors_hidden=False):
        """
        Build list of Door objects for use on the activity board.

        Arguments:
        activities -- list of activities that can be behind doors (newlines are
            represented by backticks: `)
        doors_hidden -- boolean that determines if the doors start off hidden
            (i.e., not displayed when calling Door.draw())
        """
        self.doors = []

        door_colors = self.config['door']['color']

        for i in range(self.num_doors):
            activity_font = pygame.font.Font(
                self.config['door']['font']['activity']['file'],
                self.config['door']['font']['activity']['size'])

            number_font = pygame.font.Font(
                self.config['door']['font']['number']['file'],
                self.config['door']['font']['number']['size'])

            # Individual props object for each door to allow for later
            # customization
            props = DoorProperties(
                bg_color=pygame.Color(self.config['board']['bg_color']),
                door_color=pygame.Color(door_colors['door']),
                ellipse_color=pygame.Color(door_colors['ellipse']),
                number_color=pygame.Color(door_colors['number']),
                cross_color=pygame.Color(door_colors['cross']),
                selection_color=pygame.Color(door_colors['selection']),
                activity_color=pygame.Color(door_colors['activity']),
                unused_color=pygame.Color(door_colors['unused']),
                activity_font=activity_font,
                line_spacing=self.config['door']['line_spacing'],
                number_font=number_font,
                border_size=self.config['door']['border_size'],
                ellipse_margin=self.config['door']['ellipse_margin'],
                cross_width=self.config['door']['cross_width'],
                cross_offset=self.config['door']['cross_offset'])

            activity = random.choice(activities)
            activities.remove(activity)

            self.doors.append(Door(
                    index=i,
                    height=self.door_height,
                    width=self.door_width,
                    activity=activity,
                    props=props,
                    is_hidden=doors_hidden))


    def _play_random_sound(self, sound_list):
        """
        Plays one random sound from a list of PyGame Sound objects.

        This should be used for all sound playback to allow for the possibility
        of adding multiple sounds.

        For effects that should always play the same sound, pass in a 
        one-item list.
        """
        sound = random.choice(sound_list)

        sound.play()

    
    def _draw_door(self, door):
        """
        Draws door onto activity board surface.
        """
        door_surface = door.get_door_surface()

        self.surface.blit(
                door_surface,
                (self.door_x_coord(door.index), self.door_y_coord(door.index)))

    
    def _draw_all_doors(self):
        """
        Draws all doors onto activity board surface.

        For best performance, keep track of which doors have been updated
        and call _draw_door() for only those doors.
        """
        for d in self.doors:
            self._draw_door(d)

    
    def _show_activity(self, door):
        """
        Shows the activity related to a particular door in
        a large font on the whole activity board surface.
        """
        activity_surface = self.activity_renderer.render_surface(door.activity)

        self.surface.fill(self.bg_color)

        activity_rect = activity_surface.get_rect()

        self.surface.blit(
                activity_surface,
                ((self.width // 2) - (activity_rect.width // 2),
                (self.height // 2) - (activity_rect.height // 2)))


    def __init__(self, surface, config, start_hidden=False):

        doors_horiz = config['board']['doors_horiz']
        doors_vert = config['board']['doors_vert']

        if surface.get_width() % doors_horiz != 0:
            raise RuntimeError('surface width must be an integer '
                    'multiple of doors_horiz')

        if surface.get_height() % doors_vert != 0:
            raise RuntimeError('surface height must be an integer '
                    'multiple of doors_vert')

        self.surface = surface
        self.config = config

        self.bg_color = pygame.Color(config['board']['bg_color'])

        self.width = surface.get_width()
        self.height = surface.get_height()

        activity_font = pygame.font.Font(
            self.config['board']['font']['activity']['file'],
            self.config['board']['font']['activity']['size'])

        line_spacing = self.config['board']['line_spacing']

        activity_color = pygame.Color(
                self.config['board']['color']['activity'])

        self.activity_renderer = TextRenderer(
                activity_font,
                line_spacing,
                activity_color)

        self._doors_horiz = doors_horiz
        self._doors_vert = doors_vert

        self._read_activities(config['activity_file'])
        self._build_door_list(self.activities, doors_hidden=start_hidden)

        self.move_sounds = self._build_sound_list(
                config['board']['sound']['move'])
        self.open_sounds = self._build_sound_list(
                config['board']['sound']['open'])
        self.oops_sounds = self._build_sound_list(
                config['board']['sound']['oops'])
        self.start_sounds = self._build_sound_list(
                config['board']['sound']['start'])
        self.reveal_all_sounds = self._build_sound_list(
                config['board']['sound']['reveal_all'])

    def run(self):
        #self._play_random_sound(self.start_sounds)

        r = random.randint(0, 10)

        self.doors[r].is_selected = True
        self.doors[r + 1].is_revealed = True

        self._draw_all_doors()

        pygame.display.update()

        time.sleep(2)

        for i in range(2, 102, 2):
            self.doors[r].pct_open = i

            print(i)

            self._draw_door(self.doors[r])

            pygame.display.update()

            time.sleep(0.02)

        self._show_activity(self.doors[r + 1])

        pygame.display.update()

        time.sleep(2)

        self.doors[r].is_open = True
        self._draw_all_doors()

        pygame.display.update()

        time.sleep(2)

        return False


class Screen:
    """
    Class representing the pyhsical screen where the board is displayed.

    Initializes the pygame display and gets the corresponding surface.
    """
    def __init__(self, width, height, bg_color, fullscreen=False):
        self.width = width
        self.height = height

        if fullscreen:
            flags = FULLSCREEN
        else:
            flags = None

        self.surface = pygame.display.set_mode(
                (self.width, self.height), flags=flags)

        self.surface.fill(bg_color)


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


def main():
    """
    Main loop for activity board.

    This is primarily a finite state machine using the states defined in
    the State class.
    """

    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = 'config.json'

    with open(config_file, 'r') as f:
        config = json.load(f)

    debug = config['debug']
    debug2 = config['debug2']

    # Small buffer size to prevent delays when playing sounds
    pygame.mixer.init(buffer=512)
    pygame.init()

    random.seed()

    pygame.mouse.set_visible(False)

    # if pygame.joystick.get_count():
    #     js = pygame.joystick.Joystick(0)
    #     js.init()
    # else:
    #     raise RuntimeError('Joystick not found')



    screen = Screen(
            width=config['display']['width'],
            height=config['display']['height'],
            bg_color=pygame.Color(config['board']['bg_color']),
            fullscreen=config['display']['fullscreen'])

    screen_surface = screen.surface
    play_again = True

    while play_again:
        board = ActivityBoard(
            surface=screen_surface,
            config=config,
            start_hidden=False)

        play_again = board.run()

    pygame.quit()

    # state = State.START

    # while True:
    #     if state == State.START:
    #         activities = read_activities('activities.txt')

    #         doors = build_door_list(activities)

    #         doors[0].is_selected = True

    #         sel_x = 0
    #         sel_y = 0
    #         selected_door = 0

    #         # List of all door numbers to track which ones have been
    #         # shown during startup animation
    #         show_list = list(range(DOORS_HORIZ * DOORS_VERT))

    #         start_sound.play()

    #         # Flag indicating if all doors have been revealed (i.e., endgame)
    #         all_revealed = False

    #         # Flag indicating if pygame display needs to be updated
    #         update_needed = True

    #         state = State.STARTING
    #     elif state == State.STARTING:
    #         time.sleep(DOOR_REVEAL_DELAY)

    #         if show_list:
    #             # Loop until show_list is empty, i.e., all doors displayed
    #             for d in doors:
    #                 d.draw(screen.surface)

    #             show_door = random.choice(show_list)
    #             doors[show_door].is_hidden = False
    #             show_list.remove(show_door)

    #             update_needed = True
    #         else:
    #             state = State.DRAW
    #     elif state == State.DRAW:
    #         for d in doors:
    #             d.draw(screen.surface)

    #         update_needed = True

    #         if all_revealed:
    #             state = State.REVEAL_ALL
    #         else:
    #             state = State.SELECT
    #     elif state == State.SELECT:
    #         for event in pygame.event.get():
    #             if debug2:
    #                 print(f'Pygame event type {event.type}')
    #             if event.type == JOYBUTTONDOWN:
    #                 if debug:
    #                     print(f'Joystick button {event.button} pressed')

    #                 if event.button == buttons.BTN_A:
    #                     if not doors[selected_door].is_open:
    #                         open_sound.play()

    #                         doors[selected_door].is_open = True
    #                         doors[selected_door].animate_open(screen.surface)

    #                         state = State.DISPLAY
    #                     else:
    #                         oops_sound.play()

    #                     pygame.event.clear()
    #                 elif event.button == buttons.BTN_Y:
    #                     if js.get_button(buttons.BTN_X):
    #                         reveal_all_sound.play()

    #                         for d in doors:
    #                             d.is_revealed = True

    #                         all_revealed = True

    #                         state = State.DRAW
    #                 elif event.button == buttons.BTN_START:
    #                     state = State.START
    #                 elif event.button == buttons.BTN_BACK:
    #                     if (js.get_button(buttons.BTN_RB)
    #                             and js.get_button(buttons.BTN_LB)):
    #                         state = State.SHUTDOWN
    #             elif event.type == JOYHATMOTION:
    #                 if debug:
    #                     print(f'Joystick hat motion {event.value}')

    #                 if event.value[0] or event.value[1]:
    #                     prev_selected = selected_door

    #                     doors[selected_door].is_selected = False

    #                     # TODO: Simplfy this based on the fact that
    #                     # selected_door and (sel_x, sel_y) are functionally
    #                     # identical.
    #                     (sel_x, sel_y) = update_door_selection(
    #                             sel_x, sel_y, event.value)
    #                     selected_door = get_door_index(sel_x, sel_y)

    #                     doors[selected_door].is_selected = True

    #                     if selected_door != prev_selected:
    #                         # Don't play move sound if player has tried to
    #                         # move off the side of the screen.
    #                         move_sound = random.choice(move_sounds)
    #                         move_sound.play()

    #                     state = State.DRAW

    #                     pygame.event.clear()
    #             elif event.type == QUIT:
    #                 state = State.SHUTDOWN
    #     elif state == State.DISPLAY:
    #         for event in pygame.event.get():
    #             if event.type == JOYBUTTONDOWN:
    #                 if event.button == buttons.BTN_B:
    #                     screen.surface.fill(SCREEN_BGCOLOR)

    #                     state = State.DRAW

    #                     pygame.event.clear()
    #                 elif event.button == buttons.BTN_BACK:
    #                     if (js.get_button(buttons.BTN_RB)
    #                             and js.get_button(buttons.BTN_LB)):
    #                         state = State.SHUTDOWN
    #     elif state == State.REVEAL_ALL:
    #         for event in pygame.event.get():
    #             if event.type == JOYBUTTONDOWN:
    #                 if event.button == buttons.BTN_START:
    #                     state = State.START
    #                 elif event.button == buttons.BTN_BACK:
    #                     if (js.get_button(buttons.BTN_RB)
    #                             and js.get_button(buttons.BTN_LB)):
    #                         state = State.SHUTDOWN
    #     elif state == State.SHUTDOWN:
    #         pygame.quit()
    #         sys.exit()
    #     else:
    #         pygame.quit()
    #         raise RuntimeError('Invalid state in main loop')

    #     if update_needed:
    #         pygame.display.update()
    #         update_needed = False

    # # Should never get here
    # pygame.quit()

if __name__ == '__main__':
    main()
