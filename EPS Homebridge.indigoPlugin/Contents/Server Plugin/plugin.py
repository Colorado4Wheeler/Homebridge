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
	TVERSION	= "3.1.0"
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
			eps.act.PASS = "On"
			eps.act.FAIL = "Off"
			eps.act.VALIDATION = "methodOn"
			
			self.ALLDEVCOUNT = 0
			self.ALLACTCOUNT = 0
		
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
			self.logger.info ("The Homebridge server has been started, give it 60 seconds to finish loading")
		
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
							retList.append ((devId, indigo.devices[int(devId)].name))
							
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
							retList.append ((devId, indigo.actionGroups[int(devId)].name))
							
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
							typeList.append ((devId, indigo.devices[int(devId)].name))
							
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
							typeList.append ((devId, indigo.actionGroups[int(devId)].name))
							
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
	# Watch for state changes on linked devices
	#
	def onWatchedStateRequest (self, dev):
		self.logger.threaddebug ("Returning watched states for {0}".format(dev.deviceTypeId))
		ret = {}
		
		try:
			if dev.deviceTypeId == "Homebridge-Relay":
				for i in range (0, 2):
					method = "On"
					if i == 1: method = "Off"
					
					if dev.pluginProps["method" + method] == "device" and ext.valueValid (dev.pluginProps, "device" + method, True):
						devEx = indigo.devices[int(dev.pluginProps["device" + method])]
						devStates = []
					
						if type(devEx) is indigo.RelayDevice or type(devEx) is indigo.DimmerDevice or "onOffState" in dev.states:
							devStates.append("onOffState")
						
						if type(devEx) is indigo.DimmerDevice or "brightnessLevel" in dev.states:
							devStates.append("brightnessLevel")
							
						if dev.pluginProps["device" + method + "ShowStates"] and ext.valueValid (dev.pluginProps, "device" + method + "State", True):
							# They are using a custom state to determine the on/off state of our device
							if dev.pluginProps["device" + method + "State"] in devStates:
								pass
							else:
								devStates.append(dev.pluginProps["device" + method + "State"])
					
						if len(devStates) > 0: ret[devEx.id] = devStates
				
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
			for i in range (0, 2):
					method = "On"
					if i == 1: method = "Off"
					
					if dev.pluginProps["method" + method] == "device" and ext.valueValid (dev.pluginProps, "device" + method, True):
						ret[int(dev.pluginProps["device" + method])] = ["address", "name"]
								
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
			if dev.deviceTypeId == "epsCustomDev":
				ret[int(dev.pluginProps["variable"])] = True # Variables don't have extra info, just that we watch the value
								
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return ret
		
	#
	# A form field changed, update defaults
	#
	def onAfter_formFieldChanged (self, valuesDict, typeId, devId):
		try:
			if valuesDict["methodOffMaster"] != "passthrough" and valuesDict["methodOffMaster"] != "on" and valuesDict["methodOffMaster"] != "same":
				valuesDict["methodOff"] = valuesDict["methodOffMaster"]
			else:
				valuesDict["methodOff"] = "hidden"
			
			# Basic defaults
			valuesDict["deviceOnShowStates"] = False	
			valuesDict["deviceOffShowStates"] = False	
			
			if valuesDict["deviceActionOn"] == "": valuesDict["deviceActionOn"] = "indigo_turnOn"
			if valuesDict["deviceActionOff"] == "": valuesDict["deviceActionOff"] = "indigo_turnOff"
				
			# If this is a switch and we are using the stock on and off commands then we don't need to show fields
			if typeId == "Homebridge-Relay":
				if valuesDict["deviceActionOn"] == "indigo_turnOn" or valuesDict["deviceActionOn"] == "indigo_turnOff":
					valuesDict["deviceOnState"] = "onOffState"
					valuesDict["deviceOnStateValue"] = "true"
					if valuesDict["deviceActionOn"] == "indigo_turnOff": valuesDict["deviceOnStateValue"] = "false"
				else:
					valuesDict["deviceOnShowStates"] = True
					
				if valuesDict["deviceActionOff"] == "indigo_turnOn" or valuesDict["deviceActionOff"] == "indigo_turnOff":
					valuesDict["deviceOffState"] = "onOffState"
					valuesDict["deviceOffStateValue"] = "true"
					if valuesDict["deviceActionOff"] == "indigo_turnOff": valuesDict["deviceOffStateValue"] = "false"
				else:
					valuesDict["deviceOffShowStates"] = True
				
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
		return valuesDict
	
	#
	# Our device was turned on
	#
	def onDeviceCommandTurnOn (self, dev):	
		try:
			if dev.pluginProps["methodOn"] == "device" and ext.valueValid (dev.pluginProps, "deviceOn", True):
				return eps.act.runAction (dev.pluginProps)
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			return False
			
		return True
		
	#
	# Our device was turned off
	#
	def onDeviceCommandTurnOff (self, dev):	
		try:
			if dev.pluginProps["methodOffMaster"] == "passthrough" and ext.valueValid (dev.pluginProps, "deviceOn", True):
				# Pass through is just that, a one-for-one so we are simply turning off the device
				props = dev.pluginProps
				props["deviceActionOn"] = "indigo_turnOff"
				
				return eps.act.runAction (props)
				
			elif dev.pluginProps["methodOff"] == "device" and ext.valueValid (dev.pluginProps, "deviceOff", True):
				return eps.act.runAction (dev.pluginProps, "Off")
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			return False
			
		return True	
		
	#
	# A watched state changed, we need to see if we have to update our own device state as a result
	#
	def onWatchedStateChanged (self, origDev, newDev, changeInfo):
		parent = indigo.devices[changeInfo.parentId]
		child = indigo.devices[changeInfo.childId]
		
		# Get our on and off devices (typically we expect them to be the same but who knows what lerks in the minds of users)
		devOn = False
		devOff = False
		
		if ext.valueValid (parent.pluginProps, "deviceOn", True): devOn = indigo.devices[int(parent.pluginProps["deviceOn"])]
		if ext.valueValid (parent.pluginProps, "deviceOff", True): devOff = indigo.devices[int(parent.pluginProps["deviceOff"])]
		
		# Before proceeding make sure the state change matches the on or off states of our devices, otherwise no need to go on
		isOnState = False
		isOffState =False
		
		if devOn and parent.pluginProps["deviceOnState"] == changeInfo.name and child.id == devOn.id: isOnState = True
		if devOff and parent.pluginProps["deviceOffState"] == changeInfo.name and child.id == devOff.id: isOffState = True
		
		if isOnState == False and isOffState == False:
			self.logger.debug ("The device state change does not match the states being monitored for either off or on on this device")
			return
		
		onValue = None
		offValue = None
		
		if devOn: onValue = devOn.states[parent.pluginProps["deviceOnState"]]
		if devOff: offValue = devOff.states[parent.pluginProps["deviceOffState"]]
		
		# If the parent and child devices and states are the same (and typically we expect them to be) then it's an easy comparison
		if devOn and devOff and devOn.id == devOff.id and parent.pluginProps["deviceOnState"] == parent.pluginProps["deviceOffState"]:
			if unicode(onValue).lower() == parent.pluginProps["deviceOnStateValue"].lower():
				parent.updateStateOnServer("onOffState", True)
				
			elif unicode(offValue).lower() == parent.pluginProps["deviceOffStateValue"].lower():
				parent.updateStateOnServer("onOffState", False)
				
			else:
				self.logger.warn ("Even though our on and off devices and states are the same somehow we cannot figure out if we should be on or off")
				indigo.server.log(unicode(onValue).lower())
				indigo.server.log(parent.pluginProps["deviceOnStateValue"].lower())
				indigo.server.log(unicode(offValue).lower())
				indigo.server.log(parent.pluginProps["deviceOffStateValue"].lower())
		
		return
		
		# To know if we should be on or off is based on one state being a match and the other not because if both
		# states are matched to the configured values then it's both on and off at the same time and while it could be
		# possible there's no way to actually reflect that in the UI
		if unicode(devOn).lower() == parent.pluginProps["deviceOnStateValue"].lower() and unicode(devOff).lower() != parent.pluginProps["deviceOffStateValue"].lower():
			# The device On is true and the device Off is false, therefor we are on
			parent.updateStateOnServer("onOffState", True)
			
		elif unicode(devOn).lower() != parent.pluginProps["deviceOnStateValue"].lower() and unicode(devOff).lower() == parent.pluginProps["deviceOffStateValue"].lower():
			# The device Off is true and the device On is false, therefor we are off
			parent.updateStateOnServer("onOffState", False)
			
		else:
			self.logger.warn ("The device '{0}' is somehow both on and off based on the states of the device it references, I don't know what to do".format(parent.name))
			return
		
		
		return
		
		onValue = parent.pluginProps["deviceOnStateValue"]
		offValue = parent.pluginProps["deviceOffStateValue"]
		
		onNewValue = ""
		offNewValue = ""
		
		if changeInfo.name == parent.pluginProps["deviceOnState"] and changeInfo.childId == int(parent.pluginProps["deviceOn"]):
			# Our on device on state changed
			onNewValue = unicode(child.states[changeInfo.name])
		
		if changeInfo.name == parent.pluginProps["deviceOffState"] and changeInfo.childId == int(parent.pluginProps["deviceOff"]):
			# Our on device on state changed
			offNewValue = unicode(child.states[changeInfo.name])
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
	
			
	def onWatchedVariableChanged (self, origVar, newVar, changeInfo):
		self.logger.info ("I just got a watched variable change")
		# Test the conditions
		dev = indigo.devices[changeInfo.parentId]
		if dev.deviceTypeId == "epsCustomDev2":
			eps.plug.checkConditions (dev.pluginProps, dev)
		
	def onWatchedAttributeChanged (self, origDev, newDev, changeInfo):
		self.logger.info ("I just got a watched attribute change")
		#indigo.server.log(unicode(changeInfo))
		
		dev = indigo.devices[changeInfo.parentId]
		if dev.deviceTypeId == "epsCustomDev2":
			eps.plug.checkConditions (dev.pluginProps, dev)
		
	def onWatchedPropertyChanged (self, origDev, newDev, changeInfo):
		self.logger.info ("I just got a watched property change")
		indigo.server.log(unicode(changeInfo))
	
	def onAfter_deviceStartComm (self, dev):
		pass
		
	def onAfter_pluginDevicePropChanged (self, origDev, newDev, changedProps):	
		if newDev.deviceTypeId == "epsActionDev":
			eps.act.runAction (newDev.pluginProps)
			
	def onAfter_pluginDeviceUpdated (self, origDev, newDev):
		pass
		
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
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	