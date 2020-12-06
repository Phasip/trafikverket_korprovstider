#!/usr/bin/python
import json
import datetime
import sys
import os
import subprocess
import time
import ssl
import urllib.request

# <config>
SSN="19XXXXXX-XXXX"
mail_server="smtp.mydomain.com"
mail_port="587"
mail_to="XXXXXXXXX@gmail.com"
mail_from="XXXXXXX@mydomain.com"
mail_subject="Lediga uppkörningstider"
mail_user=mail_from
mail_password="notsosecretpassword"
#use absolute path for cron
SEEN_FILE="/home/MYUSER/seen.txt"
LOGFILEFORMAT="/home/MYUSER/korprov_%s-%s.log"

# Don't report times later than these dates
current_booking_korprov = datetime.datetime.strptime("2020-08-24", '%Y-%m-%d')
current_booking_teoriprov = datetime.datetime.strptime("2020-10-08", '%Y-%m-%d')
# Don't report times earlier than these dates
earliest_booking_korprov = datetime.datetime.strptime("2020-08-01","%Y-%m-%d")
earliest_booking_teoriprov = datetime.datetime.strptime("2020-08-16", '%Y-%m-%d')
# Where you think it makes sense to make the theory test
locationmap = {"Järfälla":1000326, "Sollentuna":1000134, "Stockholm City":1000140}
# Where you think it makes sense to take the practical test
locationmap_korprov = {"Järfälla":100326}
# </config>

# Constants, add new if you want to monitor some other setup (e.g manual transmission)
# All these found from search_info_url
KUNSKAPSPROV_ID=3
LICENSE_ID_B=5
KORPROV_ID=12
SWELANG_ID=13
MAX_DAYS=90
VHEICLE_AUTOMAT=4

def make_post_request(url, data):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    params = json.dumps(data).encode('utf8')
    req = urllib.request.Request(url, data=params, headers={'content-type': 'application/json'})
    response = urllib.request.urlopen(req,context=ctx)
    return json.loads(response.read().decode('utf8'))

def mail_swaks(smtpserver,smtpport,user,password,mail_to,mail_from,subject,body):
    # Warning! I don't take responsibility if SWAKS fails to handle
    # arguments correctly!
    subprocess.run([
        "swaks",
        "--add-header","Content-Type: text/plain;charset=utf-8",
        "-s",smtpserver,
        "-p",smtpport,
        "-t",mail_to,
        "-f",mail_from,
        "--header","Subject: %s"%subject,
        "-S","--protocol","ESMTP","-a",
        "-au",user,
        "-ap",password,
        "--body",body])
        
search_info_data = {"bookingSession":{"socialSecurityNumber":SSN,"licenceId":LICENSE_ID_B,"bookingModeId":0,"ignoreDebt":False,"ignoreBookingHindrance":False,"excludeExaminationCategories":[],"rescheduleTypeId":0,"paymentIsActive":False,"paymentReference":None,"paymentUrl":None}}
search_info_url = "https://fp.trafikverket.se/boka/search-information"
time_info_url = "https://fp.trafikverket.se/boka/occasion-bundles"
def _build_search_query(license_type=LICENSE_ID_B):
     return {
        "bookingSession": {
            "bookingModeId": 0,
            "excludeExaminationCategories": [],
            "ignoreBookingHindrance": False,
            "ignoreDebt": False,
            "licenceId": license_type,
            "paymentIsActive": False,
            "paymentReference": None,
            "paymentUrl": None,
            "rescheduleTypeId": 0,
            "socialSecurityNumber": SSN
        },
        "occasionBundleQuery": None
    }
def getQueryDate():
    return datetime.datetime.now().strftime("%Y-%m-%dT00:00:00.000Z")
    #return "2020-06-13T22:00:00.000Z"
    
def build_kunskapsprov_query(location):
    q = _build_search_query(license_type=LICENSE_ID_B)
    q["occasionBundleQuery"] = {
            "examinationTypeId": KUNSKAPSPROV_ID,
            "languageId": SWELANG_ID,
            "locationId": location,
            "occasionChoiceId": 1,
            "startDate": getQueryDate(),
            "tachographTypeId": 1
        }
    return q;

def build_korprov_query(location):
    q = _build_search_query(license_type=LICENSE_ID_B)
    q["occasionBundleQuery"] = {
        "startDate":getQueryDate(),
        "locationId":location,
        "languageId":SWELANG_ID,
        "vehicleTypeId":VHEICLE_AUTOMAT,
        "tachographTypeId":1,
        "occasionChoiceId":1,
        "examinationTypeId":KORPROV_ID}
    
    return q;

def get_result_data(tider, min_date, max_date, seen_last_time, seen_this_time):
    for tid in tider["data"]:
        if len(tid["occasions"]) != 1:
            dump_debug_info("multi_occasions",tider)
        tid = tid["occasions"][0]
        if tid["isLateCancellation"]:
            dump_debug_info("isLateCancellation", tider)
            
        date_parsed = datetime.datetime.strptime(tid["date"], '%Y-%m-%d')
        
        out = "%s, %s, %s %s"%(tid["name"],tid["locationName"],tid["date"],tid["time"])
        seen_this_time.add(out)
        if date_parsed > max_date or date_parsed  < min_date or out in seen_last_time:
            continue
        
        yield out

info = make_post_request(search_info_url,search_info_data)
if len(sys.argv) == 2 and sys.argv[1] == "search":
    for location in info["data"]["locations"]:
        location = location["location"]
        print("%s - id: %d"%(location["name"],location["id"]))
    sys.exit(0)

def dump_debug_info(name, data):
    with open(LOGFILEFORMAT%(name,getQueryDate()),"w") as f:
        f.write(json.dumps(data,indent=4,sort_keys=True))

seen_last_time = set()
seen_this_time = set()
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE,'r') as f:
        for line in f.read().splitlines():
            seen_last_time.add(line)
output = []
for (name,id) in locationmap.items():
    if name in locationmap_korprov:
        time.sleep(1)
        korprov_tider = make_post_request(time_info_url,build_korprov_query(id))        
        for out in get_result_data(korprov_tider, earliest_booking_korprov, current_booking_korprov, seen_last_time, seen_this_time):
            if out not in output:
                output.append(out)
                
    time.sleep(1)
    kunskapsprov_tider = make_post_request(time_info_url,build_kunskapsprov_query(id))
    for out in get_result_data(kunskapsprov_tider, earliest_booking_teoriprov, current_booking_teoriprov, seen_last_time, seen_this_time):
        if out not in output:
            output.append(out)

if len(output) != 0:
    print("Mailing output!")
    mail_swaks(mail_server, mail_port, mail_user, mail_password, mail_to, mail_from, mail_subject, "\n\n".join(output))
    
with open(SEEN_FILE,"w") as f:
    for line in list(seen_this_time):
        f.write(line + "\n")

