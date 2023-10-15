import logging
import struct
import threading
import socket


# pigpio command numbers

_PI_CMD_SERO = 76
_PI_CMD_SERC = 77
_PI_CMD_SERRB = 78
_PI_CMD_SERWB = 79
_PI_CMD_SERR = 80
_PI_CMD_SERW = 81
_PI_CMD_SERDA = 82


class PigpioClient(threading.Thread):
    """
    A class describing a Client connected to the pigpiod server

        This class is designed to be threaded, that's why it inherits
        from the 'threading.Thread' class.
        The thread is automatically started during the creation of
        the class.

    Attributes
    ----------
    main_conn : <socket Object>
        The socket that identifies the main client socket.
    notification_conn : <socket Object>
        The socket that identifies the notification socket.
        It is used to send information without a client requests.
    id : int
        The id attributed to this client connection.
    virtual_hardware : <VirtualHardware Object>
        Describe the hardware monitored and handle by pigpiod.
    serial_instances : <SerialPortInstance Object>[]
        Contains all the serial port instances handled by this client.
    log : <Logger Object>
        The reference to the logger session used.
    want_stop : bool
        Specifies if a client stop has been requested.

    Methods
    -------
    send_notification(self, msg)
        Sends a message (designated by the msg arg) to the client
        notification socket.
    stop()
        Stops the current connection to the client
    run()
        Overflow of the run function described in the 'threading.Thread'
        class.
        This function is executed on a different thread once instantiated.
    """
    def __init__(self, main_conn, notification_conn, id, virtual_hardware):
        """ Constructor of the Pigpio Client Class """

        super().__init__()
        self.main_conn = main_conn
        self.notification_conn = notification_conn
        self.id = id
        self.virtual_hardware = virtual_hardware
        self.serial_instances = []

        self.main_conn.settimeout(None)

        self.log = logging.getLogger("pigpiod_emulator.client_{}".format(self.id))

        self.want_stop = False

        self.start()

    def send_notification(self, msg):
        """ Sends a message to the client notification socket """
        pass

    def stop(self):
        """ Stops the current connection to the client """
        self.main_conn.shutdown(socket.SHUT_RDWR)
        self.want_stop = True

    def run(self):
        """
        This function is runned indefinitely while the connection
        with the client is maintained.
        It checks if a new frame of data is available on the main
        client connection, parse it and finally interprets it by
        calling related functions.
        """

        self.notification_conn.send(struct.pack('IIII', 10, 0, 0, 0))

        while not self.want_stop:
            try:
                # Wait for the next frame to come
                raw = self.main_conn.recv(16)
                if not raw:
                    self.log.info("Connection lost with client ID n°{}".format(self.id))
                    break

                cmd, p1, p2, p3 = struct.unpack('II4sI', raw)

                if p3 != 0:
                    ext = struct.unpack(f'{p3}s', self.main_conn.recv(p3))[0]
                    p2 += ext

                self.log.debug("New frame received from client ID n°{}: ".format(self.id))
                self.log.debug("     cmd: {}".format(cmd))
                self.log.debug("     p1: {}".format(p1))
                self.log.debug("     p2: {}".format(p2))
                self.log.debug("     p3: {}".format(p3))

                if cmd == _PI_CMD_SERO:
                    # Request to open a serial port
                    ext = ext.decode('ascii')
                    for serialport in self.virtual_hardware.serialports:
                        if serialport.port == ext and serialport.baudrate == p1:
                            self.serial_instances.append(PigpioSerialInstance(serialport,
                                                                              len(self.serial_instances),
                                                                              self.main_conn))
                            self.serial_instances[-1].open(p2, p1)
                            break
                    else:
                        self.main_conn.send(struct.pack('IIIi', 0, 0, 0, -1))
                        self.log.error("Serial port '{}' does not exist".format(p2))
                elif cmd == _PI_CMD_SERC:
                    # Request to close an existing serial port connection
                    self.serial_instances[p1].close()
                elif cmd == _PI_CMD_SERW:
                    # Request to write data to a specified serial port
                    self.serial_instances[p1].write_request(p2)
                elif cmd == _PI_CMD_SERR:
                    # Request to read data on a specified serial port
                    p2 = struct.unpack('I', p2)[0]
                    self.serial_instances[p1].read_request(p2)
                elif cmd == _PI_CMD_SERDA:
                    # Request to get the amount of available data to
                    # read on the serial port.
                    self.serial_instances[p1].data_available_request()
                else:
                    # If the received command is not implemented
                    self.log.warn("Command '{}' not implemented yet".format(cmd))
            except socket.timeout:
                pass

        self.main_conn.close()
        self.notification_conn.close()


class PigpioSerialInstance:
    """
    A class that represents a serial instance instantiated by a client

        This class is in charge to bind a single pigpio client to a unique
        virtual serial port.

        It will handle the convertion between the socket connection
        exposed by the client to the serial port emulated by the
        corresponding class.

    Attributes
    ----------
    serialport : <SerialPort Object>
        Specifies the virtual serial port bound to the pigpio client.
    handle_id : int
        Id number attributed to this serial port instance.
    main_conn : <socket Object>
        The socket that identifies the main client socket.
    input_buffer_r_index : int
        The input buffer pointer index used to get data from
        the input buffer of the serial port.
    output_buffer_r_index : int
        The output buffer pointer index user to get data from
        the output buffer of the serial port.
    log : <Logger Object>
        The reference to the logger session used.

    Methods
    -------
    open(port, baudrate)
        Binds the pigpio client to the emulated serial port.
    close()
        Unbind the pigpio client to the emulated serial port.
    write_request(data)
        Writes new data to the emulated serial port.
    read_request(size)
        Reads new data to the emulated serial port.
    request_avail_data()
        Get the amount of bytes to read from the serial port.
    """
    def __init__(self, serialport, handle_id, main_conn):
        """ Constructor of the Pigpio Client Class """

        self.serialport = serialport
        self.handle_id = handle_id
        self.main_conn = main_conn

        self.input_buffer_r_index = 0
        self.output_buffer_r_index = 0

        self.log = logging.getLogger("pigpiod_emulator_serial_instance_{}".format(self.handle_id))

    def open(self, port, baudrate):
        """ Binds the pigpio client to the emulated serial port """

        self.input_buffer_r_index, self.output_buffer_r_index = self.serialport.bind()

        self.main_conn.send(struct.pack('IIII', 0, 0, 0, self.handle_id))
        self.log.info("Serial instance n°{} attached to port '{}' with baudrate {}".format(self.handle_id,
                                                                                           port, baudrate))

    def close(self):
        """ Unbind the pigpio client to the emulated serial port """
        self.main_conn.send(struct.pack('IIII', 0, 0, 0, self.handle_id))
        self.log.info("Serial instance n°{} detached from port '{}'".format(self.handle_id,
                                                                            self.serialport.port))

    def write_request(self, data):
        """ Writes new data to the emulated serial port """

        __, to_add = struct.unpack(f'I{len(data) - 4}s', data)
        self.serialport.put_output(to_add)

        self.log.info("New data written to serial instance n°{}: {}".format(self.handle_id,
                                                                            to_add.decode('utf-8')))

        self.main_conn.send(struct.pack('IIII', 0, 0, 0, self.handle_id))

    def read_request(self, size):
        """ Reads new data to the emulated serial port """

        if size > self.serialport.input_dat_avail(self.input_buffer_r_index):
            size = self.serialport.input_dat_avail(self.input_buffer_r_index)

        to_send, self.input_buffer_r_index = self.serialport.get_input(size,
                                                                       self.input_buffer_r_index)

        self.log.info("New data read from serial instance n°{}: {}".format(self.handle_id,
                                                                           to_send.decode('utf-8')))

        self.main_conn.send(struct.pack('IIII', 0, 0, 0, len(to_send)))
        self.main_conn.send(to_send)

    def data_available_request(self):
        """ Get the amount of bytes to read from the serial port """

        data_available = self.serialport.input_dat_avail(self.input_buffer_r_index)
        self.main_conn.send(struct.pack('IIII', 0, 0, 0, data_available))
