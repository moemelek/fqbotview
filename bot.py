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

#----------------------------------
#  ALERT: This script must be _RUN_ within the file structure of a docker container
#----------------------------------
DOCKER_CONTAINER_PATH = "~/ft_userdata"

#TODO:
#
#

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
    def __init__(self, d_name="",b_name="",docker_config={}):
        self.docker_name = d_name
        self.docker_config = docker_config
        self.docker_state = ""
        
        self.bot_name = b_name
        self.bot_dict = {}
        
        self.os_logfile = ""
        
        self.yaml_dict = {}

    def getData(self):
        #Format the logfile name as seen by the OS
        self.os_logfile = self.docker_config['logfile'].replace("/freqtrade",DOCKER_CONTAINER_PATH,1)
        
        #Get info on the runnning _DOCKER CONTAINER_
        #Result of 'sudo docker inspect freqtrade_bitvavo' implies leading'[' and trailing ']' needs to be removed for json.load to work
        try:
          docker_string = subprocess.check_output(['sudo','docker','inspect',self.bot_name], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as error:
            #If the docker container is not up...
            if error.output.find('Error: No such object: '+self.bot_name) > -1:
              self.docker_state = "down"
              self.docker_config = {}
              self.bot_data = {}
              self.bot_data['state'] = "-" #bot state
              self.bot_data['runmode'] = "-" #bot mode
              return
            else:
              print(error.output)
              exit()
          
        docker_string=docker_string.rstrip(']\n')
        docker_string=docker_string.lstrip('[')
        docker_dict = json.loads(docker_string) # Load to dictionary format
        #self.docker_config = self.dictFromJsonArgs(docker_dict['Args']) #But args (commands) are in a list so convert to dict
        
        #Get the state of docker container (if not declared "down" in try statement above)
        self.docker_state = docker_dict['State']['Status']
        
        #Get info on the running _BOT_
        bot_data_str = subprocess.check_output(['sudo','docker','exec',self.bot_name,'scripts/rest_client.py','--config',self.docker_config['config'],'show_config'])
        self.bot_dict = json.loads(bot_data_str)


#---------------   Prapare Data - load the yaml file-----------------------
#Load docker-compose.yml
with open("docker-compose.yml", "r") as stream:
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
    row[5] = i.docker_config['strategy'] #strategy
    row[6] = i.os_logfile
    
    table.add_row(row)

#-----------------------   Output --------------------------------

print
#Print the table of bots   
print(table)
print

# 
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
