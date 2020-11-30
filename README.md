# activity-board
 A fun way to select random activities

 This is a program designed for the Raspberry Pi that makes it fun  to select a random activity for a class or other group.

 Main code released under MIT License.
 
 Sound effects created by Little Robot Sound Factory (www.littlerobotsoundfactory.com) and licensed under Creative Commons (https://creativecommons.org/licenses/by/3.0/)

## Requirements
- Python 3.6 or later
- PyGame 1.9 or later
- USB game controller
- 1920x1080 screen resolution

## Instructions
Edit the file **activities.txt** with your desired activity choices. Use a back quote (`) to indicate a new line.

### Joystick functions
- Move selection with **digital pad or POV hat**
- Press **A** to open selected door
- Press **B** to return to selection screen
- Hold **X** then press **Y** to reveal all doors
- Press **START** to shuffle and reset all doors
- Hold **LB** and **RB** then press **BACK** to exit

## Limitations/Possible Enhancements
- Screen resolution must be exactly 1920x1080
- Joystick is required - no keyboard support at this time
- Time delays are optimized for Raspberry Pi 3 and might need to be changed for other versions

## Debugging
- Debug mode can be activated by passing the command line argument **debug**
- Extra debugging can be activated by passing the command line argument **debug2**
- No dashes or slashes are used before the argument. Example: `python3 activityboard.py debug`