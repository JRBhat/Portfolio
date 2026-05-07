import flask
import datetime

# import PlanoutImport_MSSQL_adjusted as PlanoutImport ,sendJSON, Overrides, RoomDefinitions
import PlanoutImport_MSSQL_adjusted_V5_multi_resource_filter   as PlanoutImport ,sendJSON, Overrides, RoomDefinitions


#TODO: Was ist mit UTC, Sommerzeit und so nem Krempel?

app = flask.Flask(__name__)
planout = PlanoutImport.PlanoutImport()
glt = sendJSON.sendJSON()
overrides = Overrides.Overrides()

def listOfListToHTMLTable(iterable):
    resultstring = '<TABLE border=1>'
    if isinstance(iterable, list):
        for row in iterable:
            resultstring+='<TR>'
            if isinstance(row, dict):
                for column in row:
                    resultstring+='<TD>'+str(row[column])+'</TD>'
            elif isinstance(row, list):
                for column in row:
                    resultstring+='<TD>'+str(column)+'</TD>'
            resultstring+='</TR>'
        resultstring += '</TABLE>'
    return resultstring

def htmlstringescapetreatment(input :str):
    tempstring = input.replace('+','%2B')
    tempstring = tempstring.replace(' ','+')
    return tempstring

@app.route('/')
@app.route('/index')
@app.route('/index.html')
def index():
    return '''
            <h1>Planout Export Webinterface</h1><br>
            <h2>Standardbefehle:</h2>
            <h3><a href="/combinedview">Kombinierte Ansicht</a><br><br>
            <a href="/clearglt">Alle Skriptschaltpunkte auf der GLT löschen</a><br><br><br>
            <h2>Detailsicht:</h2>
            <h3><a href="/planoutview">Übersicht Export aus Planout</a><br><br>
            <a href="/gltview">Übersicht Export zur GLT</a><br><br><br>
            <h2>Overrides:</h2>
            <h3><a href="/overridesview">Übersicht der Overrides (Änderungen an Planoutdaten)</a><br><br>
            <a href="/override_form">neuen Override erstellen ohne Planout</a><br><br><br>
            <h2>Weitere Planout Exporte:</h2>
            <h3><a href="/ressourceOutput_form">Ressource-Output (PM)</a><br>
            <h2>Email Scheduler:</h2>
            <h3><a href="/scheduler">📧 Email Report Scheduler verwalten</a><br>
            '''



@app.route('/planoutview')
def planoutview():
    datalist=planout.fetch()
    
    #get the dict.keys and add them to the front to act as table headers
    try:
      datalist.insert(0, list(datalist[0].keys()))
    except IndexError:
        pass
    except AttributeError:
        return "Couldn't read datalist from planoutPlanoutiew"
    #convert to html-table
    return listOfListToHTMLTable(datalist)

@app.route('/gltview')
def gltview():
    try:
        datalist=planout.translatePlanoutListToGLTSettingsAndAddOverrides(planout.fetch(),viewer=True)
    except TypeError: #trying to access None['stuff'] bc planout.fetch returned None
        return "Couldn't read datalist from planoutGltView"

    #add overridelink to the end:
    for entry in datalist:
        parameterstring = ''
        for parameter in entry.keys():
            parameterstring += str(parameter) + '=' + str(entry[parameter]) + '&'
        if overrides.isOverridden(entry['gltname'],entry['startzeit']):
            linktext="!!! MODIFY OVERRIDE !!!"
        else:
            linktext="ADD OVERRIDE"
        entry["ADDOVERRIDE"] = '<a href="/override_form_editmode?'+htmlstringescapetreatment(parameterstring)+'">'+linktext+'</a>'

    #get the dict.keys and add them to the front to act as table headers
    try:
        datalist.insert(0, list(datalist[0].keys()))
    except IndexError:
        pass
    return listOfListToHTMLTable(datalist)+'<br><a href=/sendtoglt>SEND THIS TABLE TO GLT</a><br><br>'

@app.route('/combinedview')
def combinedview():
    table2='GLT:'+gltview()
    table3='OVERRIDES:'+overridesview()
    return table2+table3

@app.route('/sendtoglt')
def sendToGLT():
    try:
        result=planout.translatePlanoutListToGLTSettingsAndAddOverrides(planout.fetch())
    except TypeError: #trying to access None['stuff'] bc planout.fetch returned None
        return "Could read datalist from planoutsendToGLT"
    htmlstring = str(glt.sendToGLT(glt.prepareJSONList(result)))
    return htmlstring

@app.route('/clearglt')
def clearglt():

    #delete all tsv files ...
    #os.listdir()

    return str(glt.clearGLT())

@app.route('/overridesview')
@app.route('/overrideview')
def overridesview():
    #create an tabluar overview over all overrides (even past ones)
    datalist=overrides.getAllOverrides()

    #add deletelink to the end:
    for entry in datalist:
        entry["DELETE"] = '<a href="/override_delete/'+str(entry['hash'])+'">DELETE</a>'

    try:
      datalist.insert(0, list(datalist[0].keys()))
    except IndexError:
        pass
    return listOfListToHTMLTable(datalist)+'<br><a href="/override_form">ADD NEW OVERRIDE</a>'

@app.route('/override_delete/<hashstr>')
def override_delete(hashstr):
    #remove an override based on its hash (which is the only thing we have to identify things right now)
    return str(overrides.removeOverrideByHash(hashstr=hashstr))+'<br><a href="/">Zurück</a>'

@app.route('/override_insert', methods=['GET', 'POST'])
def override_insert():
    #get form data from override_form and call the function inside class Overrides + sanity checks
    overridedict = dict()
    for entry in ('gltname','startzeit','endzeit','betriebszustand','sollwertTemp','hystereseTemp','sollwertFeuchte','hystereseFeuchte','volumenstrom','vorlaufzeit'):
            overridedict[entry] = flask.request.args.get(entry) #get all the parameters passed in the URL by name

            #check if startzeit and endzeit are properly formatted, otherwise the hash will not be correct
            if entry == 'startzeit' or entry == 'endzeit':
                try:
                    overridedict[entry] = datetime.datetime.fromisoformat(overridedict[entry])
                except ValueError as e:
                    return str(e)

            #no missing parameters allowed
            if overridedict[entry] is None:
                return 'Malformed URL: parameter ' + entry + ' is missing or None'
    return str(overrides.insertOverride(gltname=overridedict['gltname'], startzeit=overridedict['startzeit'],endzeit=overridedict['endzeit'],betriebszustand=overridedict['betriebszustand'],sollwertTemp=overridedict['sollwertTemp'],hystereseTemp=overridedict['hystereseTemp'],sollwertFeuchte=overridedict['sollwertFeuchte'],hystereseFeuchte=overridedict['hystereseFeuchte'],volumenstrom=overridedict['volumenstrom'],vorlaufzeit=overridedict['vorlaufzeit']))+'<br><a href="/">Zurück</a>'

@app.route('/override_form_editmode', methods=['GET', 'POST'])
def override_form_editmode():
    return override_form(editmode=True) #the same form, but room and starttime will not be editable

@app.route('/override_form', methods=['GET', 'POST'])
def override_form(editmode=False):
    #build a table of forms from the POST-ed parameters and submit them to the override_insert function
    overridedict = dict()
    htmlstring = '<table><form action="/override_insert">'
    for entry in ('gltname','startzeit','endzeit','betriebszustand','sollwertTemp','hystereseTemp','sollwertFeuchte','hystereseFeuchte','volumenstrom','vorlaufzeit'):
            overridedict[entry] = flask.request.args.get(entry) #get all the parameters passed in the URL by name
            
            if entry=='gltname': #gets dropdownlist
                htmlstring += '<tr><td>' + str(entry) + ': </td><td><select id="gltname" name="gltname"'
                if editmode:
                    htmlstring += ' hidden>'
                else:
                    htmlstring += '>'
                for room in RoomDefinitions.RoomDefinitions().getGLTNameList():
                    htmlstring+='<option value="'+str(room)+'"'
                    if str(room) == str(overridedict[entry]):
                        htmlstring+=' selected'
                    htmlstring+='>'+str(room)+'</option>'
                htmlstring+='</select>'
            else: #all other are textfields
                htmlstring += '<tr><td>' + str(entry) + ': </td><td> <input type="text" id="' + str(entry) + '" name="' + str(entry) + '" value='
                #if parameter was not given leave form empty
                if overridedict[entry] is None:
                    htmlstring += '""'
                #else include initial value
                else:
                    htmlstring += '"' + str(overridedict[entry]) + '"'
                if entry == 'startzeit' and editmode:
                    htmlstring += ' hidden'
            htmlstring += '></td><td>(initialer Wert: '+str(overridedict[entry])+')</td></tr>'

    htmlstring += '<tr><input type="submit" value="Override eintragen"></tr></form></table><br><br>DATUMSFORMAT: YYYY-MM-DD HH-MM <br>Betriebszustand -1 bedeutet dieser Eintrag wird ignoriert.<br><br><a href="/">Zurück</a>'
    return htmlstring

@app.route('/corporatePlannerOutput_download', methods=['GET', 'POST'])
def corporatePlannerOutput_download():
    #sanity check
    try:
        startdatum = datetime.date.fromisoformat(flask.request.args.get('startdatum'))
        enddatum = datetime.date.fromisoformat(flask.request.args.get('enddatum'))
    except ValueError:
        return "Start oder Enddatum hat nicht das richtige Format YYYY-MM-DD"
    
    return flask.send_file(planout.corporatePlannerOutput(startdatum, enddatum),as_attachment=True, download_name="CorporatePlannerOverview-"+str(flask.request.args.get('enddatum'))+".tsv")
    #todo: deletefile (not easy...) .. webcron tidy up



@app.route('/ressourceOutput_form')
def ressource_output_form():
    #build a table of forms from the POST-ed parameters and submit them to the override_insert function
    htmlstring = '<table><form action="/ressourceOutput_download">'
    for entry in ('projekt', 'resource', 'startdatum','enddatum'):
        htmlstring += '<tr><td>' + str(entry) + ': </td><td> <input type="text" id="' + str(entry) + '" name="' + str(entry) + '" value=' '"' + '"></td></tr>'
    htmlstring += '<tr><input type="submit" value="Planout Übersicht herunterladen"></tr></form></table><br><br>DATUMSFORMAT: YYYY-MM-DD <br>Die Datumsangaben sind inkl Starttag und Endtag<br><br>Projektname mit "%" als Wildcard für die Suche <br>Ressource: Einzelner Name oder mehrere durch Komma getrennt (z.B. "DermLites, MacIS-M, AEVA")<br>Wildcards werden automatisch hinzugefügt<br><br><a href="/">Zurück</a>'
    return htmlstring

@app.route('/ressourceOutput_download', methods=['GET', 'POST'])
def ressourceOutput_download():
    # Get parameters
    projekt = flask.request.args.get('projekt', '').strip()
    resource = flask.request.args.get('resource', '').strip()
    startdatum_str = flask.request.args.get('startdatum', '').strip()
    enddatum_str = flask.request.args.get('enddatum', '').strip()
    
    # Parse dates if provided (check for non-empty strings)
    if startdatum_str != '' and enddatum_str != '':
        try:
            startdatum = datetime.date.fromisoformat(startdatum_str)
            enddatum = datetime.date.fromisoformat(enddatum_str)
        except ValueError:
            return "Start oder Enddatum hat nicht das richtige Format YYYY-MM-DD"
    else:
        startdatum = None
        enddatum = None
    
    # Strip non alphanumeric from projectname and resource to use in filename
    downloadFilename = ""
    if projekt:
        downloadFilename += "".join(e for e in projekt if e.isalnum())
    if resource:
        if downloadFilename:
            downloadFilename += "_"
        # For multiple resources, just use "MultipleResources" in filename
        resource_count = len([r.strip() for r in resource.split(',') if r.strip()])
        if resource_count > 1:
            downloadFilename += "MultipleResources"
        else:
            downloadFilename += "".join(e for e in resource if e.isalnum())
    if not downloadFilename:
        downloadFilename = "Export"
    
    return flask.send_file(
        planout.corporatePlannerOutput(startdatum, enddatum, projekt, resource),
        as_attachment=True, 
        download_name="PlanoutRessourceOverview-"+downloadFilename+".tsv"
    )
    
from EmailScheduler import EmailScheduler

# Initialize scheduler alongside your other globals
email_scheduler = EmailScheduler(planout_instance=planout)
email_scheduler.start()

# ─────────────────────────────────────────────
# SCHEDULER FORM
# ─────────────────────────────────────────────

@app.route('/scheduler')
def scheduler_overview():
    """Overview of all active scheduled jobs with option to add/remove/trigger"""

    active_jobs = email_scheduler.get_all_jobs()

    # Build jobs table
    if active_jobs:
        job_table = '<table border=1 cellpadding=6>'
        job_table += '<tr><th>Recipient</th><th>Resources</th><th>Day</th><th>Time</th><th>Lookahead (days)</th><th>Created</th><th>Actions</th></tr>'
        for job in active_jobs:
            job_table += f'''
            <tr>
                <td>{job["recipient_email"]}</td>
                <td>{job["resources"] if job["resources"] else "All"}</td>
                <td>{job["day"].capitalize()}</td>
                <td>{job["time"]}</td>
                <td>{job["lookahead_days"]}</td>
                <td>{job["created_at"]}</td>
                <td>
                    <a href="/scheduler/trigger/{job["job_id"]}">▶ Send Now</a> &nbsp;|&nbsp;
                    <a href="/scheduler/remove/{job["job_id"]}" onclick="return confirm('Remove this job?')">🗑 Remove</a>
                </td>
            </tr>'''
        job_table += '</table>'
    else:
        job_table = '<p><i>No active scheduled jobs.</i></p>'

    # Build add job form
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    day_options = ''.join(
        f'<option value="{d}" {"selected" if d == "friday" else ""}>{d.capitalize()}</option>'
        for d in days
    )

    form = f'''
    <form action="/scheduler/add" method="GET">
        <table border=0 cellpadding=6>
            <tr>
                <td><b>Recipient Email:</b></td>
                <td><input type="text" name="recipient_email" style="width:300px" placeholder="your-email@example.com" required></td>
            </tr>
            <tr>
                <td><b>Resources:</b></td>
                <td>
                    <input type="text" name="resources" style="width:300px" placeholder="DermLites, AEVA, Visia (empty = all)">
                    <br><small>Comma-separated, wildcards added automatically</small>
                </td>
            </tr>
            <tr>
                <td><b>Day:</b></td>
                <td><select name="day">{day_options}</select></td>
            </tr>
            <tr>
                <td><b>Time (HH:MM):</b></td>
                <td><input type="text" name="time_str" value="17:00" placeholder="17:00"></td>
            </tr>
            <tr>
                <td><b>lookahead (days):</b></td>
                <td>
                    <input type="number" name="lookahead_days" value="7" min="1" max="365">
                    <br><small>How many days back the report should cover</small>
                </td>
            </tr>
            <tr>
                <td></td>
                <td><input type="submit" value="➕ Add Scheduled Job"></td>
            </tr>
        </table>
    </form>
    '''

    return f'''
    <h1>📧 Email Report Scheduler</h1>
    <h2>Active Scheduled Jobs</h2>
    {job_table}
    <br>
    <h2>Add New Scheduled Job</h2>
    {form}
    <br><a href="/">← Back to Home</a>
    '''

@app.route('/scheduler/add')
def scheduler_add():
    """Add a new scheduled email job"""
    recipient_email = flask.request.args.get('recipient_email', '').strip()
    resources       = flask.request.args.get('resources', '').strip()
    day             = flask.request.args.get('day', 'friday').strip().lower()
    time_str        = flask.request.args.get('time_str', '17:00').strip()
    lookahead_days   = flask.request.args.get('lookahead_days', '7').strip()

    # Validate inputs
    if not recipient_email or '@' not in recipient_email:
        return 'Invalid email address. <br><a href="/scheduler">← Back</a>'

    valid_days = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
    if day not in valid_days:
        return f'Invalid day. Must be one of: {", ".join(valid_days)}. <br><a href="/scheduler">← Back</a>'

    try:
        datetime.datetime.strptime(time_str, '%H:%M')
    except ValueError:
        return 'Invalid time format. Please use HH:MM (e.g. 17:00). <br><a href="/scheduler">← Back</a>'

    try:
        lookahead_days = int(lookahead_days)
        if lookahead_days < 1:
            raise ValueError
    except ValueError:
        return 'lookahead days must be a positive integer. <br><a href="/scheduler">← Back</a>'

    job_id = email_scheduler.add_job(
        recipient_email=recipient_email,
        resources=resources,
        day=day,
        time_str=time_str,
        lookahead_days=lookahead_days
    )

    if job_id:
        return f'''
        <h2>✓ Scheduled Job Added!</h2>
        <table border=1 cellpadding=6>
            <tr><td><b>Job ID</b></td><td>{job_id}</td></tr>
            <tr><td><b>Recipient</b></td><td>{recipient_email}</td></tr>
            <tr><td><b>Resources</b></td><td>{resources if resources else "All"}</td></tr>
            <tr><td><b>Schedule</b></td><td>Every {day.capitalize()} at {time_str}</td></tr>
            <tr><td><b>lookahead</b></td><td>{lookahead_days} days</td></tr>
        </table>
        <br>
        <a href="/scheduler/trigger/{job_id}">▶ Send Test Email Now</a> &nbsp;|&nbsp;
        <a href="/scheduler">← Back to Scheduler</a>
        '''
    else:
        return 'Failed to add job. Check server logs. <br><a href="/scheduler">← Back</a>'


@app.route('/scheduler/remove/<job_id>')
def scheduler_remove(job_id):
    """Remove a scheduled job by ID"""
    success = email_scheduler.remove_job(job_id)
    if success:
        return f'✓ Job <b>{job_id}</b> removed. <br><br><a href="/scheduler">← Back to Scheduler</a>'
    else:
        return f'✗ Job <b>{job_id}</b> not found. <br><br><a href="/scheduler">← Back to Scheduler</a>'


@app.route('/scheduler/trigger/<job_id>')
def scheduler_trigger(job_id):
    """Manually trigger a job immediately"""
    success = email_scheduler.trigger_job_now(job_id)
    if success:
        return f'''
        <h2>▶ Job Triggered!</h2>
        <p>Job <b>{job_id}</b> is running in the background.</p>
        <p>Check your inbox at the recipient email in a few moments.</p>
        <br><a href="/scheduler">← Back to Scheduler</a>
        '''
    else:
        return f'✗ Job <b>{job_id}</b> not found. <br><br><a href="/scheduler">← Back to Scheduler</a>'
    
    
if __name__ == '__main__':
    import os
    HOST = os.environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT)
