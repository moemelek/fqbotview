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
import time
import datetime
import json
import subprocess
import os
from pprint import pprint
from prettytable import PrettyTable
from sys import exit

#Colorama - For formating text
#https://pypi.org/project/colorama/
from colorama import init
init()
from colorama import Fore, Back, Style

DOCKER_CONTAINER_PATH = "/home/rickard/ft_userdata/"

#TODO:
# - More clever path replacement for os paths
# - Elaborate on restAPIcommand, error handling, and use it in GetData as well
# - Commands in menus, implement
# - Implement command line arguments

def mainMenu():
    print
    print botOverview() #Print the table of bots   
    print
    pick = raw_input("Pick container: ")
    if pick == "":
        print "Goodbye"
        exit() 
    for x in botsList:
      if x.docker_name == pick:
        itemMenu(x)
    return

#Menu , send i = object
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
    
    #Prepare fourth column
    profit_cp_str = "Not available"
    profit_cc_str = "Not available" 
    
    if (i.docker_state) == "running":
      #Read current profit stats
      profit_dict = restAPIcommand(i.bot_name,i.bot_config['config'],'profit')
      
      profit_cp = profit_dict['profit_closed_percent']
      profit_cc = round(profit_dict['profit_closed_coin'],2) 
  
      profit_cp_str = str(profit_cp) + " %"
      profit_cc_str = str(profit_cc) + " " + i.bot_dict['stake_currency']
      
    #Add rows to table
    table.add_row(["Docker state",i.docker_state,"Total profit closed trades ",profit_cp_str])
    table.add_row(["Bot state",i.bot_dict['state'],"Total profit closed trades ", profit_cc_str ])
    table.add_row(["Bot strategy",i.bot_dict['strategy'],"",""])
    table.add_row(["Exchange",i.bot_dict['exchange'],"",""])
    table.add_row(["Mode",i.bot_dict['runmode'],"",""])
    table.add_row(["Title (config.json)",i.bot_dict['bot_name'],"",""])
    
    print table
    print
    print "Quick access"
    print "-----------------------"
    print "LOGS: " + i.os_logfile + "*"
    print "JSON: " + i.os_configfile
    print "-----------------------"
    print
#    print "r - Reload bot"
#    print 
#    print "d - Docker down"
#    print "u - Docker up"
#    print 
#    print "tl - tail log" 
#    print "sl - scan log for buy signals" 


def botOverview():
    #Prepare table
    table = PrettyTable()
    table.field_names = ["Container","Name", "Docker","Bot","Mode","Strategy", "Logfile"]

    #Make table data 
    for i in botsList:
        row = ["","","","","","",""]
        row[0] = Fore.BLUE + i.docker_name + Style.RESET_ALL  #Instance name
        row[1] = i.bot_name #name of bot
        row[2] = cc("docker",i.docker_state) #docker state
        row[3] = cc("bot",i.bot_dict['state']) #bot state
        row[4] = cc("mode",i.bot_dict['runmode']) #bot mode
        row[5] = i.bot_config['strategy'] #strategy
        row[6] = i.os_logfile
        
        table.add_row(row)
        
    return table 
  
# dictionary keys as list
def getList(dict):
    return dict.keys()

#Color code
def cc(mode,text):
    return_text = text
    
    if mode == "docker":
      if text == "running": 
        return_text = Fore.GREEN + "Up" + Style.RESET_ALL
      elif text == "stopped":
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
            
#Function to parse the command arguments in *.yaml  affter: command > xxxxx
def parseCommands(cmd_str):
    dict = {}

    command = cmd_str.split('--')
    del command[0] #remove first element in list
    for e in command:
      r=e.strip() #remove leading and trailing spaces
      r=r.split(' ')
      dict[r[0]] = str(r[1])
    return dict
    
#FTBot Class    
class FTBot:
    def __init__(self, d_name="",b_name="",bot_config={}):
        self.docker_name = d_name
        self.docker_state = ""
       
        self.bot_name = b_name
        self.bot_config = bot_config
        self.bot_dict = {}
        
        self.os_logfile = ""
        self.os_configfile = ""
                
        self.yaml_dict = {}

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
              self.bot_config = {}
              self.bot_dict = {}
              self.bot_dict['state'] = "-" #bot state
              self.bot_dict['runmode'] = "-" #bot mode
              return
            else:
              print(error.output)
              exit()

        #Result of 'sudo docker inspect freqtrade_bitvavo': leading'[' and trailing ']' needs to be removed for json.load to work          
        docker_string=docker_string.rstrip(']\n')
        docker_string=docker_string.lstrip('[')
        docker_dict = json.loads(docker_string) # Load to dictionary format
        
        #Get the state of docker container (if not declared "down" in try statement above)
        self.docker_state = docker_dict['State']['Status']
        
        #Get info on the running _BOT_
        #bot_data_str = subprocess.check_output(['sudo','docker','exec',self.bot_name,'scripts/rest_client.py','--config',self.bot_config['config'],'show_config'])
        self.bot_dict = restAPIcommand(self.bot_name,self.bot_config['config'],'show_config')

        #self.bot_dict = json.loads(bot_data_str)


#---------------   Prapare Data - load the yaml file-----------------------
#Load docker-compose.yml
filename = os.path.join(DOCKER_CONTAINER_PATH, 'docker-compose.yml')
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

 
#---------------------   Save for later ---------------------------
#*** Run though OS call 
#  result = os.system("sudo docker-compose ps")
#*** To stop one bot
#sudo docker-compose rm -s -v -f freqtrade2
#*** run command into docker
#sudo docker exec freqtrade_bitvavo scripts/rest_client.py --config user_data/bitvavo_nfinext_live.json show_config
#*** location of webfiles:
#freqtrade/rpc/api_server/ui/installed
#*** api location 
#http://127.0.0.1:8080/api/v1/ping
#***serving javascript
#freqtrade/rpc/api_server/ui/installed/js/trade.16b3869c.js
#-----------------------    TRASH -----------------------------------
#    print
#    print Fore.BLUE + "instance: " + Style.RESET_ALL + bot
#    print Fore.BLUE + "name: " + Style.RESET_ALL + yaml_dict['services'][bot]['container_name']
#    print "Strategy name: " + command_dict['strategy']
#    print "Logfile: " + logfile
#    print (Style.RESET_ALL)
