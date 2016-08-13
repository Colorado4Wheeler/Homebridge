# eps.plug - Mirrors definitions from Indigo API and passes them to other routines if/when needed
#
# Copyright (c) 2016 ColoradoFourWheeler / EPS
#

import indigo
import logging
import sys
import random # for uniqueIdentifier
import datetime
from datetime import date, timedelta
import string

import ext
import dtutil

# ENUMS
NOTHING = 0
BEFORE = 1
AFTER = 2

class plug:	
	isSubscribedVariables = False
	isSubscribedDevices = False
	isSubscribedActionGroups = False
	
	lastDeviceLoaded = True # Initialize as the plugin starting up

	#
	# Initialize the  class
	#
	def __init__(self, factory):
		self.logger = logging.getLogger ("Plugin.plug")
		self.factory = factory
		
	#
	# Subscribe to changes
	#
	def subscribeChanges (self, changes = []):
		try:
			for change in changes:
				if change.lower() == "variables": self.isSubscribedVariables = True
				if change.lower() == "devices": self.isSubscribedDevices = True
				if change.lower() == "actiongroups": self.isSubscribedActionGroups = True
				
				f = getattr(indigo, change.lower())
				f.subscribeToChanges()
				
		except Exception as e:
			self.logger.error (ext.getException(e))	
						
	#
	# Subscribe to protocols
	#
	def subscribeProtocols (self, changes = {}):
		try:
			#indigo.server.log(unicode(changes))
			for protocol, change in changes.iteritems():
				# Load the protocol library for zwave if needed
				if protocol.lower() == "zwave":
					self.logger.threaddebug ("ZWave listener, loading zwave library")
				
				cmds = change.split("|")
				for cmd in cmds:			
					self.logger.threaddebug ("Listening for {0} {1} commands".format(protocol, cmd))
					
					if cmd == "outgoing": 
						cmd = "subscribeToOutgoing"
					else:
						cmd = "subscribeToIncoming"
				
					f = getattr(getattr(indigo, protocol.lower()), cmd)
					f()
				
		except Exception as e:
			self.logger.error (ext.getException(e))	
					
					
	#
	# Check for a callback
	#
	def _callBack (self, type, args, funcname = None):
		retval = None
		
		try:
			caller = sys._getframe(1).f_code.co_name
			
			if funcname is None:
				prefix = "onBefore_"
				if type == AFTER: prefix = "onAfter_"
			
				funcname = prefix + caller
			
			if funcname in dir(self.factory.plugin):	
				if caller != "runConcurrentThread":		
					self.logger.threaddebug ("Raising {0} in plugin.py from call to {1}".format(funcname, caller))
			
				func = getattr(self.factory.plugin, funcname)
				
				if len(args) > 0: 
					retval = func(*args)
				else:
					retval = func()
				
			return retval
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return retval
			
	#
	# Check to see if we have finished our loading
	#
	def isFinishedLoading (self):
		try:
			if self.lastDeviceLoaded:
				try:
					lastLoad = datetime.datetime.strptime (self.lastDeviceLoaded, "%Y-%m-%d %H:%M:%S")
				except:
					return False
					
				diff = dtutil.dateDiff ("seconds", indigo.server.getTime(), lastLoad)
				if diff > 3:
					self.lastDeviceLoaded = False
					self.logger.info (self.factory.plugin.pluginDisplayName + " is loaded and ready to use")
					return True
				else:
					return False
				
			else:
				return True
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return False
			
		return False
		
			
	################################################################################
	# PLUGIN ROUTINES
	################################################################################	

	# Plugin starting up (Indigo)
	def startup (self): 
		try:
			self.logger.threaddebug ("Plugin '{0}' is starting".format(self.factory.plugin.pluginDisplayName))
			
			self._callBack (NOTHING, [], "pluginUpgrade")
			
			self._callBack (BEFORE, [])	
			
			# Load up the plugin cache here, this allows the plugin to load the UI without the weight of
			# the refresh, but only do it if we need it for something, otherwise if the plugin needs it
			# for something else it can load in the on_after call
			if "cond" in dir(self): self.factory.ui.pcache = plugcache(self.factory.plugin)
			if "act" in dir(self): self.factory.ui.action = self.act
			
			self._callBack (AFTER, [])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	# Plugin shutting down (Indigo)
	def shutdown (self): 
		try:
			self.logger.threaddebug ("Plugin '{0}' is stopping".format(self.factory.plugin.pluginDisplayName))
			
			self._callBack (BEFORE, [])	
			
			self._callBack (AFTER, [])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	# Plugin deleted (Indigo)
	def delete (self):
		pass
			
	# Plugin configuration UI validation (Indigo)
	def validatePrefsConfigUi(self, valuesDict):
		errorDict = indigo.Dict()
		success = True
		
		try:
			self.logger.threaddebug ("Validating plugin configuration")
			
			retval = self._callBack (BEFORE, [valuesDict])
			if retval is not None:
				if "success" in retval: success = retval["success"]
				if "valuesDict" in retval: valuesDict = retval["valuesDict"]
				if "errorDict" in retval: errorDict = retval["errorDict"]
				
			
			
			retval = self._callBack (AFTER, [valuesDict])
			if retval is not None:
				if "success" in retval: success = retval["success"]
				if "valuesDict" in retval: valuesDict = retval["valuesDict"]
				if "errorDict" in retval: errorDict = retval["errorDict"]
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return (success, valuesDict, errorDict)
		
	# Plugin configuration UI closing (Indigo)
	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		try:
			if userCancelled:
				self.logger.threaddebug ("Plugin '{0}' configuration dialog cancelled".format(self.factory.plugin.pluginDisplayName))
			else:
				self.logger.threaddebug ("Plugin '{0}' configuration dialog closed".format(self.factory.plugin.pluginDisplayName))
			
			self._callBack (BEFORE, [valuesDict, userCancelled])	
			
			# Set the debug level
			if int(valuesDict["logLevel"]) < 20: 
				self.logger.info("Debug logging enabled")
			else:
				self.logger.info("Debug logging disabled")
				
			self.factory.plugin.indigo_log_handler.setLevel(int(valuesDict["logLevel"]))
			
			self._callBack (AFTER, [valuesDict, userCancelled])
		
		except Exception as e:
			self.logger.error (ext.getException(e))
	
	################################################################################
	# CONCURRENT THREAD
	################################################################################	
	def runConcurrentThread(self):
		try:
			while True:
				self._callBack (BEFORE, [])
				
				if "update" in dir(self.factory):
					self.factory.update.check (False, False)
				
				self._callBack (AFTER, [])
				
				self.isFinishedLoading() # Passive if we are ready, calculation if we are not - lightweight
								
				self.factory.plugin.sleep(1)
				
				
		except self.factory.plugin.StopThread:
			pass
			
	def stopConcurrentThread(self):
		self._callBack (BEFORE, [])
		self.factory.plugin.stopThread = True
		self._callBack (AFTER, [])
				
	################################################################################
	# DEVICE COMMUNICATION
	################################################################################			
	
	# Call that Indigo makes to change the state display ID on the fly (Indigo)
	def getDeviceDisplayStateId(self, dev):
		try:
			ret = self._callBack (BEFORE, [dev])
			if ret is not None and ret != "": return ret
			
			ret = self._callBack (AFTER, [dev])
			if ret is not None and ret != "": return ret
			
			return self.factory.plugin.devicesTypeDict[dev.deviceTypeId][u'DisplayStateId']
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	# Device starts communication (Indigo)
	def deviceStartComm (self, dev):
		try:
			self.logger.threaddebug ("Starting communications on '{0}'".format(dev.name))
			self._callBack (BEFORE, [dev])
			
			self.deviceStateUpgrade (dev) # Do this before committing state changes in case we need to upgrade or migrate
			dev.stateListOrDisplayStateIdChanged() # Commit any state changes
			
			if ext.valueValid (dev.states, "lastreset"):
				if ext.valueValid (dev.states, "lastreset", True) == False: dev.updateStateOnServer("lastreset", indigo.server.getTime().strftime("%Y-%m-%d"))
			
			self.addPluginDeviceToCache (dev)
			
			# If the name has "copy" as the last word in the name, check if this might have been copied from another device,
			# but this can only happen after we are already up and running
			#i = string.find (dev.name, "copy")
			#if i > -1:
			#	if self.isFinishedLoading():
			#		indigo.server.log("copy")
			
			self._callBack (AFTER, [dev])
			
			if self.lastDeviceLoaded: self.lastDeviceLoaded = indigo.server.getTime().strftime("%Y-%m-%d %H:%M:%S")
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	# Add device to cache and initialize callbacks for it - here so we can re-call this on device updates as well as start comm (Custom)
	def addPluginDeviceToCache (self, dev):
		try:
			self._callBack (BEFORE, [dev])
			
			if "cache" in dir(self.factory): 
				self.factory.cache.addDevice (dev)
				#indigo.server.log(unicode(self.factory.cache.items))
				
				# If the plugin is defining watched states request them
				watcher = self._callBack (NOTHING, [dev], "onWatchedStateRequest")
				if watcher is not None and len(watcher) > 0:
					self.factory.cache.addWatchedStates (dev, watcher)
					
				# If the plugin is defining watched attributes request them
				watcher = self._callBack (NOTHING, [dev], "onWatchedAttributeRequest")
				if watcher is not None and len(watcher) > 0:
					self.factory.cache.addWatchedAttribute (dev, watcher)
					
				# If the plugin is defining watched device config props request them
				watcher = self._callBack (NOTHING, [dev], "onWatchedPropRequest")
				if watcher is not None and len(watcher) > 0:
					self.factory.cache.addWatchedProperty (dev, watcher)
					
				# If the plugin wants to simply watch an object without diving into details (like props, states, 
				# attributes, etc) - useful if we want to find items in cache but don't really need to know about
				# actual changes to that item (i.e., doing address lookups)
				watcher = self._callBack (NOTHING, [dev], "onWatchedObjectRequest")
				if watcher is not None and len(watcher) > 0:
					self.factory.cache.addWatchedObject (dev, watcher)
					
				# If the plugin is defining watched variables request them
				# Note: If variables are auto-detected then the plugin doesn't need to do this since
				# if auto-detected the value is watched automatically, it's more for plugins that
				# call the variable field something odd like "myvariable" or something
				watcher = self._callBack (NOTHING, [dev], "onWatchedVariableRequest")
				if watcher is not None and len(watcher) > 0:
					self.factory.cache.addWatchedVariable (dev, watcher)
					
				# If the plugin wants to know when an action group is run
				watcher = self._callBack (NOTHING, [dev], "onWatchedActionGroupRequest")
				if watcher is not None and len(watcher) > 0:
					self.factory.cache.addWatchedActionGroup (dev, watcher)
					
			self._callBack (AFTER, [dev])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	# Device state upgrade in case we are changing things from release to release, happens before we update states in deviceStartCom
	def deviceStateUpgrade (self, dev):
		try:
			self.logger.threaddebug ("Checking for device state updates on '{0}'".format(dev.name))
			
			self._callBack (BEFORE, [dev])
			
			
			self._callBack (AFTER, [dev])
		
		except Exception as e:
			self.logger.error (ext.getException(e))				
				
				
	# Device updated (Indigo)
	def deviceUpdated (self, origDev, newDev):
		try:
			if self.isFinishedLoading():
				pass
			else:
				return
			
			if newDev.pluginId == self.factory.plugin.pluginId:
				if len(origDev.pluginProps) > 0: 
					self.pluginDeviceUpdated (origDev, newDev)
					
				elif len(origDev.pluginProps) == 0 and len(newDev.pluginProps) == 0 and newDev.deviceTypeId != "":
					self.pluginDeviceBegun (newDev)
					
				elif len(origDev.pluginProps) == 0 and len(newDev.pluginProps) > 0:
					self.pluginDeviceCreated (newDev)
					
			
			# See if we are watching this
			if "cache" in dir(self.factory):
				ret = self.factory.cache.watchedItemChanges (origDev, newDev)
				for change in ret:
					self.logger.debug ("'{0}' {1} '{2}' has changed".format(newDev.name, change.type, change.name))
					
					if change.itemType == "Device":
						if change.type == "state": self._callBack (NOTHING, [origDev, newDev, change], "onWatchedStateChanged")
						if change.type == "property": self._callBack (NOTHING, [origDev, newDev, change], "onWatchedPropertyChanged")
						if change.type == "attribute": self._callBack (NOTHING, [origDev, newDev, change], "onWatchedAttributeChanged")
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	# New plugin device entering configuration
	def pluginDeviceBegun (self, dev):
		try:
			self.logger.threaddebug ("Plugin device '{0}' being created and configured".format(dev.name))
			
			self._callBack (BEFORE, [dev])	
			
			self._callBack (AFTER, [dev])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
				
	# Plugin device created (Custom)
	def pluginDeviceCreated (self, dev):
		try:
			self.logger.threaddebug ("Plugin device '{0}' created".format(dev.name))
			
			self._callBack (BEFORE, [dev])	
			
			# Collapse conditions to return form to correct size if conditions are loaded
			if "cond" in dir(self.factory):	self.factory.cond.collapseAllConditions (dev)
			
			self.addPluginDeviceToCache (dev)
									
			self._callBack (AFTER, [dev])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
				
	# Plugin device updated (Custom)
	def pluginDeviceUpdated (self, origDev, newDev):
		try:
			self.logger.threaddebug ("Plugin device '{0}' has been updated".format(newDev.name))
			self._callBack (BEFORE, [origDev, newDev])	
			
			# See if any states changed so we can raise the correct event
			changedStates = []
			for oKey, oVal in origDev.states.iteritems():
				for nKey, nVal in newDev.states.iteritems():
					if oKey == nKey and oVal != nVal: changedStates.append(oKey)
					
			changedProps = []
			for oKey, oVal in origDev.pluginProps.iteritems():
				for nKey, nVal in newDev.pluginProps.iteritems():
					if oKey == nKey and oVal != nVal: changedProps.append(oKey)
					
			changedAttributes = []
			oProps = [a for a in dir(origDev) if not a.startswith('__') and not callable(getattr(origDev,a))]
			nProps = [a for a in dir(newDev) if not a.startswith('__') and not callable(getattr(newDev,a))]
			for o in oProps:
				for n in nProps:
					if getattr(origDev, o) != getattr(newDev, n): changedAttributes.append(o)
							
			# Collapse conditions to return form to correct size if conditions are loaded
			if "cond" in dir(self.factory):	self.factory.cond.collapseAllConditions (newDev)
			
			# If props changed then re-cache the device to be safe
			if "cache" in dir(self.factory) and len(changedProps) > 0:
				# For ease simply remove the device cache and re-add it
				self.factory.cache.removeDevice (newDev)
				self.addPluginDeviceToCache (newDev) # If cache is enabled
			
			self._callBack (AFTER, [origDev, newDev])
					
			if len(changedStates) > 0: self.pluginDeviceStateChanged (origDev, newDev, changedStates)
			if len(changedProps) > 0: self.pluginDevicePropChanged (origDev, newDev, changedProps)
			if len(changedAttributes) > 0: self.pluginDeviceAttribChanged (origDev, newDev, changedAttributes)
				
		except Exception as e:
			self.logger.error (ext.getException(e))		


	# Plugin device updated and had a state change (Custom)
	def pluginDeviceStateChanged (self, origDev, newDev, changedStates):
		try:
			self.logger.threaddebug ("Plugin device '{0}' has had one or more state changes".format(newDev.name))
			
			self._callBack (BEFORE, [origDev, newDev, changedStates])	
			
			self._callBack (AFTER, [origDev, newDev, changedStates])
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			

	# Plugin device updated and had a property change (Custom)
	def pluginDevicePropChanged (self, origDev, newDev, changedProps):
		try:
			self.logger.threaddebug ("Plugin device '{0}' has had one or more property changes".format(newDev.name))
			
			self._callBack (BEFORE, [origDev, newDev, changedProps])	
			
			self._callBack (AFTER, [origDev, newDev, changedProps])
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
	# Plugin device updated and had an attribute change (Custom)
	def pluginDeviceAttribChanged (self, origDev, newDev, changedAttributes):
		try:
			self.logger.threaddebug ("Plugin device '{0}' has had one or more attribute changes".format(newDev.name))
			
			self._callBack (BEFORE, [origDev, newDev, changedAttributes])	
			
			self._callBack (AFTER, [origDev, newDev, changedAttributes])
		
		except Exception as e:
			self.logger.error (ext.getException(e))		


	# Plugin device stopped communication (Indigo)
	def deviceStopComm (self, dev):
		try:
			self.logger.threaddebug ("Plugin device '{0}' stopped communication".format(dev.name))
			
			self._callBack (BEFORE, [dev])	
			
			self._callBack (AFTER, [dev])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	# Plugin device deleted (Indigo)
	def deviceDeleted(self, dev):
		try:
			self.logger.threaddebug ("Device '{0}' deleted".format(dev.name))
			
			self._callBack (BEFORE, [dev])
			
			if "cache" in dir(self.factory):
				self.factory.cache.removeDevice (dev)	
				
			if dev.pluginId == self.factory.plugin.pluginId:
				self.pluginDeviceDeleted (dev)
			
			self._callBack (AFTER, [dev])
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
	# Plugin device deleted (Custom)
	def pluginDeviceDeleted (self, dev):
		try:
			self.logger.threaddebug ("Plugin device '{0}' deleted".format(dev.name))
			
			self._callBack (BEFORE, [dev])
			
			self._callBack (AFTER, [dev])
		
		except Exception as e:
			self.logger.error (ext.getException(e))		


	# Validate the device configuration (Indigo)
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		errorDict = indigo.Dict()
		success = True
		
		try:
			dev = indigo.devices[devId]
			self.logger.threaddebug ("Validating configuration on '{0}'".format(dev.name))
			
			retval = self._callBack (BEFORE, [valuesDict, typeId, devId])
			if retval is not None:
				if retval[0] == False: success = False
				valuesDict = retval[1]
				errorDict = retval[2]
				
			# Validate conditions if needed
			if "cond" in dir(self.factory):
				retval = self.factory.cond.validateDeviceConfigUi(valuesDict, typeId, devId)
				if retval[0] == False: success = False
				valuesDict = retval[1]
				errorDict = retval[2]
				
			# Validate actions if needed
			if "act" in dir(self.factory):
				retval = self.factory.act.validateDeviceConfigUi(valuesDict, typeId, devId)
				if retval[0] == False: success = False
				valuesDict = retval[1]
				errorDict = retval[2]
			
			retval = self._callBack (AFTER, [valuesDict, typeId, devId])
			if retval is not None:
				if retval[0] == False: success = False
				valuesDict = retval[1]
				errorDict = retval[2]
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return (success, valuesDict, errorDict)


	# Device configuration closed (Indigo)
	def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
		try:
			dev = indigo.devices[devId]
			
			if userCancelled:
				self.logger.threaddebug ("Plugin device '{0}' configuration dialog cancelled".format(dev.name))
			else:
				self.logger.threaddebug ("Plugin device '{0}' configuration dialog closed".format(dev.name))
			
			self._callBack (BEFORE, [valuesDict, userCancelled, typeId, devId])	
			
			# Make sure we've flushed the cache for this device
			self.factory.ui.flushCache (dev.id)
			
			self._callBack (AFTER, [valuesDict, userCancelled, typeId, devId])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	

	
	# Device turn on/off/toggle/brightness (Indigo)
	def actionControlDimmerRelay(self, action, dev):
		try:
			self.logger.threaddebug ("Plugin device '{0}' command sent".format(dev.name))
			
			self._callBack (BEFORE, [dev])	
			
			success = False
			stateName = "onOffState"
			stateVal = True
			command = "on"
			
			if action.deviceAction == indigo.kDimmerRelayAction.TurnOn:
				command = "on"
				stateName = "onOffState"
				
				success = self._callBack (NOTHING, [dev], "onDeviceCommandTurnOn")
				if success:
					stateVal = True
									
			elif action.deviceAction == indigo.kDimmerRelayAction.TurnOff:
				command = "off"
				stateName = "onOffState"
				
				success = self._callBack (NOTHING, [dev], "onDeviceCommandTurnOff")
				if success:
					stateVal = False
									
			elif action.deviceAction == indigo.kDimmerRelayAction.Toggle:
				command = "toggle"
				stateName = "onOffState"
				stateVal = dev.states["onOffState"]
								
				#success = self._callBack (NOTHING, [dev], "onDeviceCommandToggle")
				# Toggle is just a fancy name for on and off, so raise the on and off events
				if stateVal:
					success = self._callBack (NOTHING, [dev], "onDeviceCommandTurnOff")
				else:
					success = self._callBack (NOTHING, [dev], "onDeviceCommandTurnOn")
				
				if success:
					# Reverse the state value so we can update our own state to be the opposite of what it was
					if stateVal: 
						stateVal = False
					else:
						stateVal = True
						
			elif action.deviceAction == indigo.kDimmerRelayAction.SetBrightness:
				command = "set brightness"
				stateName = "brightnessLevel"
				
				if ext.valueValid (dev.states, stateName):
					success = self._callBack (NOTHING, [dev, action.actionValue], "onDeviceCommandSetBrightness")
					stateVal = action.actionValue
				else:
					success = False
				
				if success:
					stateVal = action.actionValue
					
			else:
				self.logger.error ("Unknown device command: " + unicode(action))
					
					
			if success:
				dev.updateStateOnServer(stateName, stateVal)
				self.logger.info(u"sent \"%s\" %s" % (dev.name, command))
			else:
				self.logger.error (u"send \"%s\" %s failed" % (dev.name, command))
			
			self._callBack (AFTER, [dev])
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
	
	
	################################################################################
	# INDIGO PROTOCOL EVENTS
	################################################################################
	
	# Device protocol command received (Custom)
	def protocolCommandReceivedFromCache (self, dev, cmd, type):
		try:
			self._callBack (BEFORE, [dev, cmd, type])	
			
			self._callBack (AFTER, [dev, cmd, type])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	# Device protocol command sent (Custom)
	def protocolCommandSentFromCache (self, dev, cmd, type):
		try:
			self._callBack (BEFORE, [dev, cmd, type])	
			
			self._callBack (AFTER, [dev, cmd, type])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	# ZWave command sent from device (Indigo)
	def zwaveCommandReceived(self, cmd):
		try:
			command = self.zwaveCommandAction (cmd)
			self.logger.threaddebug ("Plugin detected ZWave '{0}' action from device node {1}".format(command[1], command[0]))
			
			self._callBack (BEFORE, [cmd])	
			
			if "cache" in dir(self.factory):
				dev = self.factory.cache.addressToDev (command[0])
				if dev: self.protocolCommandReceivedFromCache (dev, command[1], "zwave")
			
			self._callBack (AFTER, [cmd])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	# Indigo sent a ZWave command (Indigo)
	def zwaveCommandSent(self, cmd):
		try:
			command = self.zwaveCommandAction (cmd)
			self.logger.threaddebug ("Plugin detected ZWave '{0}' action sent from Indigo to device node {1}".format(command[1], command[0]))
			
			self._callBack (BEFORE, [cmd])	
			
			if "cache" in dir(self.factory):
				dev = self.factory.cache.addressToDev (command[0])
				if dev: self.protocolCommandSentFromCache (dev, command[1], "zwave")
					
			
			self._callBack (AFTER, [cmd])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	# Decode ZWave command (Custom)
	def zwaveCommandAction (self, cmd):
		nodeId = 0
		
		try:
			byteList = cmd['bytes']
			byteListStr = ' '.join(["%02X" % byte for byte in byteList])
		
			if ext.valueValid (cmd, "nodeId", True): nodeId = cmd['nodeId']
			
			cmdFunc = "Unknown"
			cmdF = int(cmd['bytes'][8])
			if cmdF == 0: cmdFunc = "off"
			if cmdF == 255: cmdFunc = "on"
			
			return [nodeId, cmdFunc]
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return [nodeId, "Unknown"]
	
	# Insteon command sent from device (Indigo)
	def insteonCommandReceived (self, cmd):
		try:
			command = cmd.cmdFunc
			self.logger.threaddebug ("Plugin detected Insteon '{0}' action from the network".format(command))
			
			self._callBack (BEFORE, [cmd])	
			
			if "cache" in dir(self.factory):
				dev = self.factory.cache.addressToDev (cmd.address)
				if dev: self.protocolCommandReceivedFromCache (dev, command, "insteon")
			
			self._callBack (AFTER, [cmd])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	# Indigo sent an Insteon command (Indigo)
	def insteonCommandSent (self, cmd):
		try:
			command = cmd.cmdFunc
			self.logger.threaddebug ("Plugin detected Insteon '{0}' action sent from Indigo".format(command))
			
			self._callBack (BEFORE, [cmd])	
			
			if "cache" in dir(self.factory):
				dev = self.factory.cache.addressToDev (cmd.address)
				if dev: self.protocolCommandSentFromCache (dev, command, "insteon")
			
			self._callBack (AFTER, [cmd])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	# X10 command sent from device (Indigo)
	def X10CommandReceived (self, cmd):
		try:
			command = "on" # placeholder
			self.logger.threaddebug ("Plugin detected X10 '{0}' action from the network".format(command))
			
			self._callBack (BEFORE, [cmd])	
			
			if "cache" in dir(self.factory):
				dev = self.factory.cache.addressToDev (cmd.address)
				if dev: self.protocolCommandReceivedFromCache (dev, command, "x10")
			
			self._callBack (AFTER, [cmd])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	# Indigo sent an X10 command (Indigo)
	def X10CommandSent (self, cmd):
		try:
			command = "on" # placeholder
			self.logger.threaddebug ("Plugin detected X10 '{0}' action sent from Indigo".format(command))
			
			self._callBack (BEFORE, [dev])	
			
			if "cache" in dir(self.factory):
				dev = self.factory.cache.addressToDev (cmd.address)
				if dev: self.protocolCommandSentFromCache (dev, command, "x10")
			
			self._callBack (AFTER, [dev])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	################################################################################
	# INDIGO VARIABLE EVENTS
	################################################################################
	
	# Variable created (Indigo)
	def variableCreated(self, var):
		try:
			self.logger.threaddebug ("Variable '{0}' created".format(var.name))
			
			self._callBack (BEFORE, [var])	
			
			self._callBack (AFTER, [var])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	# Variable updated (Indigo)
	def variableUpdated (self, origVar, newVar):
		try:
			self.logger.threaddebug ("Variable '{0}' updated".format(newVar.name))
			
			self._callBack (BEFORE, [origVar, newVar])	
			
			if "cache" in dir(self.factory):
				ret = self.factory.cache.watchedItemChanges (origVar, newVar)
				for change in ret:
					self.logger.debug ("'{0}' {1} has changed".format(newVar.name, change.type))
					self._callBack (NOTHING, [origVar, newVar, change], "onWatchedVariableChanged")
			
			self._callBack (AFTER, [origVar, newVar])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	# Variable deleted (Indigo)
	def variableDeleted(self, var):
		try:
			self.logger.threaddebug ("Variable '{0}' deleted".format(var.name))
			
			self._callBack (BEFORE, [var])	
			
			self._callBack (AFTER, [var])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	################################################################################
	# INDIGO EVENT EVENTS
	################################################################################
	
	# Event configuration closed (Indigo)
	def closedEventConfigUi(self, valuesDict, userCancelled, typeId, eventId):
		try:
			evt = indigo.events[eventId]
			
			if userCancelled:
				self.logger.threaddebug ("Event '{0}' configuration dialog cancelled".format(evt.name))
			else:
				self.logger.threaddebug ("Event '{0}' configuration dialog closed".format(evt.name))
			
			self._callBack (BEFORE, [valuesDict, userCancelled, typeId, eventId])	
			
			self._callBack (AFTER, [valuesDict, userCancelled, typeId, eventId])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	# Validate the event configuration (Indigo)
	def validateEventConfigUi(self, valuesDict, typeId, eventId):
		errorDict = indigo.Dict()
		success = True
		
		try:
			evt = indigo.events[eventId]
			self.logger.threaddebug ("Validating configuration on '{0}'".format(evt.name))
			
			retval = self._callBack (BEFORE, [valuesDict, typeId, eventId])
			if retval is not None:
				if "success" in retval: success = retval["success"]
				if "valuesDict" in retval: valuesDict = retval["valuesDict"]
				if "errorDict" in retval: errorDict = retval["errorDict"]
			
			retval = self._callBack (AFTER, [valuesDict, typeId, eventId])
			if retval is not None:
				if "success" in retval: success = retval["success"]
				if "valuesDict" in retval: valuesDict = retval["valuesDict"]
				if "errorDict" in retval: errorDict = retval["errorDict"]
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return (success, valuesDict, errorDict)
			
			
	################################################################################
	# INDIGO ACTION EVENTS
	################################################################################
	
	# Action group created (Indigo)
	def actionGroupCreated(self, actionGroup): 
		try:
			self.logger.threaddebug ("Action group '{0}' created".format(actionGroup.name))
			
			self._callBack (BEFORE, [actionGroup])	
			
			self._callBack (AFTER, [actionGroup])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	# Action group updated (Indigo)
	def actionGroupUpdated (self, origActionGroup, newActionGroup):
		try:
			self.logger.threaddebug ("Action group '{0}' updated".format(newActionGroup.name))
			
			self._callBack (BEFORE, [origActionGroup, newActionGroup])	
			
			if "cache" in dir(self.factory):
				ret = self.factory.cache.watchedItemChanges (origActionGroup, newActionGroup)
				for change in ret:
					self.logger.debug ("'{0}' {1} has changed".format(newActionGroup.name, change.type))
					self._callBack (NOTHING, [origActionGroup, newActionGroup, change], "onWatchedActionGroupChanged")
			
			self._callBack (AFTER, [origActionGroup, newActionGroup])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	# Action group deleted (Indigo)
	def actionGroupDeleted(self, actionGroup): 
		try:
			self.logger.threaddebug ("Action group '{0}' deleted".format(actionGroup.name))
			
			self._callBack (BEFORE, [actionGroup])	
			
			self._callBack (AFTER, [actionGroup])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	# Validate the action configuration (Indigo)
	def validateActionConfigUi(self, valuesDict, typeId, deviceId):
		errorDict = indigo.Dict()
		success = True
		
		try:
			# We don't get the action information here, only the device ID if a device was selected
			if deviceId != 0:
				dev = indigo.devices[deviceId]
				self.logger.threaddebug ("Validating configuration for an action group referencing '{0}'".format(dev.name))
			else:
				self.logger.threaddebug ("Validating configuration for an action group")
			
			retval = self._callBack (BEFORE, [valuesDict, typeId, deviceId])
			if retval is not None:
				if "success" in retval: success = retval["success"]
				if "valuesDict" in retval: valuesDict = retval["valuesDict"]
				if "errorDict" in retval: errorDict = retval["errorDict"]
			
			retval = self._callBack (AFTER, [valuesDict, typeId, deviceId])
			if retval is not None:
				if "success" in retval: success = retval["success"]
				if "valuesDict" in retval: valuesDict = retval["valuesDict"]
				if "errorDict" in retval: errorDict = retval["errorDict"]
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return (success, valuesDict, errorDict)
	
	# Action configuration closed (Indigo)
	def closedActionConfigUi(self, valuesDict, userCancelled, typeId, deviceId):
		try:
			# We don't get the action information here, only the device ID if a device was selected
			if deviceId != 0:
				dev = indigo.devices[deviceId]
				
				if userCancelled:
					self.logger.threaddebug ("Action group referencing '{0}' dialog cancelled".format(dev.name))
				else:
					self.logger.threaddebug ("Action group referencing '{0}' dialog closed".format(dev.name))
				
			else:			
				if userCancelled:
					self.logger.threaddebug ("Action group configuration dialog cancelled")
				else:
					self.logger.threaddebug ("Action group configuration dialog closed")
			
			self._callBack (BEFORE, [valuesDict, userCancelled, typeId, deviceId])	
			
			# Make sure we've flushed the cache for this device
			self.factory.ui.flushCache (deviceId)
			if ext.valueValid (valuesDict, "uniqueIdentifier", True): self.factory.ui.flushCache (int(valuesDict["uniqueIdentifier"]))
			
			self._callBack (AFTER, [valuesDict, userCancelled, typeId, deviceId])
		
		except Exception as e:
			self.logger.error (ext.getException(e))		

	################################################################################
	# INDIGO TRIGGER EVENTS
	################################################################################

	# Start watching for events to fire trigger (Indigo)
	def triggerStartProcessing(self, trigger):
		try:
			self.logger.threaddebug ("Trigger '{0}' has started processing".format(trigger.name))
			
			self._callBack (BEFORE, [trigger])	
			
			self._callBack (AFTER, [trigger])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	# Trigger was disabled or removed (Indigo)
	def triggerStopProcessing(self, trigger):
		try:
			self.logger.threaddebug ("Trigger '{0}' has been removed or disabled".format(trigger.name))
			
			self._callBack (BEFORE, [trigger])	
			
			self._callBack (AFTER, [trigger])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
		
	# Trigger property changed (Indigo)
	def didTriggerProcessingPropertyChange(self, origTrigger, newTrigger):
		try:
			self.logger.threaddebug ("Trigger '{0}' has changed".format(newTrigger.name))
			
			self._callBack (BEFORE, [origTrigger, newTrigger])	
			
			self._callBack (AFTER, [origTrigger, newTrigger])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	# New trigger created (Indigo)
	def triggerCreated(self, trigger):
		try:
			self.logger.threaddebug ("Trigger '{0}' was crated".format(trigger.name))
			
			self._callBack (BEFORE, [trigger])	
			
			self._callBack (AFTER, [trigger])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	# Trigger has changed (Indigo)
	def triggerUpdated(self, origTrigger, newTrigger):
		try:
			self.logger.threaddebug ("Trigger '{0}' has been updated".format(newTrigger.name))
			
			self._callBack (BEFORE, [origTrigger, newTrigger])	
			
			self._callBack (AFTER, [origTrigger, newTrigger])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	# Trigger deleted (Indigo)
	def triggerDeleted(self, trigger):
		try:
			self.logger.threaddebug ("Trigger '{0}' was deleted".format(trigger.name))
			
			self._callBack (BEFORE, [trigger])	
			
			self._callBack (AFTER, [trigger])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	################################################################################
	# EPS HANDLERS
	################################################################################
	
	# Stock menu handlers
	
	# Show debug information
	def pluginMenuSupportData (self):
		try:
			self._callBack (BEFORE, [])	
			
			#indigo.server.log(unicode(self.factory.cache.items))
			self.factory.support.dumpPlugin ()
			
			self._callBack (AFTER, [])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	# Show debug information (comprehensive
	def pluginMenuSupportDataEx (self):
		try:
			self._callBack (BEFORE, [])	
			
			#indigo.server.log(unicode(self.factory.cache.items))
			self.factory.support.dumpAll ()
			
			self._callBack (AFTER, [])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	# Show basic version information
	def pluginMenuSupportInfo (self):
		try:
			self._callBack (BEFORE, [])	
			
			self.factory.support.pluginMenuSupportInfo ()
			
			self._callBack (AFTER, [])
		
		except Exception as e:
			self.logger.error (ext.getException(e))
			
				
	# Check for updates
	def pluginMenuCheckUpdates (self):
		try:
			self.factory.update.check (True)			
		
		except Exception as e:
			self.logger.error (ext.getException(e))
	
	# UI calls
	def formFieldChanged (self, valuesDict, typeId, devId):
		try:
			if devId != 0:
				self.logger.debug ("Plugin device '{0}' configuration field changed".format(indigo.devices[devId].name))
			else:
				self.logger.debug ("Configuration field changed")
				
			retval = self._callBack (BEFORE, [valuesDict, typeId, devId])
			if retval is not None: valuesDict = retval
			
			# If we are using a "uniqueIdentifier" field then generate it if needed so we can reference it in
			# other libs that might look for it
			if ext.valueValid (valuesDict, "uniqueIdentifier"):
				if valuesDict["uniqueIdentifier"] == "" or valuesDict["uniqueIdentifier"] == "0":
					uId = int(random.random() * 100000000)
					valuesDict["uniqueIdentifier"] = str(uId)
					self.logger.threaddebug ("Assigned unique identifier of {0}".format(str(uId)))
			
			# See if we cached a list that we can use for default values
			if devId > 0:
				for field, value in valuesDict.iteritems():
					if type(valuesDict[field]) is indigo.List: 
						# We cannot default lists because they are multiple choice, skip them
						pass
					else:
						valuesDict[field] = self.factory.ui.getDefaultListItem (devId, field, value)
					
			else:
				# See if we have a unique ID we can use instead
				if ext.valueValid (valuesDict, "uniqueIdentifier"):
					if valuesDict["uniqueIdentifier"] != "" or valuesDict["uniqueIdentifier"] != "0":	
						targetId = int(valuesDict["uniqueIdentifier"])
						for field, value in valuesDict.iteritems():
							valuesDict[field] = self.factory.ui.getDefaultListItem (targetId, field, value)	
					
			
			if "cond" in dir(self.factory): valuesDict = self.factory.cond.setUIDefaults (valuesDict)
			if "act" in dir(self.factory): valuesDict = self.factory.act.setUIDefaults (valuesDict)
			
			retval = self._callBack (AFTER, [valuesDict, typeId, devId])
			if retval is not None: valuesDict = retval
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
		
		return valuesDict
		
		
	################################################################################
	# EPS ACTION HANDLERS
	################################################################################	
	
	# An action that ran returned a value
	def actionReturnedValue (self, action, id, args, value):
		try:
			self._callBack (BEFORE, [])	
			
			self._callBack (AFTER, [])
			
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
	# An action that ran got an exception
	def actionGotException (self, action, id, props, e):
		try:
			self._callBack (BEFORE, [])	
			
			self.logger.error ("Running an action resulted in an exception.  While this may appear to come from {0} it is actually coming from the action belonging to the plugin being called!".format(self.factory.plugin.pluginDisplayName) )
			
			self._callBack (AFTER, [])
			
		except Exception as e:
			self.logger.error (ext.getException(e))		

	################################################################################
	# EPS CONDITION HANDLERS
	################################################################################
	
	# Check if conditions pass (the caller can either use the T/F returned here or ignore it and implement the raised events, either is fine
	def checkConditions (self, propsDict, obj, supressLogging = False):
		objName = "Non Indigo Device Object"
		
		try:
			if obj is not None: objName = obj.name
			
			self.logger.debug ("Checking conditions on '{0}'".format(objName))
			
			if "cond" in dir(self.factory):
				ret = self.factory.cond.conditionsPass (propsDict)
					
				if ret:
					if supressLogging:
						self.logger.debug ("Conditions passed on '{0}'".format(objName))
					else:
						self.logger.info ("Conditions passed on '{0}'".format(objName))
						
					self._callBack (NOTHING, [obj], "onConditionsCheckPass")
					
					return True
					
				else:
					if supressLogging:
						self.logger.debug ("Conditions did not pass on '{0}'".format(objName))
					else:
						self.logger.info ("Conditions did not pass on '{0}'".format(objName))
						
					self._callBack (NOTHING, [obj], "onConditionsCheckFail")
					
					return False
				
			else:
				self.logger.warning ("Trying to check conditions but they are not enabled for this plugin")
				return False
		
		except Exception as e:
			self.logger.error ("Conditions exception on '{0}', defaulting to a PASSED state".format(obj.name))
			self.logger.error (ext.getException(e))	
			self._callBack (NOTHING, [obj], "onConditionsCheckPass")
			return True
	
























