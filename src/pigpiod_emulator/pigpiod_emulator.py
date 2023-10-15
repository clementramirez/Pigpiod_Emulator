import struct
import threading
import logging
import socket

from .virtual_hardware import VirtualHardware

class PigpiodEmulator(threading.Thread):
    """
    Main class corresponding to the pigpiod server.

        This class creates a main TCP server to which all
        pigpio clients can connect.

    Attributes
    ----------
    virtual_hardware : <VirtualHardware Object>
        Describe the hardware monitored and handle by pigpiod.
    want_stop : bool
        Specifies if a client stop has been requested.
    client_connections : <PigpioClient Object>[]
        Contains all the Clients Connected to
        the pigpiod server.
    main_server : <Socket Object>
        Represents the pigiod server to which all
        the client will connect.
    log : <Logger Object>
        The reference to the logger session used.

    Methods
    -------
    stop()
        Stops the current connection to the client.
    establish_connection(conn_1, conn_2)
        Establish connection between the server and
        the new client.
    run()
        Wait indefinitely for new connections to the
        pigpiod server.
    """
    def __init__(self, virtual_hardware=VirtualHardware()):
        """ Constructor of the PigpiodEmulator class """
        super().__init__()

        self.log = logging.getLogger("pigpiod_emulator.main")

        self.want_stop = False

        self.main_server = socket.create_server(('127.0.0.1', 8888))
        self.main_server.settimeout(5)
        self.client_connections = []
        self.virtual_hardware = virtual_hardware

    def stop(self):
        """ Stops the pigpiod emulator """

        self.log.warn('Stopping pigpio clients...')
        self.want_stop = True

    def establish_connection(self, conn_1, conn_2):
        """ Establish connection between the server and the new client """

        conn_2.send(struct.pack('IIII', 10, 0, 0, 0))
        notification_client = conn_2
        main_client = conn_1

        return main_client, notification_client

    def run(self):
        """ Runs indefinitely as long as we don't want to stop """

        while not self.want_stop:
            try:
                conn_1, __ = self.main_server.accept()
                conn_2, __ = self.main_server.accept()

                self.log.info('Connecting to the incomming connection...')

                main_client, notification_client = self.establish_connection(conn_1, conn_2)

                self.client_connections.append(PigpioClient(main_client,
                                                            notification_client,
                                                            len(self.client_connections),
                                                            self.virtual_hardware))

                self.log.info('Connection established with {} throught {} port'.format(main_client.getpeername()[0],
                                                                                       main_client.getpeername()[1]))
            except socket.timeout:
                pass

        for client in self.client_connections:
            client.stop()
            client.join()

        self.main_server.close()
        self.log.warn('All the client instances are stopped, exiting pigpiod, Bye bye !')


def main():
    logging.basicConfig()

    # Describe the virtual hardware used
    virtual_hardware = VirtualHardware()
    virtual_hardware.add_serialport("/dev/ttyAMA0", 115200)
    virtual_hardware.add_serialport("/dev/ttyUSBMotorCard", 115200)

    pigpiod = PigpiodEmulator()
    pigpiod.start()


if __name__ == "__main__":
    main()
