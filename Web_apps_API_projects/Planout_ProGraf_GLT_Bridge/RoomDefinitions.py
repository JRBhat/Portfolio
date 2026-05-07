

from typing import Optional, Generator

class RoomDefinitions(object):
    """Hält Raumcapabilities und Übersetzungsschicht"""

    def __init__(self):
        #capabilities: H: heating, C: cooling, F:Feuchtigkeit, V: Volumenstrom
        self.roomdict={
            'Luna1' : {         'GLTNAME' : 'LUNA U 1', 'PLANOUTNAME' : 'Luna R1 (-255)', 'RES_ID' : 51, 'CAPABILITIES' : 'HC' },
            'Luna1A' : {        'GLTNAME' : 'LUNA U 1a', 'PLANOUTNAME' : 'Luna R1A (-256)', 'RES_ID' : 485, 'CAPABILITIES' : 'HC' },
            'Luna2' : {         'GLTNAME' : 'LUNA U 2', 'PLANOUTNAME' : 'Luna R2 (-224)', 'RES_ID' : 53, 'CAPABILITIES' : 'HC' },
            'Luna2A' : {        'GLTNAME' : 'LUNA U 2a', 'PLANOUTNAME' : 'Luna R2a (-257)', 'RES_ID' : 523, 'CAPABILITIES' : 'HC' },
            'Luna34' : {        'GLTNAME' : 'LUNA U 3+4', 'PLANOUTNAME' : 'Luna R3/4 (-291)', 'RES_ID' : 88, 'CAPABILITIES' : 'HCF' },
            'Luna5' : {         'GLTNAME' : 'LUNA U 5', 'PLANOUTNAME' : 'Luna R5 (-46)', 'RES_ID' : 90, 'CAPABILITIES' : 'HCF' },
            'Luna67' : {        'GLTNAME' : 'LUNA U 6+7', 'PLANOUTNAME' : 'Luna R6/7 (-267)', 'RES_ID' : 55, 'CAPABILITIES' : 'HCF' },
            'Luna8' : {         'GLTNAME' : 'LUNA U 8', 'PLANOUTNAME' : 'Luna R8 (-218)', 'RES_ID' : 87, 'CAPABILITIES' : 'HCF' },
            'Luna9' : {         'GLTNAME' : 'LUNA U 9', 'PLANOUTNAME' : 'Luna R9 Fotoraum (-72)', 'RES_ID' : 524, 'CAPABILITIES' : 'HCF' },
            'Luna10' : {        'GLTNAME' : 'LUNA U 10', 'PLANOUTNAME' : 'Luna R10 (-214)', 'RES_ID' : 92, 'CAPABILITIES' : 'HC' },
            'Luna11' : {        'GLTNAME' : 'LUNA U 11', 'PLANOUTNAME' : None, 'RES_ID' : None, 'CAPABILITIES' : 'HC' },
            'LunaFlur1' : {     'GLTNAME' : 'LUNA Flur 1', 'PLANOUTNAME' : None, 'RES_ID' : None, 'CAPABILITIES' : 'HC' },
            'LunaFlur3' : {     'GLTNAME' : 'LUNA Flur 3', 'PLANOUTNAME' : None, 'RES_ID' : None, 'CAPABILITIES' : 'H' },
            'Solaris1' : {      'GLTNAME' : 'SOLARIS U 1 (Vorraum Hotroom)', 'PLANOUTNAME' : 'Solaris R 1 Vorraum 314', 'RES_ID' : 459, 'CAPABILITIES' : 'HC' },
            'Solaris2' : {      'GLTNAME' : 'SOLARIS U 2 (Hotroom)', 'PLANOUTNAME' : 'Solaris R 2 Hotroom', 'RES_ID' : 460, 'CAPABILITIES' : 'HCFV' },
            'Solaris3' : {      'GLTNAME' : None, 'PLANOUTNAME' : 'Solaris R 3 Aerosol+L 74', 'RES_ID' : 461, 'CAPABILITIES' : '' },
            'Solaris4' : {      'GLTNAME' : 'SOLARIS U 4 (Sonne)', 'PLANOUTNAME' : None, 'RES_ID' : None, 'CAPABILITIES' : 'HC' },
            'Solaris4Umkleide' : { 'GLTNAME' : 'SOLARIS U 4 Umkleide (Sonne)', 'PLANOUTNAME' : None, 'RES_ID' : None, 'CAPABILITIES' : 'H' },
            'Solaris4A' : {     'GLTNAME' : 'SOLARIS U 4a (Whirlpool)', 'PLANOUTNAME' : None, 'RES_ID' : None, 'CAPABILITIES' : 'HC' },
            'Solaris5' : {      'GLTNAME' : 'SOLARIS U 5', 'PLANOUTNAME' : 'Solaris R 5 Patch+L 234', 'RES_ID' : 463, 'CAPABILITIES' : 'HC' },
            'Solaris6' : {      'GLTNAME' : 'SOLARIS U 6', 'PLANOUTNAME' : 'Solaris R 6 Patch 215', 'RES_ID' : 464, 'CAPABILITIES' : 'HC' },
            'Solaris7' : {      'GLTNAME' : 'SOLARIS U 7', 'PLANOUTNAME' : 'Solaris R 7 -367', 'RES_ID' : 465, 'CAPABILITIES' : 'HC' },
            'Solaris8' : {      'GLTNAME' : 'SOLARIS U 8', 'PLANOUTNAME' : 'Solaris R 8+L -368', 'RES_ID' : 466, 'CAPABILITIES' : 'HC' },
            'Solaris9' : {      'GLTNAME' : 'SOLARIS U 9 (Sauna)', 'PLANOUTNAME' : 'Solaris R 9 Sauna 73', 'RES_ID' : 467, 'CAPABILITIES' : 'HC' },
            'SolarisEmpfang' : { 'GLTNAME' : 'SOLARIS Empfang', 'PLANOUTNAME' : None, 'RES_ID' : None, 'CAPABILITIES' : 'HC' },
            'SolarisWartebereichVorne' : { 'GLTNAME' : 'SOLARIS vorderer Wartebereich', 'PLANOUTNAME' : None, 'RES_ID' : 51, 'CAPABILITIES' : 'HC' }
        }

        #TODO: Groups? Hotroom aktiviert Solaris Empfang und Wartebereich, Luna67 aktiviert Flur3 (warum auch immer)

    def translateCanonicalToGLT(self, canonicalKey: str) -> str:
        try:
            return self.roomdict[str(canonicalKey)]['GLTNAME'] #can be None
        except:
            print("unknown canonicalKey "+str(canonicalKey))
            raise LookupError

    def translateCanonicalToPlanout(self, canonicalKey: str) -> str:
        try:
            return self.roomdict[str(canonicalKey)]['PLANOUTNAME'] #can be None
        except:
            print("unknown canonicalKey "+str(canonicalKey))
            raise LookupError

    def getCanonicalKey(self, gltOrPlanoutName: str) -> str:
        for entry in self.roomdict.keys():
            if gltOrPlanoutName == self.roomdict[entry]['GLTNAME'] or gltOrPlanoutName == self.roomdict[entry]['PLANOUTNAME']:
                return entry
        print("unknown gltOrPlanoutName "+str(gltOrPlanoutName))
        raise LookupError

    def getCanonicalKeyFromRES_ID(self, RES_ID: int) -> str:
        for entry in self.roomdict.keys():
            if RES_ID == self.roomdict[entry]['RES_ID']:
                return entry
        print("unknown RES_ID "+str(RES_ID))
        raise LookupError

    def isValidGLTName(self, gltName: str) -> str:
        for entry in self.roomdict.keys():
            if gltName == self.roomdict[entry]['GLTNAME'] and gltName != "None":
                return True
        return False

    def getGLTNameList(self) -> Generator[str, None, None]:                       
        for entry in self.roomdict.keys():
            yield self.roomdict[entry]['GLTNAME']

    def generateRoomSettings(self, canonicalName: str, temperatur: float, feuchte: float, betriebsart: Optional[int] = None) -> None:
        if canonicalName == 'Solaris2': #special case hotroom, bc of betriebsmodi 0,1,2,3,4
            if temperatur <= 28: # not hotroom/superhotroom:
                if feuchte != None:
                    return {'betriebszustand':3,
                            'sollwertTemp' : temperatur,  #°C
                            'hystereseTemp': 0.2,   #+-0.1°C
                            'sollwertFeuchte': feuchte,         #r.F
                            'hystereseFeuchte': 2,     #+-1%
                            'volumenstrom' : 1000,     #m/s         #eigentlich 500m/s aber wegen Corona hochgesetzt! TODO
                            'vorlaufzeit': 1.5 }        #h
                else: #feuchte egal
                    return {'betriebszustand':3,
                            'sollwertTemp' : temperatur,  #°C
                            'hystereseTemp': 0.2,   #+-0.1°C
                            'sollwertFeuchte': 50,              #r.F
                            'hystereseFeuchte': 50,     #+-25%
                            'volumenstrom' : 1000,     #m/s
                            'vorlaufzeit': 1.5 }        #h
            elif temperatur < 40: # hotroom FDA
                return {'betriebszustand':2,
                        'sollwertTemp' : temperatur,  #°C
                        'hystereseTemp': 0.2,   #+-0.1°C
                        'sollwertFeuchte': feuchte,         #r.F
                        'hystereseFeuchte': 2,     #+-1%
                        'volumenstrom' : 1000,      #m/s
                        'vorlaufzeit': 2 }          #h
            elif temperatur < 43: # hotroom BDF
                return {'betriebszustand':1,
                        'sollwertTemp' : temperatur,  #°C
                        'hystereseTemp': 0.2,   #+-0.1°C
                        'sollwertFeuchte': feuchte,         #r.F
                        'hystereseFeuchte': 2,     #+-1%
                        'volumenstrom' : 1000,      #m/s
                        'vorlaufzeit': 2 }          #h
            elif temperatur <= 56: # superhotroom
                return {'betriebszustand':4,
                        'sollwertTemp' : temperatur,  #°C
                        'hystereseTemp': 0.2,   #+-0.1°C
                        'sollwertFeuchte': feuchte,         #r.F
                        'hystereseFeuchte': 2,     #+-1%
                        'volumenstrom' : 1000,      #m/s
                        'vorlaufzeit': 8 }          #h
            else:
                raise ValueError("Hotroom temperature setting too high")


            # if (betriebsart is None) or (betriebsart == 4):
            #     if feuchte != None:
            #         return {'betriebszustand':4,
            #                 'sollwertTemp' : temperatur,  #°C
            #                 'hystereseTemp': 0.2,   #+-0.1°C
            #                 'sollwertFeuchte': feuchte,         #r.F
            #                 'hystereseFeuchte': 2,     #+-1%
            #                 'volumenstrom' : 1000,     #m/s         #eigentlich 500m/s aber wegen Corona hochgesetzt! TODO
            #                 'vorlaufzeit': 2 }        #h
            #     else: #feuchte egal
            #         return {'betriebszustand':4,
            #                 'sollwertTemp' : temperatur,  #°C
            #                 'hystereseTemp': 0.2,   #+-0.1°C
            #                 'sollwertFeuchte': 50,              #r.F
            #                 'hystereseFeuchte': 50,     #+-25%
            #                 'volumenstrom' : 1000,     #m/s
            #                 'vorlaufzeit': 2 }        #h
            # elif betriebsart>0:
            #     return {'betriebszustand':betriebsart,
            #             'sollwertTemp' : temperatur,  #°C
            #             'hystereseTemp': 0.2,   #+-0.1°C
            #             'sollwertFeuchte': feuchte,         #r.F
            #             'hystereseFeuchte': 2,     #+-1%
            #             'volumenstrom' : 1000,      #m/s
            #             'vorlaufzeit': 3 }
            # else:
            #     raise ValueError("Hotroom temperature setting unknown")
        #override: Saunaroom generates 25°C by default!!
        elif canonicalName == 'Solaris9': #special case saunaraum = Temp 25°C:
            temperatur = 25.0

        #default return klimaroom
        if feuchte != None:
            if 'F' not in self.roomdict[canonicalName]['CAPABILITIES']:
                raise ValueError('room ' +canonicalName + ' is not capable of Feuchtigkeitseinstellung')
            return {'betriebszustand':1,
                    'sollwertTemp' : temperatur,  #°C
                    'hystereseTemp': 0.2,   #+-0.1°C
                    'sollwertFeuchte': feuchte,         #r.F
                    'hystereseFeuchte': 2,     #+-2%
                    'volumenstrom' : 0,         #m/s  #kann keinen Volumenstrom regeln
                    'vorlaufzeit': 1.5 }        #h
        else: #Feuchte egal
            return {'betriebszustand':1,
                    'sollwertTemp' : temperatur,  #°C
                    'hystereseTemp': 0.2,   #+-0.1°C
                    'sollwertFeuchte': 50,              #r.F
                    'hystereseFeuchte': 50,     #+-25%
                    'volumenstrom' : 0,         #m/s  #kann keinen Volumenstrom regeln
                    'vorlaufzeit': 1.5 }        #h
            

    def generateBestEffortRoomSettings(self, canonicalName: str, temperatur: float, feuchte: float, betriebsart: Optional[int] = None):
        #same as generateRoomSettings, but does not raise exceptions, instead gives best effort values
        try:
            return self.generateRoomSettings(canonicalName,temperatur,feuchte, betriebsart)
        except ValueError as e:
            if canonicalName == 'Solaris2':
                #superhotroom fallback ... temp is set over 56°C ... alert has been raised, so return superhotroomsetting
                return {'betriebszustand':4,
                        'sollwertTemp' : temperatur,  #°C
                        'hystereseTemp': 2,   #+-1°C
                        'sollwertFeuchte': feuchte,         #r.F
                        'hystereseFeuchte': 4,      #+-2%
                        'volumenstrom' : 1000,      #m/s
                        'vorlaufzeit': 8 }          #h
            else: #Feuchte egal, weil kein echter Klimaraum, alert has been raised at this point
                return {'betriebszustand':1,
                        'sollwertTemp' : temperatur,  #°C
                        'hystereseTemp': 1,   #+-0.5°C
                        'sollwertFeuchte': 50,              #r.F
                        'hystereseFeuchte': 50,     #+-25%
                        'volumenstrom' : 0,         #m/s  #kann keinen Volumenstrom regeln
                        'vorlaufzeit': 1.5 }        #h
