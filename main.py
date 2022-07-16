#! /usr/bin/env python3
import argparse
import platform
import logging
import os
import sys
import datetime
import csv

from scpi_comm import SCPIComm

LXI_PORT = 5555
# On the DS1054Z, the maximum amount you can transfer at once is 500000
# The larger the chunk size the faster the transfer
CHUNK_SIZE = 500000 

# Set the desired logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=os.path.basename(sys.argv[0]) + '.log',
    filemode='w',
)

logging.info("Start of program.")

parser = argparse.ArgumentParser(
    description='Download memory from Rigol DS1054Z oscilloscopes. ' +
    'Currently only supports download of all memory into CSV format.'
)

parser.add_argument(
    '-u', '--unsupported',
    help="Allow unsupported oscilloscope models. Defaults to false",
    action='store_true'
)

parser.add_argument(
    'oscilloscope_ip',
    help="IP address of oscilloscope to download data from",
)

parser.add_argument(
    'filename',
    help="filename for the resulting CSV file. If no name is supplied, the filename will be the current timestamp",
    type=argparse.FileType('w', encoding='utf-8'),
    nargs="?"
)

args = parser.parse_args()

def validate_address(address: str) -> bool:
    if platform.system() == "Windows":
        response = os.system("ping -n 1 " + args.oscilloscope_ip + " > nul")
    else:
        response = os.system("ping -c 1 " + args.oscilloscope_ip + " > /dev/null")
    
    return response == 0

      
    
def validate_scope_id(id_string:str) -> bool:
    id_fields = id_string.split(",")
    if len(id_fields) == 4:
        company = id_fields[0]
        model = id_fields[1]
        serial = id_fields[2]
        version = id_fields[3]
    else:
        logging.error("Invalid response to *IDN? command")
        sys.exit(1)
    
    logging.info(f"Found instrument model '{model}' from '{company}'")

    is_supported = company == "RIGOL TECHNOLOGIES" and model[:3] == "DS1" and model[-1] == "Z"

    return is_supported


if __name__ == "__main__":
    if not validate_address(args.oscilloscope_ip):
        print ()
        print ("WARNING! No response pinging " + args.oscilloscope_ip)
        print ("Make sure this is a valid address, then check network cables and settings.")
        print ("You should be able to ping the oscilloscope.")
        sys.exit(1)


    comm = SCPIComm(args.oscilloscope_ip, LXI_PORT)
    response = comm.query("*IDN")

    if not validate_scope_id(response):
        if args.unsupported:
            logging.warning(f"Scope company and model not supported. Continuing anyway due to commandline option...")
        else:
            logging.error(f"Scope company and model not supported. Exiting.")
            sys.exit(1)

    # Check the current status. Oscilloscope data download only works when stopped
    # The queries will be used later to restore scope state after the stop command
    status = comm.query(":TRIG:STAT")
    sweep_type = comm.query(":TRIG:SWE")
    if status != "STOP":
        comm.set(":STOP", "")
        comm.wait()
        stopped_status = comm.query(":TRIG:STAT")
        if stopped_status != "STOP":
            logging.error("Oscilloscope did not stop after :STOP command. Exiting.")
            sys.exit(1)


    comm.set(":WAV:MODE", "RAW")
    comm.set(":WAV:FORM", "BYTE")

    # sys.exit(0)

    preamble_split = comm.query(":WAV:PRE").split(',')
    memory_depth = int(preamble_split[2])
    xincrement = float(preamble_split[4])
    xorigin = float(preamble_split[5])

    # metadata_split = comm.query(":WAV:PRE").split(',')
    # metadata = {
    #     'format': metadata_split[0],
    #     'type': metadata_split[1],
    #     'points': int(metadata_split[2]),
    #     'count': int(metadata_split[3]),
    #     'xincrement': float(metadata_split[4]),
    #     'xorigin': float(metadata_split[5]),
    #     'xreference': int(metadata_split[6]),
    #     'yincrement': float(metadata_split[7]),
    #     'yorigin': int(metadata_split[8]),
    #     'yreference': int(metadata_split[9]),
    # }
    
    channel_data = []
    channel_data.append(['TIME'] + [i*xincrement - xorigin for i in range(memory_depth)])

    for channel in range(1,5):
        response = comm.query(f":CHAN{channel}:DISP")

        if response == "1":
            logging.info(f"Channel {channel} is active onscreen")

            comm.set(":WAV:SOUR", f"CHAN{channel}")

            preamble_split = comm.query(":WAV:PRE").split(',')
            yincrement = float(preamble_split[7])
            yorigin = int(preamble_split[8])
            yreference = int(preamble_split[9])

            channel_data.append([f'CHAN{channel}'])

            for i in range(1, memory_depth+1, CHUNK_SIZE):
                start = i
                stop = min(i+CHUNK_SIZE-1, memory_depth)

                comm.set(":WAV:STAR", str(start))
                comm.set(":WAV:STOP", str(stop))

                chunk_data = comm.get_waveform_data()
                chunk_data_scaled = [(raw_byte - yorigin - yreference) * yincrement for raw_byte in chunk_data]

                channel_data[-1] += chunk_data_scaled



    with open(datetime.datetime.now().strftime('%Y-%m-%mT%H:%M:%S') + '.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(zip(*channel_data))

