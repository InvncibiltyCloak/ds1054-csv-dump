# ds1054-csv-dump
Get the data off your DS1054Z oscilloscope so you can look at it better/later.

The script is designed to download data fast so that you can download large (24M sample) captures quickly.

It is a Python script with no dependencies. The output is a CSV file for easy plotting. 

# Usage

Connect your oscilloscope via LAN. (There are apparently bugs with the USB connection.)

Then just call main.py with the ip address and optionally a filename for the data. 

```
usage: main.py [-h] [-u] oscilloscope_ip [filename]

Download memory from Rigol DS1054Z oscilloscopes.Currently only supports download of all memory into CSV format.

positional arguments:
  oscilloscope_ip    IP address of oscilloscope to download data from
  filename           filename for the resulting CSV file. If no name is supplied, the filename will be the current timestamp

options:
  -h, --help         show this help message and exit
  -u, --unsupported  Allow unsupported oscilloscope models. Defaults to false
```

# Future Ideas

It would be nice if you could export other stuff, like pictures of the screen and what all the settings are. This is easy to do in an interactive terminal, it is just a matter of adding the command line options and other code.

# Other Notes

The `SCPIComm` class in `scpi_comm.py` is pretty useful for communicating with the scope on the command line.

I am not 100% certain the voltage scaling on this script is correct. There are some reports that it is buggy on the oscilloscope and cannot be scaled correctly.

