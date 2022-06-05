#!/usr/bin/env python

# This is a simple web server for a traffic counting application.
# It's your job to extend it by adding the backend functionality to support
# recording the traffic in a SQL database. You will also need to support
# some predefined users and access/session control. You should only
# need to extend this file. The client side code (html, javascript and css)
# is complete and does not require editing or detailed understanding.

# import the various libraries needed
import http.cookies as Cookie # some cookie handling support
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import TextIOBase # the heavy lifting of the web server
import urllib # some url parsing support
import json # support for json encoding
import sys # needed for agument handling
import os
import sqlite3
import string
import random
import time 
import datetime
import dateutil.relativedelta 

def access_database(dbfile, query, tup_values):
    connect = sqlite3.connect(dbfile)
    cursor = connect.cursor()
    cursor.execute(query,tup_values)
    connect.commit()
    connect.close()
    
def access_database_with_result(dbfile, query, tup_values):
    connect = sqlite3.connect(dbfile)
    cursor = connect.cursor()
    rows = cursor.execute(query, tup_values).fetchall()
    connect.commit()
    connect.close()
    return rows

# def create_table(dbfile):
#     access_database(dbfile,"CREATE TABLE IF NOT EXISTS users (userid INTEGER PRIMARY KEY, username TEXT NOT NULL, password TEXT NOT NULL)",())
#     access_database(dbfile, "CREATE TABLE IF NOT EXISTS session (sessionid INTEGER PRIMARY KEY, userid INTEGER, magic TEXT NOT NULL, start INTEGER, end INTEGER)",())
#     access_database(dbfile, "CREATE TABLE IF NOT EXISTS traffic (recordid INTEGER PRIMARY KEY, sessionid INTEGER, time INTEGER, type INTEGER, occupancy INTEGER, location TEXT NOT NULL, mode INTEGER)",())

#     access_database(dbfile, "INSERT INTO users VALUES(1,'test1','password1')",())
#     access_database(dbfile, "INSERT INTO users VALUES(2,'test2','password2')",())
#     access_database(dbfile, "INSERT INTO users VALUES(3,'test3','password3')",())
#     access_database(dbfile,"INSERT INTO users VALUES(4,'test4','password4')",())
#     access_database(dbfile, "INSERT INTO users VALUES(5,'test5','password5')",())
#     access_database(dbfile, "INSERT INTO users VALUES(6,'test6','password6')",())
#     access_database(dbfile, "INSERT INTO users VALUES(7,'test7','password7')",())
#     access_database(dbfile, "INSERT INTO users VALUES(8,'test8','password8')",())
#     access_database(dbfile, "INSERT INTO users VALUES(9,'test9','password9')",())
#     access_database(dbfile, "INSERT INTO users VALUES(10,'test10','password10')",())

# create_table("traffic.db")

def build_response_refill(where, what): #refill the same page needed to be reloaded with something defined in function??
    """This function builds a refill action that allows part of the
       currently loaded page to be replaced."""
    return {"type":"refill","where":where,"what":what}


def build_response_redirect(where): #redirects users to the page defined
    """This function builds the page redirection action
       It indicates which page the client should fetch.
       If this action is used, only one instance of it should
       contained in the response and there should be no refill action."""
    return {"type":"redirect", "where":where}

def handle_validate(iuser, imagic): 
    """Decide if the combination of user and magic is valid"""
    ## alter as required
    validate = access_database_with_result("traffic.db",'SELECT * FROM session JOIN users ON session.userid=users.userid WHERE users.username = ? and session.magic = ? ',(iuser,imagic))
    if len(validate)>0:
        return True
    else:
        return False

def handle_delete_session(iuser, imagic):
    """Remove the combination of user and magic from the data base, ending the login"""
    now = int(time.time()) 
    access_database("traffic.db","UPDATE session SET end = ? WHERE magic = ? ",(now,imagic))
    return

def magic_token_generator(size = 10, chars = string.digits + string.ascii_lowercase):
    return ''.join(random.choice(chars) for _ in range(size))

def handle_login_request(iuser, imagic, parameters):
    """A user has supplied a username (parameters['usernameinput'][0])
       and password (parameters['passwordinput'][0]) check if these are
       valid and if so, create a suitable session record in the database
       with a random magic identifier that is returned.
       Return the username, magic identifier and the response action set."""
    
    if handle_validate(iuser, imagic) == True: 
        #checking if user and magic is true
        #the user is already logged in, so end the existing session.
        handle_delete_session(iuser, imagic) #close the login page
    
    response = []
    
    if len(parameters)!=4:
        response.append(build_response_refill('message', 'Please enter username and password'))
        user = '!'
        magic = ''

    else:

        previous_session_of_existing_user = access_database_with_result("traffic.db","SELECT session.sessionid FROM session JOIN users ON session.userid = users.userid WHERE users.username = ? and session.end = 0",(parameters['usernameinput'][0],))
        #print(previous_session_of_existing_user)
        now = int(time.time())
        if len(previous_session_of_existing_user) > 0:
            access_database("traffic.db","UPDATE session SET end = ? WHERE sessionid = ?", (now,previous_session_of_existing_user[0][0])) 
        
        username_password_database = access_database_with_result("traffic.db", "SELECT userid FROM users WHERE username = ? and password = ? ",(parameters['usernameinput'][0],parameters['passwordinput'][0]))
        if len(username_password_database) > 0:
            response.append(build_response_redirect('/page.html')) 
            magic = magic_token_generator()
            user = parameters['usernameinput'][0] 
            access_database("traffic.db", "INSERT INTO session (userid, magic, start, end) VALUES(?,?,?, 0)",(username_password_database[0][0],magic,now))

        else: ## The user is not valid
            response.append(build_response_refill('message', 'Invalid password'))
            user = '!'
            magic = ''
    
    return [user, magic, response]

def handle_add_request(iuser, imagic, parameters):
    """The user has requested a vehicle be added to the count
       parameters['locationinput'][0] the location to be recorded
       parameters['occupancyinput'][0] the occupant count to be recorded
       parameters['typeinput'][0] the type to be recorded
       Return the username, magic identifier (these can be empty  strings) and the response action set."""
    
    response = []
    ## alter as required
    
    if handle_validate(iuser, imagic) != True:
        #Invalid sessions redirect to login
        response.append(build_response_redirect('/index.html'))
    
    else: ## a valid session so process the addition of the entry.

        if parameters['typeinput'][0] == 'car':
            parameters['typeinput'][0] = 0
        elif parameters['typeinput'][0] == 'van':
            parameters['typeinput'][0] = 1
        elif parameters['typeinput'][0] == 'truck':
            parameters['typeinput'][0] = 2
        elif parameters['typeinput'][0] == 'taxi':
            parameters['typeinput'][0] = 3
        elif parameters['typeinput'][0] == 'other':
            parameters['typeinput'][0] = 4
        elif parameters['typeinput'][0] == 'motorbike':
            parameters['typeinput'][0] = 5
        elif parameters['typeinput'][0] == 'bicycle':
            parameters['typeinput'][0] = 6
        elif parameters['typeinput'][0] == 'bus':
            parameters['typeinput'][0] = 7
            
        type_list = [0,1,2,3,4,5,6,7]
        occupancy_list = [1,2,3,4]
        location_avoided_characters = list(string.punctuation + string.ascii_uppercase) 
        digits_spaces_list  =  list(string.digits + " ")

        session_id_list = access_database_with_result("traffic.db","SELECT sessionid FROM session WHERE magic = ? ",(imagic,))  
        count = access_database_with_result("traffic.db","SELECT COUNT(type) FROM traffic WHERE sessionid = ? and mode = 1",(session_id_list[0][0],))      
    
        if len(parameters)==5:

            if parameters['typeinput'][0] not in type_list and parameters['occupancyinput'][0] not in occupancy_list:
                response.append(build_response_refill('message', 'Entry invalid.'))
                response.append(build_response_refill('total', str(count[0][0])))
            
            elif any([char in location_avoided_characters for char in parameters['locationinput'][0]])==True:
                response.append(build_response_refill('message', 'Entry invalid.'))
                response.append(build_response_refill('total', str(count[0][0])))
            
            elif all([char in digits_spaces_list for char in parameters['locationinput'][0]])==True:
                response.append(build_response_refill('message', 'Entry invalid.'))
                response.append(build_response_refill('total', str(count[0][0])))

            else:
                now = int(time.time())
                access_database("traffic.db","INSERT into traffic(sessionid,time,type,occupancy,location,mode) VALUES(?,?,?,?,?,1)",(session_id_list[0][0],now,parameters['typeinput'][0],parameters['occupancyinput'][0], parameters['locationinput'][0]))
                response.append(build_response_refill('message', 'Entry added.'))
                count = access_database_with_result("traffic.db","SELECT COUNT(type) FROM traffic WHERE sessionid = ? and mode = 1",(session_id_list[0][0],))
                response.append(build_response_refill('total', str(count[0][0])))    
        else:
            response.append(build_response_refill('message', 'Entry invalid.'))
            response.append(build_response_refill('total', str(count[0][0])))

    user = iuser
    magic = imagic
    print(parameters)
    return [user, magic, response]
    
    

def handle_undo_request(iuser, imagic, parameters):
    """The user has requested a vehicle be removed from the count
       This is intended to allow counters to correct errors.
       parameters['locationinput'][0] the location to be recorded
       parameters['occupancyinput'][0] the occupant count to be recorded
       parameters['typeinput'][0] the type to be recorded
       Return the username, magic identifier (these can be empty  strings) and the response action set."""
    response = []
    ## alter as required
    
    if handle_validate(iuser, imagic) != True:
        #Invalid sessions redirect to login
        response.append(build_response_redirect('/index.html'))
    
    else: ## a valid session so process the recording of the entry.
        if parameters['typeinput'][0] == 'car':
                parameters['typeinput'][0] = 0
        elif parameters['typeinput'][0] == 'van':
                parameters['typeinput'][0] = 1
        elif parameters['typeinput'][0] == 'truck':
                parameters['typeinput'][0] = 2
        elif parameters['typeinput'][0] == 'taxi':
                parameters['typeinput'][0] = 3
        elif parameters['typeinput'][0] == 'other':
                parameters['typeinput'][0] = 4
        elif parameters['typeinput'][0] == 'motorbike':
                parameters['typeinput'][0] = 5
        elif parameters['typeinput'][0] == 'bicycle':
                parameters['typeinput'][0] = 6
        elif parameters['typeinput'][0] == 'bus':
                parameters['typeinput'][0] = 7

        type_list = [0,1,2,3,4,5,6,7]
        occupancy_list = [1,2,3,4]
        location_avoided_characters = list(string.punctuation + string.ascii_uppercase)
        digits_spaces_list  =  list(string.digits + " ") 
        session_id_list = access_database_with_result("traffic.db","SELECT sessionid FROM session WHERE magic = ? ",(imagic,))
        count = access_database_with_result("traffic.db","SELECT COUNT(type) FROM traffic WHERE sessionid = ? and mode = 1",(session_id_list[0][0],))
        
        if len(parameters)==5:
            
            if parameters['typeinput'][0] not in type_list and parameters['occupancyinput'][0] not in occupancy_list:
                response.append(build_response_refill('message', 'Entry invalid.'))
                response.append(build_response_refill('total', str(count[0][0])))
            
            if any([char in location_avoided_characters for char in parameters['locationinput'][0]])==True:
                response.append(build_response_refill('message', 'Entry invalid.'))
                response.append(build_response_refill('total', str(count[0][0])))
            
            if all([char in digits_spaces_list for char in parameters['locationinput'][0]])==True:
                response.append(build_response_refill('message', 'Entry invalid.'))
                response.append(build_response_refill('total', str(count[0][0])))
        
            traffic_exist = access_database_with_result("traffic.db","SELECT * FROM traffic WHERE sessionid = ? and type = ? and occupancy = ? and location = ? order by time desc limit 1", (session_id_list[0][0],parameters['typeinput'][0],parameters['occupancyinput'][0],parameters['locationinput'][0]))
            
            if len(traffic_exist) > 0:
                access_database("traffic.db","UPDATE traffic SET mode = 2 WHERE recordid = ? and sessionid = ? and type = ? and occupancy = ? and location = ? ",(traffic_exist[0][0],traffic_exist[0][1],traffic_exist[0][3],traffic_exist[0][4],traffic_exist[0][5]))
                access_database("traffic.db","INSERT into traffic(sessionid,time,type,occupancy,location,mode) VALUES(?,?,?,?,?,0)",(traffic_exist[0][1],traffic_exist[0][2],traffic_exist[0][3],traffic_exist[0][4],traffic_exist[0][5]))
                response.append(build_response_refill('message', 'Entry Un-done.'))
                count = access_database_with_result("traffic.db","SELECT COUNT(type) FROM traffic WHERE sessionid = ? and mode = 1", (traffic_exist[0][1],))
                response.append(build_response_refill('total', str(count[0][0])))
            
            else:
                response.append(build_response_refill('message', 'Entry invalid.'))
                response.append(build_response_refill('total', str(count[0][0])))
        else:
            response.append(build_response_refill('message', 'Entry invalid.'))
            response.append(build_response_refill('total', str(count[0][0])))

    user = ''
    magic = ''
    return [user, magic, response]


def handle_back_request(iuser, imagic, parameters):
    """This code handles the selection of the back button on the record form (page.html)
       You will only need to modify this code if you make changes elsewhere that break its behaviour"""
    response = []
    ## alter as required
    if handle_validate(iuser, imagic) != True:
        response.append(build_response_redirect('/index.html'))
    else:
        response.append(build_response_redirect('/summary.html'))
    user = ''
    magic = ''
    return [user, magic, response]


def handle_logout_request(iuser, imagic, parameters):
    """This code handles the selection of the logout button on the summary page (summary.html)
       You will need to ensure the end of the session is recorded in the database
       And that the session magic is revoked."""
    response = []
    ## alter as required
    if handle_validate(iuser, imagic) != True:
        response.append(build_response_redirect('/index.html'))
    else:
        now = int(time.time())
        access_database("traffic.db","UPDATE session SET end = ? WHERE magic = ?", (now,imagic))
        response.append(build_response_redirect('/index.html'))
    user = '!'
    magic = ''
    return [user, magic, response]


def handle_summary_request(iuser, imagic, parameters):
    """This code handles a request for an update to the session summary values.
       You will need to extract this information from the database.
       You must return a value for all vehicle types, even when it's zero."""
    response = []
    ## alter as required
    if handle_validate(iuser, imagic) != True:
        response.append(build_response_redirect('/index.html'))
    
    else:
        
        session_id_list = access_database_with_result("traffic.db","SELECT sessionid FROM session WHERE magic = ? ", (imagic,))

        car_total = access_database_with_result("traffic.db", "SELECT COUNT(type) FROM traffic WHERE type = 0 and sessionid = ? and mode = 1",(session_id_list[0][0],))
        taxi_total = access_database_with_result("traffic.db", "SELECT COUNT(type) FROM traffic WHERE type = 3 and sessionid = ? and mode = 1",(session_id_list[0][0],))
        bus_total = access_database_with_result("traffic.db", "SELECT COUNT(type) FROM traffic WHERE type = 7 and sessionid = ? and mode = 1",(session_id_list[0][0],))
        motorcycle_total = access_database_with_result("traffic.db", "SELECT COUNT(type) FROM traffic WHERE type = 5 and sessionid = ? and mode = 1",(session_id_list[0][0],))
        bicycle_total = access_database_with_result("traffic.db", "SELECT COUNT(type) FROM traffic WHERE type = 6 and sessionid = ? and mode = 1",(session_id_list[0][0],))
        van_total = access_database_with_result("traffic.db", "SELECT COUNT(type) FROM traffic WHERE type = 1 and sessionid = ? and mode = 1",(session_id_list[0][0],))
        truck_total = access_database_with_result("traffic.db", "SELECT COUNT(type) FROM traffic WHERE type = 2 and sessionid = ? and mode = 1", (session_id_list[0][0],))
        other_total = access_database_with_result("traffic.db", "SELECT COUNT(type) FROM traffic WHERE type = 4 and sessionid = ? and mode = 1 ", (session_id_list[0][0],))
        total_vehicles_recorded = access_database_with_result("traffic.db", "SELECT COUNT(type) FROM traffic WHERE sessionid = ? and mode = 1", (session_id_list[0][0],))
        
        response.append(build_response_refill('sum_car', str(car_total[0][0])))
        response.append(build_response_refill('sum_taxi', str(taxi_total[0][0])))
        response.append(build_response_refill('sum_bus', str(bus_total[0][0])))
        response.append(build_response_refill('sum_motorbike', str(motorcycle_total[0][0])))
        response.append(build_response_refill('sum_bicycle', str(bicycle_total[0][0])))
        response.append(build_response_refill('sum_van', str(van_total[0][0])))
        response.append(build_response_refill('sum_truck', str(truck_total[0][0])))
        response.append(build_response_refill('sum_other', str(other_total[0][0])))
        response.append(build_response_refill('total', str(total_vehicles_recorded[0][0])))
        user = iuser
        magic = imagic
    
    return [user, magic, response]


# HTTPRequestHandler class
class myHTTPServer_RequestHandler(BaseHTTPRequestHandler):

    # GET This function responds to GET requests to the web server.
    def do_GET(self):

        # The set_cookies function adds/updates two cookies returned with a webpage.
        # These identify the user who is logged in. The first parameter identifies the user
        # and the second should be used to verify the login session.
        def set_cookies(x, user, magic):
            ucookie = Cookie.SimpleCookie()
            ucookie['u_cookie'] = user
            x.send_header("Set-Cookie", ucookie.output(header='', sep=''))
            mcookie = Cookie.SimpleCookie()
            mcookie['m_cookie'] = magic
            x.send_header("Set-Cookie", mcookie.output(header='', sep=''))

        # The get_cookies function returns the values of the user and magic cookies if they exist
        # it returns empty strings if they do not.
        def get_cookies(source):
            rcookies = Cookie.SimpleCookie(source.headers.get('Cookie'))
            user = ''
            magic = ''
            for keyc, valuec in rcookies.items():
                if keyc == 'u_cookie':
                    user = valuec.value
                if keyc == 'm_cookie':
                    magic = valuec.value
            return [user, magic]

        # Fetch the cookies that arrived with the GET request
        # The identify the user session.
        user_magic = get_cookies(self)

        print(user_magic)

        # Parse the GET request to identify the file requested and the parameters
        parsed_path = urllib.parse.urlparse(self.path)

        # Decided what to do based on the file requested.

        # Return a CSS (Cascading Style Sheet) file.
        # These tell the web client how the page should appear.
        if self.path.startswith('/css'):
            self.send_response(200)
            self.send_header('Content-type', 'text/css')
            self.end_headers()
            with open('.'+self.path, 'rb') as file:
                self.wfile.write(file.read())
            file.close()

        # Return a Javascript file.
        # These tell contain code that the web client can execute.
        elif self.path.startswith('/js'):
            self.send_response(200)
            self.send_header('Content-type', 'text/js')
            self.end_headers()
            with open('.'+self.path, 'rb') as file:
                self.wfile.write(file.read())
            file.close()

        # A special case of '/' means return the index.html (homepage)
        # of a website
        elif parsed_path.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('./index.html', 'rb') as file:
                self.wfile.write(file.read())
            file.close()

        # Return html pages.
        elif parsed_path.path.endswith('.html'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('.'+parsed_path.path, 'rb') as file:
                self.wfile.write(file.read())
            file.close()

        # The special file 'action' is not a real file, it indicates an action
        # we wish the server to execute.
        elif parsed_path.path == '/action':
            self.send_response(200) #respond that this is a valid page request
            # extract the parameters from the GET request.
            # These are passed to the handlers.
            parameters = urllib.parse.parse_qs(parsed_path.query)

            if 'command' in parameters:
                # check if one of the parameters was 'command'
                # If it is, identify which command and call the appropriate handler function.
                if parameters['command'][0] == 'login':
                    [user, magic, response] = handle_login_request(user_magic[0], user_magic[1], parameters)
                    #The result of a login attempt will be to set the cookies to identify the session.
                    set_cookies(self, user, magic)
                elif parameters['command'][0] == 'add':
                    [user, magic, response] = handle_add_request(user_magic[0], user_magic[1], parameters)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')
                elif parameters['command'][0] == 'undo':
                    [user, magic, response] = handle_undo_request(user_magic[0], user_magic[1], parameters)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')
                elif parameters['command'][0] == 'back':
                    [user, magic, response] = handle_back_request(user_magic[0], user_magic[1], parameters)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')
                elif parameters['command'][0] == 'summary':
                    [user, magic, response] = handle_summary_request(user_magic[0], user_magic[1], parameters)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')
                elif parameters['command'][0] == 'logout':
                    [user, magic, response] = handle_logout_request(user_magic[0], user_magic[1], parameters)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')
                else:
                    # The command was not recognised, report that to the user.
                    response = []
                    response.append(build_response_refill('message', 'Internal Error: Command not recognised.'))

            else:
                # There was no command present, report that to the user.
                response = []
                response.append(build_response_refill('message', 'Internal Error: Command not found.'))

            text = json.dumps(response)
            print(text)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(bytes(text, 'utf-8'))

        elif self.path.endswith('/statistics/hours.csv'):
            ## if we get here, the user is looking for a statistics file
            ## this is where requests for /statistics/hours.csv should be handled.
            ## you should check a valid user is logged in. You are encouraged to wrap this behavour in a function.
            #Start with daily values for the amount of time test1 logged in
            response = []
            
            if handle_validate(user_magic[0],user_magic[1])!=True:
                response.append(build_response_redirect('/index.html'))
            
            else:
                end_of_day_week_month = access_database_with_result("traffic.db","SELECT MAX(session.end) FROM session",())
                end_of_date = datetime.datetime.fromtimestamp(end_of_day_week_month [0][0]).strftime('%Y-%m-%d')
                start_of_date = datetime.datetime.strptime(end_of_date, "%Y-%m-%d")
                start_of_day = time.mktime(start_of_date.timetuple())
                # print(end_of_day_week_month)
                # print(end_of_date)
                # print(type(start_of_date))
                # print(start_of_day)

                start_of_week = start_of_date - dateutil.relativedelta.relativedelta(days = 6) 
                #print(start_of_week)
                start_of_week_secs = time.mktime(start_of_week.timetuple())
                #print(start_of_week_secs)

                start_of_month = start_of_date + dateutil.relativedelta.relativedelta(months= -1,days = 1) 
                #print(start_of_month)
                start_of_month_secs = time.mktime(start_of_month.timetuple())
                #print(start_of_month_secs)
                
                userid_list = access_database_with_result("traffic.db","SELECT username,userid FROM users",())
                #print(userid_list)
                text = "Username,Day,Week,Month\n"
                
                for user in userid_list:
                    check_for_active_session = access_database_with_result("traffic.db","SELECT MAX(end) FROM session WHERE userid = ? ",(user[1],))
                    
                    if check_for_active_session[0][0]==0:
                        day = 0
                        week = 0
                        month = 0
                    
                    else:
                        
                        day=0
                        week=0
                        month=0
                        
                        day_hours = access_database_with_result("traffic.db","SELECT start,end FROM session WHERE userid = ? and end <= ? and start >= ? and end!=0",(user[1],end_of_day_week_month[0][0],start_of_day))
                        for s in day_hours:
                            if s[0]>=start_of_day:
                                day+=s[1]-s[0]
                            else:
                                day+=s[1]-start_of_day
                        day = round(day/3600,1)     
                        week_hours = access_database_with_result("traffic.db","SELECT start,end FROM session WHERE userid = ? and end <= ? and start >= ? and end!=0", (user[1],end_of_day_week_month[0][0],start_of_week_secs))
                        for s in week_hours:
                            if s[0]>=start_of_week_secs:
                                week+=s[1]-s[0]
                            else:
                                week+=s[1]-start_of_week_secs
                        week = round(week/3600,1)
                        month_hours = access_database_with_result("traffic.db","SELECT start,end FROM session WHERE userid = ? and end <= ? and start >= ? and end!=0",(user[1],end_of_day_week_month[0][0],start_of_month_secs))
                        for s in month_hours:
                            if s[0]>=start_of_month_secs:
                                month+=s[1]-s[0]
                            else:
                                month+=s[1]-start_of_month_secs
                        month = round(month/3600,1)

                    data_list = [str(user[0]), str(day),str(week),str(month)]
                    count = ",".join(data_list)
                    text += count + "\n"

            encoded = bytes(text, 'utf-8')
            self.send_response(200)
            self.send_header('Content-type', 'text/csv')
            self.send_header("Content-Disposition", 'attachment; filename="{}"'.format('hours.csv'))
            self.send_header("Content-Length", len(encoded))
            self.end_headers()
            self.wfile.write(encoded)
    
        
        elif self.path.endswith('/statistics/traffic.csv'):
            ## if we get here, the user is looking for a statistics file
            ## this is where requests for  /statistics/traffic.csv should be handled.
            ## you should check a valid user is checked in. You are encouraged to wrap this behavour in a function.
            response = []
            
            if handle_validate(user_magic[0],user_magic[1])!=True:
                response.append(build_response_redirect('/index.html'))

            else:

                time_max = access_database_with_result("traffic.db","SELECT MAX(time) FROM traffic WHERE mode = 1",())
                #print(time_max)
                max_date = datetime.datetime.fromtimestamp(time_max[0][0]).strftime('%Y-%m-%d')
                time_min = time.mktime(datetime.datetime.strptime(max_date, "%Y-%m-%d").timetuple()) 
                #print(time_min)
                location_data = access_database_with_result("traffic.db","SELECT distinct(location) FROM traffic WHERE mode = 1 and time <= ? and time >= ?",(time_max[0][0],time_min))
                print(location_data)
                type_data = access_database_with_result("traffic.db","SELECT distinct(type) FROM traffic WHERE mode = 1 and time <= ? and time >= ? ", (time_max[0][0],time_min))
                #print(type_data)
                text = "Location,Type,Occupancy1,Occupancy2,Occupancy3,Occupancy4\n"
                
                for i in location_data:
                    for j in type_data:
                        occupancy1_count = access_database_with_result("traffic.db","SELECT COUNT(occupancy) FROM traffic WHERE occupancy = 1 and type = ? and location = ? and mode =1 and time <= ? and time >= ?", (j[0],i[0],time_max[0][0],time_min))
                        occupancy2_count = access_database_with_result("traffic.db","SELECT COUNT(occupancy) FROM traffic WHERE occupancy = 2 and type = ? and location = ? and mode =1 and time <= ? and time >= ? ", (j[0],i[0],time_max[0][0],time_min))
                        occupancy3_count = access_database_with_result("traffic.db","SELECT COUNT(occupancy) FROM traffic WHERE occupancy = 3 and type = ? and location = ? and mode =1 and time <= ? and time >= ?", (j[0],i[0],time_max[0][0],time_min))
                        occupancy4_count = access_database_with_result("traffic.db","SELECT COUNT(occupancy) FROM traffic WHERE occupancy = 4 and type = ? and location = ? and mode =1 and time <= ? and time >= ?", (j[0],i[0],time_max[0][0],time_min))
                        
                        if occupancy1_count[0][0]==0 and occupancy2_count[0][0]==0 and occupancy3_count[0][0]==0 and occupancy4_count[0][0]==0:
                            continue
                        
                        else:
                            data_list = [str(i[0]) ,str(j[0]),str(occupancy1_count[0][0]),str(occupancy2_count[0][0]),str(occupancy3_count[0][0]),str(occupancy4_count[0][0])]
                            count = ",".join(data_list)
                            text += count + "\n"

            encoded = bytes(text, 'utf-8')
            self.send_response(200)
            self.send_header('Content-type', 'text/csv')
            self.send_header("Content-Disposition", 'attachment; filename="{}"'.format('traffic.csv'))
            self.send_header("Content-Length", len(encoded))
            self.end_headers()
            self.wfile.write(encoded)

        else:
            # A file that doesn't fit one of the patterns above was requested.
            self.send_response(404)
            self.end_headers()
        return

def run():
    """This is the entry point function to this code."""
    print('starting server...')
    ## You can add any extra start up code here
    # Server settings
    # Choose port 8081 over port 80, which is normally used for a http server
    if(len(sys.argv)<2): # Check we were given both the script name and a port number
        print("Port argument not provided.")
        return
    server_address = ('127.0.0.1', int(sys.argv[1]))
    httpd = HTTPServer(server_address, myHTTPServer_RequestHandler)
    print('running server on port =',sys.argv[1],'...')
    httpd.serve_forever() # This function will not return till the server is aborted.

run()
