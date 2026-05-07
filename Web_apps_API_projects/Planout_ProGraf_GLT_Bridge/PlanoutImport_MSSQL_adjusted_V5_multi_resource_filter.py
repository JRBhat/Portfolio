
import logging
import os
import sys
import datetime
import pyodbc
from datetime import timedelta
import RoomDefinitions, Overrides, SendEmail

"""Connects to a SQL database using pyodbc."""

SERVER = os.environ.get("DB_SERVER", "localhost")
DATABASE = os.environ.get("DB_NAME", "scheduling_db")
USERNAME = os.environ.get("DB_USERNAME", "db_user")
PASSWORD = os.environ.get("DB_PASSWORD", "")


# Load query from file
def load_sql_query(filename):
    with open(filename, 'r') as file:
        return file.read()
    
class PlanoutImport(object):
    """Importiert Daten aus einer SQL Abfrage"""

    def __init__(self, url=None):
        self.url = url or os.environ.get("DB_URL", "localhost:1521/xe")
        self.server = os.environ.get("DB_SERVER", "localhost")
        self.database = os.environ.get("DB_NAME", "scheduling_db")
        self.username = os.environ.get("DB_USERNAME", "db_user")
        self.__password = os.environ.get("DB_PASSWORD", "")
        self.sendReport = False

        self.connectionString = f'DRIVER={{ODBC Driver 18 for SQL Server}};\
                                    SERVER={self.server};\
                                    DATABASE={self.database};\
                                    UID={self.username};\
                                    PWD={self.__password};\
                                    ENCRYPT=no;TRUST_SERVER_CERTIFICATE=yes; ENCODING="UTF-8"'
        

    def buildview(self) -> None:
        #This only has to be called once per Database/Installation -> Persistent View
        #Do get a line 10 error calling this, so I pushed this via GUI
        with pyodbc.connect(self.connectionString) as connection:
            cur = connection.cursor()
            cur.execute("""create or replace view V_GLT_REPORT as
                select p.Short_name               Projekt
                      ,r.short_name               Ressource
                      ,r.long_name                ResLangName
                      ,t.datestart_target         Datum
                      ,t.duration_target/60       Dauer
                      ,t.datestart_target         StartDatum
                      ,t.dateend_target           EndeDatum
                      ,t.task_comment             Kommentar
                      ,t.short_name               Vorgang
                      ,tr.erp_task_res_key        TempFeuchte
                      ,p.task_id                  PROJECT_ID
                      ,t.task_ID                  
                      ,tr.task_res_id
                      ,r.res_id
                from   T_TASK            p
                join   T_TASK            t  on p.TASK_ID = t.Project_Fk
                join   T_TASK_RES        tr on t.TASK_ID = tr.Task_Fk
                join   T_RES             r  on r.RES_ID  = tr.res_fk
                where p.dispatched = 1
                order  by p.Short_name, t.datestart_target;
            """)

    #region Fetch quickfix  V1 Sei 
    def fetch(self) -> list:
        resultlist = list()
        try:
            resultlist += self.fetchKlima()
            logging.debug("fetch: Klima completed")
            new_list = self.fetchHotroom()
            for x in new_list:
                if x not in resultlist:
                    resultlist.append(x)
            logging.debug("fetch: Hotroom completed")
            new_list = self.fetchBelueftung()
            for x in new_list:
                if x not in resultlist:
                    resultlist.append(x)
            logging.debug("fetch: Belueftung completed")
            return sorted(resultlist, key=lambda k: k['MIN_STARTDATUM'])
        except pyodbc.DatabaseError as e:
            emailErr = SendEmail.SendEmail()
            emailErr.send(subject="ERROR could not connect to planout database!", message=str(e))
            return None
        
        
    def fetchKlima(self) -> list:
        resultlist = list()
        emailtempfeuchteErr = SendEmail.SendEmail()
        try:
            with pyodbc.connect(self.connectionString) as connection:
                # AVAILABLE HEADERS: "PROJEKT, RESSOURCE, RESLANGNAME, DATUM, DAUER, STARTDATUM, ENDEDATUM, KOMMENTAR, VORGANG, TEMPFEUCHTE, PROJECT_ID, TASK_ID, TASK_RES_ID, RES_ID"
                cur = connection.cursor()

                #TODO: Sonne (Solaris R4) is not in planout, and should therefore run via Schaltuhrkanal
       
                #TODO: Check for time overlap, if there are two projects in the same room, at the same date but distinct roomtemp-req
                #cur.execute("select * from V_GLT_REPORT WHERE ((RESLANGNAME LIKE 'Luna Klima%' OR RESLANGNAME='Luna R5 ' OR RESLANGNAME='U 2 Hotroom') AND PROJEKT IN (select PROJEKT from V_GLT_REPORT WHERE RESLANGNAME=' Klima extra') AND (STARTDATUM>=GETDATE() AND STARTDATUM<DATEADD(DAY, 14, GETDATE()))  )")
            
                #Each result should be handled like a 22/50% case, if Raumtemperatur=None (because of Klima Extra device link)
                #this will get me the rooms and start/endtimes without gap, even if there are two different studies booked at the same day for one room.
                #only if there are different Raumtemperatur-Entries for a room and two times, they will produce two separate entries (which is good) 
                # [!TODO: they could however then overlap, so this has to be checked in python]
                #I can however not get the Projektname (Studynr) at the same time, but do not need it for the GLT
                
                #region fetch Klima V1 query
                # cur.execute("select RESSOURCE, TEMPFEUCHTE, MIN(STARTDATUM) AS MIN_STARTDATUM, MAX(ENDEDATUM) AS MAX_ENDEDATUM, COUNT(RESSOURCE) AS COUNT_RESSOURCE, RES_ID from V_GLT_REPORT \
                # WHERE ((\
                # (RESSOURCE LIKE 'Luna %' OR RESSOURCE LIKE 'Solaris %') \
                # AND PROJEKT IN (select PROJEKT from V_GLT_REPORT WHERE (RESLANGNAME=' Klima extra' \
                # OR RESSOURCE LIKE 'AEVA%' \
                # OR RESSOURCE LIKE 'Aquaflux%' \
                # OR RESSOURCE LIKE 'Biozoom%' \
                # OR RESSOURCE LIKE 'Chroma%' \
                # OR RESSOURCE LIKE 'Corneo%' \
                # OR RESSOURCE LIKE 'Cuto%' \
                # OR RESSOURCE LIKE 'Dermatop%' \
                # OR RESSOURCE LIKE 'Epsilon%' \
                # OR RESSOURCE LIKE 'FLPI%' \
                # OR RESSOURCE LIKE 'LC-OCT%' \
                # OR RESSOURCE LIKE 'MPA%' \
                # OR RESSOURCE LIKE 'PH%' \
                # OR RESSOURCE LIKE 'Raman%' \
                # OR RESSOURCE LIKE 'Saugblasen%' \
                # OR RESSOURCE LIKE 'Sebu%' \
                # OR RESSOURCE LIKE 'Spectro%' \
                # OR RESSOURCE LIKE 'SquameScan%' \
                # OR RESSOURCE LIKE 'TSA%' \
                # OR RESSOURCE LIKE 'Tewameter%' \
                # OR RESSOURCE LIKE 'Thermographie%' \
                # OR RESSOURCE LIKE 'Ultraschall%' \
                # OR RESSOURCE LIKE 'Visia%' \
                # OR RESSOURCE LIKE 'Vivascope%' \
                # OR RESSOURCE LIKE 'Zwick%' \
                # ) AND (STARTDATUM>=CONVERT(date,GETDATE()) AND STARTDATUM<DATEADD(DAY, 14, GETDATE()))\
                # ))\
                # AND (STARTDATUM>=CONVERT(date,GETDATE()) AND STARTDATUM<DATEADD(DAY, 14, GETDATE())) AND PROJEKT NOT LIKE '%-35%' ) \
                # GROUP BY CONVERT(date, Datum), RESSOURCE, TEMPFEUCHTE, RES_ID \
                # ORDER BY CONVERT(date, Datum)")
                
                # res = cur.fetchall()
                # endregion
                
                
                
                
                
                #region replacement code fetchKlima V2 query
                # Main execution
                sql_query = load_sql_query('complex_query_fetchKlima.sql')
                
                # Execute parameterized query
                cur.execute(sql_query)
                res = cur.fetchall()
                # with open('output_from_sql_queries/NEWfetchKlima_output.txt', 'w') as f:
                #     print(res, file=f)
                #endregion
                
                columns = [column[0] for column in cur.description]
                results = [dict(zip(columns, row)) for row in res]
                # with open('output_from_sql_queries/fetchKlima_output.txt', 'w') as f:
                #     print(res, file=f)
                    
                for row in results:
                    if row['TEMPFEUCHTE'] == None: # nothing specified, take default values
                        row['TEMPERATUR']='22.0'
                        row['FEUCHTE']='50.0'
                    else: # has a real TempFeuchte Entry but is a freely formatable field, so some regex and sanity checks:
                        try:
                            result= self.splitTempFeuchte(row['TEMPFEUCHTE'])
                            row['TEMPERATUR']=str(result['TEMPERATUR'])
                            row['FEUCHTE']=str(result['FEUCHTE'])
                        except LookupError as e:
                            emailtempfeuchteErr.collectMsg("ERROR DECIPHERING TEMPFEUCHTE, SETTING DEFAULT 22°C/50%: " + str(e) + ' for planoutentry: ' + str(row))
                            row['TEMPERATUR']='22.0'
                            row['FEUCHTE']='50.0'
                    resultlist.append(row)

            if emailtempfeuchteErr.hasCollectedMsg():
                emailtempfeuchteErr.send(subject="ERROR determining Temp/Feuchte please check GLT!", message=emailtempfeuchteErr.collectmsg)

            return sorted(resultlist, key=lambda k: k['MIN_STARTDATUM'])
        except pyodbc.DatabaseError as e:
            #wenn die Liste empty wäre, hätte cron die Einträge auf der GLT überschrieben...upstream den error handlen lassen
            raise e

    def fetchHotroom(self) -> list:
        resultlist = list()
        emailtempfeuchteErr = SendEmail.SendEmail()
        try:
            with pyodbc.connect(self.connectionString) as connection:
                # AVAILABLE HEADERS: "PROJEKT, RESSOURCE, RESLANGNAME, DATUM, DAUER, STARTDATUM, ENDEDATUM, KOMMENTAR, VORGANG, TEMPFEUCHTE, PROJECT_ID, TASK_ID, TASK_RES_ID, RES_ID"
                cur = connection.cursor()
     
                #this will get all Hotrooms (RES_ID=460), without Klima Extra (which would indicate not-hotroom study) and Projektindex -35 (ATH)
                
                #region fetch hotroom query V1 CHoppe
                # cur.execute("select RESSOURCE, TEMPFEUCHTE, MIN(STARTDATUM) \
                # AS MIN_STARTDATUM, MAX(ENDEDATUM) \
                # AS MAX_ENDEDATUM, COUNT(RESSOURCE) \
                # AS COUNT_RESSOURCE, RES_ID, \
                # PROJEKT from V_GLT_REPORT \
                # WHERE ( \
                # (RES_ID=460 AND PROJEKT NOT IN \
                # (select PROJEKT from V_GLT_REPORT WHERE \
                # (RESLANGNAME=' Klima extra' \
                # OR RESSOURCE LIKE 'AEVA%' \
                # OR RESSOURCE LIKE 'Aquaflux%' \
                # OR RESSOURCE LIKE 'Biozoom%' \
                # OR RESSOURCE LIKE 'Chroma%' \
                # OR RESSOURCE LIKE 'Corneo%' \
                # OR RESSOURCE LIKE 'Cuto%' \
                # OR RESSOURCE LIKE 'Dermatop%' \
                # OR RESSOURCE LIKE 'Epsilon%' \
                # OR RESSOURCE LIKE 'FLPI%' \
                # OR RESSOURCE LIKE 'LC-OCT%' \
                # OR RESSOURCE LIKE 'MPA%' \
                # OR RESSOURCE LIKE 'PH%' \
                # OR RESSOURCE LIKE 'Raman%' \
                # OR RESSOURCE LIKE 'Saugblasen%' \
                # OR RESSOURCE LIKE 'Sebu%' \
                # OR RESSOURCE LIKE 'Spectro%' \
                # OR RESSOURCE LIKE 'SquameScan%' \
                # OR RESSOURCE LIKE 'TSA%' \
                # OR RESSOURCE LIKE 'Tewameter%' \
                # OR RESSOURCE LIKE 'Thermographie%' \
                # OR RESSOURCE LIKE 'Ultraschall%' \
                # OR RESSOURCE LIKE 'Visia%' \
                # OR RESSOURCE LIKE 'Vivascope%' \
                # OR RESSOURCE LIKE 'Zwick%' \
                # ) AND (STARTDATUM>=CONVERT(date,GETDATE()) AND STARTDATUM<DATEADD(DAY, 14, GETDATE()))\
                # )) \
                # AND (STARTDATUM>=CONVERT(date,GETDATE()) AND STARTDATUM<DATEADD(DAY, 14, GETDATE())) AND PROJEKT LIKE '%-35%') \
                # GROUP BY CONVERT(date, Datum), RESSOURCE, TEMPFEUCHTE, RES_ID, PROJEKT \
                # ORDER BY CONVERT(date, Datum)")
                #endregion
                
                
                
                
                
                #region fetch hotroom query V2 Sei
                cur.execute("select RESSOURCE, TEMPFEUCHTE, MIN(STARTDATUM) AS MIN_STARTDATUM, \
                            MAX(ENDEDATUM) AS MAX_ENDEDATUM, COUNT(RESSOURCE) AS COUNT_RESSOURCE, \
                            RES_ID, PROJEKT from V_GLT_REPORT \
                WHERE ( \
                (RES_ID=460 ) \
                AND (STARTDATUM>=CONVERT(date,GETDATE()) AND STARTDATUM<DATEADD(DAY, 28, GETDATE())) \
                AND PROJEKT LIKE '%-35%') \
                GROUP BY CONVERT(date, Datum), RESSOURCE, TEMPFEUCHTE, RES_ID, PROJEKT \
                ORDER BY CONVERT(date, Datum)")
                #endregion

                res = cur.fetchall()
                columns = [column[0] for column in cur.description]
                results = [dict(zip(columns, row)) for row in res]
                
                # with open('output_from_sql_queries/fetchHotroom_output.txt', 'w') as f:
                #     print(res, file=f)
                    
                for row in results:
                    if row['TEMPFEUCHTE'] == None: # nothing specified, take default values
                        if ("38gc" in row['PROJEKT'].lower().replace(" ", "")):
                            row['TEMPERATUR']='39.8'
                            row['FEUCHTE']='34.0'
                        elif ("40gc" in row['PROJEKT'].lower().replace(" ", "")):
                            row['TEMPERATUR']='41.0'
                            row['FEUCHTE']='42.0'
                        else: # nothing specified, take default values
                            emailtempfeuchteErr.collectMsg("MISSING 38GC/40GC information, SETTING DEFAULT 38°C/34%: for planoutentry: " + str(row))
                            row['TEMPERATUR']='39.8'
                            row['FEUCHTE']='34.0'
                    else: # has a real TempFeuchte Entry but is a freely formatable field, so some regex and sanity checks:
                        try:
                            result= self.splitTempFeuchte(row['TEMPFEUCHTE'])
                            row['TEMPERATUR']=str(result['TEMPERATUR'])
                            row['FEUCHTE']=str(result['FEUCHTE'])
                        except LookupError as e:
                            emailtempfeuchteErr.collectMsg("ERROR DECIPHERING TEMPFEUCHTE, SETTING DEFAULT 38°C/34%: " + str(e) + ' for planoutentry: ' + str(row))
                            row['TEMPERATUR']='39.8'
                            row['FEUCHTE']='34.0'
                    del row['PROJEKT']
                    resultlist.append(row)

            if emailtempfeuchteErr.hasCollectedMsg():
                emailtempfeuchteErr.send(subject="ERROR (Hotroom) determining Temp/Feuchte please check GLT!", message=emailtempfeuchteErr.collectmsg)

            return sorted(resultlist, key=lambda k: k['MIN_STARTDATUM'])
        except pyodbc.DatabaseError as e:
            #wenn die Liste empty wäre, hätte cron die Einträge auf der GLT überschrieben...upstream den error handlen lassen
            raise e

    def fetchBelueftung(self) -> list:
        resultlist = list()
        emailtempfeuchteErr = SendEmail.SendEmail()
        try:
            with pyodbc.connect(self.connectionString) as connection:
                # AVAILABLE HEADERS: "PROJEKT, RESSOURCE, RESLANGNAME, DATUM, DAUER, STARTDATUM, ENDEDATUM, KOMMENTAR, VORGANG, TEMPFEUCHTE, PROJECT_ID, TASK_ID, TASK_RES_ID, RES_ID"
                cur = connection.cursor()

                # region fetch Belueftung V1 query
                # cur.execute("select RESSOURCE, TEMPFEUCHTE, MIN(STARTDATUM) AS MIN_STARTDATUM, MAX(ENDEDATUM) AS MAX_ENDEDATUM, COUNT(RESSOURCE) AS COUNT_RESSOURCE, RES_ID from V_GLT_REPORT \
                # WHERE (( \
                # (RESSOURCE LIKE 'Luna %' OR RESSOURCE LIKE 'Solaris %') \
                # AND RES_ID!=460 \
                # AND PROJEKT NOT IN (select PROJEKT from V_GLT_REPORT \
                #     WHERE ( \
                #         RESLANGNAME=' Klima extra' \
                #         OR RESSOURCE LIKE 'AEVA%' \
                #         OR RESSOURCE LIKE 'Aquaflux%' \
                #         OR RESSOURCE LIKE 'Biozoom%' \
                #         OR RESSOURCE LIKE 'Chroma%' \
                #         OR RESSOURCE LIKE 'Corneo%' \
                #         OR RESSOURCE LIKE 'Cuto%' \
                #         OR RESSOURCE LIKE 'Dermatop%' \
                #         OR RESSOURCE LIKE 'Epsilon%' \
                #         OR RESSOURCE LIKE 'FLPI%' \
                #         OR RESSOURCE LIKE 'LC-OCT%' \
                #         OR RESSOURCE LIKE 'MPA%' \
                #         OR RESSOURCE LIKE 'PH%' \
                #         OR RESSOURCE LIKE 'Raman%' \
                #         OR RESSOURCE LIKE 'Saugblasen%' \
                #         OR RESSOURCE LIKE 'Sebu%' \
                #         OR RESSOURCE LIKE 'Spectro%' \
                #         OR RESSOURCE LIKE 'SquameScan%' \
                #         OR RESSOURCE LIKE 'TSA%' \
                #         OR RESSOURCE LIKE 'Tewameter%' \
                #         OR RESSOURCE LIKE 'Thermographie%' \
                #         OR RESSOURCE LIKE 'Ultraschall%' \
                #         OR RESSOURCE LIKE 'Visia%' \
                #         OR RESSOURCE LIKE 'Vivascope%' \
                #         OR RESSOURCE LIKE 'Zwick%' ) \
                # AND (STARTDATUM>=CONVERT(date,GETDATE()) AND STARTDATUM<DATEADD(DAY, 14, GETDATE()))\
                # )) \
                # AND (STARTDATUM>=CONVERT(date,GETDATE()) AND STARTDATUM<DATEADD(DAY, 14, GETDATE())) ) \
                # GROUP BY CONVERT(date, Datum), RESSOURCE, TEMPFEUCHTE, RES_ID \
                # ORDER BY CONVERT(date, Datum)")
                
                # res = cur.fetchall()
                #endregion
                
                
                
                
                #region replacement fetchBelueftung V2 query
                # Main execution
                sql_query = load_sql_query('complex_query_fetchBelueftung.sql')

                cur.execute(sql_query)
                res = cur.fetchall()
                # with open('output_from_sql_queries/NEWfetchBelueftung_output.txt', 'w') as f:
                #     print(res, file=f)
                #endregion
                
                columns = [column[0] for column in cur.description]
                results = [dict(zip(columns, row)) for row in res]
                
                
                # with open('output_from_sql_queries/fetchBelueftung_output.txt', 'w') as f:
                #     print(res, file=f)
                
                
                for row in results:
                    if row['TEMPFEUCHTE'] == None: # nothing specified, take default values
                        row['TEMPERATUR']='22.0'
                        row['FEUCHTE']='50.0'
                    else: # has a real TempFeuchte Entry but is a freely formatable field, so some regex and sanity checks:
                        try:
                            result= self.splitTempFeuchte(row['TEMPFEUCHTE'])
                            row['TEMPERATUR']=str(result['TEMPERATUR'])
                            row['FEUCHTE']=str(result['FEUCHTE'])
                        except LookupError as e:
                            emailtempfeuchteErr.collectMsg("ERROR DECIPHERING TEMPFEUCHTE, SETTING DEFAULT 22°C/50%: " + str(e) + ' for planoutentry: ' + str(row))
                            row['TEMPERATUR']='22.0'
                            row['FEUCHTE']='50.0'
                    resultlist.append(row)

            if emailtempfeuchteErr.hasCollectedMsg():
                emailtempfeuchteErr.send(subject="ERROR (Belüftung) determining Temp/Feuchte please check GLT!", message=emailtempfeuchteErr.collectmsg)

            return sorted(resultlist, key=lambda k: k['MIN_STARTDATUM'])
        except pyodbc.DatabaseError as e:
            #wenn die Liste empty wäre, hätte cron die Einträge auf der GLT überschrieben...upstream den error handlen lassen
            raise e


    def temp_check_for_tempfeuchte_usage(self) -> list:
        """
        this will tell, if Studienplanung finally started inserting target temperature and feuchte
        """
        with pyodbc.connect(self.connectionString) as connection:
            cur = connection.cursor()            
            cur.execute("select PROJEKT, RESSOURCE, DATUM,TEMPFEUCHTE from V_GLT_REPORT WHERE TEMPFEUCHTE!=NULL ")
            
            #magic lambda, that gets the rowheaders and includes them in the rowfactory:
            cur.rowfactory = lambda *args: dict(zip([d[0] for d in cur.description], args))
            res = cur.fetchall()
            for row in res:
                print(row)
            #with open("output.txt", 'w') as outfile:
            #    for row in res:
            #        outfile.write(str(row)+"\n")
        return list()

    def testing(self) -> list:
        with pyodbc.connect(self.connectionString) as connection:
            cur = connection.cursor()            
            cur.execute("select PROJEKT, RESSOURCE, DATUM,TEMPFEUCHTE from V_GLT_REPORT \
                        WHERE (RESSOURCE='Solaris R 2 Hotroom' \
                                AND (STARTDATUM<=CONVERT(date,GETDATE())) \
                                AND PROJEKT LIKE '%-35%')")

            #magic lambda, that gets the rowheaders and includes them in the rowfactory:
            cur.rowfactory = lambda *args: dict(zip([d[0] for d in cur.description], args))
            res = cur.fetchall()
            for row in res:
                print(row)
            #with open("output.txt", 'w') as outfile:
            #    for row in res:
            #        outfile.write(str(row)+"\n")
        return list()            

    def weekendAlarmHauptlüftung(self) -> list:

        #Hotroom macht die ganze Anlage an, also ohne RESID=460
        #Eine Ähnliche Abfrage nochmal für Geräteeinsatz am Wochenende?? (Reslangname startet mit G und dann 3 nummern)
        #TODO: Sendemail, flaskurl für nen cronjob, wie den "schon gesendet state"?

        with pyodbc.connect(self.connectionString) as connection:
            cur = connection.cursor()            
            cur.execute("select PROJEKT,RESSOURCE, DATUM \
            from V_GLT_REPORT \
            WHERE ( \
            to_char(DATUM,'DY') in ('SAT','SUN') \
            AND (RESSOURCE LIKE 'Luna %' OR RESSOURCE LIKE 'Solaris %') \
            AND RES_ID NOT IN (459,460) \
            AND (STARTDATUM>=CONVERT(date,GETDATE()) AND STARTDATUM<DATEADD(DAY, 14, GETDATE())) \
            AND (STARTDATUM>=CONVERT(date,GETDATE()) AND STARTDATUM<DATEADD(DAY, 14, GETDATE())) \
            ) \
            ORDER BY Datum ")
            
            #magic lambda, that gets the rowheaders and includes them in the rowfactory:
            cur.rowfactory = lambda *args: dict(zip([d[0] for d in cur.description], args))
            res = cur.fetchall()
            for row in res:
                print(row)
            #with open("output.txt", 'w') as outfile:
            #    for row in res:
            #        outfile.write(str(row)+"\n")
        return list()
    
        
    def corporatePlannerOutput(self, startdatum: datetime.date, enddatum: datetime.date, project="", resource=""):
        filename = str(int(datetime.datetime.timestamp(datetime.datetime.now())))+".txt" #tempfilename
        with pyodbc.connect(self.connectionString) as connection:
            cur = connection.cursor()
            
            # Build WHERE clause based on provided parameters
            where_clauses = []
            
            if project:
                where_clauses.append(f"PROJEKT LIKE '{str(project)}'")
            
            if resource:
                # Handle multiple comma-separated resources
                resources = [r.strip() for r in resource.split(',') if r.strip()]
                if resources:
                    if len(resources) == 1:
                        # Single resource - simple LIKE
                        where_clauses.append(f"RESSOURCE LIKE '%{resources[0]}%'")
                    else:
                        # Multiple resources - use OR with LIKE for each
                        resource_conditions = [f"RESSOURCE LIKE '%{r}%'" for r in resources]
                        where_clauses.append(f"({' OR '.join(resource_conditions)})")
            
            if startdatum is not None and enddatum is not None:
                # Format dates as strings for SQL Server
                start_str = startdatum.strftime('%Y-%m-%d')
                end_str = enddatum.strftime('%Y-%m-%d')
                where_clauses.append(f"STARTDATUM >= CAST('{start_str}' AS DATE)")
                where_clauses.append(f"STARTDATUM <= CAST('{end_str}' AS DATE)")
            
            # Construct query
            query = "select PROJEKT, RESSOURCE, RESLANGNAME, DATUM, DAUER, STARTDATUM, ENDEDATUM, KOMMENTAR, VORGANG from V_GLT_REPORT"
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            print(f"Executing query: {query}")  # Debug
            
            cur.execute(query)
            res = cur.fetchall()

            with open(filename, 'w', encoding='utf-8') as outfile:
                outfile.write("PROJEKT\tRESSOURCE\tRESLANGNAME\tDATUM\tDAUER\tSTARTDATUM\tENDEDATUM\tKOMMENTAR\tVORGANG\n")
                for row in res:
                    newrow=""
                    for item in row:
                        if id(item) == id(row[0]):
                            newrow=str(item)
                        elif type(item) == datetime.datetime:
                            newrow+="\t" + item.strftime('%Y-%m-%d %H:%M:%S')
                        elif item == None:
                            newrow+="\t "
                        else:
                            newrow+="\t" + str(item)
                    outfile.write(newrow+"\n")
            return filename
                    
    def splitTempFeuchte(self, tempfeuchte: str) -> dict:

        #check for string "Raumtemperatur"
        if str(tempfeuchte).lower() == 'raumtemperatur':
            return { 'TEMPERATUR': 22, 'FEUCHTE' : None }
        import re
        p = re.compile(r'\d+') #get all digits until first non-digit
        results = p.findall(tempfeuchte) # returns a list of found 
        if len(results) == 2: # we got two results, first is temperature, second is humidity
            results[0] = float(results[0])
            results[1] = float(results[1])
            if results[0] < 100 and results[1] < 100: #VERY simple sanity check...
                return { 'TEMPERATUR': results[0], 'FEUCHTE' : results[1] }
            else:
                raise LookupError
        elif len(results) == 4: # we got FOUR results, first is temperature inkl hysteresis, second is humidity incl hysteresis
            #TODO actually implement hysteresis forwarding!! currently dropped
            results[0] = float(results[0])
            results[2] = float(results[2])
            if results[0] < 100 and results[2] < 100: #VERY simple sanity check...
                return { 'TEMPERATUR': results[0], 'FEUCHTE' : results[2] }
            else:
                raise LookupError
        elif len(results) == 1: # we got one result, first is temperature, humidity is irrelevant, let later code handle the None
            results[0] = float(results[0])
            if results[0] < 100 : #VERY simple sanity check...
                return { 'TEMPERATUR': results[0], 'FEUCHTE' : None }
            else:
                raise LookupError
        else:
            raise LookupError

    def fetchDummyData(self):
        import datetime
        todaystart = datetime.datetime(year=datetime.datetime.today().year, month=datetime.datetime.today().month, day=datetime.datetime.today().day, hour=8, minute=30, second=0)
        todaystop = datetime.datetime(year=datetime.datetime.today().year, month=datetime.datetime.today().month, day=datetime.datetime.today().day, hour=17, minute=00, second=0)
        todayintwominutes = datetime.datetime.today() + datetime.timedelta(minutes=2)
        return [
                {'RESSOURCE': 'Luna R9 Fotoraum (-72)', 'TEMPFEUCHTE': None, 'MIN_STARTDATUM': todaystart, 'MAX_ENDEDATUM': todaystop, 'COUNT_RESSOURCE': 1, 'RES_ID': 88, 'TEMPERATUR': '22.0', 'FEUCHTE': '50.0'}
                #{'RESSOURCE': 'Luna R8 (-218)', 'TEMPFEUCHTE': None, 'MIN(STARTDATUM)': datetime.datetime(2021, 9, 7, 8, 30), 'MAX(ENDEDATUM)': datetime.datetime(2021, 9, 7, 17, 0), 'COUNT(RESSOURCE)': 1, 'RES_ID': 87, 'TEMPERATUR': '22.0', 'FEUCHTE': '50.0'},
                #{'RESSOURCE': 'Luna R3/4 (-291)', 'TEMPFEUCHTE': None, 'MIN(STARTDATUM)': datetime.datetime(2021, 9, 8, 8, 30), 'MAX(ENDEDATUM)': datetime.datetime(2021, 9, 8, 17, 0), 'COUNT(RESSOURCE)': 1, 'RES_ID': 88, 'TEMPERATUR': '22.0', 'FEUCHTE': '50.0'},
                #{'RESSOURCE': 'Luna R6/7 (-267)', 'TEMPFEUCHTE': None, 'MIN(STARTDATUM)': datetime.datetime(2021, 9, 8, 8, 30), 'MAX(ENDEDATUM)': datetime.datetime(2021, 9, 8, 16, 30), 'COUNT(RESSOURCE)': 1, 'RES_ID': 55, 'TEMPERATUR': '22.0', 'FEUCHTE': '50.0'}, 
                #{'RESSOURCE': 'Luna R8 (-218)', 'TEMPFEUCHTE': None, 'MIN(STARTDATUM)': datetime.datetime(2021, 9, 8, 8, 30), 'MAX(ENDEDATUM)': datetime.datetime(2021, 9, 8, 17, 0), 'COUNT(RESSOURCE)': 1, 'RES_ID': 87, 'TEMPERATUR': '22.0', 'FEUCHTE': '50.0'},
                #{'RESSOURCE': 'Luna R3/4 (-291)', 'TEMPFEUCHTE': None, 'MIN(STARTDATUM)': datetime.datetime(2021, 9, 9, 8, 30), 'MAX(ENDEDATUM)': datetime.datetime(2021, 9, 9, 17, 0), 'COUNT(RESSOURCE)': 1, 'RES_ID': 88, 'TEMPERATUR': '22.0', 'FEUCHTE': '50.0'}, 
                #{'RESSOURCE': 'Luna R6/7 (-267)', 'TEMPFEUCHTE': None, 'MIN(STARTDATUM)': datetime.datetime(2021, 9, 9, 8, 30), 'MAX(ENDEDATUM)': datetime.datetime(2021, 9, 9, 12, 30), 'COUNT(RESSOURCE)': 1, 'RES_ID': 55, 'TEMPERATUR': '22.0', 'FEUCHTE': '50.0'}, 
                #{'RESSOURCE': 'Luna R3/4 (-291)', 'TEMPFEUCHTE': None, 'MIN(STARTDATUM)': datetime.datetime(2021, 9, 10, 8, 30), 'MAX(ENDEDATUM)': datetime.datetime(2021, 9, 10, 17, 0), 'COUNT(RESSOURCE)': 1, 'RES_ID': 88, 'TEMPERATUR': '22.0', 'FEUCHTE': '50.0'}, 
                #{'RESSOURCE': 'Luna R5 (-46)', 'TEMPFEUCHTE': None, 'MIN(STARTDATUM)': datetime.datetime(2021, 9, 10, 8, 30), 'MAX(ENDEDATUM)': datetime.datetime(2021, 9, 10, 15, 30), 'COUNT(RESSOURCE)': 1, 'RES_ID': 90, 'TEMPERATUR': '22.0', 'FEUCHTE': '50.0'}, 
                #{'RESSOURCE': 'Solaris R 2 Hotroom', 'TEMPFEUCHTE': None, 'MIN(STARTDATUM)': datetime.datetime(2021, 9, 14, 9, 30), 'MAX(ENDEDATUM)': datetime.datetime(2021, 9, 14, 17, 30), 'COUNT(RESSOURCE)': 1, 'RES_ID': 460, 'TEMPERATUR': '38.0', 'FEUCHTE': '34.0'}, 
                #{'RESSOURCE': 'Solaris R 2 Hotroom', 'TEMPFEUCHTE': None, 'MIN(STARTDATUM)': datetime.datetime(2021, 9, 15, 9, 30), 'MAX(ENDEDATUM)': datetime.datetime(2021, 9, 15, 17, 30), 'COUNT(RESSOURCE)': 1, 'RES_ID': 460, 'TEMPERATUR': '38.0', 'FEUCHTE': '34.0'}
              ]

    def translatePlanoutListToGLTSettingsAndAddOverrides(self, planoutlist: list, viewer=False):
        #build a settingslist, that has everything needed by the GLT.
        #the planoutlist is expected to be a dictionary coming from PlanoutImport.fetch()
        settingslist = list()
        roomDefinitions = RoomDefinitions.RoomDefinitions()
        email = SendEmail.SendEmail()
        overrides = Overrides.Overrides()
        if self.sendReport and not viewer:
            emailreport = SendEmail.SendEmail()
        for entry in planoutlist:
            if overrides.isOverridden(roomDefinitions.translateCanonicalToGLT(roomDefinitions.getCanonicalKeyFromRES_ID(entry['RES_ID'])),entry['MIN_STARTDATUM']):
                #ignore in planoutlist, this will be added as part of including all overrides
                pass
            else: #is not overridden, use values from planout
                try:
                    settings = roomDefinitions.generateRoomSettings(roomDefinitions.getCanonicalKeyFromRES_ID(entry['RES_ID']),float(entry['TEMPERATUR']),float(entry['FEUCHTE']))                
                except TypeError as e: # can only come from generateRoomSettings() -> float(entry['FEUCHTE']) -> float(None)
                    #probably feuchte==None
                    settings = roomDefinitions.generateBestEffortRoomSettings(roomDefinitions.getCanonicalKeyFromRES_ID(entry['RES_ID']),float(entry['TEMPERATUR']),entry['FEUCHTE'])
                except ValueError as e: # can only come from generateRoomSettings()
                    #probably a room that does not have the right capabilities
                    email.collectMsg("Error for roomsettings: " + str(e) + ' for planoutentry: ' + str(entry) + " USING 'BEST EFFORT' VALUES -> ONLY TEMPERATURE BUT IGNORE HUMIDIY ... OR SIMILAR. CHECK URGENTLY!")
                    settings = roomDefinitions.generateBestEffortRoomSettings(roomDefinitions.getCanonicalKeyFromRES_ID(entry['RES_ID']),float(entry['TEMPERATUR']),float(entry['FEUCHTE']))
                except LookupError as e: # can only come from getCanonicalKey()
                  email.collectMsg("Error for roomname translation: " + str(e) + ' for planoutentry: ' + str(entry))

                settings['gltname'] = roomDefinitions.translateCanonicalToGLT(roomDefinitions.getCanonicalKeyFromRES_ID(entry['RES_ID'])) #can be none
                settings['startzeit'] = entry['MIN_STARTDATUM']
                endzeit = entry['MAX_ENDEDATUM']
                new_datetime = endzeit.replace(hour=18, minute=0, second=0, microsecond=0)
                settings['endzeit'] = max(entry['MAX_ENDEDATUM'], new_datetime)
                if settings['gltname'] != None:
                    #thanks python3.7 for ORDERING DICTIONARIES....
                    settingslist.append({key: settings[key] for key in sorted(settings.keys())})
                    if self.sendReport and not viewer:
                        emailreport.collectMsg(str(entry) + "\n" + str(settings) + "\n")

        #get all overrides for the same timeframe:
        for entry in overrides.getAllOverrides():
            settings=entry
            settings['startzeit'] = datetime.datetime.fromisoformat(settings['startzeit'])
            settings['endzeit'] = datetime.datetime.fromisoformat(settings['endzeit'])
            settings.pop('hash')
            if self.sendReport and not viewer:
                emailreport.collectMsg(str(entry) + "\n" + str(settings) + "\n")
            #thanks python3.7 for ORDERING DICTIONARIES....
            settingslist.append({key: settings[key] for key in sorted(settings.keys())})

        if email.hasCollectedMsg() and not viewer:
            email.send(subject="Error generating GLT Settings", message=email.collectmsg)
        if self.sendReport and not viewer:
            emailreport.send(subject="Report for GLT Settings for next 14 days", message=emailreport.collectmsg)

        return sorted(settingslist, key=lambda k: k['startzeit'])

if __name__ == '__main__':
    instance = PlanoutImport()
    #TESTING
    # print(instance.fetchBelueftung()) 
    # instance.corporatePlannerOutput(startdatum=datetime.date(2023, 1,1), enddatum=datetime.date(2023,8,1), project="")
    # print("1")
    # print(instance.fetchHotroom()) 
    # print(instance.fetchDummyData()) 
    # print(instance.fetchBelueftung()) 
    # print(instance.fetchKlima()) 

    