# activity-board
 A fun way to select random activities

 This is a program designed for the Raspberry Pi that makes it fun  to select a random activity for a class or other group.

 Main code released under MIT License.

## Requirements
- Python 3.6 or later
- Pygame 1.9.6 (pygame 2 **not** recommended)

The pre-installed version of pygame on RaspiOS is 1.9.4post1. If you get an error related to pygame.get_init(), you need to upgrade to 1.9.6. To upgrade to 1.9.6, run the following command: `sudo pip3 install pygame==1.9.6`

## Instructions
Edit the file `activities.txt` (unless a different file is specified in configuration) with your desired activity choices. Use a back quote (`) to indicate a new line.

Edit the configuraton file (`config.json` by default) to customize the activity board.

Start the game by running `main.py`.

Example (Linux): `python3 main.py`

Example (Windows): `py main.py`

### Joystick controls
- Move selection with **digital pad or POV hat**
- Press **A** to open selected door
- Press **B** to return to selection screen
- Hold **X** then press **Y** to reveal all doors
- Press **START** to shuffle and reset all doors
- Press **LB** and **RB** then press **BACK** to exit

### Keyboard controls
- Move selection with **arrow keys** or **WASD**
- Press **ENTER** or **SPACE** to open selected door
- Press **ESC** or **BACKSPACE** to return to selection screen
- Hold **LEFT-SHIFT** then press **Z** to reveal all doors
- Press **HOME** to shuffle and reset all doors
- Hold **LEFT-SHIFT** and **LEFT-CTRL** then press **Q** to exit

## Limitations/Possible Enhancements
- Time delays are optimized for Raspberry Pi 3 and might need to be changed for other versions
