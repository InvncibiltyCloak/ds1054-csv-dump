import socket
import logging
import time


class SCPIComm():
    def __init__(self, ip:str, port:int):
        '''Initialize a SCPI device at a specific IP address and port number.'''
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((ip, port))


    def send(self, buffer:bytes) -> None:
        '''Internal function that sends bytes over the TCP port.
        
        This function is used to intercept the messages and log them for debugging.'''
        logging.debug(f'--> {repr(buffer.decode("utf-8"))}')
        self._sock.sendall(buffer + b"\n")


    def set(self, command:str, value:str) -> None:
        '''Sets a SCPI parameter to a certain value. There will be no return value.'''
        self.send(f'{command} {value}\n'.encode('utf-8'))
        logging.info(f"Set: {command} | Value: {value}")


    def query(self, command:str) -> str:
        '''Sends a SCPI query for a parameter and returns the result as a string.'''
        self.send(f'{command}?\n'.encode('utf-8'))
        response = self.readline()
        logging.info(f"Query: {command} | Response: {response}")
        return response


    def get_waveform_data(self) -> bytes:
        '''Optimized query for waveform data.'''
        self.send(':WAV:DATA?\n'.encode('utf-8'))
        data = self.read_tmc_data()
        return data


    def wait(self):
        '''Uses the *OPC query to wait until the scope is no longer busy.'''
        response = ""
        first = True
        while response != "1":
            if first:
                first = False
            else:
                time.sleep(1)
            response = self.query("*OPC")  # previous operation(s) has completed ?


    def readline(self) -> str:
        '''Internal function that reads data until it finds a newline.'''
        return self.read_until(b'\n')


    def read_until(self, delim:bytes) -> str:
        '''Internal function that reads data until a specific delimiter is hit.'''
        last_char = b''
        receive_bytes = b''
        while last_char != delim:
            last_char = self._sock.recv(1)
            receive_bytes += last_char
        
        response = receive_bytes.decode('utf-8').strip()
        logging.debug(f'<-- {response}')
        return response


    def read_tmc_data(self) -> bytes:
        '''Reads data that has a TMC header. 
        
        This is much more optimized than reading all data for a newline
        and can deal with binary data that may accidentally include the
        newline character.'''
        tmc_header = self._sock.recv(11) # receive TMC header
        data_length = int(tmc_header[2:].decode('utf-8'))

        data = b''
        received_length = 0
        while received_length < data_length:
            receive_buffer = self._sock.recv(data_length - received_length)
            data += receive_buffer
            received_length = len(data)
    
        self.readline() # Flush anything left in the receive buffer

        return data

