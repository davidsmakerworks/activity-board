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

Main program that instantiates ActivityBoard class and runs game

Config file is specified on command line or defaults
to config.json if not specified

TODO: Determine which PyGame functions should be moved to the
    ActivityBoard class

https://github.com/davidsmakerworks/activity-board
"""


import json
import random
import sys

import pygame

from activity_board import ActivityBoard
from screen import Screen


def main():
    """
    Main program that does some PyGame initialization and runs the
    activity board.
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
            start_hidden=True,
            surface_is_display=True)

        play_again = board.run()

    pygame.quit()


if __name__ == '__main__':
    main()
