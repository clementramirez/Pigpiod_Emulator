import threading


class SerialPort:
    """
    A class that represents a virtual serial port on a machine.

        This class have two buffer, one reprensenting the data
        flowing from the machine to the serial endpoint, and another
        in the opposite direction.
        See the diagram below:
                              *----------------*
             put_input() ---->|================|----> get_input()
                              |   in_buffer    |
                              |                |
               Emulated       |     Serial     |    Pigpio Serial
                Device        |      Port      |    Port Instance
                              |                |      (Client)
                              |   out_buffer   |
            get_output() <----|================|<---- put_output()
                              *----------------*

        In addition to this only one operation can be performed at
        a time, due to the usage of locks.

    Attributes
    ----------
    port : str
        The name of the serial device.
    baud : int
        The current baudrate of the serial device.
    input_buffer : bytes[]
        Circular buffer for the input reprenseted as a list of bytes.
    output_buffer : bytes[]
        Circular buffer for the input reprenseted as a list of bytes.
    input_buffer_size : int
        The size of the input circular buffer.
    output_buffer_size : int
        The size of the output circular buffer.
    input_buffer_w_index : int
        Write pointer index for the input circular buffer.
    output_buffer_w_index : int
        Write pointer index for the output circular buffer.
    lock : <threading.Lock>
        Lock object for this serial port.

    Methods
    -------
    bind()
        Returns the current write pointer indexes for
        the input and the output buffer.
    put_output(data)
        Puts data to the output buffer.
    get_output(size, read_index)
        Gets data from the output buffer.
    output_dat_avail(read_index)
        Returns the number of bytes available on
        the output buffer.
    put_input(data)
        Puts data to the input buffer.
    get_input(size, read_index)
        Gets data from the input buffer.
    input_dat_avail(read_index)
        Returns the number of bytes available on
        the input buffer.
    """
    def __init__(self, port, baudrate, input_buffer_size=10000,
                 output_buffer_size=10000):
        """ Constructor of the SerialPort class """
        self.baudrate = baudrate
        self.port = port

        self.input_buffer_size = input_buffer_size
        self.output_buffer_size = output_buffer_size

        self.input_buffer_w_index = 0
        self.output_buffer_w_index = 0

        self.input_buffer = [0] * input_buffer_size
        self.output_buffer = [0] * output_buffer_size

        self.lock = threading.Lock()

    def bind(self):
        """
        Binds an entity with the serial port by returning the
        write pointer index of the input and the output buffers.
        """
        return self.input_buffer_w_index, self.output_buffer_w_index

    def put_output(self, data):
        """ Puts data to the output buffer """

        self.lock.acquire()

        goal_index = (self.output_buffer_w_index + len(data)) % self.output_buffer_size

        if self.output_buffer_w_index + len(data) > self.output_buffer_size:
            self.output_buffer[self.output_buffer_w_index:] = \
                data[:self.output_buffer_size - self.output_buffer_w_index]
            self.output_buffer[0:goal_index] = \
                data[self.output_buffer_size - self.output_buffer_w_index:]
            self.output_buffer_w_index = goal_index
        else:
            self.output_buffer[self.output_buffer_w_index:goal_index] = data
            self.output_buffer_w_index = goal_index

        self.lock.release()

    def get_output(self, size, read_index):
        """
        Gets data from the output buffer and updates and
        returns the updated read_index pointer value.

        The amount of data requested is specified by
        the size parameter and the read_index specifies
        from which index of the circular buffer we have
        to read data.
        """

        self.lock.acquire()

        goal_index = (read_index + size) % self.output_buffer_size

        if read_index + size > self.output_buffer_size:
            to_send = self.output_buffer[read_index:self.output_buffer_size]
            to_send += self.output_buffer[0:goal_index]
            read_index = goal_index
        else:
            to_send = self.output_buffer[read_index:goal_index]
            read_index = goal_index

        to_send = bytes(to_send)

        self.lock.release()

        return to_send, goal_index

    def put_input(self, data):
        """ Puts data to the output buffer """

        self.lock.acquire()

        data = list(data)

        goal_index = (self.input_buffer_w_index + len(data)) % self.input_buffer_size

        if self.input_buffer_w_index + len(data) > self.input_buffer_size:
            self.input_buffer[self.input_buffer_w_index:] = \
                data[:self.input_buffer_size - self.input_buffer_w_index]
            self.input_buffer[0:goal_index] = \
                data[self.input_buffer_size - self.input_buffer_w_index:]
            self.input_buffer_w_index = goal_index
        else:
            self.input_buffer[self.input_buffer_w_index:goal_index] = data
            self.input_buffer_w_index = goal_index

        self.lock.release()

    def get_input(self, size, read_index):
        """
        Gets data from the input buffer and updates and
        returns the updated read_index pointer value.

        The amount of data requested is specified by
        the size parameter and the read_index specifies
        from which index of the circular buffer we have
        to read data.
        """

        self.lock.acquire()

        goal_index = (read_index + size) % self.input_buffer_size

        if read_index + size > self.input_buffer_size:
            to_send = self.input_buffer[read_index:self.input_buffer_size]
            to_send += self.input_buffer[0:goal_index]
            read_index = goal_index
        else:
            to_send = self.input_buffer[read_index:goal_index]
            read_index = goal_index

        self.lock.release()

        to_send = bytes(to_send)

        return to_send, goal_index

    def input_dat_avail(self, read_index):
        """
        Returns the number of bytes available on
        the input buffer.
        """
        self.lock.acquire()

        if self.input_buffer_w_index > read_index:
            data_available = self.input_buffer_w_index - read_index
        elif self.input_buffer_w_index < read_index:
            data_available = self.input_buffer_size - read_index \
                                        + self.input_buffer_w_index
        else:
            data_available = 0

        self.lock.release()

        return data_available

    def output_dat_avail(self, read_index):
        """
        Returns the number of bytes available on
        the output buffer.
        """

        self.lock.acquire()

        if self.output_buffer_w_index > read_index:
            data_available = self.output_buffer_w_index - read_index
        elif self.output_buffer_w_index < read_index:
            data_available = self.output_buffer_size - read_index \
                                        + self.output_buffer_w_index
        else:
            data_available = 0

        self.lock.release()

        return data_available


class VirtualHardware:
    """
    A class that represents the Hardware Machine Emulated

    This class stores all the peripherals accessible by
    pigpiod emulator.

    These peripherals are reprensented as classes that tries
    to emulate their behaviours.

    Attributes
    ----------
    serialport : <SerialPort Object>[]
        The list of serial ports availables on the
        virtual hardware machine.

    Methodes
    --------
    add_serialport(port, baudrate)
        Adds a serial port to the virtual hardware machine.
    """
    def __init__(self):
        """ Constructor of the VirtualHardware class """

        self.serialports = []

    def add_serialport(self, port, baudrate):
        """ Adds a serial port to the virtual hardware machine """

        self.serialports.append(SerialPort(port, baudrate))
