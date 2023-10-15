import warnings
from .virtual_hardware import VirtualHardware
from .pigpiod_emulator import PigpiodEmulator

def __getattr__(name):
    if name == "client_instances":
        warnings.warn("Directly import virtual_hardware module is not \
                      possible !")
    elif name == "virtual_hardware":
        warnings.warn("Directly import client_instances module is not \
                      possible !")
    elif name == "pigpiod_emulator":
        warnings.warn("Directly import pigpiod_emulator module is not \
                      possible !")
    elif name == "warnings":
        warnings.warn("warnings lib not supposed to be imported like \
                      this !")
