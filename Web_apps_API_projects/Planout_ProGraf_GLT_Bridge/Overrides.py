import sqlite3, datetime, hashlib

import RoomDefinitions

class Overrides(object):
    """This class logs and retrieves overrides over planned roombookings in planout.
    It gives an GUI to alter entries coming from planout before beeing sent to the glt"""

    def __init__(self, sqllite3file='overrides.sqlite3'):
        self.sqllite3file = sqllite3file
        con = sqlite3.connect(self.sqllite3file, detect_types=sqlite3.PARSE_DECLTYPES) #add type conversion
        con.row_factory = sqlite3.Row # allow results to be accessed like a dict
        cur = con.cursor()
        # initialize database if new file:
        cur.execute('''CREATE TABLE IF NOT EXISTS overrides 
                    (hash TEXT PRIMARY KEY, 
                    gltname TEXT,
                    startzeit DATETIME, 
                    endzeit DATETIME, 
                    betriebszustand INTEGER, 
                    sollwertTemp REAL, 
                    hystereseTemp REAL, 
                    sollwertFeuchte REAL, 
                    hystereseFeuchte REAL, 
                    volumenstrom INTEGER,
                    vorlaufzeit REAL)''')
        con.commit()
        con.close()

    #TODO: This somehow does not work with roomnames "luna r 3+4" when coming from HTML, as the + is used to glue strings togeher...
    def insertOverride(self, gltname:str, startzeit:datetime.datetime, endzeit:datetime.datetime, betriebszustand:int, sollwertTemp:float, hystereseTemp:float, sollwertFeuchte:float, hystereseFeuchte:float, volumenstrom:int, vorlaufzeit:float):        
        if not RoomDefinitions.RoomDefinitions().isValidGLTName(gltname):
            return ("gltname="+str(gltname)+" is not a valid glt room name")

        if startzeit-datetime.datetime(year=datetime.datetime.today().year, month=datetime.datetime.today().month, day=datetime.datetime.today().day, hour=0, minute=0, second=0) >= datetime.timedelta(days=15):
            return ("startzeit="+str(startzeit)+" cannot be further than 14 days into the future")

        if endzeit-startzeit >= datetime.timedelta(hours=24):
            return ("startzeit="+str(startzeit)+"and endzeit="+str(startzeit)+" should not be longer than 24h apart")

        for entry in (betriebszustand, sollwertTemp, hystereseTemp, sollwertFeuchte, hystereseFeuchte, volumenstrom, vorlaufzeit):
            try:
                float(entry)
            except ValueError:
                return "The following entry could not be converted to a number: " + str(entry)
        
        con = sqlite3.connect(self.sqllite3file, detect_types=sqlite3.PARSE_DECLTYPES) #add type conversion
        con.row_factory = sqlite3.Row # allow results to be accessed like a dict
        cur = con.cursor()
        cur.execute('''INSERT OR REPLACE INTO overrides 
                    (hash, 
                    gltname,
                    startzeit, 
                    endzeit, 
                    betriebszustand, 
                    sollwertTemp, 
                    hystereseTemp, 
                    sollwertFeuchte, 
                    hystereseFeuchte, 
                    volumenstrom,
                    vorlaufzeit)
                    
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                   (self.getHash(gltname,startzeit),
                    gltname,
                    startzeit,
                    endzeit,
                    betriebszustand,
                    sollwertTemp,
                    hystereseTemp,
                    sollwertFeuchte,
                    hystereseFeuchte,
                    volumenstrom,
                    vorlaufzeit
                       ) )
        con.commit()
        con.close()
        return True

    def removeOverrideByHash(self, hashstr:str):
        print(hashstr)
        con = sqlite3.connect(self.sqllite3file, detect_types=sqlite3.PARSE_DECLTYPES) #add type conversion
        con.row_factory = sqlite3.Row # allow results to be accessed like a dict
        cur = con.cursor()
        cur.execute('DELETE FROM overrides WHERE hash=?',
                   (str(hashstr),) )
        con.commit()
        con.close()
        if cur.rowcount == 1:
            return True #success
        elif cur.rowcount == 0:
            return False #notfound
        else:
            raise sqlite3.DatabaseError("UNIQUE VALUE IS NOT UNIQUE!")
        

    def removeOverride(self, gltname:str, startzeit:datetime.datetime):
        return self.removeOverrideByHash(self.getHash(gltname,startzeit))


    def getOverrideValues(self, gltname:str, startzeit:datetime.datetime):
        con = sqlite3.connect(self.sqllite3file, detect_types=sqlite3.PARSE_DECLTYPES) #add type conversion
        con.row_factory = sqlite3.Row # allow results to be accessed like a dict
        cursor = con.cursor()
        cursor.execute('SELECT * FROM overrides WHERE hash=?',
                   (self.getHash(gltname,startzeit),) )
        reply = cursor.fetchall()
        con.close()

        if len(reply) == 0:
            return None
        elif len(reply) == 1:
            return dict(reply[0])  
        else:
            raise sqlite3.DatabaseError("UNIQUE VALUE IS NOT UNIQUE!")

    def getAllOverrides(self, dayinterval=15): # dayinterval=15 changed to 15 from 14 days to correctly display all overrides immideatly; earlier it only displayed for 13 day - now 14 days
        con = sqlite3.connect(self.sqllite3file, detect_types=sqlite3.PARSE_DECLTYPES) #add type conversion
        con.row_factory = sqlite3.Row # allow results to be accessed like a dict
        cursor = con.cursor()                                                               #THIS IS USUALLY A BAD IDEA, BUT INTs CANNOT HOLD SQL INJECTIONS
        cursor.execute("SELECT * FROM overrides WHERE startzeit<=date('now','start of day','+"+str(int(dayinterval))+" day') and startzeit>=date('now','start of day') ORDER BY startzeit DESC")

        alloverrides = list()
        for row in cursor.fetchall():
            alloverrides.append(dict(row))
        con.close()
        return alloverrides
        

    def isOverridden(self, gltname:str, startzeit:datetime.datetime):
        reply = self.getOverrideValues(gltname, startzeit)
        if reply == None:
            return False
        else:
            return True
        
    def getHash(self, gltname:str, startzeit:datetime.datetime):
        if str(gltname) != '' and str(startzeit) != '':
            convertedToBytes = bytes(str(gltname) + str(startzeit), 'utf-8') #should be a unique
            return str(hashlib.new('sha256',convertedToBytes).hexdigest())
        else:
            raise ValueError('gltname and startzeit cannot be empty strings for uniqueness')


if __name__ == '__main__':
    instance = Overrides()
    todaystart = datetime.datetime(year=2021, month=6, day=13, hour=8, minute=30, second=0)
    #instance.insertOverride("LUNA U 1", todaystart, todaystart,1,22,2,50,5,0,4)
    #print(instance.isOverridden("testroom", todaystart))
    
    #instance.insertOverride("testroom2", todaystart, todaystart,1,22,2,50,5,0)