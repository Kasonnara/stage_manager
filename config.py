import time
from datetime import datetime, timedelta

GIT_ROOT = "PATH/TO/YOUR/CLONE/OF/stage_manager"
CdB_PATH = "PATH/TO/THE/MARKDOWN/FILE/TO/STORE/LOGS/carnet-de-bord.md"
STAGE_START_DATE = datetime(YEAR, MONTH, DAY)
DAY_COTA = time.strptime("07h00", "%Hh%M")
"""Expected hours per day"""
START_DELAY = timedelta(minutes=5)
"""time to remove when automatically filling start hour in the morning. Corresponds approximately to the time needed to start the pc and boot the script"""


METADAT_SHELVE_PATH = "./metadata"
"""Path to a shevle file to store data between reboots of the script. Can be anywhere. (not in /tmp as you must keep this data between reboots)"""
HEARTBIT_SHELVE_KEY = "./LAST_HEARTBIT_DATETIME"
"""Path to a file to store last heart beat time. Can be anywhere. (not in /tmp as you must keep this data between reboots)"""
HEARTBIT_TOUCH_DELAY = 5*60  # in seconds
"""Delay between heartbeats. This will define the precision of the automatic filling of end of day hour"""
KEEP_UPTIME_HISTORY = True


MARKER_START, MARKER_END = "<!---$", "$-->"
template_CdB_day = """
<!---$OPTIONALWEEK:{0}:$-->
###  `<!---$DATE:{0}:$-->` (<!---$STARTHOUR:{0}$--> -> <!---$ENDHOUR:{0}:$--> <!---$BRUNCHDURATION:{0}:$--> midi) total <!---$TOTALDAY:{0}:$-->

- Matin:
<!---$TASKLIST:{0}:matin,True$-->
- Aprem:
<!---$TASKLISTPM:{0}:aprem,True$-->
"""
