#!/usr/bin/python
import sys, os, os.path, codecs
import builtins

has_wxremindrc = False
rc = []
added = []
msg = []
error = []
warn = []
fatal = False
has_wxremindrc = False
set_ed = False
search_path = os.getenv("PATH").split(os.pathsep)

if sys.platform == "darwin":
    mac = True
else:
    mac = False


def PathSearch(filename):
    for path in search_path:
        candidate = os.path.join(path, filename)
        if os.path.os.path.isfile(candidate):
            return os.path.abspath(candidate)
    return ""


def check(variable):
    global rc, added
    # (name, defining_code, description) = variable
    name = variable[0]
    defining_code = variable[1]
    # print name, defining_code, type(defining_code)

    description = "\n### ".join(variable[2:])
    if description:
        rc.append("\n### %s" % description)
    if name in globals():
        # print "Skipping: %s" % name
        if type(globals()[name]) == str:
            if globals()[name] != "":
                s = "%s = '''%s'''" % (name, globals()[name])
            else:
                s = "%s = ''" % (name)
        else:
            s = "%s = %s" % (name, globals()[name])
        rc.append(s)
    else:
        if type(defining_code) == str:
            try:
                exec("res = %s" % defining_code)
                # print "res = %s" % res
            except:
                exec("res = '%s'" % defining_code)
                # print "res = %s" % res
        elif type(defining_code) in [tuple, list]:
            exec("res = (%s)" % repr(defining_code))
        else:
            exec("res = %s" % defining_code)
        globals()[name] = res
        if globals()[name] != "not set":
            # print "Adding: %s" % name
            if type(res) == str:
                if res != "":
                    s = "%s = '''%s'''" % (name, res)
                else:
                    s = "%s = ''" % (name)
            elif type(res) in [tuple, list]:
                s = "%s = %s" % (name, repr(res))
            else:
                s = "%s = %s" % (name, res)
            added.append(s)
            rc.append(s)


def unIndent(s):
    # remove the minimum indent from the lines in a triple-quoted string
    lines = s.splitlines()
    numDel = min([len(line) - len(line.lstrip()) for line in lines])
    return "\n".join([line[numDel:] for line in lines])


def set_rem2ps():
    rem2ps = PathSearch("rem2ps")
    if rem2ps:
        rem2ps = "%s -l > %s/.calendar.ps" % (rem2ps, os.path.expanduser("~"))
    else:
        rem2ps = ""
    return rem2ps


def set_viewps():
    if mac:
        viewps = "open -a Preview %s/.calendar.ps" % os.path.expanduser("~")
    else:
        gv = PathSearch("gv")
        if gv:
            viewps = (
                "%s --orientation=landscape --media=LETTER %s/.calendar.ps"
                % (gv, os.path.expanduser("~"))
            )
        else:
            viewps = ""
    return viewps


def set_remind():
    global fatal
    remind = PathSearch("remind")
    if not remind:
        fatal = True
        print(
            (
                unIndent(
                    """\
        Fatal Error: Could not find required file 'remind'."""
                )
            )
        )
    return remind


def set_reminders():
    reminders = os.path.expanduser("~/.reminders")
    if not os.path.isfile(reminders):
        fatal = True
        print(
            (
                unIndent(
                    """\
        Fatal Error: Could not find required file '%s'."""
                    % reminders
                )
            )
        )
        reminders = ""
    return reminders


def set_wxremindrc():
    global has_wxremindrc
    wxremindrc = os.path.expanduser("~/.wxremindrc")
    if os.path.isfile(wxremindrc):
        has_wxremindrc = True
    return wxremindrc


def set_editor_settings():
    global rc, added, set_ed
    chooselater = ["choose later", "", "", ""]
    comment = ""
    selected = []
    unselected = []
    if set_ed:
        return None
    else:
        set_ed = True
    if mac:
        options = {
            "mate": [
                "editold = '''%(e)s -l %(n)s -w %(f)s'''",
                "editnew = '''%(e)s -l 99999 -w %(f)s'''",
            ],
            "bbedit": [
                "editold = '''%(e)s +%(n)s -w --new-window %(f)s'''",
                "editnew = '''%(e)s +99999 -w --new-window %(f)s'''",
            ],
            "edit": [
                "editold = '''%(e)s +%(n)s -w --new-window %(f)s'''",
                "editnew = '''%(e)s +99999 -w --new-window %(f)s'''",
            ],
        }
        for name in ["mate", "edit", "bbedit"]:
            editor = PathSearch(name)
            if editor:
                if comment != "# ":
                    selected = (editor, options[name][0], options[name][1])
                else:
                    unselected.append(name)
                rc.append("%seditor = '''%s'''" % (comment, editor))
                added.append("%seditor = '''%s'''" % (comment, editor))
                rc.append("%s%s" % (comment, options[name][0]))
                added.append("%s%s" % (comment, options[name][0]))
                rc.append("%s%s" % (comment, options[name][1]))
                added.append("%s%s" % (comment, options[name][1]))
                comment = "# "
    else:  # not mac
        options = {
            "gvim": [
                "editold = '''%(e)s -f +%(n)s %(f)s'''",
                "editnew = '''%(e)s -f + %(f)s'''",
            ],
            "emacs": [
                "editold = '''%(e)s +%(n)s %(f)s'''",
                "editnew = '''%(e)s +999999 %(f)s'''",
            ],
        }
        for name in ["gvim", "emacs"]:
            editor = PathSearch(name)
            if editor:
                if comment != "# ":
                    selected = (editor, options[name][0], options[name][1])
                else:
                    unselected.append(name)
                rc.append("%seditor = '''%s'''" % (comment, editor))
                added.append("%seditor = '''%s'''" % (comment, editor))
                rc.append("%s%s" % (comment, options[name][0]))
                added.append("%s%s" % (comment, options[name][0]))
                rc.append("%s%s" % (comment, options[name][1]))
                added.append("%s%s" % (comment, options[name][1]))
                comment = "# "
    if selected == []:
        rc.append("editor = ''")
        rc.append("editold = ''")
        rc.append("editnew = ''")
        print(
            (
                unIndent(
                    """\

        You will need to specify values for:

            editor
            editold
            editnew

        in %s."""
                    % wxremindrc
                )
            )
        )
    else:
        print(
            (
                unIndent(
                    """\

        The following settings were made for your external editor:

            editor = '%s'
            editold = '%s'
            editnew  = '%s'

        Edit %s if you wish to make changes."""
                    % (selected[0], selected[1], selected[2], wxremindrc)
                )
            )
        )
        if len(unselected) > 0:
            print(
                unIndent(
                    """\

            Comparable settings were also made for

                %s

            but were commented out."""
                    % "\n    ".join(unselected)
                )
            )
    return None


def make_wxremindrc():
    fo = open("%s" % wxremindrc, "w")
    fo.write(
        """\
### Configuration settings for wxRemind
###
### A current version of this file will be written to ~/.wxremindrc
### if it doesn't already exist. This means you can always restore
### the default settings by either removing or renaming ~/.wxremindrc.
### Further, if you would like to restore some but not all of the default
### settings, simply erase the settings you want restored and the next
### time wxremind, wxremdata or wxremalert is run, your ~/.wxremindrc will
### be recreated with your settings together with the default settings for
### the ones you erased.
###
"""
    )
    for line in rc:
        # print "rc: %s" % line
        fo.write("%s\n" % line)
    fo.close()


variables = [
    ["encoding", '"utf-8"', "The default encoding"],
    ["remind", '"%s" % set_remind()', "The full path to remind"],
    [
        "remind_internal_server",
        True,
        "Start remind in internal server mode with the -z0 switch",
    ],
    [
        "ignore_char",
        '"~"',
        "Do not produce internal alerts for reminders with MSG strings which",
        "begin with this character",
    ],
    [
        "reminders",
        '"%s" % set_reminders()',
        "The location of the base reminders file",
        "This must be ~/.reminders",
    ],
    [
        "current",
        '"%s" % os.path.expanduser("~/.reminders")',
        'The path to "current" -new reminders will be written to this file',
    ],
    [
        "calendars",
        '"%s" % os.path.expanduser("~")',
        "Put the temporary monthly postscript calendars in this directory",
    ],
    [
        "notedir",
        '"%s" % os.path.expanduser("~/.wxremnotes")',
        "The directory to use for storing notes attached to reminders",
    ],
    [
        "notecolor",
        '"FIREBRICK4"',
        "The foreground (text) color to use in the wxremind selected day",
        "window for reminders that have attached notes",
    ],
    [
        "rem2ps",
        '"%s" % set_rem2ps()',
        "The command used to generate monthly postscript calendars",
    ],
    [
        "viewps",
        '"%s" % set_viewps()',
        "The command to view the monthly postscript calendar",
    ],
    [
        "editor",
        '"%s" % set_editor()',
        "Edit settings",
        "editor:  the full path to the external editor",
        "editold: the command for editing an old reminder",
        "editnew: the command for editing an new reminder",
        "Both editold and editnew use the following SUBSTITUTIONS:",
        "    %(e)s -> editor",
        "    %(n)s -> the line number to edit",
        "    %(f)s -> the file name",
    ],
    ["editold", '"%s" % set_editold()', ""],
    ["editnew", '"%s" % set_editnew()', ""],
    [
        "audible1",
        '""',
        'The command to run when "alert_sound = 1"',
        "   %s -> the text of the reminder message",
    ],
    [
        "audible2",
        '""',
        'The command to run when "alert_sound = 2"',
        "   %s -> the text of the reminder message",
    ],
    [
        "textfieldwidth",
        400,
        "How wide to make the text entry fields in the new event dialogs",
    ],
    [
        "alert_sound",
        0,
        "Which command, 0 (silent), 1 (audible1) or 2 (audible2), to use ",
        "for audible alerts",
    ],
    [
        "visible2",
        '""',
        'The command to run for visable alerts when "alert_display = 2"',
    ],
    [
        "alert_display",
        1,
        "Which command, 0 (no display), 1 (internal display) or 2 (visible2) to use",
        "for visible alerts",
    ],
    [
        "days",
        7,
        'The number of days to display in the "next n days" view',
        "and by default for wxremdata",
    ],
    [
        "twelvehour",
        True,
        "Display time using 12 hour format (True) or 24 hour format (False)",
    ],
    [
        "sundayfirst",
        True,
        "Have the calendar use Sunday (True) or Monday (False) as the first",
        "day of the week",
    ],
    [
        "alert_greeting",
        True,
        "If True add a time appropriate greeting to spoken message,",
        'e.g., "Good morning"',
    ],
    [
        "alert_whom",
        '"%s" % ""',
        'Added it to the spoken greeting, e.g, "Good morning, Dan"',
    ],
    [
        "alert_parsenums",
        True,
        "If True, replace all 3-digit numbers in msg with spoken",
        ' equivalents, e.g., Replace "201" with "2 O1" where O is an',
        'uppercase o) and "385" with "3 85". Thus "201" would be spoken as',
        '"two oh one" and "385" as "three eighty-five". Why course and room',
        "numbers are spoken this way is a mystery to me.",
    ],
    [
        "alert_other_message",
        '"%1"',
        'The default string provided for "alert_other_message" will be',
        'inserted in the "Other Message" field when a new alert reminder is',
        "created. Such a message will not appear on the event list or",
        "calendar but will be appended to the alert message.",
    ],
    [
        "alert_seconds",
        15,
        "How many seconds should the advance warning alert be displayed for",
        "a  reminder.",
    ],
    [
        "final_seconds",
        600,
        "How many seconds should the final alert be displayed for",
        "a  reminder. Set equal to 0 (zero) to have the final alert",
        'displayed until its "OK" button is clicked.',
    ],
    ["basefontsize", 12, "The base font size"],
    [
        "statusfontadj",
        0,
        "The adjustment to the base font size to be used in the status bar",
    ],
    [
        "listfontadj",
        0,
        "The adjustment to the base font size to be used in the event list",
    ],
    [
        "datefontadj",
        1,
        "The adjustment to the base font size to be used in the date header",
    ],
    [
        "buttonfontadj",
        0,
        'The adjustment to the base font size to be used in the "today" button',
    ],
    [
        "calendarfontadj",
        0,
        "The adjustment to the base font size to be used in the calendar",
    ],
    [
        "daysfontsize",
        '""',
        'The size or adjustment to the base font size for the "days" view.',
        'Put adjustments in quotes, e.g., "+2" and use "+0" or "" for no adjustment',
    ],
    [
        "alertfontsize",
        '"+1"',
        "The size or adjustment to the base font size for the alert display.",
        'Put adjustments in quotes, e.g., "+2" and use "+0" or "" for no adjustment',
    ],
    ["eventlistwidth", 500, "The width of the event list window"],
    ["alertsize", (500, 120), "The size of the internal alert message window"],
    [
        "zerominutes",
        15,
        "The time to assign to events with zero duration in computing the",
        "day event totals",
    ],
    [
        "agendastarthour",
        8,
        "Starting hour for agenda (free/busy) display for wxremdata",
        "This setting does not affect the wxremind display.",
    ],
    [
        "agendaendhour",
        22,
        "Ending hour for agenda (free/busy) display for wxremdata",
        "This setting does not affect the wxremind display.",
    ],
    ["defaultduration", "0:30", "The default H:MM duration for new reminders"],
    [
        "busy0",
        (40, "SLATEBLUE2"),
        '(M0, "COLOR0") Days with appointments totaling less than M0 minutes',
        'have foreground color "BLACK". Days with appointments totaling MORE',
        'than M1" minutes but less than "M1" minutes (see below) have',
        'forground color "COLOR0"',
    ],
    [
        "busy1",
        (80, "BLUE2"),
        '(M1, "COLOR1") For days with more than "M1" but less than "M2" minutes"',
    ],
    [
        "busy2",
        (160, """FORESTGREEN"""),
        '(M2, "COLOR2") For days with more than "M2" but less than "M3" minutes"',
    ],
    [
        "busy3",
        (320, "BROWN"),
        '(M3, "COLOR3") For days with more than "M3" but less than "M4" minutes"',
    ],
    [
        "busy4",
        (480, "VIOLETRED"),
        '(M4, "COLOR4") For days with more than "M4" minutes"',
    ],
    [
        "holidaycolor",
        "NAVYBLUE",
        "The color for box around holidays in the wxremind calendar",
    ],
    [
        "holidayshade",
        "240 200 200",
        "The background shading color for holidays in the monthly postscript",
        "calendar. Use a single number between 0 (black) and 255 (white) or",
        "a triple of numbers to specify the RGB components.",
    ],
    [
        "headercolor",
        "NAVYBLUE",
        "The font color for the weekday names in the calendar",
    ],
    [
        "todaycolor",
        "BLUE2",
        "The color to highlight the current date in the event list header",
    ],
    [
        "alertcolor",
        "BLUE2",
        "The color for the text in the internal alert message window",
    ],
    [
        "freebusycolor",
        (35, 142, 35),
        "A tuple of the RGB colors used to shade busy time in the free/busy display",
    ],
    [
        "freebusyfontsize",
        12,
        "The font size for weekday abbreviations and hour numbers in the free/busy display",
    ],
    ["bgcolor", "GRAY95", "The background color"],
    [
        "nfcolor",
        "GRAY95",
        'The "unfocused" background color for the calendar and the event list',
    ],
    [
        "fcolor",
        "GRAY99",
        'The "focused" color for the calendar and the event list',
    ],
    [
        "ec_border",
        "2",
        "The borders for the event and calendar",
        "sunken (-1), flat (0), raised (1) or simple (2)",
    ],
    [
        "sb_border",
        "0",
        "The border for the status bar",
        "sunken (-1), flat (0), raised (1) or simple (2)",
    ],
    [
        "viewdefault",
        '"fd"',
        "The wxremdata default view: f (free/busy), d (daily agenda)",
    ],
    [
        "days_view",
        '"fd"',
        'wxremind "days" default view: f (free/busy), d (daily agenda)',
    ],
    [
        "nullminute12",
        '"o clock"',
        "The time suffix when twelvehour is true and there are no minutes",
    ],
    [
        "undertenminuteprefix12",
        '"O"',
        'The prefix for a single digit minute. E.g., use an "O"',
        '(an uppercase o) to have "6:01" pronounced as "six oh 1"',
    ],
    [
        "minute12",
        '""',
        'The suffix for minute, e.g., 6:01, in 12 hour mode - default ""',
    ],
    [
        "minutes12",
        '""',
        'The suffix for minutes, e.g., 6:03, in 12 hour mode - default ""',
    ],
    [
        "onehour12",
        '"1"',
        "The spoken version of 1:00 in 12 hour mode - default 1",
    ],
    ["hour12", '""', 'The suffix for hour in 12 hour mode - default ""'],
    ["hours12", '""', 'The suffix for hours in 12 hour mode - default ""'],
    [
        "nullminute24",
        '""',
        'The suffix for zero minutes in 24 hour mode - default ""',
    ],
    [
        "undertenminuteprefix24",
        '""',
        'The prefix for a single digit minute in 24 hour mode - default ""',
    ],
    [
        "minute24",
        '"minute"',
        'The suffix for minute in 24 hour mode - default "minute"',
    ],
    [
        "minutes24",
        '"minutes"',
        'The suffix for minutes in 24 hour mode - default "minutes"',
    ],
    ["nullhours24", '"0 hours"', "The spoken version of 0:00 in 24 hour mode"],
    ["onehour24", '"1 hour"', "The spoken version of 1:00 in 24 hour mode"],
    [
        "hour24",
        '"hour"',
        'The suffix for hour in 24 hour mode - default "hour"',
    ],
    [
        "hours24",
        '"hours"',
        'The suffix for hours in 24 hour mode - default "hours"',
    ],
    [
        "goodmorning",
        '"Good morning"',
        "The greeting for times prior to 12 noon",
    ],
    [
        "goodafternoon",
        '"Good afternoon"',
        "The greeting for times between 12PM and 6PM",
    ],
    ["goodevening", '"Good evening"', "The greeting for times after 6PM"],
    ["thetimeis", '"The time is"', "The prefix for the spoken time"],
    [
        "remindersfor",
        '"Reminders for"',
        "The label for the event list window date bar",
    ],
    [
        "datebarformatstring",
        "%a, %b %d %Y (week %U, day %j)",
        "The format to use for the date in the datebar using the following",
        "directives: ",
        "%a:  Locale's abbreviated weekday name.",
        "%A:  Locale's full weekday name.",
        "%b:  Locale's abbreviated month name.",
        "%B:  Locale's full month name.",
        "%c:  Locale's appropriate date and time representation.",
        "%d:  Day of the month as a decimal number [01,31].",
        "%H:  Hour (24-hour clock) as a decimal number [00,23].",
        "%I:  Hour (12-hour clock) as a decimal number [01,12].",
        "%j:  Day of the year as a decimal number [001,366].",
        "%m:  Month as a decimal number [01,12].",
        "%M:  Minute as a decimal number [00,59].",
        "%p:  Locale's equivalent of either AM or PM.",
        "%S:  Second as a decimal number [00,61].",
        "%U:  Week number of the year (Sunday as the first day of the week) as a",
        "     decimal number [00,53]. All days in a new year preceding the first",
        "     first Sunday are considered to be in week 0.",
        "%V:  Week number of the year (Monday as the first day of the week) as",
        "     a decimal number (01-53).  If the week containing January 1 has",
        "     four or more days in the new year, then it is week 1; otherwise",
        "     it is the last week of the previous year, and the next week is",
        "     week 1.",
        "%w:  Weekday as a decimal number [0(Sunday),6].",
        "%W:  Week number of the year (Monday as the first day of the week) as a",
        "     decimal number [00,53]. All days in a new year preceding the first",
        "     Monday are considered to be in week 0.",
        "%x:  Locale's appropriate date representation.",
        "%X:  Locale's appropriate time representation.",
        "%y:  Year without century as a decimal number [00,99].",
        "%Y:  Year with century as a decimal number.",
        "%Z:  Time zone name (no characters if no time zone exists).",
        '%%:  A literal "%" character.',
    ],
    [
        "dateformatstring",
        "%a, %b %d %Y",
        "The format to use for the date other than in the datebar",
        "using the directives listed above.",
    ],
    [
        "pressforhelp",
        '"Press ? for help"',
        "The normal label for the status line prompt.",
    ],
]

# main
if len(sys.argv) > 1 and sys.argv[1] == "-f":
    FORCE = True
else:
    FORCE = False

wxremindrc = set_wxremindrc()
if has_wxremindrc and not FORCE:
    exec(compile(open(wxremindrc, "rb").read(), wxremindrc, "exec"))

for variable in variables:
    check(variable)

if fatal:
    sys.exit()

if len(added) > 0 or FORCE:
    # print added
    if has_wxremindrc:
        import shutil

        shutil.copyfile(wxremindrc, "%s.bak" % wxremindrc)
        make_wxremindrc()
        exec(compile(open(wxremindrc, "rb").read(), wxremindrc, "exec"))
        if FORCE:
            print(
                unIndent(
                    """\

IMPORTANT: Your configuration file

    %s

 has as been copied to

    %s.bak

and a new configuration file with default settings has been saved as

    %s

"""
                    % (wxremindrc, wxremindrc, wxremindrc)
                )
            )
        else:
            print(
                unIndent(
                    """\

IMPORTANT: Your configuration file

    %s

has as been copied to

    %s.bak

and a new configuration file which incorporates your settings together
with

    %s

has been saved as

    %s
"""
                    % (wxremindrc, wxremindrc, "\n    ".join(added), wxremindrc)
                )
            )

    else:
        make_wxremindrc()
        print(
            unIndent(
                """\
A new configuration file with default settings has been saved as

    %s
"""
                % wxremindrc
            )
        )

    print(
        unIndent(
            """\

Please remember to rate wxRemind at <http://freshmeat.net/projects/wxrem/>
and to send your comments to <daniel.graham@duke.edu>. Continuing
improvement depends upon your feedback.

Thanks for using wxRemind!

"""
        )
    )
