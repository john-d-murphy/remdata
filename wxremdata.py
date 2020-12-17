#!/usr/bin/env python
"""
wxremdata.py

Copyright (c) 2006-2007 Daniel Graham <daniel.graham@duke.edu>. All rights reserved.

License:
This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; either version 2 of the License, or (at your option) any later
version. [ http://www.gnu.org/licenses/gpl.html ]

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
"""

import os.path, sys, datetime, re, commands, codecs

viewdefault = "fd"

# make these the defaults
marker_resolution = "low"
# marker_resolution can be set (low, high or custom) in ~/.wxremindrc to change this default

# print viewdefault, marker_resolution

from version import *
from wxremindrc import *


if marker_resolution == "low":
    be = "*"
    b5 = "["
    e5 = "]"
    b10 = "["
    e10 = "]"
    b15 = "["
    e15 = "]"
    e5b5 = "+"
    e5b10 = "+"
    e10b5 = "+"
    i15 = "="
    conflict = "X"
    freeinhour = " "
    freeathour = "."
elif marker_resolution == "high":
    be = "*"
    b5 = "("
    e5 = ")"
    b10 = "["
    e10 = "]"
    b15 = "|"
    e15 = "|"
    e5b5 = "+"
    e5b10 = "{"
    e10b5 = "}"
    i15 = "="
    conflict = "X"
    freeinhour = " "
    freeathour = "."
# set marker_resolution = 'custom' and supply your own choices
# for b5 ... freeathour if you would like to use different characters.

startconflicts = [b5, b10, b15, e5b10, e5b5, i15]
endconflicts = [e5, e10, e15, e10b5, e5b5, i15]
free = [freeinhour, freeathour]


def MarkHelp(option, opt, value, parser):
    print """When marker_resolution = 'low'
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

When marker_resolution = 'high'
    Only one event uses any of the 15 minute slot:
        (   begin an event taking the last 5 minutes of this slot
        [   begin an event taking the last 10 minutes of this slot
        |   begin or end an event taking all 15 minutes of this slot
        )   end an event taking the first 5 minutes of this slot
        ]   end an event taking the first 10 minutes of this slot
        *   event begins and ends within this slot and lasts less than 15
            minutes
        #   event begins and ends within this slot and lasts 15 minutes

    Two events use parts of the 15 minute slot but there is no conflict:
        +   end an event taking the first 5 minutes and begin an event
            taking the last 5 minutes of this slot
        {   end an event taking the first 5 minutes and begin an event
            taking the last 10 minutes of this slot
        }   end an event taking the first 10 minutes and begin an event
            taking the last 5 minutes of this slot

    Two events use parts of the 15 minute slot and there is a conflict:
        X   minutes taken by ending event and minutes taken by begining
            event add up to more than 15.

For events scheduled at the following times:
    7:40AM - 8:40AM, 8:20AM - 9:25AM, 9:55AM - 10:10AM, 10:10AM,
    10:30AM, 10:35AM - 11:20AM, 11:20AM - 12:05PM, 12:30PM - 1:20PM,
    1:25PM - 2:15PM, 2:40PM, 2:45PM - 3:40PM, 3:40PM - 4:30PM, 5:15PM
    - 7:45PM, 6:00PM - 7:00PM, 8:00PM - 8:15PM, 8:35PM - 9:00PM

when marker_resolution = 'low':
    7   8   9   10  11  12  1   2   3   4   5   6   7   8   9
    . [==XX==] [+ +==+==] [==+==] *[==+==]  .[==XXXX==] # [].

when marker_resolution = 'high':
    7   8   9   10  11  12  1   2   3   4   5   6   7   8   9
    . (==XX==] (} {=={==) |==+==| *|==}==|  .|==XXXX==| # [|.

Currently marker_resolution = '%s'.""" % marker_resolution
    sys.exit()


class RemData:

    leadingzero = re.compile(r"^0")

    nummonths = 4
    if twelvehour:
        timefmt = "%I:%M%p"
        indent1 = 9
        indent2 = 17
    else:
        indent1 = 7
        indent2 = 13
        timefmt = "%H:%M"

    datefmt = "%a %d %b %Y"
    regat = re.compile(r"\s+at.*$")
    data = {}
    searchstr = ""
    startdate = ""
    foundlist = []
    lastfound = ""
    nextitem = 0
    oneday = datetime.timedelta(days=1)

    # Since remind only recognizes English month abbreviations but python gives
    # the appropriate Locale version.
    mnthabbrv = {
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

    def _init__(self):
        # self.oldstdout = sys.stdout
        # sys.stdout = codecs.lookup(encoding)[-1](sys.stdout)
        self.getMonths()

    def getMonths(self):
        self.data = {}
        today = datetime.date.today()
        year, month = map(int, today.strftime("%Y %m").split())
        if month == 1:
            startmonth = 12
            startyear = year - 1
        else:
            startmonth = month - 1
            startyear = year
        self.slurp(startyear, startmonth, self.nummonths)

    def getDay(self, y, m, d):
        year, month, day = map(int, (y, m, d))
        requesteddate = datetime.date(year, month, day)
        self.shortremdate = requesteddate.strftime("%d %m")
        if not self.data.has_key(year) or not self.data[year].has_key(month):
            self.slurp(y, m, 1)
        try:
            retval = self.data[year][month][day]
        except:
            retval = None
        return retval

    def getOccurances(self):
        command = "%s -n %s | sort" % (remind, reminders)
        events = commands.getoutput(command).split("\n")
        nevents = []
        for event in events:
            parts = event.split()
            year, month, day = map(int, parts[0].split("/"))
            parts[0] = datetime.date(year, month, day).strftime(self.datefmt)
            nevents.append(" ".join(parts))
        res = "\n".join(nevents)
        return res

    def getMonthlyDurations(self, y, m):
        year, month = map(int, (y, m))
        busy = {}
        if self.data.has_key(year) and self.data[year].has_key(month):
            for day in self.data[year][month].keys():
                minutes = 0
                for event in self.data[year][month][day]:
                    minutes += max(zerominutes, event[6])
                    if event[9] == "HOLIDAY":
                        minutes += 1600
                busy.setdefault(day, minutes)
        return busy

    def slurp(self, y, m, n):
        startyear, startmonth, months = map(int, (y, m, n))
        startmonth = "%02d" % startmonth
        # Slurp remind output for the relevant date and number of months
        command = "%s -b2 -rls%s %s %s %s" % (
            remind,
            months,
            reminders,
            self.mnthabbrv[startmonth],
            startyear,
        )
        # fo = codecs.open(file, 'r', encoding)
        # lines = codecs.lookup(encoding)[2](commands.getoutput(command)).split('\n')
        lines = commands.getoutput(command).split("\n")
        linenum = 0
        filename = ""
        for line in lines:
            parts = line.split()
            if len(parts) == 0:
                continue
            if parts[1] == "fileinfo":
                linenum, filename = parts[2:4]
                # go to the next line for the item details
                continue
            if parts[0] == "REMIND":
                msg = (
                    """
Fatal error: the command:
%s
raised a syntax error message from remind."""
                    % command
                )
                raise RuntimeError, msg
            try:
                year, month, day = map(int, parts[0].split("/"))
            except:
                msg = "Error parsing remind output: %s" % line
                raise RuntimeError, msg
            date = datetime.date(year, month, day).strftime(self.datefmt)
            special, tag = parts[1:3]
            if special == "*":
                special = ""
            else:
                special = special.strip()
            if tag == "*":
                tag = ""
            else:
                tag = tag.strip()
            durationminutes, startminutes = parts[3:5]
            if startminutes != "*":
                startminutes = int(startminutes)
                starttime = datetime.datetime(
                    year, month, day, startminutes / 60, startminutes % 60
                )
                if durationminutes != "*":
                    durationminutes = int(durationminutes)
                    durationdelta = datetime.timedelta(
                        hours=durationminutes / 60, minutes=durationminutes % 60
                    )
                    end = starttime + durationdelta
                    endtime = end.strftime(self.timefmt)
                    if twelvehour:
                        endtime = self.leadingzero.sub(" ", endtime)
                else:
                    endtime = ""
                    # durationminutes = zerominutes
                    durationminutes = 0
                starttime = starttime.strftime(self.timefmt)
                if twelvehour:
                    starttime = self.leadingzero.sub(" ", starttime)
            else:
                starttime = ""
                endtime = ""
                durationminutes = zerominutes
            if starttime and endtime:
                interval = "-"
            else:
                interval = ""
            msg = " ".join(parts[5:])

            # The following creates a value for data[year][month][day]
            # creating year, month and day keys when necessary.
            # Is this cool or what?
            self.data.setdefault(year, {}).setdefault(month, {}).setdefault(
                day, []
            ).append(
                [
                    starttime,  # 0
                    interval,  # 1
                    endtime,  # 2
                    msg,  # 3
                    filename,  # 4
                    linenum,  # 5
                    durationminutes,  # 6
                    startminutes,  # 7
                    special,  # 8
                    tag,  # 9
                ]
            )

    def firstOccurance(self, str):
        if not self.startdate:
            self.startdate = datetime.date.today().strftime("%d %m %Y")
        self.nextitem = 0
        self.foundlist = []
        self.searchstr = str
        try:
            d, m, y = map(int, self.startdate.split())
        except:
            msg = (
                "Error in firstOccurance spliting self.startdate: %s"
                % self.startdate
            )
            raise msg
        self.lastfound = (y, m, d)
        mnth = self.mnthabbrv["%02d" % m]
        command = "%s -b2 -n %s %s %s %s | grep -i '%s' | sort" % (
            remind,
            reminders,
            d,
            mnth,
            y,
            self.searchstr,
        )
        so = os.popen(command, "r")
        events = so.readlines()
        so.close()
        # events = commands.getoutput(command).split('\n')
        for event in events:
            if len(event) > 0:
                parts = event.split()
                year, month, day = map(int, parts[0].split("/"))
                msg = "%s" % self.regat.sub("", " ".join(parts[1:]))
                self.foundlist.append((year, month, day, msg))
        return self.nextOccurance()

    def nextOccurance(self):
        numfound = len(self.foundlist)
        if numfound > 0 and self.nextitem < numfound:
            retval = self.foundlist[self.nextitem]
            self.lastfound = retval[:-1]
            self.nextitem += 1
            return retval
        else:
            return None


def SlotList():
    l = []
    for x in range(agendastarthour * 60, agendaendhour * 60, 15):
        if x % 60 == 0:
            l.append(".")
        else:
            l.append(" ")
    l.append(".")
    return l


def HourBar():
    s = ""
    hour = agendastarthour
    for x in range(agendastarthour, agendaendhour + 1):
        if twelvehour and x > 12:
            x -= 12
        h = "%d" % x
        s += "%-4s" % h
    return "%s%s" % (" " * 7, s)


def MarkInterval(list, state, duration, startminutes):
    endminutes = min(startminutes + duration, 60 * agendaendhour)
    startminutes = max(startminutes, 60 * agendastarthour)
    s = (startminutes - 60 * agendastarthour) / 15
    S = ((startminutes - 60 * agendastarthour) % 15) / 5  # num 5 min intervals
    e = (endminutes - 60 * agendastarthour) / 15
    E = ((endminutes - 60 * agendastarthour) % 15) / 5  # num 5 min intervals

    if s == e:
        # start and end in the same slot
        if state.has_key(s):
            if state[s][S]:
                list[s] = conflict
            elif state[s][E]:
                list[s] = conflict
        else:
            state[s] = [0, 0, 0]
        if S == E:
            state[s][S] = 4
        else:
            state[s][S] = 2
            state[s][E] = 3
        if S == 0 and E == 2:
            state[s][1] = 1
        list[s] = be

    for i in range(s, e):
        if not state.has_key(i):
            state[i] = [0, 0, 0]
        if i == s:
            for k in range(S, 3):
                if state[i][k]:
                    list[i] = conflict
                if k == S:
                    state[i][k] = 2
                else:
                    state[i][k] = 1
        else:
            for k in range(0, 3):
                if state[i][k]:
                    list[i] = conflict
                else:
                    state[i][k] = 1

    if s != e:
        # e != s
        if not state.has_key(e - 1):
            state[e - 1] = [0, 0, 0]
        if not state.has_key(e):
            state[e] = [0, 0, 0]
        if E == 0:
            state[e - 1][2] = 3
        elif E == 1:
            state[e][0] = 3
        else:
            state[e][0] = 1
            state[e][1] = 3

    for i in range(s, e + 1):
        if not list[i] == conflict:
            if state[i] == [1, 1, 1]:
                list[i] = i15
            elif state[i] == [1, 1, 3]:
                list[i] = e15
            elif state[i] == [2, 1, 1]:
                list[i] = b15
            elif state[i] == [0, 2, 1]:
                list[i] = b10
            elif state[i] == [1, 3, 0]:
                list[i] = e10
            elif state[i] == [0, 0, 2]:
                list[i] = b5
            elif state[i] == [3, 0, 0]:
                list[i] = e5
            elif state[i] == [3, 2, 1]:
                list[i] = e5b10
            elif state[i] == [4, 2, 1]:
                list[i] = e5b10
            elif state[i] == [1, 3, 2]:
                list[i] = e10b5
            elif state[i] == [1, 3, 4]:
                list[i] = e10b5
            elif state[i] == [3, 0, 2]:
                list[i] = e5b5
            elif state[i] == [4, 0, 0]:
                list[i] = be
            elif state[i] == [0, 4, 0]:
                list[i] = be
            elif state[i] == [0, 0, 4]:
                list[i] = be
            elif state[i] == [0, 4, 2]:
                list[i] = e5b5
            elif state[i] == [3, 4, 0]:
                list[i] = e5b5
            elif state[i] == [2, 3, 0]:
                list[i] = be
            elif state[i] == [0, 2, 3]:
                list[i] = be
            elif state[i] == [2, 1, 3]:
                list[i] = "#"


def SysInfo(list, state, duration, startminutes):
    from platform import python_version as pv
    from wx import VERSION_STRING as wv
    from dateutil import __version__ as dv
    import wx

    print "System Information:"
    print "    python %s; wx %s (%s); dateutil %s" % (
        pv(),
        wv,
        " ".join(wx.PlatformInfo[1:3]),
        dv,
    )
    sys.exit()


def main():
    global options, args, days
    from optparse import OptionParser

    viewhelp = """View [f]ree/busy schedule and/or [d]aily agenda"""
    output = []
    parser = OptionParser(
        version="wxremdata %s" % version,
        description="""Send nicely formatted output from remind to standard output.""",
    )
    parser.add_option(
        "-b",
        "--begin",
        action="store",
        type="string",
        dest="begin",
        default=datetime.date.today().strftime("%Y-%m-%d"),
        help="""starting date: YYYY-MM-DD, Defaults to today""",
    )
    parser.add_option(
        "-d",
        "--days",
        action="store",
        type="string",
        dest="days",
        default="%d" % days,
        help="""number of days to display/search, defaults to %d""" % days,
    )
    parser.add_option(
        "-v",
        "--view",
        action="store",
        type="string",
        dest="view",
        default="%s" % viewdefault,
        help=viewhelp,
    )
    parser.add_option(
        "-s",
        "--search",
        action="store",
        type="string",
        dest="search",
        default="",
        help="""search for string within DAYS""",
    )
    parser.add_option(
        "-f",
        "--fileinfo",
        action="store_true",
        default=False,
        dest="fileinfo",
        help="""append file name and line number information""",
    )
    parser.add_option(
        "-n",
        "--nextoccurances",
        action="store_true",
        default=False,
        dest="next",
        help="""list next occurances (ignores other options)""",
    )
    parser.add_option(
        "-m",
        "--markerinfo",
        action="callback",
        callback=MarkHelp,
        help="Show free/busy marker information (ignores other options).",
    )
    parser.add_option(
        "-i",
        "--systeminfo",
        action="callback",
        callback=SysInfo,
        help="Show system information.",
    )

    (options, args) = parser.parse_args()
    (y, m, d) = map(int, options.begin.split("-"))
    date = datetime.date(y, m, d)
    days = int(options.days)
    mydata = RemData()
    startdate = date
    count = 0
    showoutput = True
    if options.next:
        showoutput = False
        print mydata.getOccurances()
    else:
        if options.search:
            showoutput = False
            regs = re.compile(r"%s" % options.search, re.IGNORECASE)
        else:
            regs = re.compile(r".*")
        fblist = []
        while count < days:
            fb = SlotList()  # populate a free busy list for the day
            state = {}  # for the 0-7 5min interval state codes
            y, m, d = date.strftime("%Y %m %d").split()
            count += 1
            daystr = "%s:\n" % date.strftime("%a, %d %b")
            shortdaystr = "%s" % date.strftime("%d %a")
            if mydata.getDay(y, m, d) != None:
                found = False
                for event in mydata.getDay(y, m, d):
                    # print event
                    if event[7] != "*" and event[6] != "*":
                        MarkInterval(fb, state, event[6], event[7])
                    str = " ".join(event[:-6])
                    if not options.search or regs.search(str):
                        found = True
                        file = event[4]
                        line = event[5]
                        if options.fileinfo:
                            daystr += "    %s [%s:%s]\n" % (
                                str.lstrip(),
                                file,
                                line,
                            )
                        else:
                            daystr += "    %s\n" % str
                if found:
                    output.append("%s" % daystr)
            enddate = date
            fblist.append("%s %s" % (shortdaystr, "".join(fb)))
            date = date + RemData.oneday
        if startdate == enddate:
            title = " %s " % startdate.strftime("%a, %d %b %Y")
        else:
            title = " %s - %s " % (
                startdate.strftime("%a, %d %b %Y"),
                enddate.strftime("%a, %d %b %Y"),
            )
        agendawidth = len(SlotList()) + 9
        lbar = (agendawidth - len(title)) / 2
        bars = "=" * lbar
        viewparts = []
        for i in range(len(options.view)):
            viewparts.append(options.view[i])
        if showoutput:
            needstitle = True
            toshow = {}
            if "f" in viewparts:
                toshow["f"] = "%s\n%s\n" % (HourBar(), "\n".join(fblist))
            if "d" in viewparts:
                toshow["d"] = "\n".join(output)
            for s in viewparts:
                if (s == "f" or s == "d") and needstitle:
                    print "%s%s%s" % (bars, title, bars)
                    needstitle = False
                print toshow[s]
        else:
            print "\n".join(output)


if __name__ == "__main__":
    main()
