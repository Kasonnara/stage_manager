#!/usr/bin/python3.6
from datetime import datetime, timedelta
import os
import re

import matplotlib.pyplot as plt

from config import GIT_ROOT, CdB_PATH, DAY_COTA, template_CdB_day, MARKER_START, MARKER_END
from time_management import get_optional_week, get_formated_date, get_start_hour, get_bruch_duration, get_end_hour, \
    compute_total_day, datetime2markerParameter, periodic_touch_thread


def get_tasks(mdt: datetime, line:str, matin_or_aprem, is_empty, *args, auto=False) -> str:
    """Asks the user for the tasks he has done today"""
    if auto:
        return None

    is_empty = (is_empty == "True")
    tasks = []
    skip = datetime.now() > mdt and not is_empty
    while len(tasks) == 0 and not skip:
        print(mdt.strftime("Entrer les tâches du %D {}".format(matin_or_aprem)))
        end = False
        #  Ask for other tasks until the user input nothing
        while not end:
            task = input("Tache {}:\n\t>>".format(len(tasks)+1)) 
            if task == "":
                end = True
            else:
                tasks.append("  - {}\n".format(task))
        if len(tasks) == 0:
            return None
        if datetime.now() < mdt:
            # If this task list doesn't belong to yesterday, reinsert the tag such task new tasks can be added.
            tasks.append("<!---$TASKLIST:{}:{},{}$-->".format(datetime2markerParameter(mdt),
                                                              matin_or_aprem, len(tasks) == 0 and is_empty))
    return "".join(tasks), True


def count_work_hours_cmd(CdB_PATH: str, *args, auto=False):
    """Read the log file and print/plot a summary of the number of hours performed"""
    if auto:
        return

    # r'^###  `\w* \d\d/\d\d/\d\d` \(\d\dh\d\d -> \d\dh\d+ \[\d\dh\d+] -\d\dh\d\d <!---start=\d\dh\d+,end=\d\dh\d+--> midi.*\) total (?P<total_hour>\w+)$'
    simple_pattern = r"^### .*[^-].$"
    recheck_pattern = re.compile(simple_pattern)
    pattern = r"^###  `{day_name} {date}` \({hour} -> {hour} \[{hour}\] -{hour} <!---start={hour},end={hour}--> midi{pause}\) total {total_hour}$".format(
        hour=r'\d\dh\d+', day_name=r'\w*', date=r'\d\d/\d\d/\d\d', pause=r".*", total_hour=r'(?P<total_hour>\w+)')
    day_line_pattern = re.compile(pattern)
    with open(CdB_PATH, "r") as cdb_file:
        match_list = []
        for line in cdb_file:
            # filter day title lines
            match_result = day_line_pattern.match(line)
            if match_result:
                #print("match {}, with total_hour={}".format(line, m.group('total_hour')))
                match_list.append((line, match_result.group('total_hour')))
            elif recheck_pattern.match(line):
                print("- line '{}' seems like a day title but doesn't fully match".format(line))
    print("\nNumber of days detected:", len(match_list))

    found_total = timedelta()
    day_cota = timedelta(hours=DAY_COTA.tm_hour, minutes=DAY_COTA.tm_min)
    expected_total = day_cota * len(match_list)
    td_list = []
    for _, total_hour in match_list:
        timedelta_day = timedelta(hours=int(total_hour[:total_hour.find("h")]),
                                  minutes=int(total_hour[total_hour.find("h")+1:]))
        # TODO also retrive the dates to use as x axis on the plot
        td_list.append(timedelta_day)
        found_total = found_total + timedelta_day
    print("Expected work hour = {}d {}h{}".format(expected_total.days, expected_total.seconds//(60*60), (expected_total.seconds%(60*60))//60))
    print("Realized work hour = {}d {}h{}".format(found_total.days, found_total.seconds//(60*60), (found_total.seconds%(60*60))//60))
    if expected_total > found_total:
        delta = expected_total - found_total
        print("  Delta = -{}d {}h{}\n".format(delta.days, delta.seconds//(60*60), (delta.seconds%(60*60))//60))
    else:
        delta = found_total - expected_total
        print("  Delta = +{}d {}h{}\n".format(delta.days, delta.seconds // (60 * 60), (delta.seconds % (60 * 60)) // 60))
    # Plot the totoal hour history
    plt.bar(range(len(td_list)), [td.seconds/(60*60) for td in td_list])
    # Plot a red horizontal line at the day cota value
    plt.plot([0, len(td_list)], [day_cota.seconds/(60*60)]*2, color="r")
    plt.show()


def auto_git_commit_cmd(mdt, *args, auto=True):
    """Code to execute automatic commit of the log file (Triggered by the COMMITPUSH tag)"""
    if not auto:
        return
    ok = input("Auto commit, make sur you have not add changes yet >>[y,N] ")
    if ok == "y":
        r = os.system("cd {} && git reset && git add {} &&  git add -p && git commit -m \"Update carnet_de_bord.md (auto commit {})\ && git push".format(
            GIT_ROOT, CdB_PATH, mdt.strftime("%D")))
        print("commit done : {}".format("SUCCES" if r == 0 else "/!\\ FAIL /!\\"))
    else:
        print("Abort commit")


# =======================================================================
# Marqueurs de champ a remplir, heure a partir de laquel ils doivent être rempli et fonction de remplissage
MARKERS_CdB = {"DATE": (0, get_formated_date),                  # A tag automatically replaced by the current date
               "STARTHOUR": (0, get_start_hour),                # A tag automatically replaced by the current hour in the morning
               "OPTIONALWEEK": (0, get_optional_week),          # A tag automatically replaced the currend week in year on Mondays
               "ENDHOUR": (17, get_end_hour),                   # A tag replaced by end of day hours manually or automatically on next day using heartbeats
               "BRUNCHDURATION": (11, get_bruch_duration),      # A tag automatically replaced by the total duration of the meals
               "TOTALDAY": (18, compute_total_day),             # A tag automatically replaced by the total work hour of the day
               "TASKLIST": (0, get_tasks),                      # A tag manually replaced by the tasks performed this day (in the morning)
               "TASKLISTPM": (13, get_tasks),                   # A tag manually replaced by the tasks performed this day (in the afternoon)
               "COMMITPUSH": (0, auto_git_commit_cmd),          # A tag that trigger an automatic add + commit + push of the markdown log file
               "RESTARTANALYSE": (0, None),                     # A tag taht restart the analysis process
}
"""
Dictionary of the TAGs present in the markdown file when more time, more data or specific action are needed before being able to fill the log file

The keys are the TAG string itself, while values are a tuple of : 
1. the hours to past before autofilling or asking user th fill the tag
2. the function to run to fill the tag
"""


def fill_file(dt: datetime, filename, marker_filter=None, auto_only=False):
    """Read the markdown file, while trying to fill found TAGs"""
    restart_analyse = True
    unfilled_marker = None
    while restart_analyse:
        restart_analyse = False
        cdt = datetime.now()
        unfilled_marker = []
        # open and read file
        sdata = ""
        lines = []
        with open(filename, "r") as datafile:
            for line in datafile:
                lines.append(line)
        # find tags <!---$ ... $-->
        for line in reversed(lines):
            if not restart_analyse:
                i_start = line.find(MARKER_START, 0)
                i_end = line.find(MARKER_END, i_start)
                while i_start > -1 and i_end > -1:
                    # extract marker and parameters
                    content = line[i_start+len(MARKER_START):i_end].split(":")
                    marker = content[0]
                    marker_date = datetime(*[int(x) for x in content[1].split("/")], 23, 59)
                    params = ":".join(content[2:]).split(",")

                    # call related function
                    r = None
                    if marker == "RESTARTANALYSE":
                        print("Restarting the analyse (it's not a bug, it's a feature)")
                        # Remove this marker and restart the analyse from the start
                        restart_analyse = True
                        line = line[: i_start] + line[i_end + len(MARKER_END):]
                    elif ((marker_filter is None and (dt.hour >= MARKERS_CdB[marker][0] or marker_date < cdt))
                        or (marker_filter is not None and marker in marker_filter)):
                        r = MARKERS_CdB[marker][1](marker_date, line, *params, auto=auto_only)
                    # Replace the marker with function result
                    if r is None:
                        unfilled_marker.append((marker, marker_date))
                        # find next tag <!--- ... -->
                        i_start = line.find(MARKER_START, i_end)
                        i_end = line.find(MARKER_END, i_start)
                    else:
                        replace_text, skip = r
                        line = line[: i_start] + replace_text + line[i_end + len(MARKER_END):]
                        # find next tag <!--- ... -->
                        i_start = line.find(MARKER_START, i_start + (len(replace_text) if skip else 0))
                        i_end = line.find(MARKER_END, i_start)

            sdata = line + sdata
        with open(filename, "w") as outdata:
            outdata.write(sdata)
    return unfilled_marker


def add_new_day(mdt: datetime, filename: str):
    """Add a copy of the template a the end of the log file, replacing all {0} parameters by the given date"""
    with open(filename, "a") as data:
        data.write(template_CdB_day.format(datetime2markerParameter(mdt)))


def find_day(target_datetime: datetime = None, cbd_path: str = CdB_PATH) -> (datetime, str):
    """
    If target_datetime is not defined:
        return the datetime and line of last day written in the logfile

    If target_datetime:
        return the datetime and line corresponding to the given target_datetime or None if the day wasn't found

    :param target_datetime: optional(datetime), None or a specific day
    :param cbd_path: str, the path to the markdown log file
    :return: Optional((datetime, str)), the line found as well as the corresponding datetime
    """
    target_date = None if target_datetime is None else datetime.strptime(target_datetime.strftime("%D"), "%m/%d/%y")
    last_dateline = None
    with open(cbd_path, "r") as lines:
        for line in lines:
            if line.startswith("###  `"):  # TODO improve with rexeg and factor code
                i1 = line.find("`")
                i2 = line.find("`", i1 + 1)
                date_part = line[i1 + 1:i2]
                if date_part.startswith(MARKER_START + "DATE:"):
                    print("'"+date_part+"'", "'"+date_part[len(MARKER_START + "DATE:"):-len(":"+MARKER_END)]+"'" )
                    cdate = datetime.strptime(date_part[len(MARKER_START + "DATE:"):-len(":"+MARKER_END)], "%Y/%m/%d")
                else:
                    cdate = datetime.strptime(date_part, "%A %m/%d/%y")

                # Memorise the last found date for the last day search case
                if last_dateline is None or last_dateline[0] < cdate:
                    last_dateline = cdate, line
                # Stop if the target day is found
                if target_date is not None and cdate == target_date:
                    return cdate, line
    return None if target_datetime is not None else last_dateline


def find_last_day(filename: str) -> datetime:
    """Simpler method to get the datetime of the last day present in the log file"""
    cdate, line = find_day(target_datetime=None, cbd_path=filename)
    return cdate


def isDayCreated(cdt: datetime, cdb_path: str) -> bool:
    """
    Return True if the given day exist in the log file
    """
    return find_day(cdt, cdb_path) is not None


if __name__ == "__main__":
    # Start the thread which keep track of the last hour when this script(~=this computer) was running
    periodic_touch_thread.start()

    today = datetime.now()
    if not isDayCreated(today, CdB_PATH):
        add_new_day(today, CdB_PATH)
    remaining_markers = fill_file(today, CdB_PATH, auto_only=True)
    user_response = ""

    # Main loop
    while not user_response == "exit":
        # Print menu
        print("Terminé, action possibles:\n\texit)\tEnd the script")
        print("\t )\tRe-read the file")
        print("\tcommit)\tCommit and push change on CdB")
        print("\tcount)\tCount the average total hours per day")
        for k,m in enumerate(remaining_markers):
            print("\t{})\t{} \t{}".format(k,m[0], "" if m[1] is None else (m[1].strftime("%D"))))

        # Get user input
        user_response = input(">>")

        # Analyse input command  # TODO use argparse
        if user_response.isdigit():
            i = int(user_response)
            print("selected", remaining_markers[i][0])
            if (i>=0 and i<len(remaining_markers)):
                remaining_markers = fill_file(datetime.now(), CdB_PATH, [remaining_markers[i][0]])
        if user_response == "":
            remaining_markers = fill_file(datetime.now(), CdB_PATH, None)
        if user_response == "commit":
            auto_git_commit_cmd(datetime.now())
        if user_response == "count":
            count_work_hours_cmd(CdB_PATH)
