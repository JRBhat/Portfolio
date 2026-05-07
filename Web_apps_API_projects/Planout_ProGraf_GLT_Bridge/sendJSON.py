import os
import requests,datetime

import RoomDefinitions,SendEmail

class sendJSON():
    """This class takes room/temp/humidity values, packages them into a JSON object and sends it to the GLT"""

    def __init__(self, GLTURL=None):
        self.GLTURL = GLTURL or os.environ.get("BMS_API_URL", "http://your-bms-server/api/postSetValues")
        self.roomDefinitions = RoomDefinitions.RoomDefinitions() #we need this more often, so we keep a copy around in memory
        self.user=os.environ.get("BMS_API_USER", "api_user")
        self.__password=os.environ.get("BMS_API_PASSWORD", "")
        #TODO: GENERATE SEPARATE USER/PW COMBO! (what capabilities are needed?)


    def generateJSONString(self, GLTroomname: str, timepoint: int, betriebszustand: int, sollwertTemp: float, hystereseTemp: float, sollwertFeuchte: float, hystereseFeuchte: float, volumenstrom: float):
        #all numbers have to be positive:
        for number in (betriebszustand, sollwertTemp, hystereseTemp,sollwertFeuchte,hystereseFeuchte,volumenstrom):
            if number < 0:
                raise ValueError("all values have to be >= 0")

        #timepoint has to be a unix timestamp or a datetime object
        #furthermore only timepoints from yesterday onwards are allowed
        todaymidnight = datetime.datetime(year=datetime.datetime.today().year, month=datetime.datetime.today().month, day=datetime.datetime.today().day, hour=0, minute=0, second=0) 
        if type(timepoint) == datetime.datetime and timepoint >= (todaymidnight-datetime.timedelta(days=1)) :
            timepoint = int(timepoint.timestamp())
        elif type(timepoint) == int and timepoint >= (todaymidnight-datetime.timedelta(days=1)).timestamp():
            pass
        else:
            raise ValueError("timepoint has to be > yesterday and of type unixtimestamp or datetime.datetime")

        #roomname has to be a valid roomname and a string:
        if type(GLTroomname) != str:
            raise ValueError("GLTroomname has to be a string")
        if not self.roomDefinitions.isValidGLTName(GLTroomname):
            raise ValueError("GLTroomname has to be listed in RoomDefinitions GLTNAME")

        return ({"Raumname": GLTroomname, "Schaltzeitpunkt": int(timepoint), "Betriebszustand": int(betriebszustand), "SW Temperatur": round(sollwertTemp,1), "Hysterese Temperatur": round(hystereseTemp,1), "SW Feuchte": round(sollwertFeuchte,1), "Hysterese Feuchte": round(hystereseFeuchte,1), "SW Volumenstrom": round(volumenstrom,1) })

    def prepareJSONList(self, settingslist: list):
        #build a jsonlist, that can be plugged directly into a request. each entry generates two json entries: start and stop
        #the settingslist is expected to be a dictionary coming from PlanoutImport.translatePlanoutListToGLTSettingsAndAddOverrides()
        jsonlist = list()
        for settings in settingslist:
            if int(settings['betriebszustand']) < 0:
                continue # skip generating this setting, a betriebszustand of -1 means it should be ignored
            #starttime
            json = self.generateJSONString(GLTroomname=settings['gltname'],
                                    timepoint=settings['startzeit']-datetime.timedelta(hours=settings['vorlaufzeit']), 
                                    betriebszustand=settings['betriebszustand'], 
                                    sollwertTemp=settings['sollwertTemp'], 
                                    hystereseTemp=settings['hystereseTemp'],
                                    sollwertFeuchte=settings['sollwertFeuchte'], 
                                    hystereseFeuchte=settings['hystereseFeuchte'], 
                                    volumenstrom=settings['volumenstrom'])
            jsonlist.append(json)

            #endtime
            json = self.generateJSONString(GLTroomname=settings['gltname'],
                                    timepoint=settings['endzeit']+datetime.timedelta(minutes=30), #leave runnting for additional hour, aka "feinplanung"
                                    betriebszustand=0, 
                                    sollwertTemp=22, 
                                    hystereseTemp=5,
                                    sollwertFeuchte=50, 
                                    hystereseFeuchte=50, 
                                    volumenstrom=0)
            jsonlist.append(json)

        return jsonlist


    def sendToGLT(self, jsonlist):
        try:
            response = requests.post(self.GLTURL, json=jsonlist, auth=(self.user, self.__password))
            # print("Post blocked for debugging - sendToGLT")
            response.raise_for_status()
            return True
        except requests.exceptions.ConnectionError:
            email = SendEmail.SendEmail()
            email.send("Error connecting to glt-1", "Could not program the next 14 days on GLT-1.\n If this happens once, it probably is of no concern as 13 days into the future are still programmed\nhowever short-notice changes to planout and new overrides cannot take effect")
            return "Cannot connect to GLT REST API"


    #remove everything from GLT by sending an empty list
    def clearGLT(self):
        try:
            response = requests.post(self.GLTURL, json=list(), auth=(self.user, self.__password))
            response.raise_for_status()
            # print("Post blocked for debugging - clearGLT")
            
            return True
        except requests.exceptions.ConnectionError:
            return "Cannot connect to GLT REST API"


    def _testsend(self):
        import time
        currenttime=int(time.time() + 120) #+2min
        #jsonstr=[({"Raumname": "LUNA U 9", "Schaltzeitpunkt": currenttime, "Betriebszustand": True, "SW Temperatur": 22.0, "Hysterese Temperatur": 1.5, "SW Feuchte": 50.00001, "Hysterese Feuchte": 5.0, "SW Volumenstrom": 0 }),({"Raumname": "LUNA U 9", "Schaltzeitpunkt": currenttime+60, "Betriebszustand": 0, "SW Temperatur": 24.0, "Hysterese Temperatur": 5.0, "SW Feuchte": 50.0, "Hysterese Feuchte": 50, "SW Volumenstrom": 0 })]
        jsonstr=list()
        #, headers={"Content-Type":"text/csv"}
        # response = requests.post(self.GLTURL, json=jsonstr, auth=(self.user, self.__password))
        print("Testing Post blocked for debugging - testsend")
        # print(response.request.body)
        # print(response.url)
        # return response


if __name__ == '__main__':
    instance = sendJSON()
    instance._testsend()
    #import datetime
    #todaystart = datetime.datetime(year=datetime.datetime.today().year, month=datetime.datetime.today().month, day=datetime.datetime.today().day, hour=8, minute=30, second=0)
    #todaystop = datetime.datetime(year=datetime.datetime.today().year, month=datetime.datetime.today().month, day=datetime.datetime.today().day, hour=17, minute=00, second=0)
    #todayintwominutes = datetime.datetime.today() + datetime.timedelta(minutes=2)
    #instance.sendToGLT(instance.translatePlanoutList([{'RESSOURCE': 'Luna R9 Fotoraum (-72)', 'TEMPFEUCHTE': None, 'MIN(STARTDATUM)': todaystart, 'MAX(ENDEDATUM)': todaystop, 'COUNT(RESSOURCE)': 1, 'RES_ID': 88, 'TEMPERATUR': '22.0', 'FEUCHTE': '50.0'}]))
