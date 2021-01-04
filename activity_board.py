# MIT License

# Copyright (c) 2021 David Rice

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

A fun way to select random activities

This file contains main ActivityBoard class that can be instantiated
to play the game

https://github.com/davidsmakerworks/activity-board
"""


import random
import time

from enum import Enum, unique, auto
from typing import List

import pygame

# Wildcard import used here based on standard pygame code style
from pygame.locals import *

from button import Button
from door import Door, DoorProperties
from text_renderer import TextRenderer


class ActivityBoard:
    """
    Class representing the entire activity board.

    Properties:
    surface -- the pygame surface where the board will be drawn
    config -- dictionary representing the activity board configuration -
        almost all configuration is done through this object rather than by
        programmatically changing class properties
    start_hidden -- determines whether doors start hidden (i.e., the doors will
        appear one by one during startup animation)
    surface_is_display -- determines whether the surface object is to be
        treated as a pygame display (i.e., calling pygame.display.update() when
        needed)

    TODO: Clean up properties and methods related to door coordinates,
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
        START = auto()
        SELECTING = auto()
        IN_PROGRESS = auto()
        ALL_REVEALED = auto()
        GAME_OVER = auto()

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
        UP = auto()
        DOWN = auto()
        LEFT = auto()
        RIGHT = auto()
        OPEN = auto()
        RETURN = auto()
        REVEAL = auto()
        RESTART = auto()
        QUIT = auto()

    @property
    def num_doors(self) -> int:
        """Returns total number of doors on the board."""
        return self._doors_horiz * self._doors_vert

    @property
    def door_width(self) -> int:
        """Returns width (in pixels) of one door."""
        return self._surface.get_width() // self._doors_horiz

    @property
    def door_height(self) -> int:
        """Returns height (in pixels) of one door."""
        return self._surface.get_height() // self._doors_vert

    def __init__(
            self, surface: pygame.Surface, config: dict,
            start_hidden: bool = False,
            surface_is_display: bool = True) -> None:
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

        self._surface_is_display = surface_is_display

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

        # Initialize pygame if it hasn't been initialized already
        if not pygame.get_init():
            # Use small buffer size to prevent delays when playing sounds
            pygame.mixer.init(buffer=512)
            pygame.init()

        # Joystick is optional - see documentation for controls
        if pygame.joystick.get_count():
            self._joystick = pygame.joystick.Joystick(0)
            self._joystick.init()

    def _door_x_coord(self, index: int) -> int:
        """
        Calculate and return the screen X coordinate (in pixels) of the door.
        """
        return (index % self._doors_horiz) * self.door_width

    def _door_y_coord(self, index: int) -> int:
        """
        Calculate and return the screen Y coordinate (in pixels) of the door.
        """
        return (index // self._doors_horiz) * self.door_height

    def _clear_surface(self) -> None:
        """
        Clear the underlying surface by filling with background color.
        """
        self._surface.fill(self.bg_color)

        if self._surface_is_display:
            pygame.display.update()

    def _read_activities(self, file_name: str) -> List[str]:
        """Read activities from file (one per line)."""
        activities = []

        with open(file_name, 'r') as activity_file:
            for line in activity_file:
                activities.append(line.strip())

        return activities

    def _build_sound_list(
            self, sound_files: List[str]) -> List[pygame.mixer.Sound]:
        """
        Builds a list of pygame Sound objects given a list of sound file names.
        """
        sound_list = []

        for f in sound_files:
            sound_list.append(pygame.mixer.Sound(f))

        return sound_list

    def _build_door_list(
            self, activities: List[str],
            doors_hidden: bool = False) -> List[Door]:
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

    def _play_random_sound(self, sound_list: List[pygame.mixer.Sound]) -> None:
        """
        Plays one random sound from a list of pygame Sound objects.

        This should be used for all sound playback to allow for the possibility
        of adding multiple sounds.

        For effects that should always play the same sound, pass in a
        one-item list.
        """
        sound = random.choice(sound_list)

        sound.play()

    def _get_new_selection(self, door: Door, action: Action) -> int:
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

        if action is ActivityBoard.Action.UP:
            new_index_v = old_index_v - 1
        elif action is ActivityBoard.Action.DOWN:
            new_index_v = old_index_v + 1
        elif action is ActivityBoard.Action.LEFT:
            new_index_h = old_index_h - 1
        elif action is ActivityBoard.Action.RIGHT:
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

    def _translate_action(self, event: pygame.event.Event) -> Action:
        """
        Translate particular pygame events into generalized in-game actions.

        Returns a value from the Action enum if the event represents a valid
        action, otherwise returns None.

        Arguments:
        event -- the pygame event to be translated
        """
        if event.type == JOYBUTTONDOWN:
            # Button is an IntEnum so compare by value instead of identity
            if event.button == Button.BTN_A:
                return ActivityBoard.Action.OPEN
            elif event.button == Button.BTN_B:
                return ActivityBoard.Action.RETURN
            elif event.button == Button.BTN_Y:
                if self._joystick.get_button(Button.BTN_X):
                    return ActivityBoard.Action.REVEAL
            elif event.button == Button.BTN_START:
                return ActivityBoard.Action.RESTART
            elif event.button == Button.BTN_BACK:
                    timestamp = time.time()

                    pygame.event.clear()

                    # Only return QUIT action if Back button is held for
                    # at least 2 seconds
                    while self._joystick.get_button(Button.BTN_BACK):
                        # Event queue needs to be pumped in order for
                        # get_button() to update properly
                        pygame.event.pump()
                        
                        if time.time() - timestamp > 2:
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

    def _draw_door(
            self, door: Door, update_display: bool = True) -> None:
        """
        Draws door onto activity board surface.

        Arguments:
        door -- the Door object to render
        update_display -- boolean that determines whether the pygame display
            should be updated after drawing. Set to False when drawing
            multiple doors in a loop.
        """
        door_surface = door.get_door_surface()

        self._surface.blit(
            door_surface,
            (self._door_x_coord(door.index),
            self._door_y_coord(door.index)))

        if update_display and self._surface_is_display:
            pygame.display.update()

    def _draw_updated_doors(self) -> None:
        """
        Draws only doors that are marked as being changed by setting their
        is_updated property.
        """
        for d in self._doors:
            if d.is_updated:
                self._draw_door(d, update_display=False)
                d.is_updated = False
    
        if self._surface_is_display:
            pygame.display.update()

    def _draw_all_doors(self) -> None:
        """
        Draws all doors onto activity board surface.

        For best performance, keep track of which doors have been updated
        and call _draw_door() for only those doors.
        """
        for d in self._doors:
            self._draw_door(d, update_display=False)
            d.is_updated = False
        
        if self._surface_is_display:
            pygame.display.update()

    def _show_activity(self, door: Door) -> None:
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

        if self._surface_is_display:
            pygame.display.update()

    def _animate_intro(self) -> None:
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

    def _animate_open(self, door: Door) -> None:
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

    def _animate_open_all(self) -> None:
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

        for i in range(5, 105, 5):
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

    def run(self) -> bool:
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

        while self._state is not ActivityBoard.State.GAME_OVER:
            if self._state is ActivityBoard.State.START:
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

                pygame.event.clear()
            elif self._state is ActivityBoard.State.SELECTING:
                for event in pygame.event.get():
                    action = self._translate_action(event)

                    if action is ActivityBoard.Action.OPEN:
                        if not selected_door.is_open:
                            self._play_random_sound(self._open_sounds)
                            self._animate_open(selected_door)
                            self._show_activity(selected_door)

                            selected_door.is_open = True

                            self._state = ActivityBoard.State.IN_PROGRESS
                        else:
                            self._play_random_sound(self._oops_sounds)

                        pygame.event.clear()
                    elif action is ActivityBoard.Action.RESTART:
                        play_again = True
                        self._state = ActivityBoard.State.GAME_OVER

                        pygame.event.clear()
                    elif action is ActivityBoard.Action.QUIT:
                        play_again = False
                        self._state = ActivityBoard.State.GAME_OVER

                        pygame.event.clear()
                    elif action is ActivityBoard.Action.REVEAL:
                        self._play_random_sound(self._reveal_all_sounds)
                        
                        self._animate_open_all()

                        self._state = ActivityBoard.State.ALL_REVEALED

                        pygame.event.clear()
                    elif action in [
                            ActivityBoard.Action.UP,
                            ActivityBoard.Action.DOWN,
                            ActivityBoard.Action.LEFT,
                            ActivityBoard.Action.RIGHT
                    ]:
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
            elif self._state is ActivityBoard.State.IN_PROGRESS:
                for event in pygame.event.get():
                    action = self._translate_action(event)

                    if action is ActivityBoard.Action.RETURN:
                        self._draw_all_doors()

                        self._state = ActivityBoard.State.SELECTING

                        pygame.event.clear()
            elif self._state is ActivityBoard.State.ALL_REVEALED:
                 for event in pygame.event.get():
                    action = self._translate_action(event)

                    if action is ActivityBoard.Action.RESTART:
                        play_again = True
                        self._state = ActivityBoard.State.GAME_OVER

                        pygame.event.clear()
                    elif action is ActivityBoard.Action.QUIT:
                        play_again = False
                        self._state = ActivityBoard.State.GAME_OVER

                        pygame.event.clear()
            elif self._state is ActivityBoard.State.GAME_OVER:
                pass
            else:
                raise RuntimeError('Invalid state in main loop')

        return play_again


if __name__ == '__main__':
    print('This file should not be run directly. Run main.py instead.')