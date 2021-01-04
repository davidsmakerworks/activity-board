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

Door-related classes

TODO: Make certain sounds a property of the door for increased variation

https://github.com/davidsmakerworks/activity-board

"""


import pygame

from text_renderer import TextRenderer


class DoorProperties:
    """
    Class to contain configurable properties of a Door object.

    All color-related properties are pygame Color objects.

    All font-related properties are pygame Font objects.

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
            self, bg_color: pygame.Color, door_color: pygame.Color,
            ellipse_color: pygame.Color, number_color: pygame.Color,
            cross_color: pygame.Color, selection_color:pygame.Color,
            activity_color: pygame.Color, unused_color: pygame.Color,
            activity_font: pygame.Color, line_spacing: pygame.Color,
            number_font: pygame.font.Font, border_size: int,
            ellipse_margin: int, cross_width: int, cross_offset: int,
            open_step_time: float) -> None:
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
            self, index: int, height: int, width: int, activity: str,
            props: DoorProperties, is_selected: bool = False,
            is_open: bool = False,
            is_revealed: bool = False,
            is_hidden: bool = False) -> None:
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

    def _draw_cross(self, surf: pygame.Surface) -> None:
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

    def get_door_surface(self) -> pygame.Surface:
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

                open_rect = pygame.Rect(x, y, open_width, open_height)

                surf.blit(open_surface, (x, y), open_rect)

        return surf


if __name__ == '__main__':
    print('This file should not be run directly. Run main.py instead.')
