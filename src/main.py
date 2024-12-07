import csv
from enum import Enum
from typing import List
from datetime import datetime, timedelta

def is_similar_time(time_str1, time_str2):
    # Convert strings to datetime objects
    time1 = datetime.strptime(time_str1, "%H:%M")
    time2 = datetime.strptime(time_str2, "%H:%M")
    
    # Calculate difference
    diff = abs(time1 - time2)
    
    # If times are same, return True
    if diff == timedelta(0):
        return True
    
    # Check if difference is <= 3 minutes
    return diff <= timedelta(minutes=3)

EMPTY_CITI = ["","","","","",""]
EMPTY_SIDERA = ["","","","","",]

# CameraName ;IncType    ;IncType                    ;TEXTO AÑOS;TEXTO HORAS

class MatchState(Enum):
    IDENTICAL = 1
    SIMILAR = 2
    DIFFERENT = 3

class Log:
    raw: List
    camera_id: str
    desc: str
    year: str
    hour: str
    is_citi: bool

    def __init__(self, line: List, is_citi: bool):
        self.is_citi = is_citi
        self.raw = line
        self.camera_id = line[0]
        if is_citi:
            self.desc = line[3]
            self.year = line[4]
            self.hour = line[5]
        else:
            self.desc = line[1]
            self.year = line[3]
            self.hour = line[5]

    def __str__(self):
        return_str: str = self.camera_id + self.desc + self.year + self.hour + str(self.is_citi)
        return return_str

    def compare(self, other) -> MatchState:
        if self.camera_id != other.camera_id:
            return MatchState.DIFFERENT

        if self.year != other.year:
            return MatchState.DIFFERENT

        if self.hour == other.hour:
            return MatchState.IDENTICAL

        if is_similar_time(self.hour, other.hour):
            return MatchState.SIMILAR
        else:
            return MatchState.DIFFERENT


class TrafficEvent:
    citi_logs: List[Log]
    sidera_logs: List[Log]

    def __init__(self, log: Log):
        self.citi_logs = []
        self.sidera_logs = []
        if log.is_citi:
            self.citi_logs.append(log)
        else:
            self.sidera_logs.append(log)

    def add_if_same(self, log: Log) -> bool:
        is_citi = len(self.citi_logs) != 0 and self.citi_logs[0].compare(log) != MatchState.DIFFERENT
        is_sidera = len(self.sidera_logs) != 0 and self.sidera_logs[0].compare(log) != MatchState.DIFFERENT
        if is_citi and is_sidera:
            return False
        if log.is_citi:
            self.citi_logs.append(log)
        else:
            self.sidera_logs.append(log)
        return True


    def title(self):
        if len(self.citi_logs) == 0 or len(self.sidera_logs) == 0:
            return "no coincide"
        if len(self.citi_logs) > len(self.sidera_logs):
            return "repetido citi"
        elif len(self.citi_logs) < len(self.sidera_logs):
            return "repetido sidera"

        match_state = self.citi_logs[0].compare(self.sidera_logs[0])

        if match_state == MatchState.IDENTICAL:
            return "coincide"
        else:
            return "coincide diff horas"

    def return_list(self) -> List:
        return_list = []

        cached_title = self.title()

        max_length = max(len(self.citi_logs), len(self.sidera_logs))

        sidera_output = []
        for log in self.sidera_logs:
            sidera_output.append(log.raw)

        citi_output = []
        for log in self.citi_logs:
            citi_output.append(log.raw)

        citi_padded = citi_output + EMPTY_CITI * (max_length - len(citi_output))
        sidera_padded = citi_output + EMPTY_SIDERA * (max_length - len(sidera_output))

        for citi_log, sidera_log in zip(citi_padded, sidera_padded):
            return_list.append(citi_log + sidera_log + [cached_title])

        return return_list



def compare_files(citi_path: str, sidera_path: str):

    print("comparing")
    citi_log_file: list
    sidera_log_file: list

    with open(citi_path, encoding='iso-8859-1') as citi_raw:  # or 'latin1'
        citi_log_file = list(csv.reader(citi_raw, delimiter=';'))  # Note the semicolon delimiter
    
    with open(sidera_path, encoding='iso-8859-1') as sidera_raw:
        sidera_log_file = list(csv.reader(sidera_raw, delimiter=';'))

    citi_logs: list = []
    sidera_logs: list = []
    events: list = []

    for line in citi_log_file:
        citi_logs.append(Log(line, True))

    for line in sidera_log_file:
        sidera_logs.append(Log(line, False))

    return_list = []

    for citi_log in citi_logs[1:]:
        match_found: bool = False
        for event in events:
            if event.add_if_same(citi_log):
                match_found = True

        if match_found == False: 
            events.append(TrafficEvent(citi_log))

    for sidera_log in sidera_logs[1:]:
        match_found: bool = False
        for event in events:
            if event.add_if_same(sidera_log):
                match_found = True

        if match_found == False: 
            events.append(TrafficEvent(sidera_log))


    return_list.append(["CITILOG","","","","","","SIDERA","","","","",""])
    return_list.append(["CameraName","Start","IncType","TEXTO AÑOS", "Equipo", "esc. variable", "Fecha", "TEXTO AÑOS", "TEXTO SEGUNDOS", "ESTADO"])
    for event in events:
        return_list.append(event.return_list())

    with open("output.csv", 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(return_list)

if __name__ == "__main__":
    sidera_path = "./sidera.csv"
    citi_path = "./citi.csv"
    compare_files(citi_path, sidera_path)

# Sidera
# Equipo    ;Desc. variable                                 ;Fecha                  ;TEXTO AÑOS;TEXTO HORAS ;TEXTO SEGUNDOS
# 03FL02TV01;Alarma de vehículo parado con tráfico fluido   ;22-11-2024 00:37:19.19 ;22-11-2024;00:37       ;19.19

# Citi
# CameraName ;Start          ;IncType    ;IncType                    ;TEXTO AÑOS;TEXTO HORAS
# 03FL02TV01 ;22/11/2024 0:37;Pedestrian ;Alarma de peatón en calzada;22-11-2024;00:37

# A y B
# Is identical
# Is identical with time difference
# Is different

# log A
# Has identical
# has identical with time difference
# has no matches


# CITILOG                                                                                                      SIDERA                        
# CameraName      Start   IncType       IncType                        TEXTO AÑOS    TEXTO HORAS               Equipo                esc. variable                 Fecha                     TEXTO AÑOS    TEXTO HORAS    TEXTO SEGUNDOS    ESTADO
# ?    21/11/2024 3:04    Pedestrian    Alarma de peatón en calzada    21-11-2024    03:04                             03FL02TV01    Alarma de baja visibilidad    21-11-2024 23:13:58.58    21-11-2024    23:13    58.58                   COINCIDE
# ?    21/11/2024 3:07    StopF         Alarma de vehículo parado con tráfico fluido    21-11-2024    03:07            03FL02TV01    Alarma de vehículo parado     21-11-2024 23:14:18.18    21-11-2024    23:14    18.18                   COINCIDE NO HORA
# ?    21/11/2024 3:55    Visibility    Alarma de baja visibilidad por humo    21-11-2024    03:55                     03FL02TV01    Alarma de peatón en calzada   22-11-2024 00:37:05.05    22-11-2024    00:37    05.05                   NO COINCIDE
# ?    21/11/2024 5:30    Visibility    Alarma de baja visibilidad por humo    21-11-2024    05:30                     03FL02TV01    Alarma de vehículo parado     22-11-2024 00:37:19.19    22-11-2024    00:37    19.19    
# ?    21/11/2024 6:35    Visibility    Alarma de baja visibilidad por humo    21-11-2024    06:35                     03FL02TV01    Alarma de vehículo parado     23-11-2024 03:20:46.46    23-11-2024    03:20    46.46    
# ?    21/11/2024 8:30    StopC         Alarma de vehículo parado con tráfico con congestión    21-11-2024    08:30    03FL02TV01    Alarma de baja visibilidad    23-11-2024 04:59:27.27    23-11-2024    04:59    27.27

