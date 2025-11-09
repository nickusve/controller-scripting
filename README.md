# Controller Scripting
This repository contains software used for scripting controller inputs using a Raspberry Pi. In order to use this each of the inputs of a controller must be connected to a GPIO pin of a Pi.

During development a PowerA "Enhanced" controller was used. It conveniently has an accessible test point for every button input and uses 3.3v logic, so "pressing" a button only requires setting a GPIO to high. This is the foundation of how the scripting works.

## Requirements
* Python 3.11
* python3-smbus (for DAC control)
* Pi i2c enabled (for DAC control)


## Scripts & Routines
Automation of inputs is broken up into two different types of actions:
* Scripts
* Routines

Scripts are a sequence of commands to execute, while Routines are a sequence of _scripts_ to execute.

### Scripts
Scripts are a set of actions to execute, and require both a script and a configuration to run. The "Running" section below will cover this in more depth, read on to better understand what these files are.

#### Configuation
While scripts define the actions to take the configuration defines what inputs of the Pi map where, and how things are to be controlled. See the "defaults" subdirectory for example configs, or read on to understand the fields:

* board_pin_map - this is a map of the buttons to what GPIO pins they connect to
  * As of writing the default is for a switch controller and the code itself is expecting these buttons. The code and the config can be expanded to support other controllers / buttons
* stick_channels - This maps the X and Y movements of sticks to the DAC channel that controls them
  * As of writing the code is designed around the use of an MCP4728 DAC to provide the voltage of LX/LY/RX/RY. The code includes a driver to do so with a Pi. This could be modified to use other DACs while still reusing this field to indicate teh channel number
* stick_settings - Config settings specific to how the sticks are used, mainly tailored towards the MCP4728
  * bus - i2c bus
  * address 0 i2c address
  * vref - 0 for VDD, 1 for internal voltage ref
  * gain - 0 for gain of 1, 1 for gain of 2
  * max - the DAC value that represents a stick moved to the maximum position
  * min - the DSC value that represents a stick unmoved
  * deadzone - from the min, the last value in which the stick is in the deadzone (I.e. any value higher then this will result in stick movement)
  * reset_on_start - If the stick should be zeroed out when a script starts
* min_transition_times_ms - The minimum time between actions for sticks and buttons in order for them to be processed, any faster and the input may be dropped or broken
* reset_inputs_on_exit - whether to zero sticks and release buttons when a script is done
* abort_if_file_present - (May be removed) A file which, if it exists, will abort a script


#### Script CSVs
Scripts are stored as CSV files with a custom format. See the scripts subdirectory for example scripts as they will be the most useful, or read on to understand the fields:

* input - the input to press or stick to move
  * Inputs can be anything in the board_pin_map field of the config file, or any stick in the stick_channels section of the config file
* angle - the angle to move a stick, ignored for buttons
* magnitude - How far (-100 to 100) to move a stick, ignored for buttons
* start_delay_ms - how long to wait before executing the action
* duration_ms - how long to hold a button or keep a stick in a position
* start_after_id - what action / line to run this action after
  * defaults to the line above
* id - a way to name an action
  * Typically used in combination with start_after_id to enable simultaneous actions like holding a trigger and pressing a button
  * Can also be used to name actions making debugging a script easier
  * **Note** - there is a (hidden) "start" id that occurs _before_ the _first_ line in the CSV

### Routines
Routines are akin to a script of scripts. See the "routines" subdirectory for examples or read on for a brief description.

Routines combine a configuration, and must have the configuration fields, as wel las a list of scripts (with repeats per script) to run. Note that all scripts run once, so repeats == 0 means run once, while repeats == 1 means run twice.

Scripts and their repeats are run in the order they appear.

## Running
### Running preface
During development it was noticed that (at least the PowerA) controllers do a type of calibration of their sticks when they connect to a device (switch,  in the example of development). As such, whatever the DAC is set to when the controller connects is used as "zero". To avoid unintentional movements it is recommended to pre-zero or reset sticks before connecting a controller. 
There is , of course, a script to help with this (at least for the PowerA controller). scripts/reset_and_connect_controller.csv will reset the sticks and press a button to wake up the controller and allow it to connect. This should be done whenever re-connecting a controller

### Running Scripts & Routines

The Run program is what runs both scripts and routines. It akes a command, either script or routine, and the file to run as an argument.

E.g.  
`./run script scripts/day_to_night_bench.csv`  
`./run routine routines/abort_if_file_present`  

The command also has a help flag:  
`./run script --help`  
`./run routine --help`  

The most common extra flag, what is applicable to both, is -l which loops the script or routine.

