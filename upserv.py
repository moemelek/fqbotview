#!/usr/bin/env python
#pip install fabric

#using hosts defined in /home/rickard/.ssh/config

from fabric import Connection
from fabric import SerialGroup as Group
from getpass import getpass

HOSTS = Group('amd1','amd2','amd3','amd4','arm2','vultr')

def list_bot_info(c):
  if c.original_host == "vultr":
    pswd = getpass('SUDO password:')
    if pswd != "":
    	result = c.sudo('./bot.py q', password=pswd)
    else:
	print "Skipping..."
  else:
    result = c.run('./bot.py q')

def update_aliases(c):
  print "Copying alias file..."
  c.put('.bash_aliases', '')

def update_script(c):
  print "Copying script file..."
  c.put('ftbotview/bot.py', '')

def get_server_info(c):
  result = c.run('uname -n')
  result = c.run('date')

def iterate_servers(option):
  print
  for connection in HOSTS:
    print "Connecting to: " + connection.original_host + " @ " + connection.host
    if option == "1":
      list_bot_info(connection)
    if option == "2":
      update_aliases(connection)
    if option == "3":
      update_script(connection)
    if option == "4":
      get_server_info(connection)
    print 

print "1 - List all bots on all servers"
print "2 - Update alias file on all servers"
print "3 - Update bot.py on all servers"
print "4 - Get info from all servers"

command = "foo"
while command != "":
  command = raw_input(">> ")
  if command == "1":
    iterate_servers("1")
  if command == "2":
    ans = raw_input("Update >> aliases << to servers? (y/N) : ")
    if ans == "Y" or ans == "y":
      iterate_servers("2")
  if command == "3":
    ans = raw_input("Update >> bot.py << to servers? (y/N) : ")
    if ans == "Y" or ans == "y":
      iterate_servers("3")
  if command == "4":
    iterate_servers("4")

print
print "Done"
