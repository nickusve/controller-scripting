from csv import DictReader
from os import path
from copy import deepcopy
from math import sin, cos, radians

class ButtonState(object):
    ON = True
    OFF = False
    def __init__(self, state=OFF, time=0):
        self.state = state
        self.time = time

class StickPosition(object):
    START = True
    END = False
    def __init__(self, angle: float=0, magnitude: int=0, state=END, time=0, x=None, y=None):
        # Simple class to hold data, validate valid position elsewhere
        self.angle = angle
        self.magnitude = magnitude
        self.time = time
        # Unlike button presses where it is a discrete press and release it is not desirable
        # to snap the stick back to origin between operations as it can lead to odd inputs.
        # Instead there is a start and end marker where the start marker indicates when the stick
        # should move, and the end marker indicated when the next movement can be made
        self.state = state
        
        # X/Y typically independent of angle/magnitude, but also harder to use directly. Either
        # can be used/stored here, though. Up to user to determine which to use if both present.
        self.y = x
        self.x = y


class ButtonInputs(dict):
    def __init__(self, *arg, **kw):
        # Could use args to denote type of controller, right now it's the switch buttons
        super(ButtonInputs, self).__init__(*arg, **kw)
        self["a"] = []
        self["b"] = []
        self["x"] = []
        self["y"] = []
        self["+"] = []
        self["-"] = []
        self["up"] = []
        self["down"] = []
        self["left"] = []
        self["right"] = []
        self["lb"] = []
        self["zl"] = []
        self["rb"] = []
        self["zr"] = []
        self["home"] = []

class StickInputs(dict):
    LEFT_STICK = "ls"
    RIGHT_STICK = "rs"
    def __init__(self, *arg, **kw):
        super(StickInputs, self).__init__(*arg, **kw)
        self[self.LEFT_STICK] = []
        self[self.RIGHT_STICK] = []

class Script(object):
    MS_TO_NS = 1000000

    def __init__(self, file, repeats=0, min_btn_transition_time_ms: int = 0, min_stk_transition_time_ms: int = 0):
        self.repeats = repeats
        self.buttons = ButtonInputs()
        self.sticks = StickInputs()
        self.stick_transition_time_ns = min_stk_transition_time_ms * self.MS_TO_NS
        self.button_transition_time_ns = min_btn_transition_time_ms * self.MS_TO_NS

        if not path.isfile(file):
            print(f"'{file}' does not exist!")
            raise SystemExit(1)
        self.end_time = self.parseScript(file)

    def getInputs(self, start_time_ns):
        buttons = ButtonInputs()
        sticks = StickInputs()
        end_time_ns = start_time_ns

        for _ in range(self.repeats + 1):
            # Copy to modify
            iter_buttons = deepcopy(self.buttons)
            iter_sticks = deepcopy(self.sticks)

            # Iterate over every button adding the end time to each time value.
            # Note that for first iteration the end time is the start time, thus
            # adding the end is akin to offsetting times to the start time. For
            # subsequent loops it's offset by the last repeat's end time.
            for button in iter_buttons.keys():
                for item in iter_buttons[button]:
                    item.time += end_time_ns
                    buttons[button].append(item)
            for stick in iter_sticks.keys():
                for item in iter_sticks[stick]:
                    item.time += end_time_ns
                    sticks[stick].append(item)
            end_time_ns += self.end_time

        return buttons, sticks, end_time_ns

    def parseScript(self, file):

        # Stores the END TIME of the IDs for lookup for later lines.
        # EVERY line will have an ID, either auto_generated or named

        # Every line's end time is stored in the list. Unique IDs are stored with
        # the value corresponding to the index of end_times where that ID ends
        end_times = [0]
        ids = {"start": 0}

        with open(file, "r") as csv_file:
            buttons = self.buttons.keys()
            sticks = self.sticks.keys()
            reader = DictReader(csv_file)
            for line in reader:
                # Validate required fields
                if "" == line["start_delay_ms"]:
                    print(f"No start delay for line\n{line}")
                    raise SystemExit(1)
                if "" == line["duration_ms"]:
                    print(f"No duration for line\n{line}")
                    raise SystemExit(1)

                # Ensure ms times are numbers
                try:
                    start_delay_ns = int(line["start_delay_ms"]) * self.MS_TO_NS
                    duration_ns = int(line["duration_ms"]) * self.MS_TO_NS
                except Exception:
                    print(f"Invalid line (start delay or duration invalid):\n{line}")
                    raise SystemExit(1)

                # If there is no specified ID to start after use the last line, otherwise
                # look up the ID and use that
                if "" == line["start_after_id"]:
                    start_at = end_times[-1] + start_delay_ns
                    end_time = start_at + duration_ns
                else:
                    start_at = end_times[ids[line["start_after_id"]]] + start_delay_ns
                    end_time = start_at + duration_ns

                # Add the end time of the line and the unique ID if given
                end_times.append(end_time)
                if "" != line["id"]:
                    if line["id"] in ids:
                        print(f"ID {line['id']} already in use ('start' is reserved)")
                        raise SystemExit(1)
                    # Minus 1 because list is 0-indexed and entry has been added already
                    ids[line["id"]] = (len(end_times) -1)

                ### Button input ###
                if line["input"] in buttons:
                    # Check to make sure that the start time of this button press does not overlap
                    # with the last press
                    if 0 != len(self.buttons[line["input"]]):
                        last_action = self.buttons[line["input"]][-1]
                        if last_action.state != ButtonState.OFF:
                            print(f"Parsing / logic error! Button {line['input']} last action is not OFF")
                            raise SystemExit(1)
                        if last_action.time > start_at:
                            print(f"Attempting to press button while it is pressed! Line:\n{line}")
                            raise SystemExit(1)
                        elif (last_action.time + self.button_transition_time_ns) > start_at:
                            print(f"Attempting to press button too quickly! Might not keep up! Line:\n{line}")
                    self.buttons[line["input"]].append(ButtonState(ButtonState.ON, start_at))
                    self.buttons[line["input"]].append(ButtonState(ButtonState.OFF, end_time))

                ### Stick input ###
                elif line["input"] in sticks:
                    # Validate positions given and in range
                    try:
                        angle = float(line["angle"])
                        magnitude = int(line["magnitude"])
                    except Exception:
                        print(f"Invalid line (stick position not float or magnitude not int):\n{line}")
                        raise SystemExit(1)
                    if 360 < angle or 0 > angle or -100 > magnitude or 100 < magnitude:
                        print(f"Invalid line (stick position not in range (0->360 angle, -100->100 mag):\n{line}")
                        raise SystemExit(1)

                    # Check to make sure that the start time of this position does not overlap
                    # with the last press
                    if 0 != len(self.sticks[line["input"]]):
                        last_action = self.sticks[line["input"]][-1]
                        if last_action.state != StickPosition.END:
                            print(f"Parsing / logic error! Stick {line['input']} last action is not END")
                            raise SystemExit(1)
                        last_action_start = self.sticks[line["input"]][-2]
                        if last_action.time > start_at:
                            print(f"Attempting to move stick before last movement ended! Line:\n{line}")
                            raise SystemExit(1)
                        elif (last_action_start.time + self.stick_transition_time_ns) > start_at:
                            print(f"Attempting to move stick too quickly! Might not keep up! Line:\n{line}")
                    self.sticks[line["input"]].append(StickPosition(angle, magnitude,
                                                        StickPosition.START, start_at))
                    self.sticks[line["input"]].append(StickPosition(angle, magnitude,
                                                        StickPosition.END, end_time))
                else:
                    print(f"Unknown input for line:\n{line['input']}")
                    raise SystemExit(1)
        return max(end_times)

