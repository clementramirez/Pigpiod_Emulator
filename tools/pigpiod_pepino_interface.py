import socket
import threading
import logging
import time

from pigpiod_emulator import VirtualHardware, PigpiodEmulator


class user_card_recv_Thread(threading.Thread):
    def __init__(self, user_card, pigpiod):
        threading.Thread.__init__(self)
        self.user_card = user_card
        self.pigpiod = pigpiod

    def run(self):
        while True:
            data = self.user_card.recv(1)
            #print('data', data)
            if data:
                self.pigpiod.virtual_hardware.serialports[0].put_input(data)

class motor_card_recv_Thread(threading.Thread):
    def __init__(self, motor_card, pigpiod):
        threading.Thread.__init__(self)
        self.motor_card = motor_card
        self.pigpiod = pigpiod

    def run(self):
        while True:
            data = self.motor_card.recv(1)
            #print('data', data)
            if data:
                self.pigpiod.virtual_hardware.serialports[1].put_input(data)

if __name__ == '__main__':
    # Configure the logger
    logging.basicConfig(filename='test_pepino.log', level=logging.DEBUG)

    # Describe the virtual hardware used
    virtual_hardware = VirtualHardware()
    virtual_hardware.add_serialport("/dev/ttyAMA0", 115200)
    virtual_hardware.add_serialport("/dev/ttyUSBMotorCard", 115200)

    # Start the pigpio daemon emulator with the virtual hardware
    pigpiod = PigpiodEmulator(virtual_hardware)
    pigpiod.start()
    # Connect the 2 Pepino's servers
    # user_card = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # user_card.connect(('192.168.0.45', 5000))

    motor_card = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    motor_card.connect(('localhost', 5000))

    print('Connected !')

    # Start the threads that will receive the data from the Pepino's servers
    # user_card_recv_Thread(user_card, pigpiod).start()
    motor_card_recv_Thread(motor_card, pigpiod).start()

    # Check if there is any data to send to the Pepino's servers
    user_card_read_index = 0
    motor_card_read_index = 0

    while True:
        # user_data_nb = pigpiod.virtual_hardware.serialports[0].data_available_out(user_card_read_index)
        # if user_data_nb > 0:
        #     data = pigpiod.virtual_hardware.serialports[0].get_output(user_data_nb, user_card_read_index)
        #     user_card.send(data)
        #     user_card_read_index += user_data_nb
        #     print('data sent', data)

        motor_data_nb = pigpiod.virtual_hardware.serialports[1].output_dat_avail(motor_card_read_index)
        if motor_data_nb > 0:
            data, motor_card_read_index = pigpiod.virtual_hardware.serialports[1].get_output(motor_data_nb, motor_card_read_index)
            print('data sent', data)
            motor_card.send(data)

        time.sleep(0.001)

