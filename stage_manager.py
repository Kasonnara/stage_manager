from datetime import datetime, timedelta
import os
import time
import winsound

GIT_ROOT =  "C:/Users/fx599216/Documents/git/clones/doc-stage"
CdB_PATH = "C:\\Users\\fx599216\\Documents\\git\\clones\\doc-stage\\carnet_de_bord.md"
STAGE_START_DATE = datetime(2018,6,4)
MARKER_START, MARKER_END = "<!---$", "$-->"
DAY_COTA = time.strptime("7h00", "%Hh%M")
START_DELAY = timedelta(0,5,0) # = 5 minutes. number of minute to remove in the morning, represent time needed to start the script

template_CdB_day = """
<!---$OPTIONALWEEK:{0}:$-->
###  `<!---$DATE:{0}:$-->` (<!---$STARTHOUR:{0}$--> -> <!---$ENDHOUR:{0}:$--> <!---$BRUNCHDURATION:{0}:$--> midi) <!---$TOTALDAY:{0}:$-->

- Matin:
<!---$TASKLIST:{0}:matin,True$-->
- Aprem:
<!---$TASKLIST:{0}:aprem,True$-->
"""


def get_optional_week(mdt:datetime, *args):
    """Return the week extra line if the current day is Monday"""
    if (mdt.weekday == 0):
        week_value = ((mdt - STAGE_START_DATE).days // 7) + 1
        return "## Semaine {}\n".format(week_value)
    else:
        return ""


def get_formated_date(dt:datetime, *args):
    """return formated date"""
    return dt.strftime("%A %D")


def get_hour(dt:datetime, *args):
    """return formated hour"""
    return dt.strftime("%Hh%M")


def get_user_hour(prompt_msg:str):
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
                return "{}h{}".format(hours,minutes)
        except ValueError as ve:
            os.write(2, b"Erreur : format hh:mm incorrect.\n")
            time.sleep(0.1)
            invalid_input = True


def get_start_hour(mdt:datetime, *args):
    cdt = datetime.now()
    if (mdt > cdt and cdt.hour <= 10):
        # this day template is created the day it refers to.
        return get_hour(cdt - START_DELAY, *args)
    else:
        return get_user_hour(mdt.strftime("A quelle heure est tu arrivés le %D ?"))


def get_bruch_duration(mdt:datetime, line:str,  *args):
    start_hour = None
    if len(args) == 1 and not args[0] == '':
        # Use saved start hour
        start_hour = args[0]
    else:
        # Ask user
        start_hour =  get_user_hour(mdt.strftime("A quelle heure a commencé la pause de midi le %D?"))
    if start_hour is None:
        return None
    else:
        end_hour = get_user_hour(mdt.strftime("A quelle heure a fini la pause de midi le %D?"))
        if end_hour is None:
            return "<!---$BRUNCHDURATION:{0}:{1}$-->".format(datetime2markerParameter(mdt), start_hour)
        else:
            h1 = time.strptime(start_hour, "%Hh%M")
            h2 = time.strptime(end_hour, "%Hh%M")
            delta = hour_op(h2, h1, difference=True)
            h0 = time.strptime( line[line.find("(")+1:line.find(" ->")], "%Hh%M") # parse day start hour
            predicted_end_hour = hour_op(hour_op(h0, delta), DAY_COTA)
            print("Heure théorique de fin de la journée : "+time.strftime("%Hh%M", predicted_end_hour))
            return "[{}] -{} <!---start={},end={}-->".format(time.strftime("%Hh%M", predicted_end_hour),time.strftime("%Hh%M", delta), start_hour, end_hour)


def get_end_hour(mdt:datetime, line:str, *args):
    return get_user_hour(mdt.strftime("A quelle heure es tu parti le soir du %D?"))


def compute_total_day(mdt:datetime, line:str, *args):
    # TODO
    return None


def get_tasks(mdt:datetime, line:str, matin_or_aprem, isEmpty, *args):
    isEmpty = isEmpty=="True"
    tasks = []
    skip = datetime.now() > mdt and not isEmpty
    while len(tasks) == 0 and not skip:
        print(mdt.strftime("Entrer les tâches du %D {}".format(matin_or_aprem)))
        end = False
        while not end:
            task = input("Tache {}:\n\t>>".format(len(tasks)+1)) 
            if task == "":
                end = True
            else:
                tasks.append("  - {}\n".format(task))
        if datetime.now()<mdt:
            tasks.append("<!---$TASKLIST:{}:{},{}$-->".format(datetime2markerParameter(mdt), matin_or_aprem, len(tasks) == 0 and isEmpty))
    return "".join(tasks)

def auto_git_commit(mdt, *args):
    ok = input("Auto commit, make sur you have not add changes yet >>[y,N] ")
    if ok == "y":
        r = os.system("cd {} && git reset && git add {} && git commit -m \"Update carnet_de_bord.md (auto commit {})\ && git push".format(GIT_ROOT, CdB_PATH, mdt.strftime("%D")))
        print("commit done : {}".format("SUCCES" if r == 0 else "/!\\ FAIL /!\\"))
    else:
        print("Abort commit")
# Marqueurs de champ a remplir, heure a partir de laquel ils doivent être rempli et fonction de remplissage
MARKERS_CdB = {"DATE": (0, get_formated_date),
               "STARTHOUR": (0, get_start_hour),
               "OPTIONALWEEK": (0, get_optional_week),
               "ENDHOUR": (18, get_end_hour),
               "BRUNCHDURATION": (11, get_bruch_duration),
               "TOTALDAY": (18, compute_total_day),
               "TASKLIST": (0, get_tasks),
               "COMMITPUSH": (0, auto_git_commit),
               "RESTARTANALYSE": (0, None), 

}


def fill_file(dt:datetime, filename, marker_filter=None):
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
                    elif ((marker_filter is None and (dt.hour > MARKERS_CdB[marker][0] or marker_date < cdt))
                        or (marker_filter is not None and marker in marker_filter)):
                        r = MARKERS_CdB[marker][1](marker_date, line, *params)
                    # Replace the marker with function result
                    if r is None:
                        unfilled_marker.append((marker,marker_date))
                    else:
                        line = line[: i_start] + r + line[i_end + len(MARKER_END):]
                    # find next tag <!--- ... -->
                    i_start = line.find(MARKER_START, i_end)
                    i_end = line.find(MARKER_END, i_start)   
            sdata = line + sdata
        with open(filename, "w") as outdata:  
            outdata.write(sdata) 
    return unfilled_marker


def datetime2markerParameter(marker_dt:datetime):
    return marker_dt.strftime("%Y/%m/%d")


def add_new_day(mdt:datetime, filename:str):
    """Add a copy of the template a the end of the file, replacing all {0} parameters by the given date"""
    with open(filename, "a") as data:
        data.write(template_CdB_day.format(datetime2markerParameter(mdt)))


def hour_op(t1:time.struct_time, t2:time.struct_time, difference=False):
    dh = t1.tm_hour + (- t2.tm_hour if difference else t2.tm_hour)
    dm = t1.tm_min + (- t2.tm_min if difference else t2.tm_min)
    if dm < 0:
        dm += 60
        dh -= 1
    elif dm >= 60:
        dm -= 60
        dh += 1
    return time.strptime("{} {}".format(dh,dm), "%H %M")


def find_last_day(filename:str):
    last_date = None
    with open(filename, "r") as lines:
        for line in lines:
            if line.startswith("### `"):
                i1 = line.find("`")
                i2 = line.find("`",i1+1)
                cdate = datetime.strptime(line[i1+1:i2]) 
                if last_date is None or last_date < cdate:
                    last_date = cdate
    return cdate


def isDayCreated(cdt:datetime, filename:str):
    current_date = datetime.strptime(cdt.strftime("%D"),"%m/%d/%y")
    with open(filename, "r") as lines:
        for line in lines:
            if line.startswith("###  `"):
                i1 = line.find("`")
                i2 = line.find("`",i1+1)
                cdate = datetime.strptime(line[i1+1:i2], "%A %m/%d/%y") 
                if cdate == current_date:
                    return True
    return False

notes = { 'c':1898, 'd':1690, 'e':1500, 'f':1420, 'g':1265, 'x':1194, 'a':1126, 'z':1063, 'b':1001, 'C':947, 'y':893, 'D':843, 'w':795, 'E':749, 'F':710, 'q':668, 'G':630, 'i':594 };
note_duration = 200

def alarm():
    for n in "Cbzaaa":
        if not n ==" ":
            winsound.Beep(notes[n], note_duration)
        else:
            time.sleep(note_duration/1000)


if __name__ == "__main__":
    # récupération de la journée
    today = datetime.now()
    if not isDayCreated(today, CdB_PATH):
        add_new_day(today, CdB_PATH)
    remaining_markers = fill_file(today, CdB_PATH) 
    user_response = ""
    while not user_response == "exit":
        print("Terminé, action possibles:\n\texit)\tEnd the script")
        print(" )\tRe-read the file")
        print("\tcommit)\tCommit and push change on CdB")
        for k,m in enumerate(remaining_markers):
            print("\t{})\t{} \t{}".format(k,m[0], "" if m[1] is None else (m[1].strftime("%D"))))
        user_response = input(">>")
        if user_response.isdigit():
            i = int(user_response)
            print("selected",remaining_markers[i][0]) 
            if (i>=1 and i<len(remaining_markers)):
                remaining_markers = fill_file(datetime.now(), CdB_PATH, [remaining_markers[i][0]])
        if user_response == "":
            remaining_markers = fill_file(datetime.now(), CdB_PATH, None)
        if user_response == "commit":
            auto_git_commit(datetime.now())

