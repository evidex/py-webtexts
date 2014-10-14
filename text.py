#! /usr/bin/env python

# Simple Script to send texts using Three
# Ireland's webtext form.
import argparse
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import tempfile
import subprocess
import os
import csv

VERBOSE = False
EDITOR = "vim"
PHONEBOOK_PATH = "PATH_TO_PHONEBOOK"
# Read number of rows and columns in terminal
ROWS, COLUMNS = os.popen('stty size', 'r').read().split()

LOGIN_USER = "USER_PHONE_NUM"
LOGIN_PASS = "USER_PIN"

URL_BASE = "https://webtexts.three.ie/webtext"
LOGIN_STUB = "/users/login"
LOGOUT_STUB = "/users/logout"
SEND_STUB = "/messages/send"

#############
# Functions #
#############
def readPhoneBook(PHONEBOOK_PATH):
    """ Reads a CSV phone book file of names and phone numbers

    Params:
        PHONEBOOK_PATH - Path of file to read

    Returns:
        Dictionary of phone numbers, indexed by names
    """
    phoneBook = {}
    with open(PHONEBOOK_PATH) as f:
        reader = csv.reader(f, delimiter=",")
        for row in reader:
            phoneBook[row[0].lower()] = row[1]
    return phoneBook


def printMenu(phoneBook):
    """ Prints a menu to allow user to select a number from phoneBook.

    Params:
        phoneBook - Dictionary of phone numbers, indexed by names

    Returns:
        Tuple of (name, phone number)
    """
    print "Select text message recipient"
    print("-"*int(COLUMNS))
    for name, number in phoneBook.iteritems():
       print "{}\t-\t{}".format(name, number)
    print("-"*int(COLUMNS))
    while True:
        try:
            sel = raw_input("Name -> ").lower()
        except KeyboardInterrupt:
            print "\nBye Bye!"
            sys.exit(0)
        if sel in phoneBook:
            return (sel, phoneBook[sel])
        else:
            print "Name not recognised, please try again."

def createMessage():
    """ Creates a temporary file and opens in using EDITOR. Once EDITOR is saved and closed, the file is read
    and its contents returned.
    """
    # Create a temp file to write to
    tmpFile = tempfile.NamedTemporaryFile(mode="w+t", delete=False)
    tmpFile.close()
    # Open the file using EDITOR
    subprocess.call([EDITOR, tmpFile.name])
    # Read and return the contents of tmpFile
    with open(tmpFile.name) as f:
        return f.read()

def login(session):
    # Get the login token
    r = session.get(URL_BASE+LOGIN_STUB)
    #print r.status_code
    soup = BeautifulSoup(r.text)
    tokens = {}
    tokens["data[_Token][key]"] = soup.find_all("input", attrs={"name": "data[_Token][key]"})[0].attrs["value"]
    # Send login request
    data = {"_method": "POST",
            "data[User][telephoneNo]": LOGIN_USER,
            "data[User][pin]": LOGIN_PASS
            }
    data.update(tokens)
    #print "Logging in"
    r = session.post(URL_BASE+LOGIN_STUB, data=data)
    #print r.status_code
    #print "Finding token fields"
    soup = BeautifulSoup(r.text)
    tokens["data[_Token][fields]"] = soup.find_all("input", attrs={"name": "data[_Token][fields]"})[0].attrs["value"]
    tokens["data[_Token][unlocked]"] = soup.find_all("input", attrs={"name": "data[_Token][unlocked]"})[0].attrs["value"]
    return tokens

def sendText(session, tokens, message, recipients=[], schedule=False):
    """
    Send request to Three.ie webtext server.

    Re-uses HTTP session session to ensure user logged in.

    Params:
        session     - HTTP session
        tokens      - Login tokens returned by login()
        message     - Message to send
        recipients  - List of phone numbers (strings) up to three, to send message to
        schedule    - Not implemented
    """
    # Generate form data
    data = {"data[Message][message]": message,
            "data[Message][recipients_contacts]": "",
            "data[Message][schedule]": 0,
            "data[Message][schedule_date][day]": "",
            "data[Message][schedule_date][month]": "",
            "data[Message][schedule_date][year]": "",
            "data[Message][schedule_date][hour]": "",
            "data[Message][schedule_date][min]": "",
            "data[Message][schedule_date][meridian]": "",
           }
    for i in xrange(3):
        try:
            number = recipients[i]
        except:
            number = ""
        data.update({"data[Message][recipients_individual]["+str(i)+"]": number})
    data.update(tokens)
    # Send the requests
    r = session.post(URL_BASE+SEND_STUB, data=data)
    #print r.status_code
    # Find remaining number of texts
    soup = BeautifulSoup(r.text)
    ul = soup.find_all("ul", attrs={"class":"webtext"})[0]
    li = list(ul.children)[3]
    remaining = li.p.text
    return remaining

########
# Main #
########
if __name__ == "__main__":
    # Setup Argparse
    parser = argparse.ArgumentParser(description="Send texts using Three IE Webtexts.",
                                     prog="text.py")
    parser.add_argument("--recipients", "-r", nargs="+",
                        help="Phone numbers to send the message to. Eg: 0860674284")
    parser.add_argument("--message", "-m",
                        help="The message to send")
    # Parse arguments
    args = parser.parse_args()
    # Create HTTP session
    session = requests.session()
    # Login to Webtexts
    tokens = login(session)
    # Send text
    name = ""
    if args.message:
        recipients = args.recipients
        message = args.message
    else:
        print "Reading phone book"
        phoneBook = readPhoneBook(PHONEBOOK_PATH)
        name, number = printMenu(phoneBook)
        recipients = [number]
        message = createMessage()
    remaining = sendText(session, tokens, message, recipients=recipients)
    print "Sent text '{}' to {}".format(message[:50].replace("\n", " "), name if name else recipients)
    print "Remaining texts: " + remaining
