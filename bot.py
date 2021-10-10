#!/usr/bin/env python

#---------------------------------------------------
#FtBotView - https://github.com/moemelek/fqbotview
#---------------------------------------------------

#Requires these lib:   
#ALERT: make sure to install packages as SUDO if running as SUDO
#sudo pip install pyyaml
#sudo pip install colorama
#sudo pip install prettytable

import yaml
import sys
import time
import datetime
import json
import subprocess
import os
import signal

from pprint import pprint
from prettytable import PrettyTable
from sys import exit
#Colorama - For formating text
#https://pypi.org/project/colorama/
from colorama import init
init()
from colorama import Fore, Back, Style
from os.path import expanduser

#Catch CTRL-C
def signal_handler(signal, frame):
  print "\n\nAbort\n"
  exit(0)
signal.signal(signal.SIGINT, signal_handler)

#Definitions
if os.environ.has_key('SUDO_USER'):
    USER= os.environ['SUDO_USER']
else:
    USER=os.environ['USER']

HOME = "/home/"+USER
DOCKER_CONTAINER_PATH = HOME+"/ft_userdata/"
DOCKER_CONFIG_FILE = "docker-compose.yml"

#Check for command line input
COMMAND=""
if len(sys.argv) > 1:
  #sys.argv[1] will contain first argument
  COMMAND = sys.argv[1]

#TODO:
# - More clever path replacement for os paths
# - Elaborate on restAPIcommand, error handling, and use it in GetData as well
# - Implement command line arguments
# - Handle incorrect bot-name
# - Improve workflow
# - Show URL for FreqUI
#-------------------------------------------------------------- M E N U S ------------------------------------------------------
def mainMenu():
    print
    print botOverview() #Print the table of bots  
    print

    #If input on command line...
    if COMMAND == "q":   #quick mode
      exit()

    #If more then one bot is configured    
    if len(botsList) > 1:
      pick = raw_input("Pick container: ")
      if pick == "":
          print "Goodbye"
          exit() 
      for x in botsList:
        if x.docker_name == pick:
          itemMenu(x)
    #If there is just one bot...
    else:
       pick = raw_input("[RETURN]")
       itemMenu(botsList[0])       
       
def botOverview():
    #Prepare table
    table = PrettyTable()       
    table.field_names = ["Container","Name", "Docker","Bot","Mode","Strategy","Exchange","Port","Days","Gain %", "Gain Stake"]
    #Make table data 
    for i in botsList:
        row = ["","","","","","","","","","",""]

        row[0] = Fore.BLUE + i.docker_name + Style.RESET_ALL  #Instance name
        row[1] = i.bot_name #name of bot
        row[2] = cc("docker",i.docker_state) #docker state
        row[3] = cc("bot",i.bot_dict['state']) #bot state
        row[4] = cc("mode",i.bot_dict['runmode']) #bot mode
        row[5] = i.bot_config['strategy'] #strategy
        row[6] = i.bot_dict['exchange'] #exchange
        row[7] = i.port #Port 
        row[8] = i.info_dict['days_since_first_trade']
        row[9] = i.info_dict['percent']
        row[10] = i.info_dict['stake']
	
#        print i.bot_name + " >>>>>>>>>>>>>>> i.bot_dict >>>>>>>>>><" 
#        print i.bot_dict
#        print i.bot_name + " >>>>>>>>>>>>>>> i.docker_dict >>>>>>>>>><" 
#        print i.docker_dict

        table.add_row(row)
        
    return table 
    
#Detailed Menu , send i = object
def itemMenu(i):

    #Column names
    c1 = i.bot_name
    c2 = "Data"
    c3 = "Performance"
    c4 = "-"

    #Setup table and alignment
    table = PrettyTable()
    
    table.field_names = [ c1, c2, c3,c4 ]
    table.align[c1] = "l"
    table.align[c2] = "l"
    table.align[c3] = "l"
    table.align[c4] = "r"
         
    #Add rows to table
    table.add_row(["Docker state",cc("docker",i.docker_state),"Total profit,closed trades ",i.info_dict['percent']])
    table.add_row(["Bot state",cc("bot",i.bot_dict['state']),"Total profit, closed trades ", i.info_dict['stake']])
    table.add_row(["Bot strategy",i.bot_config['strategy'],"Days since first trade",i.info_dict['days_since_first_trade']])
        
    if (i.docker_state) == "running":
      table.add_row(["Mode",cc("mode",i.bot_dict['runmode']),"",""])
      table.add_row(["Exchange",i.bot_dict['exchange'],"",""])
      table.add_row(["Title (config.json)",i.bot_dict['bot_name'],"",""])
    
    table.add_row(["","","",""])
    table.add_row(["CONFIG",i.os_configfile,"",""])
    table.add_row(["LOG",i.os_logfile,"",""])
    print table
    print
    print "r - Reload config"
    print 
    print "d - Docker down"
    print "u - Docker up"
    print 
    print "tl - tail log" 
    print "bl - scan log for buy signals" 

    command = "foo"
    while command != "":
      command = raw_input(">> ")
      if command == "d":
        result = controlDockerCompose("rm -s -v -f",i.docker_name)  #returns a dict
        print result['status']
      if command == "u":
        result = controlDockerCompose("up -d",i.docker_name) #returns a dict
        print result['status']
      #reload bot config
      if command == "r":
        result = restAPIcommand(i.bot_name,i.bot_config['config'],'reload_config')  #returns a dict
        print result['status']
      #tail log
      if command == "tl":
        osCommand("tail -f " + i.os_logfile)
      #cat in reverse date order
      if command == "bl":
        osCommand("ls -1rt "+ i.os_logfile + "*  | xargs cat | grep Buy")

    exit()

#------------------------------------------------ F U N C T I O N S --------------------------------------------------------------
# dictionary keys as list
def getList(dict):
    return dict.keys()

#Color code
def cc(mode,text):
    return_text = text
    
    if mode == "docker":
      if text == "running": 
        return_text = Fore.GREEN + "Up" + Style.RESET_ALL
      elif text == "down":
        return_text = Fore.RED + "Down" + Style.RESET_ALL
    if mode == "bot":
      if text == "running": 
        return_text = Fore.GREEN + "Running" + Style.RESET_ALL
      elif text == "stopped":
        return_text = Fore.RED + "Stopped" + Style.RESET_ALL
    if mode == "mode":
      if text == "live": 
        return_text = Fore.GREEN + "Live" + Style.RESET_ALL
      elif text == "dry_run":
        return_text = Fore.YELLOW + "DryRun" + Style.RESET_ALL
        
    return return_text

def osFilePath(path):
    return path.replace("/freqtrade/",DOCKER_CONTAINER_PATH,1)

def restAPIcommand(bot_name,bot_config,command):
    data_dict = {}
    data_str=subprocess.check_output(['sudo','docker','exec',bot_name,'scripts/rest_client.py','--config',bot_config,command])
    data_dict = json.loads(data_str)
    return data_dict

def controlDockerCompose(commands,docker_name):
    result = os.system("sudo docker-compose --file " + DOCKER_CONTAINER_PATH + DOCKER_CONFIG_FILE + " " + commands + " " + docker_name)
    return result
    
def osCommand(string):
    #Possible security issue with using shell=True,  https://en.wikipedia.org/wiki/Code_injection#Shell_injection
    print subprocess.call(string,shell=True) 
            
#Function to parse the command arguments in *.yaml  affter: command > xxxxx
def parseCommands(cmd_str):
    dict = {}

    command = cmd_str.split('--')
    del command[0] #remove first element in list
    for e in command:
      r=e.strip() #remove leading and trailing spaces
      r=r.split(' ')
      if not dict.has_key(r[0]): # Pick first entry of any given command, ignore the rest (for now)
        dict[r[0]] = str(r[1])
    return dict
    
#FTBot Class    
class FTBot:
    def __init__(self, d_name="",b_name="",bot_config={}):
        self.docker_name = d_name
        self.docker_state = ""
        self.docker_dict = {}       

        self.bot_name = b_name
        self.bot_config = bot_config
        self.bot_dict = {}
        self.info_dict = {}
        self.port= {}
        
        self.os_logfile = ""
        self.os_configfile = ""
                
#        self.yaml_dict = {}

    def getData(self):
        #Format the logfile name as seen by the OS

        self.os_logfile = osFilePath(self.bot_config['logfile'])
        self.os_configfile = osFilePath(self.bot_config['config'])
        
        #Get info on the runnning _DOCKER CONTAINER_
        try:
          docker_string = subprocess.check_output(['sudo','docker','inspect',self.bot_name], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as error:
            #If the docker container is not up...
            if error.output.find('Error: No such object: '+self.bot_name) > -1:
              self.docker_state = "down"
              #self.bot_config = {}
              self.bot_dict = {}
              self.bot_dict['state'] = "-" #bot state
              self.bot_dict['runmode'] = "-" #bot mode
              self.bot_dict['runmode'] = "-" #bot mode
              self.bot_dict['exchange']="?" #Exchange
              self.port="-" #Port
              self.info_dict['percent'] = "?"
              self.info_dict['stake'] = "?"
              self.info_dict['days_since_first_trade'] = "?"
              return
            else:
              print(error.output)
              exit()

        #Result of 'sudo docker inspect freqtrade_bitvavo': leading'[' and trailing ']' needs to be removed for json.load to work          
        docker_string=docker_string.rstrip(']\n')
        docker_string=docker_string.lstrip('[')
        self.docker_dict = json.loads(docker_string) # Load to dictionary format
        
        #Get the state of docker container (if not declared "down" in try statement above)
        self.docker_state = self.docker_dict['State']['Status']

        #Get the port
        port_txt = self.docker_dict['Config']['ExposedPorts']
        field, value = port_txt.items()[0]
        self.port = field.rstrip('/tcp')
                
        #Get info on the running _BOT_
        self.bot_dict = restAPIcommand(self.bot_name,self.bot_config['config'],'show_config')

        #Get current profit state, ongoing trades, and first trade
        self.info_dict = self.getTradeInfo()

    #Get current profit state, ongoing trades, and first trade
    def getTradeInfo(self):
        ret_dict = {}
        
        if (self.docker_state) == "running":
          profit_dict = restAPIcommand(self.bot_name,self.bot_config['config'],'profit')

          profit_cp = profit_dict['profit_closed_percent']
          profit_cc = round(profit_dict['profit_closed_coin'],2) 
      
          ret_dict['percent'] = str(profit_cp) + " %"
          ret_dict['stake'] = str(profit_cc) + " " + self.bot_dict['stake_currency']

	  #If there has been a first trade... calculate ho wmany days since it happened        
	  if profit_dict['first_trade_timestamp']!=0:
	     dsft = round ( ( time.time() - (profit_dict['first_trade_timestamp'] / 1000) ) / 86400 )
             ret_dict['days_since_first_trade'] = str ( int ( dsft ) ) +" d"
          else:
             ret_dict['days_since_first_trade'] = "-"

        return ret_dict


#---------------   ************  M A I N  ************-----------------------

#Load docker-compose.yml
filename = os.path.join(DOCKER_CONTAINER_PATH, DOCKER_CONFIG_FILE)
with open(filename, "r") as stream:
    try:
        yaml_dict = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
        exit()    

#Prepare list of bot objects
botsList = []
i =0 
for k, v in reversed(yaml_dict['services'].items()):
    cmd_str = yaml_dict['services'][k]['command']
    cmd_dict = parseCommands(cmd_str)
    botsList.append(FTBot(k,v['container_name'],cmd_dict))
    botsList[i].getData()
    i =+ 1

#Start
mainMenu()

 
#-----------------------    TRASH -----------------------------------
##https://gist.github.com/dwaltrip/bd3321880180f556ba0f9d1c4962b6f7  
#def tailFile(filename):
#    with open(filename, 'r') as f:
#      while True:
#        line = f.readline()
#        if line:
#          yield line
#        else:
#          time.sleep(0.5)
#          
##https://stackoverflow.com/questions/26355787/tail-on-python-best-performance-implementation
#from collections import deque
#def tailNR(filename, n=10):
#    'Return the last n lines of a file'
#    return deque(open(filename), n)
