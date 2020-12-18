#!/usr/bin/python
"""
wxremdata.py

Copyright (c) 2006-2007 Daniel Graham <daniel.graham@duke.edu>.
Copyright (c) 2020 John Murphy <john.david.murphy@gmail.com>
All rights reserved.

License:
This program is FREE software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the FREE Software
Foundation; either version 2 of the License, or (at your option) any later
version. [ http://www.gnu.org/licenses/gpl.html ]

This program is distributed in the hope that it will BE useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
"""

# Imports
import argparse
import datetime
import re
import subprocess
import textwrap

# Constants
MARKER_RESOLUTION = "low"
EMPTY_STRING = ""
HOLIDAY = "HOLIDAY"
REMIND = "REMIND"

BE = "*"
B5 = "["
E5 = "]"
B10 = "["
E10 = "]"
B15 = "["
E15 = "]"
E5B5 = "+"
E5B10 = "+"
E10B5 = "+"
I15 = "="
CONFLICT = "X"
FREE_IN_HOUR = " "
FREE_AT_HOUR = "."

FIFTEEN_MINUTES = 15
INDENT_1 = 7
INDENT_13 = 13
TIME_FMT = "%H:%M"
TWELVE_HOUR = False
ONE_DAY = datetime.timedelta(days=1)

START_CONFLICTS = [B5, B10, B15, E5B10, E5B5, I15]
END_CONFLICTS = [E5, E10, E15, E10B5, E5B5, I15]
FREE = [FREE_IN_HOUR, FREE_AT_HOUR]

# Event Offset Definitions
START_TIME = 0
INTERVAL = 1
END_TIME = 2
MSG = 3
FILENAME = 4
LINE_NUM = 5
DURATION_MINUTES = 6
START_MINUTES = 7
SPECIAL = 8
TAG = 9

# Event Data
FOUND = 0
DATA = 1

# Defaults
DEFAULT_AGENDA_START = 6
DEFAULT_AGENDA_END = 22
DEFAULT_DAYS = 1
DEFAULT_VIEW = "fd"

# Main
def main():
    """
    Main Method - Parses rem file and displays data
    """

    # Parse Arguments
    arguments = parse_arguments()

    # Create Reminder Data Object
    rem_data = RemData(arguments.remind, arguments.remfile)

    # Generate Output
    generate_output(arguments, rem_data)


def parse_arguments():
    """
    Parses the arguments passed in from the command line.

    Returns
    -------
    dict
        A map of the processed arguments
    """

    # Get Arguments
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=textwrap.dedent(
            """
        Output Format:
        Only one event uses any of the 15 minute slot:
            [   begin an event taking any portion of this slot and lasting
                more than 15 minutes
            ]   end an event taking any portion of this slot and lasting
                more than 15 minutes
            *   event begins and ends within this slot and lasts less than 15
                minutes
            #   event begins and ends within this slot and lasts 15 minutes

        Two events use parts of the 15 minute slot but there is no conflict:
            +   end an event and begin an event sharing this slot

        Two events use parts of the 15 minute slot and there is a conflict:
            X   minutes taken by ending event and minutes taken by begining
                event add up to more than 15.

        For events scheduled at the following times:
            7:40AM - 8:40AM, 8:20AM - 9:25AM, 9:55AM - 10:10AM, 10:10AM,
            10:30AM, 10:35AM - 11:20AM, 11:20AM - 12:05PM, 12:30PM - 1:20PM,
            1:25PM - 2:15PM, 2:40PM, 2:45PM - 3:40PM, 3:40PM - 4:30PM, 5:15PM
            - 7:45PM, 6:00PM - 7:00PM, 8:00PM - 8:15PM, 8:35PM - 9:00PM

        For Example:
            7   8   9   10  11  12  1   2   3   4   5   6   7   8   9
            . [==XX==] [+ +==+==] [==+==] *[==+==]  .[==XXXX==] # [].
        """
        ),
    )

    parser.add_argument(
        "--remind",
        default="/usr/bin/remind",
        help="Name of the remind binary (default: /usr/bin/remind)",
    )

    parser.add_argument(
        "-r",
        "--remfile",
        required=True,
        help="Name of the Remfile to parse (required)",
    )

    parser.add_argument(
        "-b",
        "--begin",
        default=datetime.date.today().strftime("%Y-%m-%d"),
        help="Starting date: YYYY-MM-DD (default: %s)"
        % datetime.date.today().strftime("%Y-%m-%d"),
    )

    parser.add_argument(
        "-d",
        "--days",
        default=DEFAULT_DAYS,
        help="Number of days to display/search (default: %d)" % DEFAULT_DAYS,
    )

    parser.add_argument(
        "--agenda_start_hour",
        default=DEFAULT_AGENDA_START,
        help="Hour in day agenda starts (default: %d)" % DEFAULT_AGENDA_START,
    )

    parser.add_argument(
        "--agenda_end_hour",
        default=DEFAULT_AGENDA_END,
        help="Hour in day agenda ends (default: %d)" % DEFAULT_AGENDA_END,
    )
    parser.add_argument(
        "-v",
        "--view",
        default=DEFAULT_VIEW,
        help="View [f]ree/busy schedule and/or [d]aily agenda (default: %s)"
        % DEFAULT_VIEW,
    )
    parser.add_argument(
        "-s",
        "--search",
        default=EMPTY_STRING,
        help="Search for string within DAYS (default: not_set)",
    )
    parser.add_argument(
        "-f",
        "--fileinfo",
        help="Append file name and line number information",
    )
    parser.add_argument(
        "-n",
        "--next_occurrences",
        default=False,
        help="""List next occurrences (ignores other options)""",
    )
    parser.add_argument(
        "-m",
        "--markerinfo",
        help="Show FREE/busy marker information (ignores other options).",
    )

    arguments = parser.parse_args()

    arguments.begin = datetime.datetime.strptime(arguments.begin, "%Y-%m-%d")
    arguments.agenda_start_hour = int(arguments.agenda_start_hour)
    arguments.agenda_end_hour = int(arguments.agenda_end_hour)

    return arguments


def generate_output(arguments, rem_data):
    """
    Prints the output of the rem_data to the screen, based on the filters
    passed on the command line.

    Parameters
    ----------
    arguments : dict
        Arguments passed on the command line
    rem_data : RemData
        Reminder Data procesesd from call to 'remind'
    """

    # Variables
    count = 0
    free_busy_list = []  # Free/Busy list
    output = []
    search_on = arguments.search != EMPTY_STRING

    # Print out the next_occurences if the parameter is passed
    if arguments.next_occurrences:
        print(rem_data.get_next_occurrences())
        return

    # Iterate over date range
    current_date = arguments.begin
    while count < int(arguments.days):
        free_busy = slot_list(
            arguments.agenda_start_hour, arguments.agenda_end_hour
        )  # create a free/busy list for the day

        # Split String into year/month/day integers
        year, month, day = (
            int(x) for x in current_date.strftime("%Y %m %d").split()
        )
        count += 1
        shortdaystr = "%s" % current_date.strftime("%d %a")
        end_date = current_date

        event_data = get_events_for_day(
            arguments,
            current_date,
            rem_data.get_day(year, month, day),
            search_on,
            free_busy,
        )

        if event_data[FOUND]:
            output.append("%s" % event_data[DATA])

        free_busy_list.append("%s %s" % (shortdaystr, "".join(free_busy)))
        current_date = current_date + ONE_DAY

    # Get Title
    title = get_title(arguments.begin, end_date)

    # Print Result
    if not search_on:
        print_agenda(arguments, title, free_busy_list, output)
    else:
        print("\n".join(output))


def get_events_for_day(arguments, date, events, search_on, free_busy):
    """
    Get all of the scheduled events for a given day.

    Parameters
    ----------
    arguments : dict
        Arguments passed on the command line
    date : datetime
        Date for events
    events : array
        Array of events for the day
    search_on : bool
        Indicates whether we're searching for or displaying all events
    free_busy : array
        List of possible agenda slots for the day

    Returns
    -------
    array
        0 - bool indicating if data was found
        1 - summary of day's events
    """

    if events is None:
        return [False, ""]

    # Generate Regex based on argument params
    if search_on:
        regex = re.compile(r"%s" % arguments.search, re.IGNORECASE)
    else:
        regex = re.compile(r".*")

    found = False
    summary = "%s:\n" % date.strftime("%a, %d %b")
    state = {}  # for the 0-7 5min interval state codes

    for event in events:
        if event[START_MINUTES] != "*" and event[DURATION_MINUTES] != "*":
            mark_interval(
                free_busy,
                state,
                event[DURATION_MINUTES],
                event[START_MINUTES],
                arguments.agenda_start_hour,
                arguments.agenda_end_hour,
            )
        event_str = " ".join(event[:-6])
        if not search_on or regex.search(event_str):
            found = True
            if arguments.fileinfo:
                summary += "    %s [%s:%s]\n" % (
                    event_str.lstrip(),
                    event[FILENAME],
                    event[LINE_NUM],
                )
            else:
                summary += "    %s\n" % event_str

    return [found, summary]


def get_title(start_date, end_date):
    """
    Gets the title for the agenda

    Parameters
    ----------
    start_date : datetime
        Agenda start date
    end_date : datetime
        Agenda end date

    Returns
    -------
    string
        Title of the agenda
    """
    if start_date == end_date:
        title = " %s " % start_date.strftime("%a, %d %b %Y")
    else:
        title = " %s - %s " % (
            start_date.strftime("%a, %d %b %Y"),
            end_date.strftime("%a, %d %b %Y"),
        )

    return title


def print_agenda(arguments, title, free_busy_list, output):
    """
    Print agenda to std_out

    Parameters
    ----------
    arguments : dict
        Arguments passed on the command line
    title : string
        Title of agenda
    free_busy_list : array
        Free/Busy time slots
    output : string
        Data to output
    """

    agenda_width = (
        len(slot_list(arguments.agenda_start_hour, arguments.agenda_end_hour))
        + 9
    )
    lbar = int((agenda_width - len(title)) / 2)
    bars = "=" * lbar
    needs_title = True
    toshow = {}
    if "f" in arguments.view:
        toshow["f"] = "%s\n%s\n" % (
            hour_bar(arguments.agenda_start_hour, arguments.agenda_end_hour),
            "\n".join(free_busy_list),
        )

    if "d" in arguments.view:
        toshow["d"] = "\n".join(output)

    for view_part in arguments.view:
        if view_part in ("f", "d") and needs_title:
            print("%s%s%s" % (bars, title, bars))
            needs_title = False
        print(toshow[view_part])


class RemData:
    """
    Class to manage RemFile information
    """

    # Constants
    DATE_FMT = "%a %d %b %Y"
    LEADING_ZERO = re.compile(r"^0")
    NUM_MONTHS = 4
    REGAT = re.compile(r"\s+at.*$")
    LEADING_ZERO = re.compile(r"^0")

    # Variables
    data = {}
    found_list = []
    last_found = EMPTY_STRING
    next_item = 0
    remind_filename = EMPTY_STRING
    remind_cmd = EMPTY_STRING
    search_str = EMPTY_STRING
    start_date = EMPTY_STRING

    # Since remind only recognizes English month abbreviations but python gives
    # the appropriate Locale version.
    month_abbr = {
        "01": "Jan",
        "02": "Feb",
        "03": "Mar",
        "04": "Apr",
        "05": "May",
        "06": "Jun",
        "07": "Jul",
        "08": "Aug",
        "09": "Sep",
        "10": "Oct",
        "11": "Nov",
        "12": "Dec",
    }

    def __init__(self, remind_cmd, remind_filename):
        """__init__.

        Parameters
        ----------
        remind_cmd : string
            Path of the Remind binary
        remind_filename : string
            Path of the Remind filename to read
        """
        self.remind_cmd = remind_cmd
        self.remind_filename = remind_filename
        start_month, start_year = self.get_months()

        self.slurp(start_year, start_month, self.NUM_MONTHS)

    def get_months(self):
        """
        Gets the start month/year for the reminders

        Returns
        -------
        int
            starting month
        int
            starting year

        """
        self.data = {}
        today = datetime.date.today()
        year, month = list(map(int, today.strftime("%Y %m").split()))
        if month == 1:
            start_month = 12
            start_year = year - 1
        else:
            start_month = month - 1
            start_year = year

        return start_month, start_year

    def get_day(self, year, month, day):
        """
        Gets RemData for one day

        Parameters
        ----------
        year : int
            year
        month : int
            month
        day : int
            day

        Returns
        -------
        array
            Array of events for the day
        """
        if year not in self.data or month not in self.data[year]:
            self.slurp(year, month, 1)

        try:
            return self.data[year][month][day]
        except KeyError:
            return None

    def get_next_occurrences(self):
        """
        Gets list of next occurence for each event

        Returns
        -------
        string
            String representation of next occurrences for each event.
        """
        command = "%s -n %s | sort" % (self.remind_cmd, self.remind_filename)
        events = subprocess.getoutput(command).split("\n")
        next_events = []
        for event in events:
            parts = event.split()
            year, month, day = list(map(int, parts[0].split("/")))
            parts[0] = datetime.date(year, month, day).strftime(self.DATE_FMT)
            next_events.append(" ".join(parts))
        res = "\n".join(next_events)
        return res

    def slurp(self, start_year, start_month, months):
        """
        Get Data from Remind output and put in Python datastructures

        Parameters
        ----------
        start_year : int
            Year where reminders should start
        start_month : int
            Month in the year where the reminders should start
        months : int
            Number of months to create reminders for
        """
        # start_year, start_month, months = list(map(int, (y, m, n)))
        start_month = "%02d" % start_month
        # Slurp remind output for the relevant date and number of months
        command = "%s -b2 -rls%s %s %s %s" % (
            self.remind_cmd,
            months,
            self.remind_filename,
            self.month_abbr[start_month],
            start_year,
        )
        lines = subprocess.getoutput(command).split("\n")
        self.process_slurp(lines)

    def process_slurp(self, lines):
        """
        Processes data slurped from the remind command

        Parameters
        ----------
        lines : array
            Output of Remind Command

        Raises
        ------
        RuntimeError
            If there is an issue with the Remind command or the output,
            raises a runtime error
        """
        line_num = 0
        filename = EMPTY_STRING

        for line in lines:
            parts = line.split()

            # Determine if the line is describing the file
            if line != EMPTY_STRING and parts[1] == "fileinfo":
                line_num, filename = parts[2:4]
                # go to the next line for the item details
                continue

            # Determine if line is valid
            self.validate_data_line(parts)

            # Populate local variables
            special, tag = parts[1:3]
            special = EMPTY_STRING if special == "*" else special.strip()
            tag = EMPTY_STRING if tag == "*" else tag.strip()
            start_time, end_time, duration = self.get_event_details(parts)

            if start_time and end_time:
                interval = "-"
            else:
                interval = EMPTY_STRING

            # The following creates a value for data[year][month][day]
            # creating year, month and day keys when necessary.
            year, month, day = list(map(int, parts[0].split("/")))

            self.data.setdefault(year, {}).setdefault(month, {}).setdefault(
                day, []
            ).append(
                [
                    start_time,  # Start Time
                    interval,  # Interval
                    end_time,  # End Time
                    " ".join(parts[5:]),  # Msg
                    filename,  # Filename
                    line_num,  # Line Num
                    duration,  # Duration Minutes
                    parts[4],  # Start Minutes
                    special,  # Special
                    tag,  # Tag
                ]
            )

    @staticmethod
    def validate_data_line(parts):
        """
        Determines if the row is skippable or raises an exception if the data is
        unparsable.

        Parameters
        ----------
        parts : array
            Array of data from the output line

        Raises
        ------
        RuntimeError
            If there was an issue parsing the result
        """

        if len(parts) == 0:
            msg = "Line should not be empty"
            raise RuntimeError(msg)

        if parts[0] == REMIND:
            msg = "Fatal error running remind command"
            raise RuntimeError(msg)

        try:
            list(map(int, parts[0].split("/")))
        except RuntimeError as remind_exception:
            msg = "Error parsing remind output"
            raise RuntimeError(msg) from remind_exception

    def get_event_details(self, parts):
        """
        Gets the event details for a given event.

        Parameters
        ----------
        parts : array
            raw event details

        Returns
        -------
        string
            start_time of the event

        string
            end_time of the event

        int
            duration of the event
        """
        year, month, day = list(map(int, parts[0].split("/")))
        duration, start_minutes = parts[3:5]

        if start_minutes != "*":
            start_minutes = int(start_minutes)
            start_time = datetime.datetime(
                year, month, day, int(start_minutes / 60), start_minutes % 60
            )
            if duration != "*":
                duration = int(duration)
                durationdelta = datetime.timedelta(
                    hours=duration / 60,
                    minutes=duration % 60,
                )
                end = start_time + durationdelta
                end_time = end.strftime(TIME_FMT)
                if TWELVE_HOUR:
                    end_time = self.LEADING_ZERO.sub(" ", end_time)
            else:
                end_time = EMPTY_STRING
                duration = 0
            start_time = start_time.strftime(TIME_FMT)
            if TWELVE_HOUR:
                start_time = self.LEADING_ZERO.sub(" ", start_time)
        else:
            start_time = EMPTY_STRING
            end_time = EMPTY_STRING
            duration = FIFTEEN_MINUTES

        return start_time, end_time, duration


def slot_list(agenda_start_hour, agenda_end_hour):
    """
    Create an array for slots of events in 15 minute increments

    Parameters
    ----------
    agenda_start_hour : int
        Hour the agenda starts
    agenda_end_hour : int
        Hour the agenda ends

    Returns
    -------
    array
        Array of possible agenda times for the day
    """
    intervals = []
    for interval in range(agenda_start_hour * 60, agenda_end_hour * 60, 15):
        if interval % 60 == 0:
            intervals.append(".")
        else:
            intervals.append(" ")
    intervals.append(".")
    return intervals


def hour_bar(agenda_start_hour, agenda_end_hour):
    """
    Create a display of the hours in the agenda

    Parameters
    ----------
    agenda_start_hour : int
        Hour the agenda starts
    agenda_end_hour : int
        Hour the agenda ends

    Returns
    -------
    string
        Representation of the hours in the agenda
    """
    display = EMPTY_STRING
    hour = agenda_start_hour
    for hour in range(agenda_start_hour, agenda_end_hour + 1):
        if TWELVE_HOUR and hour > 12:
            hour -= 12
        hour = "%d" % hour
        display += "%-4s" % hour
    return "%s%s" % (" " * 7, display)


def mark_interval(
    free_busy,
    state,
    duration,
    start_minutes,
    agenda_start_hour,
    agenda_end_hour,
):
    """
    Annotate the free_busy interval with attending or conflicts

    Parameters
    ----------
    free_busy : array
        List of agenda times during the day
    state : dict
        List of state codes
    duration : int
        Duration of the event
    start_minutes : int
        Minute where the event starts
    agenda_start_hour : int
        Time the agenda starts
    agenda_end_hour : int
        Time the agenda end
    """

    start_minutes = max(int(start_minutes), 60 * agenda_start_hour)
    start_offset = start_minutes - 60 * agenda_start_hour
    start_interval = int(start_offset / 15)
    start_interval_count = int((start_offset % 15) / 5)  # num 5 min intervals

    end_minutes = min(int(start_minutes) + duration, 60 * agenda_end_hour)
    end_offset = end_minutes - 60 * agenda_start_hour
    end_interval = int(end_offset / 15)
    end_interval_count = int((end_offset % 15) / 5)  # num 5 min intervals

    if start_interval == end_interval:
        # start and end in the same slot
        if start_interval in state:
            if state[start_interval][start_interval_count]:
                free_busy[start_interval] = CONFLICT
            elif state[start_interval][end_interval_count]:
                free_busy[start_interval] = CONFLICT
        else:
            state[start_interval] = [0, 0, 0]
        if start_interval_count == end_interval_count:
            state[start_interval][start_interval_count] = 4
        else:
            state[start_interval][start_interval_count] = 2
            state[start_interval][end_interval_count] = 3
        if start_interval_count == 0 and end_interval_count == 2:
            state[start_interval][1] = 1
        free_busy[start_interval] = BE

    for i in range(start_interval, end_interval):
        if i not in state:
            state[i] = [0, 0, 0]
        if i == start_interval:
            for k in range(start_interval_count, 3):
                if state[i][k]:
                    free_busy[i] = CONFLICT
                if k == start_interval_count:
                    state[i][k] = 2
                else:
                    state[i][k] = 1
        else:
            for k in range(0, 3):
                if state[i][k]:
                    free_busy[i] = CONFLICT
                else:
                    state[i][k] = 1

    if start_interval != end_interval:
        if end_interval - 1 not in state:
            state[end_interval - 1] = [0, 0, 0]
        if end_interval not in state:
            state[end_interval] = [0, 0, 0]
        if end_interval_count == 0:
            state[end_interval - 1][2] = 3
        elif end_interval_count == 1:
            state[end_interval][0] = 3
        else:
            state[end_interval][0] = 1
            state[end_interval][1] = 3

    for i in range(start_interval, end_interval + 1):
        if not free_busy[i] == CONFLICT:
            if state[i] == [1, 1, 1]:
                free_busy[i] = I15
            elif state[i] == [1, 1, 3]:
                free_busy[i] = E15
            elif state[i] == [2, 1, 1]:
                free_busy[i] = B15
            elif state[i] == [0, 2, 1]:
                free_busy[i] = B10
            elif state[i] == [1, 3, 0]:
                free_busy[i] = E10
            elif state[i] == [0, 0, 2]:
                free_busy[i] = B5
            elif state[i] == [3, 0, 0]:
                free_busy[i] = E5
            elif state[i] == [3, 2, 1]:
                free_busy[i] = E5B10
            elif state[i] == [4, 2, 1]:
                free_busy[i] = E5B10
            elif state[i] == [1, 3, 2]:
                free_busy[i] = E10B5
            elif state[i] == [1, 3, 4]:
                free_busy[i] = E10B5
            elif state[i] == [3, 0, 2]:
                free_busy[i] = E5B5
            elif state[i] == [4, 0, 0]:
                free_busy[i] = BE
            elif state[i] == [0, 4, 0]:
                free_busy[i] = BE
            elif state[i] == [0, 0, 4]:
                free_busy[i] = BE
            elif state[i] == [0, 4, 2]:
                free_busy[i] = E5B5
            elif state[i] == [3, 4, 0]:
                free_busy[i] = E5B5
            elif state[i] == [2, 3, 0]:
                free_busy[i] = BE
            elif state[i] == [0, 2, 3]:
                free_busy[i] = BE
            elif state[i] == [2, 1, 3]:
                free_busy[i] = "#"


if __name__ == "__main__":
    main()
