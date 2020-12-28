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

Config file is specified on command line or defaults
to config.json if not specified

For full documentation, see github.com/davidsmakerworks/activity-board

TODO: Make certain sounds a property of the door for increased variation

TODO: Additional rearrangement and cleanup

TODO: Generalize ActivityBoard class to render on any surface
"""


import json
import random
import sys
import time

from enum import Enum, unique

import pygame
import buttons

from pygame.locals import *


class TextRenderer:
    """
    Class to assist with rendering text surfaces.

    Properties:
    font -- PyGame Font object used to render text
    line_spacing -- space (in pixels) between text lines
    text_color -- PyGame Color object representing text color
    """

    def __init__(self, font, line_spacing, text_color):
        """
        Create instance using properties as shown in class documentation.
        """
        self.font = font
        self.line_spacing = line_spacing
        self.text_color = text_color


    def render_surface(self, text):
        """
        Returns a PyGame Surface with the specified text rendered on it.

        Size of the surface is minimum size necessary to fully contain text.

        Arguments:
        text -- text string to be rendered with newlines represented as
            backticks (`)
        
        TODO: Implement word wrap.
        """
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
    cross_color -- color of the X shown when door has been opened
    selection_color -- color of the selection box around selected door
    activity_color -- color of the acivity text behind the door
    unused_color -- color of activity text when unused activity
            is revealed in endgame
    number_font -- font object used to render the door number
    border_size -- size of selection border in pixels
    ellipse_margin -- margin of ellipse in pixels from edge of door surface
    cross_width -- width of the line drawn to form the X when door is opened
    cross_offset -- offset of the line from the edge of the door
    open_step_time -- time in seconds to delay after each step of the
        door opening animation. Adjust as needed for individual computer
        performance.
    """
    def __init__(
            self, bg_color, door_color, ellipse_color, number_color,
            cross_color, selection_color, activity_color,
            unused_color, activity_font, line_spacing, number_font,
            border_size, ellipse_margin, cross_width, cross_offset,
            open_step_time):
        """Create instance using properties as shown in class documentation."""
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
        self.open_step_time = open_step_time


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

    is_updated -- boolean repersenting if door has been updated since 
        the last time it was drawn (must be set manually) - used to improve 
        performance by minimizing unnecessary surface blits
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

        # All new doors need to be drawn by default
        self.is_updated = True

        # Always assume that a new door starts fully closed
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
            if self.is_open:
                activity_renderer.text_color = self.props.activity_color
            else:
                activity_renderer.text_color = self.props.unused_color

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
                    (self.height // 2) - (number_rect.height // 2)))

            # If the door is partially "open", reveal a portion of the
            # activity text surface
            #
            # This reveals a rectangular portion based on the pct_open
            # property, where pct_open = 100 represents a door that is
            # completely open.
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

    Currently renders onto a PyGame display surface and makes calls to
    pygame.display.update(). In the future, this may be generalized to
    render onto any PyGame Surface obect

    Properties:
    surface -- the PyGame surface where the board will be drawn
    config -- dictionary representing the activity board configuration -
        almost all configuration is done through this object rather than by
        programmatically changing class properties
    start_hidden -- determines whether doors start hidden (i.e., the doors will
        appear one by one during startup animation)

    TODO: Clean up properties and methods related to door corodinates,
        door sizes, etc.
    """
    @unique
    class State(Enum):
        """
        Enumeration to define states for the finite state machine in the main
        loop.

        States:
        START -- Draw all doors with optional animated sequence
        SELECTING -- Choosing a door to open
        IN_PROGRESS -- Activity displayed on screen and in progress
        ALL_REVEALED -- All doors revealed at end of game
        GAME_OVER -- Exiting game
        """
        START = 0
        SELECTING = 1
        IN_PROGRESS = 2
        ALL_REVEALED = 3
        GAME_OVER = 4


    @unique
    class Action(Enum):
        """
        Enumeration to represent player action.

        Actions:
        UP -- Move up
        DOWN -- Move down
        LEFT -- Move left
        RIGHT -- Move right
        OPEN -- Open door (i.e. joystick button A)
        RETURN -- Return to selection screen after 
            opening door (i.e., joystick button B)
        REVEAL -- Reveal all (i.e., joystick button X + Y)
        RESTART -- Start new game (i.e., joystick START button)
        QUIT -- Exit game (i.e., joystick button LB + RB + BACK)
        """
        UP = 0
        DOWN = 1
        LEFT = 2
        RIGHT = 3
        OPEN = 4
        RETURN = 5
        REVEAL = 6
        RESTART = 7
        QUIT = 8


    @property
    def num_doors(self):
        """Returns total number of doors on the board."""
        return self._doors_horiz * self._doors_vert


    @property
    def door_width(self):
        """Returns width (in pixels) of one door."""
        return self._surface.get_width() // self._doors_horiz


    @property
    def door_height(self):
        """Returns height (in pixels) of one door."""
        return self._surface.get_height() // self._doors_vert


    def __init__(self, surface, config, start_hidden=False):
        """
        Creates instance of class using properties shown in class documentation.
        """
        doors_horiz = config['board']['doors_horiz']
        doors_vert = config['board']['doors_vert']

        if surface.get_width() % doors_horiz != 0:
            raise RuntimeError('surface width must be an integer '
                    'multiple of doors_horiz')

        if surface.get_height() % doors_vert != 0:
            raise RuntimeError('surface height must be an integer '
                    'multiple of doors_vert')

        self._surface = surface
        self._config = config

        self._bg_color = pygame.Color(config['board']['bg_color'])

        self._width = surface.get_width()
        self._height = surface.get_height()

        activity_font = pygame.font.Font(
            config['board']['font']['activity']['file'],
            config['board']['font']['activity']['size'])

        line_spacing = self._config['board']['line_spacing']

        activity_color = pygame.Color(
                self._config['board']['color']['activity'])

        # One full-screen activity renderer for the whole class
        self.activity_renderer = TextRenderer(
                activity_font,
                line_spacing,
                activity_color)

        self._doors_horiz = doors_horiz
        self._doors_vert = doors_vert

        self._start_hidden = start_hidden

        self._activities = self._read_activities(config['activity_file'])
        self._doors = self._build_door_list(
                self._activities, doors_hidden=start_hidden)

        self._move_sounds = self._build_sound_list(
                config['board']['sound']['move'])
        self._open_sounds = self._build_sound_list(
                config['board']['sound']['open'])
        self._oops_sounds = self._build_sound_list(
                config['board']['sound']['oops'])
        self._start_sounds = self._build_sound_list(
                config['board']['sound']['start'])
        self._reveal_all_sounds = self._build_sound_list(
                config['board']['sound']['reveal_all'])

        self._intro_step_time = config['board']['intro_step_time']

        # Joystick is optional - see documentation for controls
        if pygame.joystick.get_count():
            self._joystick = pygame.joystick.Joystick(0)
            self._joystick.init()


    def _door_x_coord(self, index):
        """
        Calculate and return the screen X coordinate (in pixels) of the door.
        """
        return (index % self._doors_horiz) * self.door_width


    def _door_y_coord(self, index):
        """
        Calculate and return the screen Y coordinate (in pixels) of the door.
        """
        return (index // self._doors_horiz) * self.door_height


    def _read_activities(self, file_name):
        """Read activities from file (one per line)."""
        activities = []

        with open(file_name, 'r') as activity_file:
            for line in activity_file:
                activities.append(line.strip())

        return activities


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
        doors = []

        door_colors = self._config['door']['color']

        for i in range(self.num_doors):
            activity_font = pygame.font.Font(
                self._config['door']['font']['activity']['file'],
                self._config['door']['font']['activity']['size'])

            number_font = pygame.font.Font(
                self._config['door']['font']['number']['file'],
                self._config['door']['font']['number']['size'])

            # Individual props object for each door to allow for later
            # customization
            props = DoorProperties(
                bg_color=pygame.Color(self._config['board']['bg_color']),
                door_color=pygame.Color(door_colors['door']),
                ellipse_color=pygame.Color(door_colors['ellipse']),
                number_color=pygame.Color(door_colors['number']),
                cross_color=pygame.Color(door_colors['cross']),
                selection_color=pygame.Color(door_colors['selection']),
                activity_color=pygame.Color(door_colors['activity']),
                unused_color=pygame.Color(door_colors['unused']),
                activity_font=activity_font,
                line_spacing=self._config['door']['line_spacing'],
                number_font=number_font,
                border_size=self._config['door']['border_size'],
                ellipse_margin=self._config['door']['ellipse_margin'],
                cross_width=self._config['door']['cross_width'],
                cross_offset=self._config['door']['cross_offset'],
                open_step_time=self._config['door']['open_step_time'])

            # Choose a random activity for the door
            activity = random.choice(activities)
            
            # Remove the activity from the list to prevent duplicates
            activities.remove(activity)

            doors.append(Door(
                    index=i,
                    height=self.door_height,
                    width=self.door_width,
                    activity=activity,
                    props=props,
                    is_hidden=doors_hidden))

        return doors


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


    def _draw_door(self, door, update_display=True):
        """
        Draws door onto activity board surface.

        Arguments:
        door -- the Door object to render
        update_display -- boolean that determines whether the PyGame display
            should be updated after drawing. Set to False when drawing
            multiple doors in a loop.
        """
        door_surface = door.get_door_surface()

        self._surface.blit(
                door_surface,
                (self._door_x_coord(door.index), self._door_y_coord(door.index)))

        if update_display:
            pygame.display.update()


    def _draw_updated_doors(self):
        """
        Draws only doors that are marked as being changed by setting their
        is_updated property.
        """
        for d in self._doors:
            if d.is_updated:
                self._draw_door(d, update_display=False)
                d.is_updated = False

        pygame.display.update()


    def _draw_all_doors(self):
        """
        Draws all doors onto activity board surface.

        For best performance, keep track of which doors have been updated
        and call _draw_door() for only those doors.
        """
        for d in self._doors:
            self._draw_door(d, update_display=False)
            d.is_updated = False

        pygame.display.update()


    def _show_activity(self, door):
        """
        Shows the activity related to a particular door in
        a large font on the whole activity board surface.

        Arguments:
        door -- the Door object contaning the activity
        """
        activity_surface = self.activity_renderer.render_surface(door.activity)

        self._surface.fill(self._bg_color)

        activity_rect = activity_surface.get_rect()

        self._surface.blit(
                activity_surface,
                ((self._width // 2) - (activity_rect.width // 2),
                (self._height // 2) - (activity_rect.height // 2)))

        pygame.display.update()


    def _get_new_selection(self, door, action):
        """
        Return new door index based on originally selected door and 
        direction of movement.

        Arguments:
        door -- the currently selected Door object
        action -- a value from the Action enum representing a movement direction
        
        NOTE: This method takes a Door object as input but return an integer
            door index as the result.

        TODO: Change the above to be more consistent.
        """
        old_index = door.index

        old_index_h = old_index % self._doors_horiz
        old_index_v = old_index // self._doors_horiz

        new_index_h = old_index_h
        new_index_v = old_index_v

        if action == ActivityBoard.Action.UP:
            new_index_v = old_index_v - 1
        elif action == ActivityBoard.Action.DOWN:
            new_index_v = old_index_v + 1
        elif action == ActivityBoard.Action.LEFT:
            new_index_h = old_index_h - 1
        elif action == ActivityBoard.Action.RIGHT:
            new_index_h = old_index_h + 1

        if new_index_h < 0:
            new_index_h = old_index_h

        if new_index_h > self._doors_horiz - 1:
            new_index_h = old_index_h

        if new_index_v < 0:
            new_index_v = 0

        if new_index_v > self._doors_vert - 1:
            new_index_v = old_index_v

        new_index = new_index_v * self._doors_horiz + new_index_h

        return new_index

    
    def _clear_display(self):
        """
        Clear the underlying surface by filling with background color.
        """
        self._surface.fill(self.bg_color)

        pygame.display.update()


    def _translate_action(self, event):
        """
        Translate particular PyGame events into generalized in-game actions.

        Returns a value from the Action enum if the event represents a valid
        action, otherwise returns None.

        Arguments:
        event -- the PyGame event to be translated
        """
        if event.type == JOYBUTTONDOWN:
            if event.button == buttons.BTN_A:
                return ActivityBoard.Action.OPEN
            elif event.button == buttons.BTN_B:
                return ActivityBoard.Action.RETURN
            elif event.button == buttons.BTN_Y:
                if self._joystick.get_button(buttons.BTN_X):
                    return ActivityBoard.Action.REVEAL
            elif event.button == buttons.BTN_START:
                return ActivityBoard.Action.RESTART
            elif event.button == buttons.BTN_BACK:
                if (self._joystick.get_button(buttons.BTN_LB)
                        and self._joystick.get_button(buttons.BTN_RB)):
                    return ActivityBoard.Action.QUIT
        elif event.type == JOYHATMOTION:
            if event.value[0] and event.value[1]:
                # Diagonal movement not supported
                return None
            else:
                if event.value[0] > 0:
                    return ActivityBoard.Action.RIGHT
                elif event.value[0] < 0:
                    return ActivityBoard.Action.LEFT
                elif event.value[1] > 0:
                    return ActivityBoard.Action.UP
                elif event.value[1] < 0:
                    return ActivityBoard.Action.DOWN
        elif event.type == KEYDOWN:
            if event.key == K_UP or event.key == K_w:
                return ActivityBoard.Action.UP
            elif event.key == K_DOWN or event.key == K_s:
                return ActivityBoard.Action.DOWN
            elif event.key == K_LEFT or event.key == K_a:
                return ActivityBoard.Action.LEFT
            elif event.key == K_RIGHT or event.key == K_d:
                return ActivityBoard.Action.RIGHT
            elif event.key == K_RETURN or event.key == K_SPACE:
                return ActivityBoard.Action.OPEN
            elif event.key == K_BACKSPACE or event.key == K_ESCAPE:
                return ActivityBoard.Action.RETURN
            elif event.key == K_z and event.mod & KMOD_LSHIFT:
                return ActivityBoard.Action.REVEAL
            elif event.key == K_HOME:
                return ActivityBoard.Action.RESTART
            elif (event.key == K_q
                    and event.mod & KMOD_LSHIFT
                    and event.mod & KMOD_CTRL):
                return ActivityBoard.Action.QUIT
        
        return None


    def _animate_intro(self):
        """
        Runs the animated intro sequence, which shows doors one
        by one in a random order.
        """
        # Doors start hidden, so this is a quick way to clear update flags and
        # blank the screen at the same time
        self._draw_all_doors()

        intro_show_list = list(range(self.num_doors))

        while intro_show_list:
            intro_show_index = random.choice(intro_show_list)

            self._doors[intro_show_index].is_hidden = False
            self._doors[intro_show_index].is_updated = True

            self._draw_updated_doors()

            intro_show_list.remove(intro_show_index)

            time.sleep(self._intro_step_time)


    def _animate_open(self, door):
        """
        Animates the opening of a Door object by repeatedly updating the door's
        pct_open property and calling _draw_door() until the door is fully
        open.

        Arguments:
        door -- the Door object to be opened

        TODO: Remove magic numbers related to pct_open steps.
        """
        for i in range(2, 102, 2):
            door.pct_open = i

            self._draw_door(door)

            time.sleep(door.props.open_step_time)


    def _animate_open_all(self):
        """
        Animates the opening of all unopened doors for the endgame reveal.

        This can perform slowly on the Raspberry Pi due to the large
        number of surface blits involved.

        TODO: Remove magic numbers related to pct_open steps.
        """
        for d in self._doors:
            if d.is_open:
                d.is_revealed = True
                d.is_updated = True

        self._draw_updated_doors()

        for i in range(4, 104, 4):
            for d in self._doors:
                if not d.is_open:
                    d.pct_open = i
                    d.is_updated = True

            self._draw_updated_doors()

            # This is unnecessary on Raspberry Pi 3 since the speed is
            # already constrained by the speed of the system
            # time.sleep(d.props.open_step_time)

        for d in self._doors:
            d.is_revealed = True
            d.is_updated = True

        self._draw_updated_doors()


    def run(self):
        """
        Runs the activity board for one game.

        This is primarily a finite state machine representing the different 
        possible states during the game.

        Returns True if the player wants to play again and False if the
        player wants to quit.

        Calling code is responsible for calling run() if the player wants to
        play again. This is to ensure that configuration and activities
        can be updated between plays if desired.
        """
        self._state = ActivityBoard.State.START

        while self._state != ActivityBoard.State.GAME_OVER:
            if self._state == ActivityBoard.State.START:
                self._play_random_sound(self._start_sounds)

                if self._start_hidden:
                    self._animate_intro()
                else:
                    self._draw_all_doors()
                
                self._doors[0].is_selected = True
                self._doors[0].is_updated = True
                selected_door = self._doors[0]

                self._draw_updated_doors()

                self._state = ActivityBoard.State.SELECTING
            elif self._state == ActivityBoard.State.SELECTING:
                for event in pygame.event.get():
                    action = self._translate_action(event)

                    if action == ActivityBoard.Action.OPEN:
                        if not selected_door.is_open:
                            self._play_random_sound(self._open_sounds)
                            self._animate_open(selected_door)
                            self._show_activity(selected_door)

                            selected_door.is_open = True

                            self._state = ActivityBoard.State.IN_PROGRESS
                        else:
                            self._play_random_sound(self._oops_sounds)

                        pygame.event.clear()
                    elif action == ActivityBoard.Action.RESTART:
                        play_again = True
                        self._state = ActivityBoard.State.GAME_OVER

                        pygame.event.clear()
                    elif action == ActivityBoard.Action.QUIT:
                        play_again = False
                        self._state = ActivityBoard.State.GAME_OVER

                        pygame.event.clear()
                    elif action == ActivityBoard.Action.REVEAL:
                        self._play_random_sound(self._reveal_all_sounds)
                        
                        self._animate_open_all()

                        self._state = ActivityBoard.State.ALL_REVEALED

                        pygame.event.clear()
                    elif action in [
                            ActivityBoard.Action.UP,
                            ActivityBoard.Action.DOWN,
                            ActivityBoard.Action.LEFT,
                            ActivityBoard.Action.RIGHT]:
                        new_index = self._get_new_selection(
                                selected_door, action)

                        if new_index != selected_door.index:
                            selected_door.is_selected = False
                            selected_door.is_updated = True

                            self._doors[new_index].is_selected = True
                            self._doors[new_index].is_updated = True

                            selected_door = self._doors[new_index]

                            self._play_random_sound(self._move_sounds)

                            self._draw_updated_doors()
                        
                        pygame.event.clear()
            elif self._state == ActivityBoard.State.IN_PROGRESS:
                for event in pygame.event.get():
                    action = self._translate_action(event)

                    if action == ActivityBoard.Action.RETURN:
                        self._draw_all_doors()

                        self._state = ActivityBoard.State.SELECTING

                        pygame.event.clear()
            elif self._state == ActivityBoard.State.ALL_REVEALED:
                 for event in pygame.event.get():
                    action = self._translate_action(event)

                    if action == ActivityBoard.Action.RESTART:
                        play_again = True
                        self._state = ActivityBoard.State.GAME_OVER

                        pygame.event.clear()
                    elif action == ActivityBoard.Action.QUIT:
                        play_again = False
                        self._state = ActivityBoard.State.GAME_OVER

                        pygame.event.clear()
            elif self._state == ActivityBoard.State.GAME_OVER:
                pass
            else:
                raise RuntimeError('Invalid state in main loop')

        return play_again


class Screen:
    """
    Class representing the pyhsical screen where the board is displayed.

    Initializes the pygame display and gets the corresponding surface.

    Properties:
    width -- screen width in pixels
    height -- screen height in pixels
    bg_color -- PyGame Color object representing the background color to use
    fullscreen -- boolean representing whether full-screen display
        should be used
    """
    def __init__(self, width, height, bg_color, fullscreen=False):
        self.width = width
        self.height = height

        if fullscreen:
            flags = FULLSCREEN
        else:
            flags = None

        self.surface = pygame.display.set_mode(
                (self.width, self.height), flags)

        self.surface.fill(bg_color)

        pygame.display.update()


def main():
    """
    Main program that does some PyGame initialization and runs the
    activity board.

    TODO: Determine which PyGame functions should be moved to the 
        ActivityBoard class
    """

    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = 'config.json'

    with open(config_file, 'r') as f:
        config = json.load(f)

    # Small buffer size to prevent delays when playing sounds
    pygame.mixer.init(buffer=512)
    pygame.init()

    random.seed()

    pygame.mouse.set_visible(False)

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
            start_hidden=True)

        play_again = board.run()

    pygame.quit()


if __name__ == '__main__':
    main()
