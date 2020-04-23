import _gdbm
import os
import shelve
import sys

import time
from datetime import datetime, date
import datetime as dt
from threading import Thread

from config import STAGE_START_DATE, DAY_COTA, START_DELAY, HEARTBIT_SHELVE_KEY, METADAT_SHELVE_PATH, \
    KEEP_UPTIME_HISTORY, HEARTBIT_TOUCH_DELAY


def get_optional_week(mdt: datetime, *args, auto=True):
    """Return the week extra line if the current day is Monday"""
    if (mdt.weekday == 0):
        week_value = ((mdt - STAGE_START_DATE).days // 7) + 1
        return "***\n\n## Semaine {}\n".format(week_value), True
    else:
        return "", True


def get_formated_date(dt: datetime, *args, auto=True):
    """return formated date"""
    return dt.strftime("%A %D"), True


def get_hour(dt:datetime, *args, auto=True):
    """return formated hour"""
    return dt.strftime("%Hh%M"), True


def get_user_hour(prompt_msg: str, auto=False) -> str:
    """Ask the user for an hour"""
    if auto:
        return None

    invalid_input = True
    while invalid_input:
        try:
            user_response = input(prompt_msg + " [hh:mm] >>")
            if user_response is "":
                # Abort, let marker empty
                invalid_input = False
                return None
            else:
                hours, minutes = (int(x) for x in user_response.split(":"))
                invalid_inputce = False
                return "{}h{}".format(hours,minutes), True
        except ValueError as ve:
            os.write(2, b"Erreur : format hh:mm incorrect.\n")
            time.sleep(0.1)
            invalid_input = True


def get_start_hour(mdt: datetime, *args, auto=True):
    """
    If auto: automatically return the current hour
    else: ask the user
    """
    cdt = datetime.now()
    if mdt > cdt and cdt.hour <= 10:
        # this day template is created the day it refers to.
        return get_hour(cdt - START_DELAY, *args, auto=auto)
    else:
        # TODO should be prompted as soon as possible, but incompatible with full-auto mode
        return get_user_hour(mdt.strftime("A quelle heure est tu arrivés le %D ?"), auto=auto)


def get_bruch_duration(mdt: datetime, line: str,  *args, auto=False):
    """Ask the user for the begining and end hour of its meal"""
    if auto:
        return None

    start_hour = None
    if len(args) == 1 and not args[0] == '':
        # Use saved start hour
        start_hour = (args[0], True)
    else:
        # Ask user
        start_hour = get_user_hour(mdt.strftime("A quelle heure a commencé la pause de midi le %D?"), auto=auto)
    if start_hour is None:
        return None
    else:
        end_hour = get_user_hour(mdt.strftime("A quelle heure a fini la pause de midi le %D?"), auto=auto)
        if end_hour is None:
            return "<!---$BRUNCHDURATION:{0}:{1}$-->".format(datetime2markerParameter(mdt), start_hour[0]), True
        else:
            h1 = time.strptime(start_hour[0], "%Hh%M")
            h2 = time.strptime(end_hour[0], "%Hh%M")
            delta = hour_op(h2, h1, difference=True)
            h0 = time.strptime( line[line.find("(")+1:line.find(" ->")], "%Hh%M") # parse day start hour
            predicted_end_hour = hour_op(hour_op(h0, delta), DAY_COTA)
            print("Heure théorique de fin de la journée : "+time.strftime("%Hh%M", predicted_end_hour))
            return "[{}] -{} <!---start={},end={}-->".format(time.strftime("%Hh%M", predicted_end_hour),time.strftime("%Hh%M", delta), start_hour[0], end_hour[0]), True


def get_end_hour(mdt: date, line: str, *args, auto=False):
    """If end hour can be auto filled, then return it, else ask the user"""
    if date.today().day != mdt.day:
        # Try auto fill with uptime
        uptime_record = get_lastday_uptime(mdt)
        if uptime_record is not None:
            return "{}h{}".format(uptime_record.hour, uptime_record.minute), True
    return get_user_hour(mdt.strftime("A quelle heure es tu parti le soir du %D?"), auto=auto)


def compute_total_day(mdt: datetime, line: str, *args, auto=True) -> str:
    # Find start hour
    hs = time.strptime(line[line.find("(")+1:line.find(" ->")], "%Hh%M")
    #  Find end hour
    he_i = line.find(" -> ") + 4
    str_he = line[he_i: line.find(" ", he_i)]
    if len(str_he) > 5:
        return None
    he = time.strptime(str_he, "%Hh%M")
    # Find pause duration
    hm_i = line.find("] -") + 3
    if hm_i < 0:
        return None
    str_hm = line[hm_i: line.find(" ", hm_i)]
    if len(str_hm) > 5:
        return None
    hm = time.strptime(str_hm, "%Hh%M")
    # Compute total work duration
    total_hour = hour_op(hour_op(he, hs, True), hm, True)
    return time.strftime("%Hh%M", total_hour), True


def datetime2markerParameter(marker_dt: date):
    return marker_dt.strftime("%Y/%m/%d")


def hour_op(t1: time.struct_time, t2: time.struct_time, difference=False):
    """addition and substraction of hours"""
    dh = t1.tm_hour + (- t2.tm_hour if difference else t2.tm_hour)
    dm = t1.tm_min + (- t2.tm_min if difference else t2.tm_min)
    if dm < 0:
        dm += 60
        dh -= 1
    elif dm >= 60:
        dm -= 60
        dh += 1
    return time.strptime("{} {}".format(dh, dm), "%H %M")


# =======================================================================
def _get_uptime_key(date: date):
    """Generate a key (unique per day) for storing the heartbeat time"""
    return HEARTBIT_SHELVE_KEY + datetime2markerParameter(date)


def touch_uptime():
    """Update the shelve heartbeat"""
    now = datetime.now()
    # Compute the unique key for the current day
    heartbit_current_key = _get_uptime_key(now)

    # Write the current time in the uptime memory file
    with shelve.open(METADAT_SHELVE_PATH) as metadata:
        metadata[heartbit_current_key] = now.time()


def _periodic_touch_update():
    """Main of the thread to periodically update the heartbeat"""
    try:
        while True:
            try:
                touch_uptime()
            except _gdbm.error:
                pass
            time.sleep(HEARTBIT_TOUCH_DELAY)
    except Exception as e:
        print("WARNING, touch thread crashed", file=sys.stderr)
        raise
periodic_touch_thread = Thread(target=_periodic_touch_update)
periodic_touch_thread.setDaemon(True)


def get_lastday_uptime(date: datetime, remove=not KEEP_UPTIME_HISTORY):
    """Deduce the previous day end hour from the heartbeat"""
    # Compute the unique key for that day
    heartbit_key = _get_uptime_key(date)

    for failcount in range(3):
        try:
            with shelve.open(METADAT_SHELVE_PATH) as metadata:
                if heartbit_key in metadata.keys():
                    last_day_uptime: dt.time = metadata[heartbit_key]
                    if remove:
                        del metadata[heartbit_key]
                    return last_day_uptime
                else:
                    print("No heartbit")
                    return None
        except _gdbm.error:
            time.sleep(1)
            if failcount == 3 - 1:
                raise

