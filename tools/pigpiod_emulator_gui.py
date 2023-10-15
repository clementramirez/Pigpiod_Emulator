import sys
import curses
import logging
import time

from pigpiod_emulator import *


class Window:
    def __init__(self, stdscr, height, width, y, x):
        """  """
        self.stdscr = stdscr
        self.height = height
        self.width = width
        self.y = y
        self.x = x

        self.window = curses.newwin(height, width, y, x)

    def refresh(self):
        self.window.refresh()

    def clear(self):
        self.window.clear()

    def addstr(self, y, x, string, attr=None):
        if attr is None:
            self.window.addstr(y, x, string)
        else:
            self.window.addstr(y, x, string, attr)

    def attron(self, attr):
        self.window.attron(attr)

    def attroff(self, attr):
        self.window.attroff(attr)

    def border(self):
        self.window.border()


class TitleWindow(Window):
    def __init__(self, stdscr):
        __, term_width = stdscr.getmaxyx()
        super().__init__(stdscr, 3, term_width, 0, 0)

        self.main_app_name = "Pigpiod Emulator"
        self.output_window_title = "Output : Main"

        self.update_geometry()

    def update_geometry(self):
        self.clear()

        term_height, term_width = self.stdscr.getmaxyx()

        # Update window size
        self.width = term_width

        self.window = curses.newwin(3, self.width, 0, 0)

        start_x_title = int((self.width // 2) - (len(self.main_app_name) // 2) - len(self.main_app_name) % 2)
        start_x_output_title = int((self.width // 2) - (len(self.output_window_title) // 2) - len(self.output_window_title) % 2)

        self.attron(curses.color_pair(4))
        self.addstr(0, 0, " " * (start_x_title))
        self.addstr(0, start_x_title, self.main_app_name)
        self.addstr(0, start_x_title + len(self.main_app_name), " " * (start_x_title -1))
        self.attroff(curses.color_pair(4))

        self.addstr(2, start_x_output_title, self.output_window_title)

        self.refresh()


class OutputWindow(Window):
    def __init__(self, stdscr):
        term_height, term_width = stdscr.getmaxyx()

        super().__init__(stdscr, term_height-5, term_width-5, 3, 2)

        self.active = False

        self.content = []
        self.selected_line = 1
        self.index_shift = 0

        self.handler = self.Outputmessagehandler(self)
        self.handler.setLevel(logging.DEBUG)
        self.handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.log = logging.getLogger()
        self.log.addHandler(self.handler)

        self.update_geometry()

    class Outputmessagehandler(logging.Handler):
        def __init__(self, output_window):
            super().__init__()

            self.output_window = output_window

        def emit(self, record):
            self.output_window.content.append(self.format(record))
            self.output_window.refresh_content(self.output_window.content)

    def activate(self):
        self.active = True

        curses.curs_set(0)

        self.set_highlight(self.selected_line, 3)

    def deactivate(self):
        self.active = False

        self.set_highlight(self.selected_line, 0)

    def update_geometry(self):
        self.clear()

        term_height, term_width = self.stdscr.getmaxyx()

        # To adapt
        self.selected_line = 1
        self.index_shift = 0

        # Update window size
        self.height = term_height - 5
        self.width = term_width - 5

        self.window = curses.newwin(self.height, self.width, self.y, self.x)

        self.border()

        self.refresh_content(self.content)

        self.refresh()

    def refresh_content(self, content):
        # Save the last position of the cursor
        x, y = stdscr.getyx()

        start_index = len(content) - (self.height - 2) - self.index_shift
        if start_index < 0:
            start_index = 0
        stop_index = len(content) - self.index_shift


        for line_nb, line in enumerate(content[start_index:stop_index]):
            line = line.replace("\n", "")
            if len(line) > self.width - 5:
                line = line[:self.width-7] + "..."
            else:
                line = line + " " * (self.width - 4 - len(line))
            self.addstr(line_nb+1, 2, line)

        # Restore the cursor position
        stdscr.move(x, y)

        self.refresh()

    def set_highlight(self, selected_line, state):

        # add empty lines to content to fill the window height
        content = self.content.copy()
        if len(content) < self.height - 2:
            content += [""] * (self.height - 2 - len(content))

        content_index = len(content) - (self.height - selected_line) - self.index_shift + 1

        self.attron(curses.color_pair(int(state)))
        self.addstr(selected_line, 2, content[content_index] + " " * (self.width - 4 - len(content[content_index])))
        self.attroff(curses.color_pair(int(state)))
        self.refresh()

    def run(self, k):
        if True:
            if k == curses.KEY_UP:
                if self.selected_line > 1:
                    self.set_highlight(self.selected_line, 0)
                    self.selected_line -= 1
                    self.set_highlight(self.selected_line, 3)
                else:
                    if len(self.content) - (self.height - self.selected_line) - self.index_shift >= 0:
                        self.index_shift += 1
                        self.refresh_content(self.content)
                        self.set_highlight(self.selected_line, 3)
            elif k == curses.KEY_DOWN:
                if self.selected_line < (self.height - 2):
                    self.set_highlight(self.selected_line, 0)
                    self.selected_line += 1
                    self.set_highlight(self.selected_line, 3)
                else:
                    if self.index_shift > 0:
                        self.index_shift -= 1
                        self.refresh_content(self.content)
                        self.set_highlight(self.selected_line, 3)



class InputWindow(Window):
    def __init__(self, stdscr):
        self.term_height, self.term_width = stdscr.getmaxyx()
        super().__init__(stdscr, 1, self.term_width, self.term_height-1, 0)

        self.active = False

        self.text = ""

        self.update_geometry()

    def activate(self):
        self.active = True

        curses.curs_set(1)

        self.stdscr.move(self.term_height-1, len(self.text) + 3)

    def deactivate(self):
        self.active = False

    def update_geometry(self):
        self.clear()

        self.term_height, self.term_width = self.stdscr.getmaxyx()

        # Update window size
        self.width = self.term_width

        self.window = curses.newwin(1, self.width, self.term_height-1, 0)

        self.attron(curses.color_pair(3))
        self.addstr(0, 0, "=> ")
        self.addstr(0, 2, " " * (self.width - 3))
        self.attroff(curses.color_pair(3))

        self.refresh()

    def text_cmd_interpreter(self, text):
        if text == "clear":
            output_window.content.clear()
            output_window.clear()
            output_window.update_geometry()
        if text == "exit":
            pigpiodemulator.stop()
            pigpiod_gui.want_stop = True
        else:
            pigpiodemulator.virtual_hardware.serialports[1].put_input((text+'\n').encode('utf-8'))
            output_window.refresh_content(output_window.content)

    def run(self, k):
        if self.active:
            if k == curses.KEY_BACKSPACE:
                self.text = self.text[:-1]
            elif k == curses.KEY_ENTER or k == 10:
                text = self.text
                self.text = ""
                self.addstr(0, 3, " " * (self.width - 5), curses.color_pair(3))
                self.stdscr.move(self.term_height-1, 3)
                self.refresh()

                self.text_cmd_interpreter(text)
            else :
                self.text += chr(k)

            self.addstr(0, 3, " " * (self.width - 5), curses.color_pair(3))
            self.addstr(0, 3, self.text, curses.color_pair(3))
            self.refresh()


class PigpiodEmulatorGUI():
    def __init__(self):
        global stdscr
        stdscr = curses.initscr()

        stdscr.keypad(True)

        stdscr.clear()
        stdscr.refresh()

        self.want_stop = False

        # Start colors in curses
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_RED)

    def start(self):
        global main_title_window
        global output_window
        global input_window

        main_title_window = TitleWindow(stdscr)
        output_window = OutputWindow(stdscr)
        input_window = InputWindow(stdscr)

        curses.noecho()

        active_function = 1

        height, __ = stdscr.getmaxyx()
        stdscr.move(height-1, 3)

        # Loop where k is the last character pressed
        k = 1
        while not self.want_stop:
            if k == curses.KEY_RESIZE:
                stdscr.clear()
                stdscr.refresh()

                main_title_window.update_geometry()
                output_window.update_geometry()
                input_window.update_geometry()
            elif k == 9:
                active_function += 1

                if active_function >= 2:
                    active_function = 0

                if active_function == 0:
                    input_window.deactivate()
                    output_window.activate()
                elif active_function == 1:
                    input_window.activate()
                    output_window.deactivate()
            else :
                input_window.run(k)
                output_window.run(k)

            k = stdscr.getch()

        curses.endwin()
        sys.exit()



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s | %(name)s: %(message)s', filename='pigpiod_emulator.log', filemode='w')

    global pigpiodemulator

    virtual_hardware = VirtualHardware()
    virtual_hardware.add_serialport('/dev/ttyAMA0', 115200)
    virtual_hardware.add_serialport('/dev/ttyUSBMotorCard', 115200)

    pigpiodemulator = PigpiodEmulator(virtual_hardware)

    pigpiod_gui = PigpiodEmulatorGUI()
    pigpiod_gui.start()
