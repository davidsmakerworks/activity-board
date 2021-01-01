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

Text rendering utility class

https://github.com/davidsmakerworks/activity-board
"""


import pygame


class TextRenderer:
    """
    Class to assist with rendering text surfaces.

    Properties:
    font -- pygame Font object used to render text
    line_spacing -- space (in pixels) between text lines
    text_color -- pygame Color object representing text color
    """

    def __init__(
            self, font: pygame.font.Font, line_spacing: int,
            text_color: pygame.Color) -> None:
        """
        Create instance using properties as shown in class documentation.
        """
        self.font = font
        self.line_spacing = line_spacing
        self.text_color = text_color

    def render_surface(self, text: str) -> pygame.Surface:
        """
        Returns a pygame Surface with the specified text rendered on it.

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


if __name__ == '__main__':
    print('This file should not be run directly. Run main.py instead.')
