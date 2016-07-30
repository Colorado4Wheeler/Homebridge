#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Core libraries
import indigo
import os
import sys
import time
import datetime

# EPS 3.0 Libraries
import logging
from lib.eps import eps
from lib import ext
from lib import dtutil

# Plugin libraries
from os.path import expanduser
import subprocess
import string

eps = eps(None)

################################################################################
# plugin - 	Basically serves as a shell for the main plugin functions, it passes
# 			all Indigo commands to the core engine to do the "standard" operations
#			and raises onBefore_ and onAfter_ if it wants to do something 
#			interesting with it.  The meat of the plugin is in here while the
#			EPS library handles the day-to-day and common operations.
################################################################################
class Plugin(indigo.PluginBase):

	# Define the plugin-specific things our engine needs to know
	TVERSION	= "3.2.0"
	PLUGIN_LIBS = ["cache", "conditions", "actions"] #["conditions", "cache", "actions"] #["cache"]
	UPDATE_URL 	= ""
	
	#
	# Init
	#
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		
		eps.__init__ (self)
		eps.loadLibs (self.PLUGIN_LIBS)
		
		#indigo.server.log (unicode(eps.plugcache.pluginCache))
		
		#self.core = core(self, libs=self.PLUGIN_LIBS, url=self.UPDATE_URL)
		#eps.plug.subscribeChanges (["devices", "variables"])
		#eps.plug.subscribeProtocols ({"zwave":"incoming|outgoing","insteon":"incoming|outgoing"})
		
		# TESTING
		#pc = plugcache(self)
		#retList = pc.getStateUIList (None)
		
		
	################################################################################
	# PLUGIN HANDLERS
	#
	# Raised onBefore_ and onAfter_ for interesting Indigo or custom commands that 
	# we want to intercept and do something with
	################################################################################	
	
	# 
	# Change action terms
	#
	def onAfter_startup (self): 
		try:
			eps.act.FORMTERMS = ["On", "Off", "Dim1", "Dim2", "Dim3", "Dim4", "Dim5"]
			eps.act.VALIDATION = "methodOn"
			
			self.DIMMERS = ["dimmer", "door", "window", "drape"] # Types that support brightnessLevel
			
			self.ALLDEVCOUNT = 0 # For counting up devices in prefs
			self.ALLACTCOUNT = 0 # For counting up actions in prefs
			
			self.TOTALDIMMING = 4 # Total number of dimmer levels our device allows
			self.TOTALFIELDS = 5 # Total number of option settings fields we allow for actions
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	################################################################################
	# MENU ACTIONS
	################################################################################
	
	#
	# Stop the HB daemon
	#
	def menuStop (self):
		try:
			os.system("launchctl unload -w ~/Library/LaunchAgents/com.webdeck.homebridge.plist")
			self.logger.info ("The Homebridge server has been stopped")
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	#
	# Start the HB daemon
	#
	def menuStart (self):
		try:
			os.system("launchctl load -w ~/Library/LaunchAgents/com.webdeck.homebridge.plist")
			self.logger.info ("The Homebridge server has been started, give it a few minutes to finish loading")
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	#
	# Reload HB
	#
	def menuReload (self):
		try:
			self.menuStop()
			self.sleep(5)
			self.menuStart()
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	#
	# Save and reload
	#
	def menuSaveReload (self):
		try:
			self.menuSave()
			self.menuReload()
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	#
	# Build and save the configuration
	#
	def menuSave (self):
		try:
			idCount = 0
			idTotal = 0
			
			includeDev = []
			excludeDev = []
			includeAct = []
			excludeAct = []
			
			switches = []
			locks = []
			doors = []
			garages = []
			windows = []
			drapes = []
			
			# Parse the plugin devices first
			for dev in indigo.devices.iter(self.pluginId):
				includeDev.append(str(dev.id))
				idCount = idCount + 1
				idTotal = idTotal + 1
				
				if ext.valueValid (dev.pluginProps, "treatAs", True):
					if dev.pluginProps["treatAs"] == "switch": switches.append(str(dev.id))
					if dev.pluginProps["treatAs"] == "lock": locks.append(str(dev.id))
					if dev.pluginProps["treatAs"] == "door": doors.append(str(dev.id))
					if dev.pluginProps["treatAs"] == "garage": garages.append(str(dev.id))
					if dev.pluginProps["treatAs"] == "window": windows.append(str(dev.id))
					if dev.pluginProps["treatAs"] == "drape": drapes.append(str(dev.id))
					
				if self.pluginPrefs["hideWrappedItems"]:			
					for x in range (0, 2):
						method = "On"
						if x == 1: method = "Off"
					
						if dev.pluginProps["method" + method] == "device": 
							if ext.valueValid (dev.pluginProps, "device" + method, True): 
								excludeDev.append(int(dev.pluginProps["device" + method]))
							
						if dev.pluginProps["method" + method] == "action": 
							if ext.valueValid (dev.pluginProps, "action" + method, True): 
								excludeDev.append(int(dev.pluginProps["action" + method]))
			
			#indigo.server.log(str(idCount))
					
			# Parse the device includes
			for id in self.pluginPrefs["devinclude"]:
				if id == "-all-" or id == "-none-" or id == "-line-" or id == "default":
					if id == "-all-":
						# Count everything up so we can report on device counts
						for dev in indigo.devices:
							if str(dev.id) in excludeDev: # Don't count it if we are excluding
								pass
							else:
								if self.canHomeBridgeSupportDevice(dev) and dev.pluginId != self.pluginId: # We've already added our own stuff
									idCount = idCount + 1
									idTotal = idTotal + 1
								
								if self.canHomeBridgeSupportDevice(dev) == False:
									idTotal = idTotal + 1
					
					includeDev = [] # We are using everything, don't do a list
					break
					
				if id in includeDev:
					pass
				else:
					if id in excludeDev:
						pass
					else:
						includeDev.append(id)
						idCount = idCount + 1
						idTotal = idTotal + 1
						
			#indigo.server.log(str(idCount))
			
			# Parse the action includes			
			for id in self.pluginPrefs["actinclude"]:
				if id == "-all-" or id == "-none-" or id == "-line-" or id == "default":
					if id == "-all-":
						# Count everything up so we can report on device counts
						for act in indigo.actionGroups:
							if str(act.id) in excludeAct: # Don't count it if we are excluding
								pass
							else:
								idCount = idCount + 1
								idTotal = idTotal + 1
									
					includeAct = [] # We are using everything, don't do a list
					break
					
				if id in includeAct:
					pass
				else:
					if id in excludeAct:
						pass
					else:
						includeAct.append(id)
						idCount = idCount + 1
						idTotal = idTotal + 1
						
			#indigo.server.log(str(idCount))
						
			# Parse the lists
			excludeDev = self._addPrefIdToList ("devexclude", excludeDev)
			excludeAct = self._addPrefIdToList ("actexclude", excludeAct)
			switches = self._addPrefIdToList ("treatasswitch", switches)
			locks = self._addPrefIdToList ("treataslock", locks)
			doors = self._addPrefIdToList ("treatasdoor", doors)
			garages = self._addPrefIdToList ("treatasgarage", garages)
			windows = self._addPrefIdToList ("treataswindows", windows)
			drapes = self._addPrefIdToList ("treatasdrapes", drapes)
			
			# Before anything make sure we report our findings if it's more than 99 devices
			idCount = idCount - len(excludeDev) - len(excludeAct)
			#indigo.server.log(str(idCount))
			
			if idCount > 99:
				msg = eps.ui.debugHeader ("WARNING")
				msg += eps.ui.debugLine (" ")
				msg += eps.ui.debugLine ("You have {0} items for Homebridge but it only supports 99, you".format(str(idCount)))
				msg += eps.ui.debugLine ("will be unable to use some of your items!")
				msg += eps.ui.debugHeaderEx ()		
				
				self.logger.error (msg)
				
			# Do a pre-save summary
			msg = eps.ui.debugHeader ("SUMMARY")
			msg += eps.ui.debugLine (" ")
			msg += eps.ui.debugLine ("Devices for Homebridge to parse          : {0}".format(str(idTotal)))
			msg += eps.ui.debugLine ("Included devices that Homebridge can use : {0}".format(str(idCount)))
			
			if idCount >= 99:
				msg += eps.ui.debugLine ("Devices over 99 that won't work          : {0}".format(str(idCount - 99)))
			else:
				msg += eps.ui.debugLine ("Devices over 99 that won't work          : 0")
			
			msg += eps.ui.debugLine (" ")
			
			if idTotal > 99:
				msg += eps.ui.debugLine ("You are sending a lot of stuff to Homebridge, you may want to")
				msg += eps.ui.debugLine ("use some excludes to trim the list down so you can make sure")
				msg += eps.ui.debugLine ("Homebridge runs efficiently and effectively.  The extra")
				msg += eps.ui.debugLine ("devices you are sending could count against your 99 devices")
				msg += eps.ui.debugLine ("and prevent devices you think should work from working.")
				
			msg += eps.ui.debugHeaderEx ()
			self.logger.info (msg)
		
			cfg =	'{\n'
			cfg += 	'\t"bridge": {\n'
			
			cfg +=	'\t\t"name": "Homebridge",\n'
			cfg +=	'\t\t"username": "CC:22:3D:E3:CE:30",\n'
			cfg +=	'\t\t"port": 51826,\n'
			cfg +=	'\t\t"pin": "031-45-154"\n'
			
			cfg +=	'\t},\n\n'
			
			cfg += 	'\t"description": "Homebridge-Indigo configuration generated by EPS Homebridge Companion",\n\n'
			
			cfg += 	'\t"platforms": [\n'
			cfg +=	'\t\t{\n'
			
			cfg +=	'\t\t\t"platform": "{0}",\n'.format(self.pluginPrefs["platform"])
			cfg +=	'\t\t\t"name": "{0}",\n'.format(self.pluginPrefs["name"])
			cfg +=	'\t\t\t"protocol": "{0}",\n'.format(self.pluginPrefs["protocol"].lower())
			cfg +=	'\t\t\t"host": "{0}",\n'.format(self.pluginPrefs["host"])
			cfg +=	'\t\t\t"port": "{0}",\n'.format(self.pluginPrefs["port"])
			cfg +=	'\t\t\t"path": "{0}",\n'.format(self.pluginPrefs["path"])
			cfg +=	'\t\t\t"username": "{0}",\n'.format(self.pluginPrefs["username"])
			cfg +=	'\t\t\t"password": "{0}",\n'.format(self.pluginPrefs["password"])
			
			# Incorporate actions
			if len(includeAct) > 0:
				if len(includeAct) > len(excludeAct):
					cfg +=	'\t\t\t"includeActions": true,\n'
				else:
					cfg +=	'\t\t\t"includeActions": false,\n'
			else:
				# Make sure they didn't select -all-
				hasActions = False
				for id in self.pluginPrefs["actinclude"]:
					if id == "-all-":
						hasActions = True
						break
						
				if hasActions:
					cfg +=	'\t\t\t"includeActions": true,\n'
				else:
					cfg +=	'\t\t\t"includeActions": false,\n'
				
			# Incorporate included devices
			if len(includeDev) > 0 or len(includeAct) > 0:
				cfg +=	'\t\t\t"includeIds": {0},\n'.format(self._addItemListToConfig (includeDev + includeAct))
				
			# Incorporate excluded devices
			if len(excludeDev) > 0 or len(excludeAct) > 0:
				cfg +=	'\t\t\t"excludeIds": {0},\n'.format(self._addItemListToConfig (excludeDev + excludeAct))
				
			# Incorporate switches
			if len(switches) > 0:
				cfg +=	'\t\t\t"treatAsSwitchIds": {0},\n'.format(self._addItemListToConfig (switches))
				
			# Incorporate locks
			if len(locks) > 0:
				cfg +=	'\t\t\t"treatAsLockIds": {0},\n'.format(self._addItemListToConfig (locks))
				
			# Incorporate doors
			if len(doors) > 0:
				cfg +=	'\t\t\t"treatAsDoorIds": {0},\n'.format(self._addItemListToConfig (doors))
				
			# Incorporate garages
			if len(garages) > 0:
				cfg +=	'\t\t\t"treatAsGarageDoorIds": {0},\n'.format(self._addItemListToConfig (garages))
				
			# Incorporate windows
			if len(windows) > 0:
				cfg +=	'\t\t\t"treatAsWindowIds": {0},\n'.format(self._addItemListToConfig (windows))
				
			# Incorporate drapes
			if len(drapes) > 0:
				cfg +=	'\t\t\t"treatAsWindowCoveringIds": {0},\n'.format(self._addItemListToConfig (drapes))
			


			cfg +=	'\t\t\t"thermostatsInCelsius": {0},\n'.format(unicode(self.pluginPrefs["celsius"]).lower())

			cfg +=	'\t\t\t"accessoryNamePrefix": "{0}"\n'.format(self.pluginPrefs["accessory"])			
			cfg +=	'\t\t}\n'
			cfg += 	'\t],\n\n'
			
			cfg += 	'\t"accessories": [\n'
			cfg += 	'\t]\n'
			
			cfg += 	'}'
			
			indigo.server.log("\n" + cfg)
			
			#return
			
			home = expanduser("~") + "/.homebridge"
			
			if os.path.exists(home):
				if os.path.exists (home + "/config.json"):
					self.logger.debug ("Found '{0}/config.json', saving the Homebridge configuration".format(home))
					
					with open(home + "/config.json", 'w') as file_:
					    file_.write(cfg)
				else:
					self.logger.error ("Unable to find the config.json file in '{0}', are you sure Homebridge is installed?  Unable to save configuration".format(home))
			else:
				self.logger.error ("Unable to find '{0}', are you sure Homebridge is installed?  Unable to save configuration".format(home))
			
			indigo.server.log(home)
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	#
	# Add prefs array of ID's to a config list
	#
	def _addPrefIdToList (self, prefName, listValue):
		try:
			for id in self.pluginPrefs[prefName]:
				if id in listValue:
					continue
				elif id == "-line-":
					continue
				elif id == "-none-":
					continue
				elif id == "-all-":
					continue
				elif id == "-devices-":
					continue
				elif id == "-actions-":
					continue
				elif id == "default":
					continue
				else:
					listValue.append(id)
					
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return listValue
	
	# 
	# Format a list of ID's for the config.json file
	#		
	def _addItemListToConfig (self, listValues):
		idlist = ""
		
		try:
			idlist = "["
		
			for id in listValues:
				idlist += '"{0}", '.format(id)
				
			idlist = idlist[0:len(idlist) - 2] # cut the trailing delimiter
		
			idlist += "]"
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return idlist
	
	
	################################################################################
	# PLUGIN CONFIG
	################################################################################
	
	#
	# Refresh device count in configuration
	#
	def btnRefreshDeviceCount (self, valuesDict):
		try:
			localcount = 0
			
			# Add any local plugin wrappers
			if valuesDict["countWrappedItems"]:
				for dev in indigo.devices.iter(self.pluginId):
					localcount = localcount + 1
			
			# Count up devices
			for devId in valuesDict["devinclude"]:
				if devId == "-all-":
					localcount = localcount + self.ALLDEVCOUNT
					break
					
				if devId == "-none-": break
					
				if devId != "-line-" and devId != "-devices-" and devId != "-actions-":	
					localcount = localcount + 1
				
			# Count up actions
			for devId in valuesDict["actinclude"]:
				if devId == "-all-":
					localcount = localcount + self.ALLACTCOUNT
					break
					
				if devId == "-none-": break
				
				if devId != "-line-" and devId != "-devices-" and devId != "-actions-":		
					localcount = localcount + 1
				
			# Count up excludes
			for devId in valuesDict["devexclude"]:
				if devId == "-none-": break
				
				if devId != "-line-" and devId != "-devices-" and devId != "-actions-":		
					localcount = localcount - 1
				
			# Count up excludes
			for devId in valuesDict["actexclude"]:
				if devId == "-none-": break
				
				if devId != "-line-" and devId != "-devices-" and devId != "-actions-":	
					localcount = localcount - 1
				
				
				
			# Populate the field
			valuesDict["itemcount"] = str(localcount)
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return valuesDict
	
	#
	# A configuration form field changed
	#
	def configFieldChanged (self, valuesDict):
		try:
			# Do a refresh since we are here
			valuesDict = self.btnRefreshDeviceCount (valuesDict)	
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return valuesDict
			
	#
	# Special plugin lists
	#
	def pluginList (self, filter="", valuesDict=None, typeId=""):
		ret = [("default", "No data")]
		
		try:
			if filter == "": return ret
			
			data = filter.split("#")
			filter = data[0]
			
			wrappers = []
			if valuesDict["hideWrappedItems"]:			
				for dev in indigo.devices.iter(self.pluginId):
					for x in range (0, 2):
						method = "On"
						if x == 1: method = "Off"
						
						if dev.pluginProps["method" + method] == "device": 
							if ext.valueValid (dev.pluginProps, "device" + method, True): 
								wrappers.append(int(dev.pluginProps["device" + method]))
								
						if dev.pluginProps["method" + method] == "action": 
							if ext.valueValid (dev.pluginProps, "action" + method, True): 
								wrappers.append(int(dev.pluginProps["action" + method]))

			
			retList = []
			
			# INCLUDE
			if filter == "hbfriendly":
				self.ALLDEVCOUNT = 0
				retList = self._friendlyDevices (retList, wrappers, True)
				
				if len(retList) > 0:
					retList.insert(0, ("-all-", "All Indigo Devices"))
					retList.insert(0, ("-none-", "Don't Include Any Devices"))
					retList = eps.ui.insertLine (retList, 2)
					
			# EXCLUDE
			if filter == "hbexclude":
				if "devinclude" in valuesDict:
					for devId in valuesDict["devinclude"]:
						if devId == "-all-":
							retList = self._friendlyDevices (retList, wrappers)
						elif devId == "-none-":	
							break						
						else:
							if int(devId) in indigo.devices: retList.append ((devId, indigo.devices[int(devId)].name))
							
					if len(retList) > 0:
						retList.insert(0, ("-none-", "Don't Exclude Anything"))
						retList = eps.ui.insertLine (retList, 1)
						
			# ACTION GROUPS INCLUDE
			if filter == "hbactinclude":
				self.ALLACTCOUNT = 0
				retList = self._friendlyActionGroups (retList, wrappers, True)
				
				if len(retList) > 0:
					retList.insert(0, ("-all-", "All Indigo Action Groups"))
					retList.insert(0, ("-none-", "Don't Include Any Action Groups"))
					retList = eps.ui.insertLine (retList, 2)
					
			# ACTION GROUP EXCLUDE
			if filter == "hbactexclude":
				if "actinclude" in valuesDict:
					for devId in valuesDict["actinclude"]:
						if devId == "-all-":
							retList = self._friendlyActionGroups (retList, wrappers)	
						elif devId == "-none-":	
							break
						else:
							if int(devId) in indigo.devices: retList.append ((devId, indigo.actionGroups[int(devId)].name))
							
					if len(retList) > 0:
						retList.insert(0, ("-none-", "Don't Exclude Anything"))
						retList = eps.ui.insertLine (retList, 1)
						
			# TYPING
			if filter == "hbtypes":
				typeList = []
								
				if "devinclude" in valuesDict:
					for devId in valuesDict["devinclude"]:
						if self._isUsed (devId, valuesDict, data[1]): continue
						
						if devId == "-all-":
							typeList = self._friendlyDevices (typeList, wrappers)
							break		
						elif devId == "-none-":
							break				
						else:
							if int(devId) in indigo.devices: typeList.append ((devId, indigo.devices[int(devId)].name))
							
							
					# Now go through excludes and make sure those are removed
					if len(valuesDict["devexclude"]) > 0 and valuesDict["devexclude"][0] != "-none-":
						for item in typeList:
							isExclude = False
							
							for devId in valuesDict["devexclude"]:
								if devId == item[0]:
									isExclude = True
									break
									
							if isExclude:
								pass
							else:							
								retList.append (item)	
					else:
						for item in typeList:
							retList.append (item)
							
				typeList = [] # Zero out again so we can start with actions
					
				if "actinclude" in valuesDict:
					menuAdded = False
					
					for devId in valuesDict["actinclude"]:
						if self._isUsed (devId, valuesDict, data[1]): continue
						
						if devId == "-all-":
							typeList = self._friendlyActionGroups (typeList, wrappers)		
							break
						elif devId == "-none-":
							break				
						else:
							if int(devId) in indigo.devices: typeList.append ((devId, indigo.actionGroups[int(devId)].name))
							
					# Now go through excludes and make sure those are removed
					if len(valuesDict["actexclude"]) > 0 and valuesDict["actexclude"][0] != "-none-":
						for item in typeList:
							isExclude = False
							
							for devId in valuesDict["actexclude"]:
								if devId == item[0]:
									isExclude = True
									break
									
							if isExclude:
								pass
							else:
								if menuAdded:
									retList.append (item)		
								else:
									if len(retList) > 0:
										retList.insert(0, ("-devices-", "AVAILABLE DEVICES"))
										retList = eps.ui.insertLine (retList, 1)
									
										retList = eps.ui.addLine (retList)
										
									retList.append (("-actions-", "AVAILABLE ACTIONS"))
									retList = eps.ui.addLine (retList)
									
									retList.append (item)
									menuAdded = True
					else:
						for item in typeList:
							if menuAdded:
								retList.append (item)		
							else:
								if len(retList) > 0:
									retList.insert(0, ("-devices-", "AVAILABLE DEVICES"))
									retList = eps.ui.insertLine (retList, 1)
								
									retList = eps.ui.addLine (retList)
																	
								retList.append (("-actions-", "AVAILABLE ACTIONS"))
								retList = eps.ui.addLine (retList)
								
								retList.append (item)
								menuAdded = True
								
				if len(retList) > 0:
					# We have things to show
					retList.insert(0, ("-none-", "Don't use anything for this type"))
					retList = eps.ui.insertLine (retList, 1)
				else:
					return [("default", "Nothing available to assign")]
					
			
			if len(retList) > 0: return retList
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return ret
		
	#
	# Check if a item ID is used in another Treat As list
	#
	def _isUsed (self, objId, valuesDict, currentList):
		try:
			if currentList != "treataslock" and ext.valueValid (valuesDict, "treataslock", True) and str(objId) in valuesDict["treataslock"]: return True
			if currentList != "treatasdoor" and ext.valueValid (valuesDict, "treatasdoor", True) and str(objId) in valuesDict["treatasdoor"]: return True
			if currentList != "treataswindows" and ext.valueValid (valuesDict, "treataswindows", True) and str(objId) in valuesDict["treataswindows"]: return True
			if currentList != "treatasswitch" and ext.valueValid (valuesDict, "treatasswitch", True) and str(objId) in valuesDict["treatasswitch"]: return True
			if currentList != "treatasdrapes" and ext.valueValid (valuesDict, "treatasdrapes", True) and str(objId) in valuesDict["treatasdrapes"]: return True
			if currentList != "treatasgarage" and ext.valueValid (valuesDict, "treatasgarage", True) and str(objId) in valuesDict["treatasgarage"]: return True
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return True
			
		return False
		
	#
	# Build list of HB friendly devices
	#
	def _friendlyDevices (self, retList, wrappers, addCount = False):
		try:
			for dev in indigo.devices:
			
				# Don't include devices that HB can't handle, like custom plugins, IO's, etc and don't include our own devices either
				if self.canHomeBridgeSupportDevice(dev) and dev.pluginId != self.pluginId:
					if dev.id in wrappers:
						pass
					else:
						retList.append ((str(dev.id), dev.name))
						if addCount: self.ALLDEVCOUNT = self.ALLDEVCOUNT + 1	
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return retList
		
	#
	# Build list of action groups
	#
	def _friendlyActionGroups (self, retList, wrappers, addCount = False):
		try:
			for dev in indigo.actionGroups:
				if dev.id in wrappers:
					pass
				else:
					retList.append ((str(dev.id), dev.name))
					if addCount: self.ALLACTCOUNT = self.ALLACTCOUNT + 1	
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return retList
		
	#
	# Check if a device is friendly to Homebridge
	#
	def canHomeBridgeSupportDevice (self, dev):
		try:
			if type(dev) is not indigo.Device and type(dev) is not indigo.MultiIODevice: return True
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
		return False

	################################################################################
	# DEVICE HANDLERS
	################################################################################

	#
	# Device start comm
	#
	def onAfter_deviceStartComm (self, dev):
		try:
			self.checkDeviceAddress (dev)
			
			
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	#
	# Device updated
	#			
	def onAfter_pluginDeviceUpdated (self, origDev, newDev):
		try:
			self.checkDeviceAddress (newDev)
			self.setDeviceIcon (newDev)
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
			
	#
	# Set the device icon
	#
	def setDeviceIcon (self, dev):
		try:
			img = False
			
			if "brightnessLevel" in dev.states:
				pass
			else:
				return
			
			if dev.pluginProps["treatAs"] == "switch": 
				if dev.states["brightnessLevel"] == 0: img = indigo.kStateImageSel.PowerOff
				if dev.states["brightnessLevel"] != 0: img = indigo.kStateImageSel.PowerOn
				
			if dev.pluginProps["treatAs"] == "lock": 
				if dev.states["brightnessLevel"] == 0: img = indigo.kStateImageSel.DoorSensorClosed
				if dev.states["brightnessLevel"] != 0: img = indigo.kStateImageSel.DoorSensorOpened
				
			if dev.pluginProps["treatAs"] == "door": 
				if dev.states["brightnessLevel"] == 0: img = indigo.kStateImageSel.DoorSensorClosed
				if dev.states["brightnessLevel"] != 0: img = indigo.kStateImageSel.DoorSensorOpened
			
			if dev.pluginProps["treatAs"] == "dimmer": 
				if dev.states["brightnessLevel"] == 0: img = indigo.kStateImageSel.DimmerOff
				if dev.states["brightnessLevel"] != 0: img = indigo.kStateImageSel.DimmerOn
			
			if dev.pluginProps["treatAs"] == "garage": 
				if dev.states["brightnessLevel"] == 0: img = indigo.kStateImageSel.DoorSensorClosed
				if dev.states["brightnessLevel"] != 0: img = indigo.kStateImageSel.DoorSensorOpened
			
			if dev.pluginProps["treatAs"] == "window": 
				if dev.states["brightnessLevel"] == 0: img = indigo.kStateImageSel.WindowSensorClosed
				if dev.states["brightnessLevel"] != 0: img = indigo.kStateImageSel.WindowSensorOpened
				
			if dev.pluginProps["treatAs"] == "drape": 
				if dev.states["brightnessLevel"] == 0: img = indigo.kStateImageSel.LightSensor
				if dev.states["brightnessLevel"] != 0: img = indigo.kStateImageSel.LightSensorOn
		
			if img: dev.updateStateImageOnServer(img)
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	
	#
	# Check the device address
	#
	def checkDeviceAddress (self, dev):
		try:
			# If it doesn't have an address for some reason then give it one
			if dev.address == "" and ext.valueValid (dev.pluginProps, "treatAs", True):
				if dev.pluginProps["treatAs"] != "none":
					address = "Unknown Device"
					
					if dev.pluginProps["treatAs"] == "switch": address="Switch"
					if dev.pluginProps["treatAs"] == "lock": address="Lock"
					if dev.pluginProps["treatAs"] == "door": address="Door"
					if dev.pluginProps["treatAs"] == "dimmer": address="Dimmer"
					if dev.pluginProps["treatAs"] == "garage": address="Garage Door"
					if dev.pluginProps["treatAs"] == "window": address="Window"
					if dev.pluginProps["treatAs"] == "drape": address="Window Covering"

					props = dev.pluginProps
					props["address"] = address
					dev.replacePluginPropsOnServer (props)
					
		except Exception as e:
			self.logger.error (ext.getException(e))	


	#
	# Watch for state changes on linked devices
	#
	def onWatchedStateRequest (self, dev):
		self.logger.threaddebug ("Returning watched states for {0}".format(dev.deviceTypeId))
		ret = {}
		
		try:
			if dev.deviceTypeId == "Homebridge-Wrapper":
				for i in range (1, self.TOTALDIMMING + 2 + 1): # Dimmers + On + Off + 1 (since we aren't starting at 0)
					method = "Dim" + str(i)
					if i == self.TOTALDIMMING + 1: method = "On"
					if i == self.TOTALDIMMING + 2: method = "Off"

					# We never really use the device, but the device defined for the state to watch
					if dev.pluginProps["getStatusFrom" + method] == "state" and ext.valueValid (dev.pluginProps, "stateFromDevice" + method, True):	
						devId = int(dev.pluginProps["stateFromDevice" + method])
						state = dev.pluginProps["deviceState" + method]
						
						if devId in ret:
							ret[devId].append (state)
						else:
							ret[devId] = [state]
								
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return ret
	
	#
	# Watch for name or address changes on linked devices
	#	
	def onWatchedAttributeRequest (self, dev):
		self.logger.threaddebug ("Returning watched attributes for {0}".format(dev.deviceTypeId))
		ret = {}
		
		try:
			# First watch THIS device
			if dev.deviceTypeId == "Homebridge-Wrapper":
				for i in range (1, self.TOTALDIMMING + 2 + 1): # Dimmers + On + Off + 1 (since we aren't starting at 0)
					method = "Dim" + str(i)
					if i == self.TOTALDIMMING + 1: method = "On"
					if i == self.TOTALDIMMING + 2: method = "Off"
					
					if dev.pluginProps["method" + method] == "device" and ext.valueValid (dev.pluginProps, "device" + method, True):
						ret[int(dev.pluginProps["device" + method])] = ["address", "name"]
					
				# Now we have to go through our config and watch everything ELSE too
				self.logger.warn ("(DEVELOPER NOTE) Non plugin devices being sent to Homebridge needs to cache attributes!")
								
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return ret
		
	#
	# Watch for name changes on variables
	#
	def onWatchedVariableRequest (self, dev):
		self.logger.threaddebug ("Returning watched variables for {0}".format(dev.deviceTypeId))
		ret = {}
		
		try:
			if dev.deviceTypeId == "Homebridge-Wrapper":
				for i in range (1, self.TOTALDIMMING + 2 + 1): # Dimmers + On + Off + 1 (since we aren't starting at 0)
					method = "Dim" + str(i)
					if i == self.TOTALDIMMING + 1: method = "On"
					if i == self.TOTALDIMMING + 2: method = "Off"
					
					if dev.pluginProps["getStatusFrom" + method] == "variable":	
						varId = int(dev.pluginProps["deviceVariable" + method])
						ret[varId] = True # Variables don't have extra info, just that we watch the value
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return ret
		
	#
	# Watch for name changes on action groups
	#
	def XXX_onWatchedActionGroupRequest (self, dev):
		self.logger.threaddebug ("Returning watched action groups for {0}".format(dev.deviceTypeId))
		ret = {}
		
		try:
			if dev.pluginProps["methodOn"] == "action" and ext.valueValid (dev.pluginProps, "actionOn", True):
				ret[int(dev.pluginProps["actionOn"])] = True # Action groups don't have extra info, really we are just watching for if it got ran elsewhere
			
			if dev.pluginProps["methodOff"] == "action" and ext.valueValid (dev.pluginProps, "actionOff", True):
				ret[int(dev.pluginProps["actionOff"])] = True
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return ret
				
	#
	# Our device was turned on
	#
	def onDeviceCommandTurnOn (self, dev):	
		try:
			# If it's already on then only let them turn it on again if the On method cannot determine on/off states
			if dev.pluginProps["getStatusFromOn"] != "none":
				# We have a means to check status and have already in other raised events, this is redundant
				if dev.states["onOffState"]: return True 
			
			if dev.pluginProps["methodOn"] == "device" and ext.valueValid (dev.pluginProps, "deviceOn", True):
				return eps.act.runAction (dev.pluginProps, "On")
									
			if dev.pluginProps["methodOn"] == "action" and ext.valueValid (dev.pluginProps, "actionOn", True):
				indigo.actionGroup.execute(int(dev.pluginProps["actionOn"]))
				return True
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
		return False
		
	#
	# Our device was turned off
	#
	def onDeviceCommandTurnOff (self, dev):	
		try:
			# If it's already on then only let them turn it off again if the Off method cannot determine on/off states
			if dev.pluginProps["getStatusFromOff"] != "none":
				# We have a means to check status and have already in other raised events, this is redundant
				if dev.states["onOffState"] == False: return True
						
			if dev.pluginProps["methodOff"] == "device" and ext.valueValid (dev.pluginProps, "deviceOff", True):
				return eps.act.runAction (dev.pluginProps, "Off")
				
			if dev.pluginProps["methodOff"] == "action" and ext.valueValid (dev.pluginProps, "actionOff", True):
				indigo.actionGroup.execute(int(dev.pluginProps["actionOff"]))
				return True
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
		return False	
		
	#
	# Our device brightness was changed
	#
	def onDeviceCommandSetBrightness (self, dev, value):	
		try:
			# If the setting is for 0 or 100 then return the on/off
			if value == 0: return self.onDeviceCommandTurnOff (dev)
			if value == 100: return self.onDeviceCommandTurnOn (dev)
			
			# See if any of our settings control brightness
			for i in range (1, self.TOTALDIMMING + 1): 
				method = "Dim" + str(i)
				if i == self.TOTALDIMMING + 1: method = "On"
				if i == self.TOTALDIMMING + 2: method = "Off"
				
				if dev.pluginProps["method" + method] == "none": continue
				
				# If we hit this then we've defined this dim, see if it matches the value
				if dev.pluginProps["brightness" + method] == str(value):
					# If it's already on then only let them set brightness again if the method cannot determine on/off states
					if dev.pluginProps["getStatusFrom" + method] != "none":
						# We have a means to check status and have already in other raised events, this is redundant
						if dev.states["brightnessLevel"] == value: return True
				
					if dev.pluginProps["method" + method] == "device" and ext.valueValid (dev.pluginProps, "device" + method, True):
						return eps.act.runAction (dev.pluginProps, method)
				
					if dev.pluginProps["method" + method] == "action" and ext.valueValid (dev.pluginProps, "action" + method, True):
						indigo.actionGroup.execute(int(dev.pluginProps["action" + method]))
						return True
						
			# If we didn't return by now then it's a passthrough if On the device supports dimming, if they defined
			# different devices for on and off then we don't care, we only change brightness on the On device for passthrough,
			# they should have defined variants if they wanted to use something else
			if dev.pluginProps["methodOn"] == "device" and ext.valueValid (dev.pluginProps, "deviceOn", True):
				devEx = indigo.devices[int(dev.pluginProps["deviceOn"])]
				if type(devEx) is indigo.DimmerDevice:
					indigo.dimmer.setBrightness (devEx.id, value)
					return True				
				else:
					self.logger.error ("A command to change the brightness of '{0}' failed because the device doesn't support changing brightness".format(devEx.name))
					return False
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
		return False	
	
	
	#
	# Process a child device's change
	#
	def changeParentFromChild (self, parent, child, changeInfo, getStatusMethod):
		# Find out what commands are influenced by this state
		changedMethod = []
		isPassthrough = True # Assume we don't have an action to set brightness
		
		try:		
			for i in range (1, self.TOTALDIMMING + 2 + 1): # Dimmers + On + Off + 1 (since we aren't starting at 0)
				method = "Dim" + str(i)
				if i == self.TOTALDIMMING + 1: method = "On"
				if i == self.TOTALDIMMING + 2: method = "Off"
				
				#indigo.server.log(unicode(changeInfo))
			
				if parent.pluginProps["getStatusFrom" + method] != getStatusMethod: continue # wrong event, variables handled elsewhere
				
				if getStatusMethod == "state":
					if parent.pluginProps["stateFromDevice" + method] != str(child.id): continue # wrong child, move on
					if parent.pluginProps["deviceState" + method] != changeInfo.name: continue # wrong state/variable, move on
				
				if parent.pluginProps["method" + method] == "none" and method[0:3] == "Dim": 
					# The method is not enabled, it's a passthrough brightness if the child supports it
					#if ext.valueValid (child.states, "brightnessLevel"): isPassthrough = True
					continue
			
				# See if the state values match
				propValue = parent.pluginProps["value" + method].lower()
				if propValue != "" and propValue[0:1] == "{":
					propValue = parent.pluginProps["value" + method] # undo lower
					propValue = propValue.replace ("{", "")
					propValue = propValue.replace ("}", "")
					propValue = parent.pluginProps[propValue].lower()
				
				childValue = unicode(changeInfo.newValue).lower()
			
				self.logger.threaddebug ("Analyzing " + method + ": " + unicode(childValue) + " " + parent.pluginProps["valueOperator" + method] + " " + unicode(propValue))
			
				if parent.pluginProps["valueOperator" + method] == "equal":
					if childValue == propValue: changedMethod.append(method)
				
				elif parent.pluginProps["valueOperator" + method] == "notequal":
					if childValue != propValue : changedMethod.append(method)
				
				elif parent.pluginProps["valueOperator" + method] == "greater":
					if childValue > propValue: changedMethod.append(method)
				
				elif parent.pluginProps["valueOperator" + method] == "less":
					if childValue < propValue: changedMethod.append(method)	
					
				elif parent.pluginProps["valueOperator" + method] == "in":
					stringIsIn = string.find (propValue, childValue)
					if stringIsIn > -1: 
						changedMethod.append(method)	
					else:
						# See if it's in the first position
						if propValue[0:len(childValue)] == childValue: changeMethod.append(method)
		
			if len(changedMethod) == 0:
				pass	
			
			else:
				if len(changedMethod) > 1:
					self.logger.warn ("'{0}' changed but more than one method takes ownership of the change, setting '{1}' to the lowest denominator!".format(child.name, parent.name))
					# Use on if it's there, then off then dimmers in order until we get a match
					if "On" in changedMethod: 
						changedMethod = ["On"]
					elif "Off" in changedMethod: 
						changedMethod = ["Off"]
					else:
						for x in range (1, self.TOTALDIMMING + 1):
							if "Dim" + str(x) in changedMethod: 
								changedMethod = ["Dim" + str(x)]
								break
					
					self.logger.debug ("Lowest denominator method is {0}".format(changedMethod[0]))
			
				# Assume on unless found otherwise
				method = changedMethod[0]
				stateName = "onOffState"
				stateVal = True
				
				if method == "Off":
					stateVal = False
					
				elif method == "On":
					stateVal = True
					
				elif method[0:3] == "Dim":
					# We set the brightness to the "requested percent" because we are saying that we are at THIS device
					# brightness IF the child matches our conditions
					self.logger.debug ("Overriding passthrough, we have a dimmer action")
					stateName = "brightnessLevel"
					stateVal = int(parent.pluginProps["brightness" + method])
					isPassthrough = False # Override any passthrough we might have, this now has priority
											
				else:
					self.logger.error ("'{0}' changed but '{1}' method {2} doesn't exist".format(child.name, parent.name, method))
					return
					
				parent.updateStateOnServer(stateName, stateVal)
				
				# In case this device is a supported dimmer type change the brightness as well
				if parent.pluginProps["treatAs"] in self.DIMMERS:
					if stateName == "onOffState" and stateVal == False: parent.updateStateOnServer("brightnessLevel", 0)
					if stateName == "onOffState" and stateVal == True: parent.updateStateOnServer("brightnessLevel", 100)
	
			# If we had no brightness changes and we are passing through then update			
			if isPassthrough and getStatusMethod == "state" and ext.valueValid (child.states, "brightnessLevel"):
				self.logger.threaddebug ("Passing through brightness from child to the parent")
				parent.updateStateOnServer("brightnessLevel", child.states["brightnessLevel"])
							
		except Exception as e:
			self.logger.error (ext.getException(e))	
		
	#
	# A watched state changed, we need to see if we have to update our own device state as a result
	#
	def onWatchedStateChanged (self, origDev, newDev, changeInfo):
		try:
			parent = indigo.devices[changeInfo.parentId]
			child = indigo.devices[changeInfo.childId]
		
			self.changeParentFromChild (parent, child, changeInfo, "state")
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	#
	# A watched variable changed, we need to see if we have to update our own device state as a result
	#		
	def onWatchedVariableChanged (self, origVar, newVar, changeInfo):
		try:
			parent = indigo.devices[changeInfo.parentId]
			child = indigo.variables[changeInfo.childId]
		
			self.changeParentFromChild (parent, child, changeInfo, "variable")
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
		
		

	################################################################################
	# DEVICE UI HANDLERS
	################################################################################
		
	#
	# Validate the wrapper config
	#
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		try:
			# If the device state area is hidden then make sure the selected device matches - this is a safeguard
			# against them changing the main device after the defaults got set
			for i in range (1, self.TOTALDIMMING + 2 + 1): # Dimmers + On + Off + 1 (since we aren't starting at 0)
				method = "Dim" + str(i)
				if i == self.TOTALDIMMING + 1: method = "On"
				if i == self.TOTALDIMMING + 2: method = "Off"
				
				if valuesDict["showStateFromDevice" + method] == False:
					# We are hiding the device state, sync the device with the deviceIsOn device
					valuesDict["stateFromDevice" + method] = valuesDict["device" + method]
					
			# Make sure no matter what config were were viewing that we return to the On view
			valuesDict["settingSelect"] = "On"
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return valuesDict
	
	################################################################################
	# DEVICE CONFIG UI
	################################################################################
	
	#
	# Return methods appropriate for the device AsType
	#
	def listSettingSelect (self, filter="", valuesDict=None, typeId="", targetId=0):
		ret = []

		try:
			# Common
			ret.append (("cnd", "Conditions"))
			ret.append (("On", "On"))
			ret.append (("Off", "Off"))
			
			if valuesDict is None or len(valuesDict) == 0: return ret # otherwise we error out in next statement
			
			# Only if the type supports brightness
			if valuesDict["treatAs"] in self.DIMMERS:
				term = "% Open "
				if valuesDict["treatAs"] == "dimmer": term = "Brightness "
				for i in range (1, self.TOTALDIMMING + 1):
					ret.append (("Dim" + str(i), term + str(i)))
							
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return ret
	
		
	#
	# A form field changed, update defaults
	#
	def onAfter_formFieldChanged (self, valuesDict, typeId, devId):
		try:
			if valuesDict["settingSelect"] == "":
				# Brand new device but no action selected yet, set the default action and return
				valuesDict["settingSelect"] = "On"
				return valuesDict
				
			# If they changed from a device supporting variances to one that doesn't then handle that here
			if valuesDict["settingSelect"][0:3] == "Dim":
				if valuesDict["treatAs"] in self.DIMMERS:
					pass
				else:
					valuesDict["settingSelect"] = "On"
				
			for i in range (1, self.TOTALDIMMING + 2 + 1): # Dimmers + On + Off + 1 (since we aren't starting at 0)
				method = "Dim" + str(i)
				if i == self.TOTALDIMMING + 1: method = "On"
				if i == self.TOTALDIMMING + 2: method = "Off"
				
				#indigo.server.log ("Global method: " + method + " (" + str(i) + ")")
				
				# Toggle off all visibility checkboxes and let the routine determine if they get turned off
				valuesDict["showAction" + method] = False
				valuesDict["showStatusFrom" + method] = False
				valuesDict["showValueAndOperator" + method] = False
				valuesDict["showStateFromDevice" + method] = False
								
				# If we have populated the On device, and the rest are blank, auto populate all devices to save user time
				if ext.valueValid (valuesDict, "deviceOn", True):
					for x in range (1, self.TOTALDIMMING + 2 + 1):
						m = "Dim" + str(x)
						if x == self.TOTALDIMMING + 1: m = "On"
						if x == self.TOTALDIMMING + 2: m = "Off"

						if ext.valueValid (valuesDict, "device" + m, True) == False: 
							valuesDict["device" + m] = valuesDict["deviceOn"]
							valuesDict["stateFromDevice" + m] = valuesDict["deviceOn"]
							
				
				# Don't set defaults unless we are looking at the section and we are not at "Do Not Implement"
				if valuesDict["settingSelect"] == method and ext.valueValid (valuesDict, "method" + method) and valuesDict["method" + method] != "none":
					if ext.valueValid (valuesDict, "method" + method):
						# A few miscellaneous defaults
						if valuesDict["valueOperator" + method] == "": valuesDict["valueOperator" + method] = "equal"
				
						# Device values
						if valuesDict["method" + method] == "device":
							valuesDict["showAction" + method] = True
							
							# If they selected a device, show the actions
							if ext.valueValid (valuesDict, "device" + method, True):
								valuesDict = self.setDeviceStatusMethodDefaults (valuesDict["device" + method], valuesDict, method)
							
								if ext.valueValid (valuesDict, "stateFromDevice" + method, True) == False:
									# If they don't have a device to pull states from then use this one as a default
									valuesDict["stateFromDevice" + method] = valuesDict["device" + method]
							
							else:
								# We can't prompt for actions unless there is a device
								valuesDict["showAction" + method] = False
								valuesDict["showStatusFrom" + method] = False
								valuesDict["showValueAndOperator" + method] = False
								valuesDict["showStateFromDevice" + method] = False
								
						elif valuesDict["method" + method] == "action":
							# Make sure fields are hidden if they are visible now
							for x in range (1, self.TOTALFIELDS + 1):
								valuesDict["optionGroup" + method + str(x)] = eps.act.toggleGroupVisibility (valuesDict["optionGroup" + method + str(x)])
								
							# Using an action group ALWAYS requires asking for state
							valuesDict["showStatusFrom" + method] = True
							valuesDict["showStateFromDevice" + method] = True
							valuesDict["showValueAndOperator" + method] = True
							
					if ext.valueValid (valuesDict, "stateFromDevice" + method, True):
						pass
						
				else:
					# If we aren't looking at this method then make sure all field options are hidden
					for x in range (1, self.TOTALFIELDS + 1):
						valuesDict["optionGroup" + method + str(x)] = eps.act.toggleGroupVisibility (valuesDict["optionGroup" + method + str(x)])
						
				# For the "show X from" we need to toggle that if we are comparing to variable or if it cannot be determined
				if valuesDict["settingSelect"] == method and ext.valueValid (valuesDict, "getStatusFrom" + method):
					if valuesDict["getStatusFrom" + method] == "none":
						#valuesDict["showStatusFrom" + method] = False
						valuesDict["showValueAndOperator" + method] = False
						valuesDict["showStateFromDevice" + method] = False
						
					elif valuesDict["getStatusFrom" + method] == "variable":
						valuesDict["showStatusFrom" + method] = True
						valuesDict["showValueAndOperator" + method] = True
						valuesDict["showStateFromDevice" + method] = False
					
												
			# LAST order of business, if we get here then we're no longer a new device			
			valuesDict["isNewDevice"] = False	
				
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
		return valuesDict
		
	#
	# Set default values for known devices to determine if a given method is active for a device
	#
	def setDeviceStatusMethodDefaults (self, devId, valuesDict, method):
		try:
			dev = indigo.devices[int(devId)]
			devActions = eps.plugcache.getActions (dev)
			
			# Make sure the currently selected action is valid, if not then clear it out so we can set defaults below
			isMatched = False
			for act, actInfo in devActions.iteritems():
				if act == valuesDict["deviceAction" + method]: isMatched = True
				
			if isMatched == False: valuesDict["deviceAction" + method] = ""
			
			if type(dev) is indigo.MultiIODevice:
				# This can use some finesse but for now it gets us where we want to be
				valuesDict["showStatusFrom" + method] = True
				valuesDict["showValueAndOperator" + method] = True
				valuesDict["showStateFromDevice" + method] = True
			
			elif type(dev) is indigo.RelayDevice or type(dev) is indigo.DimmerDevice or type(dev) is indigo.SensorDevice:
				# If this was just created then set the defaults for all the various methods
				if valuesDict["isNewDevice"]:
					if ext.valueValid (valuesDict, "deviceActionOn"): valuesDict["deviceActionOn"] = "indigo_turnOn"
					if ext.valueValid (valuesDict, "deviceActionOff"): valuesDict["deviceActionOff"] = "indigo_turnOff"
					
					for i in range (1, self.TOTALDIMMING + 1):
						if ext.valueValid (valuesDict, "deviceActionDim" + str(i)): 
							if type(dev) is indigo.DimmerDevice:
								valuesDict["deviceActionDim" + str(i)] = "indigo_setBrightness"
								valuesDict["brightnessDim" + str(i)] = str(i * 20)
								valuesDict["strValueDim" + str(i) + "1"] = str(i * 20) # First field is brightness level
								
							else:
								valuesDict["deviceActionDim" + str(i)] = "indigo_toggle"
								valuesDict["strValueDim" + str(i) + "1"] = ""
						
					
					
				if valuesDict["value" + method] == "{strValue" + method + "1}": valuesDict["value" + method] = "" # In case they change the action don't leave this lingering, we'll add it again below
				
				if valuesDict["deviceAction" + method] == "indigo_turnOn" or valuesDict["deviceAction" + method] == "indigo_turnOff" or valuesDict["deviceAction" + method] == "indigo_toggle":
					valuesDict["getStatusFrom" + method] = "state"
					valuesDict["valueOperator" + method] = "equal"
					valuesDict["stateFromDevice" + method] = str(dev.id)
					valuesDict["deviceState" + method] = "onOffState"
					
					valuesDict["showStatusFrom" + method] = False
					valuesDict["showStateFromDevice" + method] = False
					valuesDict["showValueAndOperator" + method] = False
					
				if valuesDict["deviceAction" + method] == "indigo_toggle" and method != "On" and method != "Off":
					# If they use toggle for a brightness action we don't know what to do
					valuesDict["showStatusFrom" + method] = True
					valuesDict["showValueAndOperator" + method] = True
					valuesDict["showStateFromDevice" + method] = True
					
				if valuesDict["deviceAction" + method] == "indigo_turnOn":
					valuesDict["value" + method] = "true"
					
				elif valuesDict["deviceAction" + method] == "indigo_turnOff":
					valuesDict["value" + method] = "false"
					
				elif valuesDict["deviceAction" + method] == "indigo_toggle":
					if method == "On": valuesDict["value" + method] = "true"
					if method == "Off": valuesDict["value" + method] = "false"
					
				elif valuesDict["deviceAction" + method] == "indigo_setBrightness" or valuesDict["deviceAction" + method] == "indigo_brighten" or valuesDict["deviceAction" + method] == "indigo_dim":
					valuesDict["getStatusFrom" + method] = "state"
					valuesDict["valueOperator" + method] = "equal"
					valuesDict["stateFromDevice" + method] = str(dev.id)
					valuesDict["deviceState" + method] = "brightnessLevel"
					valuesDict["value" + method] = "{strValue" + method + "1}"
					
					valuesDict["showStatusFrom" + method] = False
					valuesDict["showValueAndOperator" + method] = False
					valuesDict["showStateFromDevice" + method] = False
					
				else:
					valuesDict["showStatusFrom" + method] = True
					valuesDict["showValueAndOperator" + method] = True
					valuesDict["showStateFromDevice" + method] = True
				
			
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
		return valuesDict
		
	

		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
	
			
	
		
	def onWatchedAttributeChanged (self, origDev, newDev, changeInfo):
		self.logger.info ("I just got a watched attribute change")
		#indigo.server.log(unicode(changeInfo))
		
		dev = indigo.devices[changeInfo.parentId]
		if dev.deviceTypeId == "epsCustomDev2":
			eps.plug.checkConditions (dev.pluginProps, dev)
		
	def onWatchedPropertyChanged (self, origDev, newDev, changeInfo):
		self.logger.info ("I just got a watched property change")
		indigo.server.log(unicode(changeInfo))
	
	
		
	def onAfter_pluginDevicePropChanged (self, origDev, newDev, changedProps):	
		if newDev.deviceTypeId == "epsActionDev":
			eps.act.runAction (newDev.pluginProps)
	
		
	def onConditionsCheckPass (self, dev):
		indigo.server.log ("CONDITIONS PASSED!")
		
	def onConditionsCheckFail (self, dev):
		indigo.server.log ("CONDITIONS FAILED!")
		
	
	
	################################################################################
	# INDIGO COMMAND HAND-OFFS
	#
	# Everything below here are standard Indigo plugin actions that get handed off
	# to the engine, they really shouldn't change from plugin to plugin
	################################################################################
	
	################################################################################
	# INDIGO PLUGIN EVENTS
	################################################################################		
	
	# System
	def startup(self): return eps.plug.startup()
	def shutdown(self): return eps.plug.shutdown()
	def runConcurrentThread(self): return eps.plug.runConcurrentThread()
	def stopConcurrentThread(self): return eps.plug.stopConcurrentThread()
	def __del__(self): return eps.plug.delete()
	
	# UI
	def validatePrefsConfigUi(self, valuesDict): return eps.plug.validatePrefsConfigUi(valuesDict)
	def closedPrefsConfigUi(self, valuesDict, userCancelled): return eps.plug.closedPrefsConfigUi(valuesDict, userCancelled)
	
	################################################################################
	# INDIGO DEVICE EVENTS
	################################################################################
	
	# Basic comm events
	def deviceStartComm (self, dev): return eps.plug.deviceStartComm (dev)
	def deviceUpdated (self, origDev, newDev): return eps.plug.deviceUpdated (origDev, newDev)
	def deviceStopComm (self, dev): return eps.plug.deviceStopComm (dev)
	def deviceDeleted(self, dev): return eps.plug.deviceDeleted(dev)
	def actionControlDimmerRelay(self, action, dev): return eps.plug.actionControlDimmerRelay(action, dev)
	
	# UI Events
	def validateDeviceConfigUi(self, valuesDict, typeId, devId): return eps.plug.validateDeviceConfigUi(valuesDict, typeId, devId)
	def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId): return eps.plug.closedDeviceConfigUi(valuesDict, userCancelled, typeId, devId)		
	
	################################################################################
	# INDIGO PROTOCOL EVENTS
	################################################################################
	def zwaveCommandReceived(self, cmd): return eps.plug.zwaveCommandReceived(cmd)
	def zwaveCommandSent(self, cmd): return eps.plug.zwaveCommandSent(cmd)
	def insteonCommandReceived (self, cmd): return eps.plug.insteonCommandReceived(cmd)
	def insteonCommandSent (self, cmd): return eps.plug.insteonCommandSent(cmd)
	def X10CommandReceived (self, cmd): return eps.plug.X10CommandReceived(cmd)
	def X10CommandSent (self, cmd): return eps.plug.X10CommandSent(cmd)

	################################################################################
	# INDIGO VARIABLE EVENTS
	################################################################################
	
	# Basic comm events
	def variableCreated(self, var): return eps.plug.variableCreated(var)
	def variableUpdated (self, origVar, newVar): return eps.plug.variableUpdated (origVar, newVar)
	def variableDeleted(self, var): return self.variableDeleted(var)
		
	################################################################################
	# INDIGO EVENT EVENTS
	################################################################################
	
	# Basic comm events
	
	# UI
	def validateEventConfigUi(self, valuesDict, typeId, eventId): return eps.plug.validateEventConfigUi(valuesDict, typeId, eventId)
	def closedEventConfigUi(self, valuesDict, userCancelled, typeId, eventId): return eps.plug.closedEventConfigUi(valuesDict, userCancelled, typeId, eventId)
		
	################################################################################
	# INDIGO ACTION EVENTS
	################################################################################
	
	# Basic comm events
	def actionGroupCreated(self, actionGroup): eps.plug.actionGroupCreated(actionGroup)
	def actionGroupUpdated (self, origActionGroup, newActionGroup): eps.plug.actionGroupUpdated (origActionGroup, newActionGroup)
	def actionGroupDeleted(self, actionGroup): eps.plug.actionGroupDeleted(actionGroup)
		
	# UI
	def validateActionConfigUi(self, valuesDict, typeId, actionId): return eps.plug.validateActionConfigUi(valuesDict, typeId, actionId)
	def closedActionConfigUi(self, valuesDict, userCancelled, typeId, actionId): return eps.plug.closedActionConfigUi(valuesDict, userCancelled, typeId, actionId)
		
	################################################################################
	# INDIGO TRIGGER EVENTS
	################################################################################
	
	# Basic comm events
	def triggerStartProcessing(self, trigger): return eps.plug.triggerStartProcessing(trigger)
	def triggerStopProcessing(self, trigger): return eps.plug.triggerStopProcessing(trigger)
	def didTriggerProcessingPropertyChange(self, origTrigger, newTrigger): return eps.plug.didTriggerProcessingPropertyChange(origTrigger, newTrigger)
	def triggerCreated(self, trigger): return eps.plug.triggerCreated(trigger)
	def triggerUpdated(self, origTrigger, newTrigger): return eps.plug.triggerUpdated(origTrigger, newTrigger)
	def triggerDeleted(self, trigger): return eps.plug.triggerDeleted(trigger)
                                   
	# UI
	
	################################################################################
	# INDIGO SYSTEM EVENTS
	################################################################################
	
	# Basic comm events
	
	# UI
	
	################################################################################
	# EPS EVENTS
	################################################################################		
	
	# Plugin menu actions
	def pluginMenuSupportData (self): return eps.plug.pluginMenuSupportData ()
	def pluginMenuSupportDataEx (self): return eps.plug.pluginMenuSupportDataEx ()
	def pluginMenuSupportInfo (self): return eps.plug.pluginMenuSupportInfo ()
	def pluginMenuCheckUpdates (self): return eps.plug.pluginMenuCheckUpdates ()
	
	# UI Events
	def getCustomList (self, filter="", valuesDict=None, typeId="", targetId=0): return eps.ui.getCustomList (filter, valuesDict, typeId, targetId)
	def formFieldChanged (self, valuesDict, typeId, devId): return eps.plug.formFieldChanged (valuesDict, typeId, devId)
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	