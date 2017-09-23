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
from lib import iutil

# Plugin libraries
from os.path import expanduser
import subprocess
import string
import re
import datetime
from datetime import date, timedelta
from bin.pexpect import pxssh # remote connection
import socket # health checking
import urllib2 # for sending forced updates to HB-Indigo (GET)
import json # for sending forced updates to HB-Indigo (POST JSON)
import requests # for sending forced updates to HB-Indigo (POST JSON)
import shutil # shell level utilities for dealing with our local HB server, mostly removing non empty folders

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
	TVERSION	= "3.2.1"
	PLUGIN_LIBS = ["cache", "plugcache", "actions", "devices"] #["conditions", "cache", "actions"] #["cache"]
	UPDATE_URL 	= ""
	
	# Plugin specific globals
	hbNames = ["CC:22:3D:E3:CE:30", "CC:22:3D:E3:CE:32", "CC:22:3D:E3:CE:E0", "CC:22:3D:E3:CE:E2", "CC:22:3D:E3:CE:EA", "CC:22:3D:E3:CE:EB", "CC:22:3D:E3:CE:EC", "CC:22:3D:E3:CE:EE", "CC:22:3D:E3:CE:F0", "CC:22:3D:E3:CE:F2"]
	hbPorts = ["51826", "51827", "51828", "51829", "51830", "51831", "51832", "51833", "51834", "51835"]
	plugindir = os.getcwd()
	
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
	
	################################################################################	
	# PLUGIN
	################################################################################	
	
	#
	# Plugin upgrade and checks
	#
	def pluginUpgrade (self):
		try:
			# ONLY DURING THE BETA PROCESS, AFTER THIS IT'S PART OF THE RELEASED PLUGIN
			if ext.valueValid (self.pluginPrefs, "restartServerChange", True) == False: self.pluginPrefs["restartServerChange"] = True
			if ext.valueValid (self.pluginPrefs, "restartNewDevice", True) == False: self.pluginPrefs["restartNewDevice"] = True
			if ext.valueValid (self.pluginPrefs, "restartDeviceType", True) == False: self.pluginPrefs["restartDeviceType"] = True
			if ext.valueValid (self.pluginPrefs, "restartNameChanges", True) == False: self.pluginPrefs["restartNameChanges"] = True
			if ext.valueValid (self.pluginPrefs, "restartDeleteDevice", True) == False: self.pluginPrefs["restartDeleteDevice"] = True
		
			# BETA 8 ADDED SERVER NAME GENERATION, MAKE SURE THE EXISTING SERVER GETS SET SO IT DOESN'T GET REGENERATED
			for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Server"):
				if ext.valueValid (dev.pluginProps, "auto_hbuser", True) == False:
					self.logger.info ("Adding property to '{0}' configuration for Beta 8".format(dev.name))
					props = dev.pluginProps
					props["auto_hbuser"] = False
					dev.replacePluginPropsOnServer (props)
			
			# RC6 new fields		
			for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Server"):
				if ext.valueValid (dev.pluginProps, "hbport", True) == False:
					self.logger.info ("Adding property to '{0}' configuration for RC6".format(dev.name))
					props = dev.pluginProps
					props["hbport"] = self.hbPorts[0]
					dev.replacePluginPropsOnServer (props)
					
			for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Server"):
				if ext.valueValid (dev.pluginProps, "autoStartStop", True) == False:
					self.logger.info ("Adding property to '{0}' configuration for RC6".format(dev.name))
					props = dev.pluginProps
					props["autoStartStop"] = True
					dev.replacePluginPropsOnServer (props)
					
			for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Custom"):
				if ext.valueValid (dev.pluginProps, "autoStartStop", True) == False:
					self.logger.info ("Adding property to '{0}' configuration for RC6".format(dev.name))
					props = dev.pluginProps
					props["autoStartStop"] = True
					dev.replacePluginPropsOnServer (props)					
					
			for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Alias"):
				if ext.valueValid (dev.pluginProps, "invertonoff", True) == False:
					self.logger.info ("Adding property to '{0}' configuration for RC6".format(dev.name))
					props = dev.pluginProps
					props["invertonoff"] = False
					dev.replacePluginPropsOnServer (props)
					
			for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Alias"):
				if ext.valueValid (dev.pluginProps, "ignore", True) == False:
					self.logger.info ("Adding property to '{0}' configuration for RC6".format(dev.name))
					props = dev.pluginProps
					props["ignore"] = False
					dev.replacePluginPropsOnServer (props)				
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	#
	# Startup
	#
	def onBefore_startup (self):
		try:
			self.migrateV4()
			
			# If they have non-local server devices and a loopback IP address then warn them about it
			msg = ""
			
			if self.pluginPrefs["host"] == "":
				msg = "\n"
				msg += eps.ui.debugHeaderEx ()
				msg += eps.ui.debugLine ("Indigo server address is empty, Homebridge will not work!")
				msg += eps.ui.debugLine (" ")
				msg += eps.ui.debugLine ("Set the proper host in the plugin configuration.")
				msg += eps.ui.debugHeaderEx ()
				
			elif self.pluginPrefs["host"] == "localhost" or self.pluginPrefs["host"] == "127.0.0.1":
				for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Server"):
					if dev.pluginProps["indigoServer"] == False:
						msg = "\n"
						msg += eps.ui.debugHeaderEx ()
						msg += eps.ui.debugLine ("Indigo server address is a loopback, Homebridge will not work!")
						msg += eps.ui.debugLine (" ")
						msg += eps.ui.debugLine ("Set the actual Indigo IP address in the plugin configuration.")
						msg += eps.ui.debugHeaderEx ()
						break
						
			self.homebridgeDiscovery()
						
			if msg != "":
				self.logger.error (msg)
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	#
	# Concurrent thread
	#
	def onAfter_runConcurrentThread (self):
		try:
			for devId in self.SERVERS:
				try:
					self.homebridgeIsRunning (indigo.devices[devId])
				except:
					continue # The device isn't in the database, failsafe to prevent race errors
				
				if indigo.devices[devId].states["restartPending"] and indigo.devices[devId].states["onOffState"]:
					d = dtutil.dateDiff ("seconds", datetime.datetime.strptime (indigo.devices[devId].states["restartTime"], "%Y-%m-%d %H:%M:%S"), indigo.server.getTime())
					if d <= 0: self.homebridgeRestart (indigo.devices[devId])
					
			#indigo.server.log(unicode(self.SPRINKLERS))
			#for devId in self.SPRINKLERS:
			#	self.setIrrigationBrightness (devId)
			
		except Exception as e:
			self.logger.error (ext.getException(e))
	
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
			
			self.SERVERS = []
			self.SPRINKLERS = []
			
			self.MANUALZONE = False # If a zone is turned on instead of a controller, this prevents auto-scheduling from being saved
			
		except Exception as e:
			self.logger.error (ext.getException(e))		
		
	
	################################################################################	
	# DEVICE
	################################################################################	
	
	#
	# Device deleted
	#
	def onAfter_deviceDeleted (self, dev):
		try:
			restartNeeded = False
			server = False			
			
			if (dev.deviceTypeId == "Homebridge-Wrapper" or dev.deviceTypeId == "Homebridge-Alias") and ext.valueValid (dev.pluginProps, "serverDevice", True):
				restartNeeded = True
				server = indigo.devices[int(dev.pluginProps["serverDevice"])]
				
			elif dev.deviceTypeId == "Homebridge-Server":
				# See if this is the last server so we can re-home Wrappers if needed
				showWarning = False
			
				for servers in indigo.devices.iter(self.pluginId + ".Homebridge-Server"):
					if servers.id != dev.id: server = servers
				
				# Now re-home any devices and notify the user
				msg = "\n" + eps.ui.debugHeaderEx()
			
				if server:
					msg += eps.ui.debugLine ("The following devices have been modified to point to a")
					msg += eps.ui.debugLine ("new server since '{0}' has been deleted:".format(dev.name))
							
				else:
					msg += eps.ui.debugLine ("The following Wrapper are no longer pointing to a server")
					msg += eps.ui.debugLine ("because '{0}' has been deleted:".format(dev.name))
				
				msg += eps.ui.debugLine (" ")
				
				for wrapper in indigo.devices.iter(self.pluginId + ".Homebridge-Wrapper"):
					if wrapper.pluginProps["serverDevice"] == str(dev.id):
						showWarning = True
						msg += eps.ui.debugLine (wrapper.name)
						props = wrapper.pluginProps
						props["serverDevice"] = str(server.id)
						wrapper.replacePluginPropsOnServer (props)
						
				for wrapper in indigo.devices.iter(self.pluginId + ".Homebridge-Alias"):
					if wrapper.pluginProps["serverDevice"] == str(dev.id):
						showWarning = True
						msg += eps.ui.debugLine (wrapper.name)
						props = wrapper.pluginProps
						props["serverDevice"] = str(server.id)
						wrapper.replacePluginPropsOnServer (props)		
					
				if showWarning: 
					if server:
						msg += eps.ui.debugLine (" ")
						msg += eps.ui.debugLine ("These devices now connect to '{0}'.".format(server.name))
			
					msg += eps.ui.debugHeaderEx()
					self.logger.warn (msg)
					
				if dev.id in self.SERVERS: 
					# Rebuild servers
					self.SERVERS = []
					for servers in indigo.devices.iter(self.pluginId + ".Homebridge-Server"):
						if servers.id != dev.id: self.SERVERS.append (server.id)
						
				home = expanduser("~") + "/.hbb/"
						
				if os.path.exists(home + str(dev.id)):
					self.logger.debug ("Removing the local server folder")
					shutil.rmtree (home + str(dev.id))
				
				return # We don't need to do the restart again, the server change will do that for us
				
			else:
				# See any server is either referencing this device specifically or all Indigo devices in general
				for serv in indigo.devices.iter(self.pluginId + ".Homebridge-Server"):
					for devId in serv.pluginProps["devinclude"]:
						if devId == str(dev.id) or devId == "-all-":
							restartNeeded = True
							server = serv
				
			if restartNeeded and server:
				self.homebridgeSaveConfig (server, self.buildServerConfig (server))
				if self.pluginPrefs["restartDeleteDevice"]: self.setServerRestart (server, dev, "Device '{0}' being monitored by '{1}' was deleted from Indigo".format(dev.name, server.name))
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	#
	# Device start comm before
	#
	def onBefore_deviceStartComm (self, dev):
		try:
			if dev.deviceTypeId == "Homebridge-Server" or dev.deviceTypeId == "Homebridge-Guest": 
				# See if we have a folder for it
				#if os.path.exists(self.plugindir + "/bin/hb/homebridge/" + str(dev.id)) == False:
				#	self.logger.debug ("Unable to find a local configuration for this Homebridge server")
				#	
				#	if self.homebridgeCreateFolder (dev, self.plugindir) == False:
				#		return
				
				home = expanduser("~") + "/.hbb/"
				if os.path.exists(home + str(dev.id)) == False:
					self.logger.debug ("Unable to find a local configuration for this Homebridge server")
					
					if self.homebridgeCreateFolder (dev, self.plugindir) == False:
						return
				
						
				# If we get to here then we should have a valid folder, now make sure our config is there or build it if not
				#if os.path.isfile(self.plugindir + "/bin/hb/homebridge/" + str(dev.id) + "/config.json"):
				if os.path.isfile(home + str(dev.id) + "/config.json"):
					self.homebridgeAutoStart (dev)
					pass					
				else:
					self.homebridgeSaveConfig (dev, self.buildServerConfig (dev))
					self.homebridgeAutoStart (dev)
					pass
								
		except Exception as e:
			self.logger.error (ext.getException(e))	

	#
	# Device start comm
	#
	def onAfter_deviceStartComm (self, dev):
		try:
			self.checkDeviceAddress (dev)
			
			if dev.deviceTypeId == "Homebridge-Server" or dev.deviceTypeId == "Homebridge-Custom" or dev.deviceTypeId == "Homebridge-Guest": 
				if dev.id in self.SERVERS:
					pass
				else:
					self.SERVERS.append(dev.id)
					
				self.homebridgeIsRunning (dev)
				
			if dev.deviceTypeId == "Homebridge-Alias": 
				self.auditSprinklerZones (dev, indigo.devices[int(dev.pluginProps["device"])])
				
			
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	#
	# Plugin device created
	#
	def onAfter_pluginDeviceCreated (self, dev):
		try:
			if dev.deviceTypeId == "Homebridge-Wrapper" or dev.deviceTypeId == "Homebridge-Alias":
				# We have to restart the server that this device is attached to so it can be recognized
				self.checkDeviceAddress (dev)
					
				if ext.valueValid (dev.pluginProps, "serverDevice", True):
					server = indigo.devices[int(dev.pluginProps["serverDevice"])]
					self.homebridgeSaveConfig (server, self.buildServerConfig (server))
					if self.pluginPrefs["restartNewDevice"]: self.setServerRestart (server, dev, "Wrapper or Alias device '{0}' was added to '{1}'".format(dev.name, server.name), 5, 120, 5)
			
			if dev.deviceTypeId == "Homebridge-Server":
				# Since we just created the device we need to create the folder and start the server
				home = expanduser("~") + "/.hbb/"
				if os.path.exists(home + str(dev.id)) == False:
					self.logger.debug ("Unable to find a local configuration for this Homebridge server")
					
					if self.homebridgeCreateFolder (dev, self.plugindir) == False:
						return
						
				# If we get to here then we should have a valid folder, now make sure our config is there or build it if not
				if os.path.isfile(home + str(dev.id) + "/config.json"):
					self.homebridgeAutoStart (dev)
					pass					
				else:
					self.homebridgeSaveConfig (dev, self.buildServerConfig (dev))
					self.homebridgeAutoStart (dev)
					pass
			
			if dev.deviceTypeId == "Homebridge-Server" or dev.deviceTypeId == "Homebridge-Custom":
				self.checkDeviceAddress (dev)
					
				if dev.id in self.SERVERS:
					pass
				else:
					self.SERVERS.append (dev.id)

				valuesDict = {}
				valuesDict["server"] = str(dev.id)
									
				ret = self.menuSave(valuesDict, dev.deviceTypeId)
				if ret[0] == False: return
			
				self.menuReload(valuesDict, dev.deviceTypeId)
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	#
	# Plugin device updated
	#			
	def onAfter_pluginDeviceUpdated (self, origDev, newDev):
		try:
			if newDev.deviceTypeId == "Homebridge-Wrapper" or newDev.deviceTypeId == "Homebridge-Alias":
				if origDev.pluginProps["treatAs"] != newDev.pluginProps["treatAs"] or newDev.address == "":
					self.checkDeviceAddress (newDev)
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	#
	# Plugin device config changed
	#
	def onAfter_pluginDevicePropChanged (self, origDev, newDev, changedProps):	
		try:
			if newDev.deviceTypeId == "Homebridge-Wrapper" or newDev.deviceTypeId == "Homebridge-Alias":
				if "treatAs" in changedProps:
					self.checkDeviceAddress (newDev)
				
					if ext.valueValid (newDev.pluginProps, "serverDevice", True):
						server = indigo.devices[int(newDev.pluginProps["serverDevice"])]
						self.homebridgeSaveConfig (server, self.buildServerConfig (server))
						if self.pluginPrefs["restartDeviceType"]: self.setServerRestart (server, origDev, "{0}'s device type changed".format(newDev.name))

				if "invertonoff" in changedProps:
					server = indigo.devices[int(newDev.pluginProps["serverDevice"])]
					self.homebridgeSaveConfig (server, self.buildServerConfig (server))
					if self.pluginPrefs["restartDeviceType"]: self.setServerRestart (server, origDev, "{0}'s device on/off inversion changed".format(newDev.name))
						
				if "serverDevice" in changedProps:
					# We need to save and reload BOTH servers (unless one of them is blank from a device delete)
					oldserver = indigo.devices[int(origDev.pluginProps["serverDevice"])]
					
					if newDev.pluginProps["serverDevice"] != "": newserver = indigo.devices[int(newDev.pluginProps["serverDevice"])]
					
					self.homebridgeSaveConfig (oldserver, self.buildServerConfig (oldserver))
					if newDev.pluginProps["serverDevice"] != "": self.homebridgeSaveConfig (newserver, self.buildServerConfig (newserver))
					
					if self.pluginPrefs["restartDeviceType"]: 
						self.setServerRestart (oldserver, newDev, "{0}'s server changed to this server".format(newDev.name))	
						if newDev.pluginProps["serverDevice"] != "": self.setServerRestart (newserver, newDev, "{0}'s server changed from this server".format(newDev.name))					
					
		
			if newDev.deviceTypeId == "Homebridge-Alias":
				if newDev.pluginProps["isSprinkler"] and newDev.pluginProps["sprinklerOptions"] == "controller" and newDev.pluginProps["manageZones"]:
					self.auditSprinklerZones (newDev, indigo.devices[int(newDev.pluginProps["device"])])	
				
			if newDev.deviceTypeId == "Homebridge-Server":
				needsRestart = False
			
				for prop in changedProps:
					if prop == "view": continue
					if prop == "itemcount": continue
					if prop == "totalcount": continue
					if prop == "wrappercount": continue
				
					needsRestart = True # If it didn't get caught yet then flag
			
				if self.pluginPrefs["restartServerChange"]:
					if needsRestart:
						self.logger.warn ("'{0}' has had a configuration change, restarting the Homebridge server now".format(newDev.name))
						self.homebridgeSaveConfig (newDev, self.buildServerConfig (newDev))
						self.homebridgeRestart (newDev)
				else:
					self.homebridgeSaveConfig (newDev, self.buildServerConfig (newDev))
					
		except Exception as e:
			self.logger.error (ext.getException(e))			


	################################################################################	
	# EXTENDED DEVICE
	################################################################################	
	
	#
	# Sprinkler is paused and the library is asking if we want to release the pause state because it's trying to start again
	#
	def onSprinklerReleasePauseState (self, devEx, change):
		try:
			parents = eps.cache.getDevicesWatchingId (devEx.dev.id)
			for devId in parents:
				if devId in indigo.devices == False: continue
				parent = indigo.devices[devId]
				
				if parent.deviceTypeId == "Homebridge-Alias" and parent.pluginProps["sprinklerOptions"] == "controller":
					# Only release the pause state for controllers, not zones
					return False # False turns off the pause state
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return True # True keeps the extended device paused
	
	#
	# Sprinkler progress changed
	#
	def onSprinklerProgressChanged (self, devEx, update):
		try:
			parents = eps.cache.getDevicesWatchingId (devEx.dev.id)
			for devId in parents:
				if devId in indigo.devices == False: continue
				parent = indigo.devices[devId]
				
				if parent.deviceTypeId == "Homebridge-Alias":
					if parent.pluginProps["isSprinkler"]:
						if parent.pluginProps["sprinklerOptions"] == "controller":
							if parent.states["brightnessLevel"] != devEx.schedulePercentRemaining: parent.updateStateOnServer ("brightnessLevel", devEx.schedulePercentRemaining)
							
						else:
							if int(parent.pluginProps["sprinklerOptions"]) == devEx.activeZone:
								if parent.states["brightnessLevel"] != devEx.zonePercentRemaining: parent.updateStateOnServer ("brightnessLevel", devEx.zonePercentRemaining)	
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	#
	# Monitored sprinkler started a schedule
	#
	def onSprinklerScheduleStarted (self, devEx, change, update):
		try:
			# Currently only handle sprinkler commands for sprinkler aliases
			parent = indigo.devices[change.parentId]
			child = indigo.devices[change.childId]
			
			if ext.valueValid (parent.pluginProps, "isSprinkler"):
				if parent.pluginProps["isSprinkler"] == True:
					if parent.pluginProps["sprinklerOptions"] == "controller":
						#indigo.server.log("SPRINKLER SCHEDULE STARTED")
						parent.updateStateOnServer ("onOffState", True)
						
						# Update auto schedules if they are enabled
						self.autoSchedule (parent, child)
						
						#indigo.server.log(unicode(devEx))
					else:
						if int(parent.pluginProps["sprinklerOptions"]) == devEx.activeZone:
							parent.updateStateOnServer ("onOffState", True)
							parent.updateStateOnServer ("brightnessLevel", devEx.zonePercentRemaining)
			
				parent.updateStateOnServer ("sprinklerPaused", False)					
				self._setDeviceIcon (parent)
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	#
	# Monitored sprinkler was stopped
	#		
	def onSprinklerScheduleStopped (self, devEx, change, update):
		try:
			# Currently only handle sprinkler commands for sprinkler aliases
			parent = indigo.devices[change.parentId]
			child = indigo.devices[change.childId]
			
			if ext.valueValid (parent.pluginProps, "isSprinkler"):
				parent.updateStateOnServer ("onOffState", False)	
				parent.updateStateOnServer ("sprinklerPaused", False)	
				self._setDeviceIcon (parent)		
				
				
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
	#
	# Monitored sprinkler was paused
	#		
	def onSprinklerSchedulePaused (self, devEx, change, update):
		try:
			# Currently only handle sprinkler commands for sprinkler aliases
			parent = indigo.devices[change.parentId]
			child = indigo.devices[change.childId]
			
			if ext.valueValid (parent.pluginProps, "isSprinkler"):
				parent.updateStateOnServer ("sprinklerPaused", True)	
				self._setDeviceIcon (parent)		
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
	#
	# Monitored sprinkler was resumed
	#		
	def onSprinklerScheduleResumed (self, devEx, change, update):
		try:
			# Currently only handle sprinkler commands for sprinkler aliases
			parent = indigo.devices[change.parentId]
			child = indigo.devices[change.childId]
			
			if ext.valueValid (parent.pluginProps, "isSprinkler"):
				parent.updateStateOnServer ("sprinklerPaused", False)	
				self._setDeviceIcon (parent)		
		
		except Exception as e:
			self.logger.error (ext.getException(e))							

	################################################################################	
	# DEVICE UI
	################################################################################	
	
	#
	# Alias device form field changed
	#
	def onAfter_formFieldChanged_Alias (self, valuesDict, typeId, devId):
		try:
			if ext.valueValid (valuesDict, "device", True):
				child = indigo.devices[int(valuesDict["device"])]
				
				valuesDict["lock_treatAs"] = True # Assume we know the device until we don't
				valuesDict["isSprinkler"] = False
				
				if type(child) is indigo.DimmerDevice:
					valuesDict["treatAs"] = "dimmer"
					
				elif type(child) is indigo.SensorDevice:
					valuesDict["treatAs"] = "sensor"
					valuesDict["lock_treatAs"] = False # Let them change it to be a switch if they want
					
				elif type(child) is indigo.SprinklerDevice:
					valuesDict["treatAs"] = "dimmer"		
					valuesDict["isSprinkler"] = True
					
					if valuesDict["manageZones"]:
						valuesDict["sprinklerOptions"] = "controller"	
					
				elif type(child) is indigo.MultiIODevice:
					valuesDict["treatAs"] = "garage"
					valuesDict["lock_treatAs"] = False		
					
				else:
					valuesDict["treatAs"] = "switch"
					valuesDict["lock_treatAs"] = False	

			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return valuesDict
			
	#
	# Server device form field changed
	#
	def onAfter_formFieldChanged_Server (self, valuesDict, typeId, devId):
		try:
			# Make sure our lists line up properly
			if "-all-" in valuesDict["devinclude"]:	
				pass
			else:
				valuesDict["devexclude"] = ["-none-"]
				
			if "-all-" in valuesDict["actinclude"]:	
				pass
			else:
				valuesDict["actexclude"] = ["-none-"]
				
			if valuesDict["auto_hbuser"]:
				unique = self.homebridgeUniqueServerCheck (devId, valuesDict)
				
				if unique["unique"] == False:
					if unique["user"] != "": valuesDict["hbuser"] = unique["user"]
					if unique["port"] != "": valuesDict["hbport"] = unique["port"]
					valuesDict["auto_hbuser"] = False
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return valuesDict
		
	#
	# Guest server device form field changed
	#
	def onAfter_formFieldChanged_Guest (self, valuesDict, typeId, devId):
		try:
			# Make sure our lists line up properly
			if valuesDict["auto_hbuser"]:
				unique = self.homebridgeUniqueServerCheck (devId, valuesDict)
				
				if unique["unique"] == False:
					if unique["user"] != "": valuesDict["hbuser"] = unique["user"]
					if unique["port"] != "": valuesDict["hbport"] = unique["port"]
					valuesDict["auto_hbuser"] = False
				
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return valuesDict	
		
	#
	# Custom server device form field changed
	#
	def onAfter_formFieldChanged_CustomServer (self, valuesDict, typeId, devId):
		try:
			# Make sure that our port and user are unique
			if valuesDict["auto_hbuser"] or valuesDict["auto_hbport"]:
				newvalues = self.incrementHomebridge (devId)
				
				valuesDict["hbuser"] = newvalues[0]
				valuesDict["hbport"] = newvalues[1]
				valuesDict["auto_hbuser"] = False
				valuesDict["auto_hbport"] = False
				
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return valuesDict	
		
	#
	# Camera device form field changed
	#
	def onAfter_formFieldChanged_Camera (self, valuesDict, typeId, devId):	
		try:
			pass
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return valuesDict
		
	#
	# A form field changed, update defaults
	#
	def onAfter_formFieldChanged (self, valuesDict, typeId, devId):
		try:
			if typeId == "Homebridge-Server": 
				return self.onAfter_formFieldChanged_Server (valuesDict, typeId, devId)
				
			if typeId == "Homebridge-Custom": 
				return self.onAfter_formFieldChanged_CustomServer (valuesDict, typeId, devId)	
				
			if typeId == "Homebridge-Guest": 
				return self.onAfter_formFieldChanged_Guest (valuesDict, typeId, devId)		
				
			if typeId == "Homebridge-Alias": 
				return self.onAfter_formFieldChanged_Alias (valuesDict, typeId, devId)	
				
			if typeId == "Homebridge-Camera": 
				return self.onAfter_formFieldChanged_Camera (valuesDict, typeId, devId)			
		
			if valuesDict["settingSelect"] == "": valuesDict["settingSelect"] = "On" # new device default
				
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
							valuesDict["deviceState" + m] = "onOffState"
							d = indigo.devices[int(valuesDict["deviceOn"])]
							if "brightnessLevel" in d.states and m == "Dim" + str(x):
								valuesDict["deviceState" + m] = "brightnessLevel"
							elif m == "Dim" + str(x):
								valuesDict["deviceState" + m] = "onOffState"
							
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
				
			# We can't get here unless a server was selected, if its not yet been toggled then toggle and return so
			# we don't change isNewDevice
			if ext.valueValid (valuesDict, "isServerSelected", True):
				if valuesDict["isServerSelected"]:
					valuesDict["isServerSelected"] = False
					return valuesDict	
												
			# LAST order of business, if we get here then we're no longer a new device	
			valuesDict["isNewDevice"] = False	
				
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
		return valuesDict
					
	#
	# Validate the wrapper config
	#
	def onAfter_validateDeviceConfigUi(self, valuesDict, typeId, devId):
		errorDict = indigo.Dict()
		success = True
		
		try:
			if typeId == "Homebridge-Wrapper":
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
				if valuesDict["settingSelect"] != "On": 
					valuesDict["settingSelect"] = "On"
			
					# Just to be completely safe, run the form value changes
					valuesDict = self.onAfter_formFieldChanged (valuesDict, typeId, devId)
					
			if typeId == "Homebridge-Server":
				unique = self.homebridgeUniqueServerCheck (devId, valuesDict)
				
				if unique["unique"] == False:
					if unique["user"] != "": valuesDict["hbuser"] = unique["user"]
					if unique["port"] != "": valuesDict["hbport"] = unique["port"]
					valuesDict["auto_hbuser"] = False		
					
			if typeId == "Homebridge-Server":
				if valuesDict["view"] != "server": 
					valuesDict["view"] = "server"
					
				if valuesDict["password"] != valuesDict["password2"]:
					errorDict["password2"] = "Password does not match"
					errorDict["showAlertText"] = "Your passwords do not match, re-type them."
					return (False, valuesDict, errorDict)
					
				# Verify that they can log in to the server
				if valuesDict["indigoServer"] == False:
					s = pxssh.pxssh()
					isOk = True
					
					try:
						if not s.login (valuesDict["computerip"], valuesDict["username"], valuesDict["password"]):
							isOk = False
						else:
							s.logout()
					except:
						isOk = False
		
					if isOk == False:
						errorDict["computerip"] = "Unable to log in"
						errorDict["username"] = "Unable to log in"
						errorDict["password"] = "Unable to log in"
						errorDict["password2"] = "Unable to log in"
						
						errorDict["showAlertText"] = "Unable to connect to the remote computer, check the IP, username and password.  You can test manually by opening terminal and trying to log into that computer by typing 'ssh {0}@{1}', if that doesn't work then neither will this.".format(valuesDict["username"], valuesDict["computerip"])
						return (False, valuesDict, errorDict)
					
				# Make sure they aren't trying to create a duplicate server
				if typeId == "Homebridge-Custom":
					for servers in indigo.devices.iter(self.pluginId + ".Homebridge-Custom"):
						if servers.id != devId:
							isOk = True
						
							if servers.pluginProps["indigoServer"] == valuesDict["indigoServer"]:
								errorDict["indigoServer"] = "Duplicate Homebridge server device for the Indigo server"
								isOk = False
							
							elif servers.pluginProps["computerip"] == valuesDict["computerip"]:
								errorDict["computerip"] = "Duplicate Homebridge server device on {0}".format(valuesDict["computerip"])
								isOk = False
							
							if isOk == False:
								errorDict["showAlertText"] = "You are attempting to create a server device for a Homebridge server that already has an Indigo device."
								return (False, valuesDict, errorDict)
							
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return (success, valuesDict, errorDict)			
			
	################################################################################	
	# WATCHERS
	################################################################################	
	
	#
	# A watched action group has changed
	#
	def onWatchedActionGroupChanged (self, origActionGroup, newActionGroup, changeInfo):
		try:
			self.checkForNameChange (origActionGroup, newActionGroup, changeInfo)
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
	
	#
	# A watched attribute changed
	#
	def onWatchedAttributeChanged (self, origDev, newDev, changeInfo):
		try:
			parent = indigo.devices[changeInfo.parentId]
			child = indigo.devices[changeInfo.childId]
			
			self.checkForNameChange (origDev, newDev, changeInfo)	
			
			if parent.deviceTypeId == "Homebridge-Wrapper":
				self.changeParentFromChild (parent, child, changeInfo, "attribute")				
		
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
						if state[0:5] == "attr_": continue
						
						if devId in ret:
							ret[devId].append (state)
						else:
							ret[devId] = [state]
							
			if dev.deviceTypeId == "Homebridge-Alias":			
				states = []
					
				if ext.valueValid (dev.pluginProps, "device", True):
					child = indigo.devices[int(dev.pluginProps["device"])]
					
					if dev.pluginProps["treatAs"] == "dimmer":
						if "onOffState" in child.states: states.append("onOffState")
						if "brightnessLevel" in child.states: states.append("brightnessLevel")	
						if "activeZone" in child.states: states.append("activeZone")	
						
					elif dev.pluginProps["treatAs"] == "switch" or dev.pluginProps["treatAs"] == "sensor":
						if "onOffState" in child.states: states.append("onOffState")
					
					ret[child.id] = states
								
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
			if dev.deviceTypeId == "Homebridge-Server":
				# Find all devices that this server is including and watch them for name changes
				config = self.buildConfigDict (dev.pluginProps, dev.id)
				
				if "-any-" in dev.pluginProps["devinclude"]:
					indigo.server.log("Passing")
					pass
				else:
					for childId in config["includeDev"]:
						ret[childId] = ["name"]
						
			if dev.deviceTypeId == "Homebridge-Wrapper":
				for i in range (1, self.TOTALDIMMING + 2 + 1): # Dimmers + On + Off + 1 (since we aren't starting at 0)
					method = "Dim" + str(i)
					if i == self.TOTALDIMMING + 1: method = "On"
					if i == self.TOTALDIMMING + 2: method = "Off"

					# We never really use the device, but the device defined for the state to watch
					if dev.pluginProps["getStatusFrom" + method] == "state" and ext.valueValid (dev.pluginProps, "stateFromDevice" + method, True):	
						devId = int(dev.pluginProps["stateFromDevice" + method])
						state = dev.pluginProps["deviceState" + method]
						if state[0:5] != "attr_": continue
						
						state = state.replace ("attr_", "")
						
						if devId in ret:
							ret[devId].append (state)
						else:
							ret[devId] = [state]			
						
				
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
	def onWatchedActionGroupRequest (self, dev):
		self.logger.threaddebug ("Returning watched action groups for {0}".format(dev.deviceTypeId))
		ret = {}
		
		try:
			if dev.deviceTypeId == "Homebridge-Server":
				# Find all devices that this server is including and watch them for name changes
				config = self.buildConfigDict (dev.pluginProps, dev.id)
				
				if "-any-" in dev.pluginProps["actinclude"]:
					indigo.server.log("Passing")
					pass
				else:
					for childId in config["includeAct"]:
						ret[childId] = ["name"]
			
			#if dev.pluginProps["methodOn"] == "action" and ext.valueValid (dev.pluginProps, "actionOn", True):
			#	ret[int(dev.pluginProps["actionOn"])] = True # Action groups don't have extra info, really we are just watching for if it got ran elsewhere
			
			#if dev.pluginProps["methodOff"] == "action" and ext.valueValid (dev.pluginProps, "actionOff", True):
			#	ret[int(dev.pluginProps["actionOff"])] = True
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return ret
		
	################################################################################	
	# RAISED EVENTS
	################################################################################		
	
	#
	# Our device was turned on
	#
	def onDeviceCommandTurnOn (self, dev):	
		try:
			if dev.deviceTypeId == "Homebridge-Wrapper":
				# If it's already on then only let them turn it on again if the On method cannot determine on/off states
				if dev.pluginProps["getStatusFromOn"] != "none":
					# We have a means to check status and have already in other raised events, this is redundant
					if dev.states["onOffState"]: return True 
			
				if dev.pluginProps["methodOn"] == "device" and ext.valueValid (dev.pluginProps, "deviceOn", True):
					return eps.act.runAction (dev.pluginProps, "On")
									
				if dev.pluginProps["methodOn"] == "action" and ext.valueValid (dev.pluginProps, "actionOn", True):
					indigo.actionGroup.execute(int(dev.pluginProps["actionOn"]))
					return True
					
				if dev.pluginProps["methodOn"] == "none":
					return True
					
			elif dev.deviceTypeId == "Homebridge-Server" or dev.deviceTypeId == "Homebridge-Custom":
				self.homebridgeStart (dev)
				return True
				
			elif dev.deviceTypeId == "Homebridge-Alias":
				#if dev.states["onOffState"]: return True # It's already on
				return self.aliasTurnOn (dev)
				
				
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
		return False
		
	#
	# Our device was turned off
	#
	def onDeviceCommandTurnOff (self, dev):	
		try:
			if dev.deviceTypeId == "Homebridge-Wrapper":
				# If it's already on then only let them turn it off again if the Off method cannot determine on/off states
				if dev.pluginProps["getStatusFromOff"] != "none":
					# We have a means to check status and have already in other raised events, this is redundant
					if dev.states["onOffState"] == False: return True
						
				if dev.pluginProps["methodOff"] == "device" and ext.valueValid (dev.pluginProps, "deviceOff", True):
					return eps.act.runAction (dev.pluginProps, "Off")
				
				if dev.pluginProps["methodOff"] == "action" and ext.valueValid (dev.pluginProps, "actionOff", True):
					indigo.actionGroup.execute(int(dev.pluginProps["actionOff"]))
					return True
					
				if dev.pluginProps["methodOff"] == "none":
					return True	
					
			elif dev.deviceTypeId == "Homebridge-Server" or dev.deviceTypeId == "Homebridge-Custom":
				self.homebridgeStop (dev)
				return True
				
			elif dev.deviceTypeId == "Homebridge-Alias":
				#if dev.states["onOffState"] == False: return True # It's already off
				return self.aliasTurnOff (dev)	
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
		return False	
		
	
		
	#
	# Our device brightness was changed
	#
	def onDeviceCommandSetBrightness (self, dev, value):	
		try:
			if dev.deviceTypeId == "Homebridge-Wrapper":
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
						
			elif dev.deviceTypeId == "Homebridge-Alias":
				return self.aliasSetBrightness (dev, value)
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
		return False	
		
	################################################################################
	# PLUGIN SPECIFIC ROUTINES
	#
	# Routines not raised by plug events that are specific to this plugin
	################################################################################	
	
	################################################################################	
	# HOMEBRIDGE
	################################################################################		
	#
	# Get unique names and ports if needed
	#
	def homebridgeUniqueServerCheck (self, devId, valuesDict):
		try:
			serverNames = []
			serverPorts = []
			ret = {}
			ret["unique"] = True
			ret["user"] = valuesDict["hbuser"]
			ret["port"] = valuesDict["hbport"]

			for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Server"):
				if dev.id != devId: 
					serverNames.append (dev.pluginProps["hbuser"])
					serverPorts.append (dev.pluginProps["hbport"])	
					
			for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Custom"):
				if dev.id != devId: 
					serverNames.append (dev.pluginProps["hbuser"])
					serverPorts.append (dev.pluginProps["hbport"])				
					
			nameUsed = False		
			for name in serverNames:
				if name == valuesDict["hbuser"]: nameUsed = True
				
			portUsed = False
			for port in serverPorts:
				if port == valuesDict["hbport"]: portUsed = True
					
			if nameUsed == False and portUsed == False: return ret
					
			for name in self.hbNames:
				if name in serverNames: continue
				ret["user"] = name
				ret["unique"] = False
				break
			
			for name in self.hbPorts:
				if name in serverPorts: continue
				ret["port"] = name
				ret["unique"] = False
				break				
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return ret
	
	#
	# Get next available user and port
	#
	def incrementHomebridge (self, devId):
		try:
			ret = []
			
			serverNames = []
			serverPorts = []
			
			for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Server"):
				if dev.id != devId: 
					serverNames.append (dev.pluginProps["hbuser"])
					serverPorts.append (dev.pluginProps["hbport"])
				
			for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Custom"):
				if dev.id != devId: 
					serverNames.append (dev.pluginProps["hbuser"])	
					serverPorts.append (dev.pluginProps["hbport"])
				
			for name in self.hbNames:
				if name in serverNames: continue
				ret.append (name)
				break
				
			for port in self.hbPorts:
				if port in serverPorts: continue
				ret.append (port)
				break	
			
		except Exception as e:
			self.logger.error (ext.getException(e))
			ret.append (self.hbUser[1])
			ret.append (self.hbPort[1])
			
		return ret
		
	#
	# Auto stop Homebridge
	#
	def homebridgeAutoStop (self, dev):
		try:
			#if self.homebridgeIsRunning (dev) == False: return # It's already stopped, don't try to stop it again	
				
			if dev.pluginProps["autoStartStop"]: self.homebridgeStop (dev)
					
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	#
	# Auto start Homebridge
	#
	def homebridgeAutoStart (self, dev):
		try:
			#if self.homebridgeIsRunning (dev): return # It's already running, don't try to start it again	
				
			if dev.pluginProps["autoStartStop"]: self.homebridgeStart (dev)
					
		except Exception as e:
			self.logger.error (ext.getException(e))			
		
	#
	# Discover a manual HB server or set up a HB-Indigo server if there is none
	#
	def homebridgeDiscovery (self):
		try:
			customserver = False
			
			home = expanduser("~") + "/.homebridge"
			if os.path.exists(home):
				if os.path.exists(home + "/migrated.hbb") == False: # We have already migrated this server			
					self.logger.info ("Custom installation of Homebridge found, adding a custom server to Indigo")
					customserver = True
			
					# There is a custom server, try to read in the settings before we create it
					if os.path.exists(home + "/config.json"):
						with open(home + "/config.json") as json_file:
							json_data = json.load(json_file)
							
						props = {}
				
						props["indigoServer"] = True
						props["auto_hbuser"] = False
						props["show_hbuser"] = True
						props["hbuser"] = unicode(json_data['bridge']['username'])
						props["hbpin"] = unicode(json_data['bridge']['pin'])
						props["hbport"] = unicode(json_data['bridge']['port'])
				
						indigo.device.create(protocol=indigo.kProtocol.Plugin,
							address='CUSTOM on Indigo Server',
							name=unicode(json_data['bridge']['name']) + " Custom Installation", 
							description='Automatically created by Homebridge Buddy because ~/.homebridge configuration was found', 
							pluginId='com.eps.indigoplugin.homebridge',
							deviceTypeId='Homebridge-Custom',
							props=props)
						
					# Now read in the old JSON file and write it back out but without any HB-Indigo configuration, that will be the role of the built in server
					hasplatform = -1
					platformloop = 0
					for platform in json_data['platforms']:
						if platform["platform"] == "Indigo": 
							hasplatform = platformloop
							
						platformloop = platformloop + 1
						
					if hasplatform != -1: del json_data['platforms'][hasplatform]
					
					#indigo.server.log(unicode(json_data))
					#indigo.server.log(unicode(json.dumps(json_data, indent=8, separators=(',',':'))))

					with open(home + "/migrated.hbb", 'w') as file_:
						file_.write("Homebridge Buddy migrated")	
					X = 1
						
			# Make sure we have a HB-Indigo server
			servers = 0
			for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Server"):
				servers = servers + 1
				
			if servers == 0:
				self.logger.info ("Automatically creating and configuring the first Homebridge server")
				
				props = {}

				if customserver == False:
					props["hbpin"] = "031-45-154"
					props["hbport"] = "51826" 
					props["hbuser"] = "DD:22:3D:E3:CE:30" # The DD ensures that no matter what this will get picked up, that name was never used before
				else:
					props["hbpin"] = "031-45-154"
					props["hbport"] = "51832"
					props["hbuser"] = "DD:22:3D:E3:CE:32"

				props["indigoServer"] = True
				props["accessory"] = ""
				props["actexclude"] = ["-none-"]
				props["actinclude"] = ["-none-"]
				props["autoStartStop"] = True
				props["auto_hbuser"] = False
				props["celsius"] = False
				props["countWrappedItems"] = True
				props["devexclude"] = ["-none-"]
				props["devinclude"] = ["-all-"]
				props["hideWrappedItems"] = True
				props["name"] = "Indigo"
				props["password"] = "password"
				props["password2"] = "password"
				props["show_hbuser"] = False
				props["treatasdoor"] = ["-none-"]
				props["treatasdrapes"] = ["-none-"]
				props["treatasgarage"] = ["-none-"]
				props["treataslock"] = ["-none-"]
				props["treatasswitch"] = ["-none-"]
				props["treataswindows"] = ["-none-"]
				props["invertonoff"] = ["-none-"]
				props["username"] = "Administrator"
				
				indigo.device.create(protocol=indigo.kProtocol.Plugin,
					address='SERVER on Indigo Server',
					name="Homebridge for Indigo", 
					description='Automatically created by Homebridge Buddy as first Homebridge server', 
					pluginId='com.eps.indigoplugin.homebridge',
					deviceTypeId='Homebridge-Server',
					props=props)
			
		except Exception as e:
			self.logger.error (ext.getException(e))
		
	#
	# Create Homebridge server folder
	#
	def homebridgeCreateFolder (self, dev, curdir):
		try:
			# RELEASE HOME FOLDER CONFIG SAVING
			if dev.pluginProps["indigoServer"]:
				# Since we are here, disable the manually installed HB if it is there
				#self.homebridgeLegacyMigration (dev)
			
				home = expanduser("~") + "/.hbb"
		
				if not os.path.exists(home):
				    os.makedirs(home)
				    
				if not os.path.exists(home):
					self.logger.error ("Unable to create Homebridge Buddy root folder " + home)
					return False
		
				os.system('"' + self.plugindir + '/bin/hb/homebridge/createdir" ' + home + '/' + str(dev.id))
				#self.logger.info ('"' + self.plugindir + '/bin/hb/homebridge/createdir" ' + home + '/' + str(dev.id))

				if os.path.exists(home + "/" + str(dev.id)):
					self.logger.debug ("Created server folder " + home + "/" + str(dev.id))
					return True
				
				else:
					self.logger.error ("Unable to create Homebridge Indigo folder " + home + "/" + str(dev.id))
					return False
					
			return
			
			# LEGACY IN-PLUGIN-FOLDER CONFIG SAVING
			if dev.pluginProps["indigoServer"]:
				# Since we are here, disable the manually installed HB if it is there
				#self.homebridgeLegacyMigration (dev)
				
				home = expanduser("~") + "/.hbb"
		
				os.system('"' + self.plugindir + '/bin/hb/homebridge/createdir" ' + home + "/" + str(dev.id))

				if os.path.exists(home + "/" + str(dev.id)):
					self.logger.debug ("Created server folder " + home + "/" + str(dev.id))
					return True
				
				else:
					self.logger.error ("Unable to create Homebridge folder " + home + "/" + str(dev.id))
					return False
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return False
			
		return True	
	
	#
	# Send request to HB-Indigo to force an update of the device (JSON POST)
	#
	def homebridgeForceUpdate (self, parent, child):
		try:
			serverIp = ""
			
			server = indigo.devices[int(parent.pluginProps["serverDevice"])]
			
			if server.pluginProps["indigoServer"]:
				serverIp = "127.0.0.1"
			else:
				serverIp = server.pluginProps["computerip"]
				
			url = "http://{0}:8445/devices/{1}".format(serverIp, str(parent.id))
			
			if self.pluginPrefs["enableStatusUpdate"] == False:
				self.logger.debug ("Experimental status update disabled in plugin configuration")
				return False
			
			data = {'temperature':'24.3'}
			data_json = json.dumps(data)
			payload = {'json_payload': data_json, 'apikey': 'YOUR_API_KEY_HERE'}
			r = requests.get('http://myserver/emoncms2/api/post', data=payload)
			
			self.logger.debug ("Homebridge update requested, querying {0}".format(url))
			
			return True		
				
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return False
	
	#
	# Send request to HB-Indigo to force an update of the device (GET)
	#
	def homebridgeForceUpdateEx (self, parent, child):
		try:
			serverIp = ""
			
			server = indigo.devices[int(parent.pluginProps["serverDevice"])]
			
			if server.pluginProps["indigoServer"]:
				serverIp = "127.0.0.1"
			else:
				serverIp = server.pluginProps["computerip"]
				
			url = "http://{0}:8445/devices/{1}".format(serverIp, str(parent.id))
			
			self.logger.debug ("Homebridge update requested, querying {0}".format(url))
			
			if self.pluginPrefs["enableStatusUpdate"] == False:
				self.logger.debug ("Experimental status update disabled in plugin configuration")
				return False
			
			ret = urllib2.urlopen(url)
			
			if int(ret.getcode()) != 200: return False
		
			return True		
				
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return False
	
	#
	# Save homebridge configuration
	#
	def homebridgeSaveConfig (self, dev, config):
		try:
			# New save routine, future use
			#data = self.buildConfigData (dev)
			#indigo.server.log(unicode(json.dumps(data, indent=8, separators=(',',':'))))
			#home = self.plugindir + "/bin/hb/homebridge/" + str(dev.id)
			#with open(home + "/config2.json", 'w') as file_:
			#	file_.write(json.dumps(data, indent=8, separators=(',',':')))
			#return
			
			# In this version the config is text, convert it as a JSON encoded string
			json_data = json.loads(config)
			
			# If this is a custom server then we save everything BUT Homebridge-Indigo
			newplatforms = []
			
			# If this is our server we save ONLY Homebridge-Indigo
			if dev.deviceTypeId == "Homebridge-Server":
				json_data["accessories"] = [] # We don't support it at the moment
				
				# Only include the plugins that we have developed for the built in homebridge
				for platform in json_data["platforms"]:
					if platform["platform"] == "Indigo": newplatforms.append (platform)
				
				json_data["platforms"] = newplatforms
				
				#home = self.plugindir + "/bin/hb/homebridge/" + str(dev.id)
				home = expanduser("~") + "/.hbb/" + str(dev.id)
				
				if os.path.exists(home):
					self.logger.debug ("Saving '{0}/config.json'".format(home))
				
					with open(home + "/config.json", 'w') as file_:
						#file_.write(config)
						file_.write (json.dumps(json_data, indent=8))
						#file_.write (json.dumps(json_data))
						
			if dev.deviceTypeId == "Homebridge-Guest":			
				json_data["accessories"] = [] # We don't support it at the moment
				
				# This was built using the parent server, change parameters as needed
				json_data["bridge"]["name"] = dev.name
				json_data["bridge"]["username"] = dev.pluginProps["hbuser"]
				json_data["bridge"]["port"] = dev.pluginProps["hbport"]
				json_data["bridge"]["pin"] = dev.pluginProps["hbpin"]
				
				# Only include the plugins that we have developed for the built in homebridge
				for platform in json_data["platforms"]:
					if platform["platform"] == "Indigo": 
						platform["name"] = dev.name # Again, this was generated from the parent server
						
						# Put in our excludes
						excludes = []
						if "excludeIds" in platform == False: excludes = platform["excludeIds"]
						
						for exId in dev.pluginProps["exclude"]:
							excludes.append (str(exId))
							
							
						platform["excludeIds"] = excludes
						newplatforms.append (platform)
				
				json_data["platforms"] = newplatforms
				
				#home = self.plugindir + "/bin/hb/homebridge/" + str(dev.id)
				home = expanduser("~") + "/.hbb/" + str(dev.id)
				
				if os.path.exists(home):
					self.logger.debug ("Saving '{0}/config.json'".format(home))
				
					with open(home + "/config.json", 'w') as file_:
						#file_.write(config)
						file_.write (json.dumps(json_data, indent=8))
						#file_.write (json.dumps(json_data))
				
			if dev.deviceTypeId == "Homebridge-Custom":
				# Read in the current config file so we can merge it
				home = expanduser("~") + "/.homebridge"
				json_current = {}
				json_current["platforms"] = []
				json_current["accessories"] = []
				
				if os.path.exists(home + "/config.json"):
					with open(home + "/config.json") as json_file:
						json_current = json.load(json_file)
						
				# Merge the platforms and accessories
				for pcurrent in json_current["platforms"]:
					if "platform" in pcurrent:
						if pcurrent["platform"] != "Indigo" and pcurrent["platform"] != "Camera-ffmpeg":
							json_data["platforms"].append (pcurrent)
							
				json_data["accessories"] = json_current["accessories"]
				
				#indigo.server.log(unicode(json_current["platforms"]))
				#indigo.server.log("=============================")
				#indigo.server.log(unicode(json_data["platforms"]))
				
				for platform in json_data["platforms"]:
					if "platform" in platform and platform["platform"] != "Indigo": newplatforms.append (platform)
									
				json_data["platforms"] = newplatforms					
				
				#indigo.server.log(unicode(json_data))	
					
				config = json.dumps(json_data, indent=8)
				
				if dev.pluginProps["indigoServer"]:
					home = expanduser("~") + "/.homebridge"
			
					if os.path.exists(home):
						if os.path.exists (home + "/config.json"):
							self.logger.debug ("Found '{0}/config.json', saving the Homebridge configuration".format(home))
					
							with open(home + "/config.json", 'w') as file_:
								file_.write(config)
						else:
							self.logger.error ("Unable to find the config.json file in '{0}', are you sure Homebridge is installed?  Unable to save configuration".format(home))
							return
					else:
						self.logger.error ("Unable to find '{0}', are you sure Homebridge is installed?  Unable to save configuration".format(home))
						return
					
				else:
					s = pxssh.pxssh()
				
					try:
						s.login (dev.pluginProps["computerip"], dev.pluginProps["username"], dev.pluginProps["password"])
					except:
						self.logger.error ("SSH session failed to login to '{0}'.  Check your IP, username and password and make sure you can SSH to that computer from the Indigo server.".format(dev.name))
						return False
				
					config = config.replace('\t', '    ')
			
					thiscfg = config.split("\n")
			
					try:
						allLines = float(len(thiscfg))
						curLine = float(2)
					
						#s.sendline ("echo '' > /Users/" + dev.pluginProps["username"] + "/.homebridge/config.json")
						#s.prompt() 
					
						for i in range (0, len(thiscfg)):
							thiscfg[i] = "echo '" + thiscfg[i] + "' >> /Users/" + dev.pluginProps["username"] + "/.homebridge/config.json"
					
						thiscfg.insert (0, "echo '' > /Users/" + dev.pluginProps["username"] + "/.homebridge/config.json")
						
						newcfg = ";".join(thiscfg)
						#indigo.server.log(unicode(newcfg))
						s.sendline (newcfg)
						s.prompt() 
						
					
			
					except Exception as e:
						self.logger.error (ext.getException(e))	
			
					s.prompt() 
					s.logout()

				self.logger.info ("Homebridge configuration for '{0}' saved".format(dev.name))
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return False
			
		return True
	
	#
	# Restart homebridge process
	#
	def homebridgeRestart (self, dev):
		try:
			if self.homebridgeIsRunning (dev):
				self.homebridgeStop (dev)
				self.sleep (3)
				
			self.homebridgeStart (dev)
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	#
	# Start homebridge process
	#
	def homebridgeStart (self, dev):
		try:
			self.logger.info ("Starting the Homebridge server '{0}', do not try to use Siri until you get a message that the server has started".format(dev.name))
			
			if dev.deviceTypeId == "Homebridge-Server" or dev.deviceTypeId == "Homebridge-Guest":
				curdir = os.getcwd()
				#os.system('"' + curdir + '/bin/hb/homebridge/load" ' + str(dev.id))
				home = expanduser("~") + "/.hbb/" + str(dev.id)
				os.system('"' + curdir + '/bin/hb/homebridge/load" ' + home)
			
			if dev.deviceTypeId == "Homebridge-Custom":
				if dev.pluginProps["indigoServer"]:
					# Python method
					os.system("launchctl load -w ~/Library/LaunchAgents/com.webdeck.homebridge.plist")

				else:
					# pxssh method
					s = pxssh.pxssh()

					try:				
						if not s.login (dev.pluginProps["computerip"], dev.pluginProps["username"], dev.pluginProps["password"]):
							self.logger.error ("SSH session failed to login to '{0}'.  Check your IP, username and password and make sure you can SSH to that computer from the Indigo server.".format(dev.name))
							return False
						else:
							self.logger.debug ("SSH session login to '{0}' successful".format(dev.name))
							s.sendline ("launchctl load -w ~/Library/LaunchAgents/com.webdeck.homebridge.plist")
							s.prompt() 
							s.logout()
					except:
						self.logger.error ("SSH session failed to login to '{0}'.  Check your IP, username and password and make sure you can SSH to that computer from the Indigo server.".format(dev.name))
						return False
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return False
			
		return True
			
	#
	# Stop homebridge process
	#
	def homebridgeStop (self, dev):
		try:
			self.logger.warn ("Stopping the Homebridge server '{0}'".format(dev.name))
			
			if dev.deviceTypeId == "Homebridge-Server" or dev.deviceTypeId == "Homebridge-Guest":
				curdir = os.getcwd()
				#os.system('"' + curdir + '/bin/hb/homebridge/unload" ' + str(dev.id))
				home = expanduser("~") + "/.hbb/" + str(dev.id)
				os.system('"' + curdir + '/bin/hb/homebridge/unload" ' + home)
			
			if dev.deviceTypeId == "Homebridge-Custom":			
				if dev.pluginProps["indigoServer"]:
					# Python method
					os.system("launchctl unload -w ~/Library/LaunchAgents/com.webdeck.homebridge.plist")
				
				else:
					# pxssh method
					s = pxssh.pxssh()

					try:				
						if not s.login (dev.pluginProps["computerip"], dev.pluginProps["username"], dev.pluginProps["password"]):
							self.logger.error ("SSH session failed to login to '{0}'.  Check your IP, username and password and make sure you can SSH to that computer from the Indigo server.".format(dev.name))
							return False
						else:
							self.logger.debug ("SSH session login to '{0}' successful".format(dev.name))
							s.sendline ("launchctl unload -w ~/Library/LaunchAgents/com.webdeck.homebridge.plist")
							s.prompt() 
							s.logout()
					except:
						self.logger.error ("SSH session failed to login to '{0}'.  Check your IP, username and password and make sure you can SSH to that computer from the Indigo server.".format(dev.name))
						return False
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			return False
			
		return True	
		
	#
	# Check homebridge running state
	#
	def homebridgeIsRunning (self, dev):
		try:
			results = []
			isRunning = False
			ipaddress = False
			
			states = iutil.updateState ("lastHealthCheck", indigo.server.getTime().strftime("%Y-%m-%d %H:%M:%S"))
			
			if dev.pluginProps["indigoServer"]: 
				ipaddress = "127.0.0.1"
			else:
				ipaddress = dev.pluginProps["computerip"]
				
			port = int(dev.pluginProps["hbport"])
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			result = sock.connect_ex((ipaddress,port))
			if result == 0:
			   isRunning = True

			if isRunning and dev.states["onOffState"] == False:
				states = iutil.updateState ("onOffState", True, states)
				states = iutil.updateState ("restartPending", False)
			
				if dev.states["onOffState"] == False: self.logger.info ("The Homebridge server '{0}' is back up".format(dev.name))
				dev.updateStatesOnServer (states)
			
			if isRunning == False and dev.states["onOffState"]:
				states = iutil.updateState ("onOffState", False, states)
				if dev.states["onOffState"]: self.logger.warn ("The Homebridge server '{0}' has stopped".format(dev.name))
				dev.updateStatesOnServer (states)
			
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			return False
			
		return True	
	
		
	################################################################################	
	# SPRINKLER METHODS
	################################################################################	
	
	#
	# Set up auto schedule for irrigation device(s)
	#
	def autoSchedule (self, parent, child):
		try:
			if parent.pluginProps["autoSchedule"] == False: return
			
			if self.MANUALZONE:
				self.logger.debug ("Auto scheduling is enabled for '{0}' but '{1}' was turned on by a single zone, '{0}' will not be updated".format(parent.name, child.name))
				self.MANUALZONE = False # Reset the flag for the next time we run
				return
			
			if len(child.zoneScheduledDurations) == 0:
				self.logger.debug ("Auto scheduling is enabled for '{0}' but '{1}' appears to be running without a schedule, '{0}' will not be updated".format(parent.name, child.name))
				return
				
			# This should only be called for the controller, since the controller is the one that gets the schedule
			schedule = ""
			for i in child.zoneScheduledDurations:
				schedule = schedule + str(i) + ", "
				
			schedule = schedule[0:len(schedule) - 2]
			
			parentProps = parent.pluginProps
			parentProps["schedule"] = schedule
			parent.replacePluginPropsOnServer(parentProps)
			
			self.logger.debug ("Auto scheduling is enabled for '{0}', setting schedule to '{1}'".format(parent.name, schedule))
			
			# Now find any attached zones that also have the option enabled
			for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Alias"):
				if dev.pluginProps["isSprinkler"]:
					if dev.pluginProps["device"] == parent.pluginProps["device"] and dev.pluginProps["sprinklerOptions"] != "controller" and dev.pluginProps["autoSchedule"]:
						duration = str(child.zoneScheduledDurations[int(dev.pluginProps["sprinklerOptions"]) - 1])
						self.logger.debug ("Auto scheduling is enabled for '{0}', setting duration to '{1}'".format(dev.name, duration))
		
						devProps = dev.pluginProps
						devProps["zoneTime"] = duration
						dev.replacePluginPropsOnServer(devProps)
		
		except Exception as e:
			self.logger.error (ext.getException(e))
			
	#
	# Audit zones for a managed controller
	#
	def auditSprinklerZones (self, parent, child):
		try:
			self.logger.threaddebug ("Checking if '{0}' is a controller and if it is managing zones".format(parent.name))
			if parent.pluginProps["isSprinkler"] and parent.pluginProps["sprinklerOptions"] == "controller" and parent.pluginProps["manageZones"]:
				# Make sure we have each zone
				zones = child.zoneEnableList
				
				for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Alias"):
					if dev.pluginProps["isSprinkler"] and dev.pluginProps["sprinklerOptions"] != "controller" and dev.pluginProps["device"] == parent.pluginProps["device"]:
						zoneIdx = int(dev.pluginProps["sprinklerOptions"]) - 1
						zones[zoneIdx] = 9
						
				self.logger.threaddebug ("Checking managed zones on plugin device '{0}' resulted in {1}".format(parent.name, unicode(zones)))
				
				zoneIdx = 0
				for z in zones:
					zoneIdx = zoneIdx + 1
					
					if z == False:
						self.logger.debug ("Not managing zone {0} on '{1}' because the zone is disabled".format(str(zoneIdx), child.name))
						continue
						
					elif z == 9:
						self.logger.debug ("Zone {0} on '{1}' is already a device in Indigo".format(str(zoneIdx), child.name))
						continue
						
					else:
						self.logger.debug ("Zone {0} on '{1}' does not have a device in Indigo, creating a new device in the same folder where '{2}' resides".format(str(zoneIdx), child.name, parent.name))
						needsReload = True
						
						try:
							props = indigo.Dict()
							props["serverDevice"] = parent.pluginProps["serverDevice"]
							props["device"] = parent.pluginProps["device"]
							props["isSprinkler"] = True
							props["manageZones"] = False
							props["sprinklerOptions"] = str(zoneIdx)
							props["autoSchedule"] = parent.pluginProps["autoSchedule"]
							props["zoneTime"] = "20"
							props["lock_treatAs"] = True
							props["treatAs"] = "dimmer"
							
							indigo.device.create(protocol=indigo.kProtocol.Plugin,
								address='',
								name='Zone ' + str(zoneIdx), 
								description='Managed sprinkler zone on ' + parent.name + ' for ' + child.name, 
								pluginId=self.pluginId,
								deviceTypeId='Homebridge-Alias',
								props=props,
								folder=parent.folderId)
							
						except Exception as e:
							self.logger.error (ext.getException(e))					
					
		except Exception as e:
			self.logger.error (ext.getException(e))
			
		#
	# Turn on an alias device
	#
	def aliasTurnOn (self, dev):
		try:
			if ext.valueValid (dev.pluginProps, "device", True) == False: return False
			if dev.pluginProps["ignore"]: return False
			
			if dev.pluginProps["treatAs"] == "switch":
				indigo.device.turnOn (int(dev.pluginProps["device"]))
				
			elif dev.pluginProps["treatAs"] == "dimmer":
				if dev.pluginProps["isSprinkler"] == False:
					indigo.device.turnOn (int(dev.pluginProps["device"]))
					
				else:
					schedule = []
					
					if dev.pluginProps["sprinklerOptions"] == "controller":
						userSchedule = dev.pluginProps["schedule"].split(",")

						if len(userSchedule) != 1:
							for zone in userSchedule:
								zone = float(zone.strip())
								schedule.append(zone)
								
						else:
							for i in range (0, 8):
								schedule.append (int(dev.pluginProps["schedule"]))		
								
					else:
						for i in range (0, 8):
							if (i + 1) != int(dev.pluginProps["sprinklerOptions"]):
								schedule.append (0.0)
							else:
								schedule.append (float(dev.pluginProps["zoneTime"]))
								
						self.MANUALZONE = True
								
					indigo.sprinkler.run (int(dev.pluginProps["device"]), schedule=schedule)
					
			self._setDeviceIcon (dev)
			return True
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
		return False
		
	#
	# Turn off an alias device
	#
	def aliasTurnOff (self, dev):
		try:
			if ext.valueValid (dev.pluginProps, "device", True) == False: return False
			if dev.pluginProps["ignore"]: return False
			
			if dev.pluginProps["treatAs"] == "switch":
				indigo.device.turnOff (int(dev.pluginProps["device"]))
				
			elif dev.pluginProps["treatAs"] == "dimmer":
				if dev.pluginProps["isSprinkler"] == False:
					indigo.device.turnOff (int(dev.pluginProps["device"]))
					
				else:
					indigo.sprinkler.stop (int(dev.pluginProps["device"]))
					
			self._setDeviceIcon (dev)
			return True
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
		return False	
		
	#
	# Set brightness of an alias device
	#
	def aliasSetBrightness (self, dev, value):
		try:
			if ext.valueValid (dev.pluginProps, "device", True) == False: return False
			if dev.pluginProps["ignore"]: return False
			
			if dev.pluginProps["treatAs"] == "dimmer":
				if dev.pluginProps["isSprinkler"] == False:
					child = indigo.devices[int(dev.pluginProps["device"])]
					if type(child) is indigo.DimmerDevice:
						indigo.dimmer.setBrightness (child.id, value=value)
					else:
						self.logger.warn ("Alias device '{0}' cannot set the brightness of '{1}' because it is not a dimmer".format(dev.name, child.name))
					
				else:
					# If a schedule is running then stop it now
					child = indigo.devices[int(dev.pluginProps["device"])]
					if child.states["activeZone"] != 0 or child.pausedScheduleZone is not None: indigo.sprinkler.stop (child.id)
						
					schedule = []
					adjusted = float(value) / 100
					
					controllerMethod = "on"
					zoneMethod = "on"
					if ext.valueValid (self.pluginPrefs, "sprinklerDim", True): controllerMethod = self.pluginPrefs["sprinklerDim"]
					if ext.valueValid (self.pluginPrefs, "zoneDim", True): zoneMethod = self.pluginPrefs["zoneDim"]
					
					if dev.pluginProps["sprinklerOptions"] == "controller":
						if controllerMethod == "on":					
							userSchedule = dev.pluginProps["schedule"].split(",")

							if len(userSchedule) != 1:
								for zone in userSchedule:
									zone = float(zone.strip())
									schedule.append(zone * adjusted)
							else:
								for i in range (0, 8):
									schedule.append (float(dev.pluginProps["schedule"]) * adjusted)		
									
						elif controllerMethod == "max":							
							for i in range (0, 8):
								if child.zoneEnableList[i] and child.zoneMaxDurations[i] > 0:
									schedule.append(child.zoneMaxDurations[i] * adjusted)
								else:
									schedule.append(0.0)
									
						elif controllerMethod == "100":
							for i in range (0, 8):
								if child.zoneEnableList[i]:
									schedule.append(value)
								else:
									schedule.append(0.0)
					
					else:
						if zoneMethod == "on":
							for i in range (0, 8):
								if (i + 1) != int(dev.pluginProps["sprinklerOptions"]):
									schedule.append (0.0)
								else:
									schedule.append (float(dev.pluginProps["zoneTime"]) * adjusted)
									
						elif zoneMethod == "max":							
							for i in range (0, 8):
								if str(i + 1) == dev.pluginProps["sprinklerOptions"] and child.zoneEnableList[i] and child.zoneMaxDurations[i] > 0:
									schedule.append(child.zoneMaxDurations[i] * adjusted)
								else:
									schedule.append(0.0)
									
						elif zoneMethod == "100":							
							for i in range (0, 8):
								if str(i + 1) == dev.pluginProps["sprinklerOptions"] and child.zoneEnableList[i]:
									schedule.append(value)
								else:
									schedule.append(0.0)			
							
					# No matter what, treat this as a manual schedule so we don't overwrite
					self.MANUALZONE = True
								
					indigo.sprinkler.run (child.id, schedule=schedule)
					
			self._setDeviceIcon (dev)
			return True
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
		return False	
		
	################################################################################	
	# GENERAL
	################################################################################	
	
	
	#
	# We got notified of an interesting change, if the parent is a server and the change is a name then restart HB
	#
	def checkForNameChange (self, origObj, newObj, changeInfo):
		try:
			# If the parent is a server and the attribute is name then we need to queue up a Homebridge restart
			dev = indigo.devices[changeInfo.parentId]
			if dev.deviceTypeId == "Homebridge-Server" and changeInfo.name == "name" and self.pluginPrefs["restartNameChanges"]:
				self.setServerRestart (dev, origObj, "'{0}' name changed to '{1}'".format(origObj.name, newObj.name))
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
		
		
	#
	# Set the server to restart
	#
	def setServerRestart (self, dev, origDev, description, restartMinutes = 1, restartAtSeconds = 20, addMinutes = 1):
		try:
			if dev.states["restartPending"] == False:
				# There isn't a restart pending, set the timer
				d = indigo.server.getTime()
				d = dtutil.dateAdd ("minutes", restartMinutes, d)
				
				self.logger.warn ("{0}, the Homebridge server will restart at {1}".format(description, d.strftime("%Y-%m-%d %H:%M:%S")))
				states = iutil.updateState ("restartTime", d.strftime("%Y-%m-%d %H:%M:%S"))
				states = iutil.updateState ("restartPending", True, states)
				dev.updateStatesOnServer (states)
			
			else:
				# If the restart is for less than 5 minutes from now then let the user know
				d = indigo.server.getTime()
				restart = datetime.datetime.strptime (dev.states["restartTime"], "%Y-%m-%d %H:%M:%S")
				secondsLeft = dtutil.dateDiff ("seconds", restart, d)
			
				if secondsLeft < restartAtSeconds:
					# It's near at hand, extend in case they need to rename other devices
					d = dtutil.dateAdd ("minutes", addMinutes, d)
				
					self.logger.warn ("{0}, the Homebridge server was set to restart in under " + str(restartAtSeconds) + " seconds, extended to {1}".format(description, d.strftime("%Y-%m-%d %H:%M:%S")))
					states = iutil.updateState ("restartTime", d.strftime("%Y-%m-%d %H:%M:%S"))
					dev.updateStatesOnServer (states)
					
				elif secondsLeft < (restartMinutes * 60):
					self.logger.warn ("{0}, the Homebridge server is already set to restart at {1}".format(description, restart.strftime("%Y-%m-%d %H:%M:%S")))	
					
				else:
					# It's further into the future, make it more immediate
					d = dtutil.dateAdd ("minutes", restartMinutes, d)
				
					self.logger.warn ("{0}, the Homebridge server will restart at {1}".format(description, d.strftime("%Y-%m-%d %H:%M:%S")))
					states = iutil.updateState ("restartTime", d.strftime("%Y-%m-%d %H:%M:%S"))
					dev.updateStatesOnServer (states)	
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	#
	# Set the device icon
	#
	def _setDeviceIcon (self, dev):
		try:
			img = False
			dev.refreshFromServer() # just in case we got set a stale copy
			
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
				
				# In case it's a sprinkler
				if ext.valueValid (dev.pluginProps, "isSprinkler"):
					if dev.pluginProps["isSprinkler"]:
						if dev.states["brightnessLevel"] == 0: img = indigo.kStateImageSel.SprinklerOff
						if dev.states["brightnessLevel"] != 0: img = indigo.kStateImageSel.SprinklerOn
						
						if dev.states["sprinklerPaused"]: img = indigo.kStateImageSel.AvPaused
						
			if dev.pluginProps["treatAs"] == "garage": 
				if dev.states["brightnessLevel"] == 0: img = indigo.kStateImageSel.DoorSensorClosed
				if dev.states["brightnessLevel"] != 0: img = indigo.kStateImageSel.DoorSensorOpened
			
			if dev.pluginProps["treatAs"] == "window": 
				if dev.states["brightnessLevel"] == 0: img = indigo.kStateImageSel.WindowSensorClosed
				if dev.states["brightnessLevel"] != 0: img = indigo.kStateImageSel.WindowSensorOpened
				
			if dev.pluginProps["treatAs"] == "drape": 
				if dev.states["brightnessLevel"] == 0: img = indigo.kStateImageSel.LightSensor
				if dev.states["brightnessLevel"] != 0: img = indigo.kStateImageSel.LightSensorOn
				
			if dev.pluginProps["treatAs"] == "sensor": 
				if dev.states["brightnessLevel"] == 0: img = indigo.kStateImageSel.MotionSensor
				if dev.states["brightnessLevel"] != 0: img = indigo.kStateImageSel.MotionSensorTripped	
				
			if dev.pluginProps["treatAs"] == "fans": 
				if dev.states["brightnessLevel"] == 0: img = indigo.kStateImageSel.FanOff
				if dev.states["brightnessLevel"] != 0: img = indigo.kStateImageSel.FanHigh		
		
			if img: dev.updateStateImageOnServer(img)
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	
	#
	# Check the device address
	#
	def checkDeviceAddress (self, dev):
		try:
			# If it doesn't have an address for some reason then give it one
			if (dev.deviceTypeId == "Homebridge-Alias"):
				childDev = indigo.devices[int(dev.pluginProps["device"])]
				
				props = dev.pluginProps
				props["address"] = childDev.name
				
				dev.replacePluginPropsOnServer (props)
				self._setDeviceIcon (dev)
				
			elif (dev.deviceTypeId == "Homebridge-Wrapper"):
				props = dev.pluginProps
				
				if dev.pluginProps["methodOn"] == "device":
					childDev = indigo.devices[int(dev.pluginProps["deviceOn"])]
					props["address"] = childDev.name

				elif dev.pluginProps["methodOn"] == "action":
					childDev = indigo.actionGroups[int(dev.pluginProps["actionOn"])]	
					props["address"] = childDev.name + " (Action)"
					
				
				dev.replacePluginPropsOnServer (props)
				self._setDeviceIcon (dev)	
				
			elif (dev.deviceTypeId == "Homebridge-Camera"):
				props = dev.pluginProps
				
				#props["address"] = props["videoSource"]					
				props["address"] = props["name"]					
				
				dev.replacePluginPropsOnServer (props)
				self._setDeviceIcon (dev)		
				
			elif (dev.deviceTypeId == "Homebridge-Wrapper" or dev.deviceTypeId == "Homebridge-Alias") and ext.valueValid (dev.pluginProps, "treatAs", True):
				
				
				
				if dev.pluginProps["treatAs"] != "none":
					address = "Unknown Device"
					
					if dev.pluginProps["treatAs"] == "switch": address="Switch"
					if dev.pluginProps["treatAs"] == "lock": address="Lock"
					if dev.pluginProps["treatAs"] == "door": address="Door"
					if dev.pluginProps["treatAs"] == "dimmer": address="Dimmer"
					if dev.pluginProps["treatAs"] == "garage": address="Garage Door"
					if dev.pluginProps["treatAs"] == "window": address="Window"
					if dev.pluginProps["treatAs"] == "drape": address="Window Covering"
					if dev.pluginProps["treatAs"] == "fan": address="Fan"

					server = False
					if ext.valueValid (dev.pluginProps, "serverDevice", True):
						server = indigo.devices[int(dev.pluginProps["serverDevice"])]
						if server.pluginProps["indigoServer"]:
							server = "Indigo Server"
						else:
							server = server.pluginProps["computerip"]

					props = dev.pluginProps
					
					if server:
						props["address"] = address + " On " + server
					else:
						props["address"] = address
					
					dev.replacePluginPropsOnServer (props)
					self._setDeviceIcon (dev)
					
			elif dev.deviceTypeId == "Homebridge-Server" or dev.deviceTypeId == "Homebridge-Guest" or dev.deviceTypeId == "Homebridge-Custom":
				props = dev.pluginProps
				props["address"] = props["hbpin"] + " @ " + props["hbport"]
				dev.replacePluginPropsOnServer (props)
				
					
			elif dev.deviceTypeId == "Homebridge-Custom" and (dev.address != "SERVER @ Indigo Server" or dev.address != "SERVER @ " + dev.pluginProps["computerip"]):
				props = dev.pluginProps
				
				if props["indigoServer"]:
					props["address"] = "SERVER @ Indigo Server"
				else:
					props["address"] = "SERVER @ " + dev.pluginProps["computerip"]
				
				dev.replacePluginPropsOnServer (props)
					
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	#
	# Calculate a schedule or zone run time and append state changes
	#
	def calculateIrrigationRunTime (self, parent, child, states):
		try:
			if len(child.zoneScheduledDurations) > 0:
				zoneTimes = child.zoneScheduledDurations
			else:
				zoneTimes = child.zoneMaxDurations
				
			# Default to using the "on" method unless otherwise stated
			if ext.valueValid (self.pluginPrefs, "sprinklerDim", True):
				if self.pluginPrefs["sprinklerDim"] == "max":
					zoneTimes = child.zoneMaxDurations	
					
			totalTime = 0
			zoneIdx = 1 # 1 based because activeZone is 1 based
			for zoneTime in zoneTimes:
				if child.states["activeZone"] <= (zoneIdx):
					totalTime = totalTime + zoneTime
					
				zoneIdx = zoneIdx + 1
				
			d = indigo.server.getTime()
			dend = dtutil.dateAdd ("minutes", totalTime, d)
			states = iutil.updateState ("sprinklerSchedule", totalTime, states)
			states = iutil.updateState ("sprinklerStartTime", d.strftime("%Y-%m-%d %H:%M:%S"), states)
			states = iutil.updateState ("sprinklerEndTime", dend.strftime("%Y-%m-%d %H:%M:%S"), states)
					
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return states
		
	#
	# Update a sprinkler alias' brightness based on user criteria
	#
	def setIrrigationBrightness (self, devId):
		try:
			# If we get here then we were cached and therefor irrigation is running
			parent = indigo.devices[devId]
			child = indigo.devices[int(parent.pluginProps["device"])]
			
			d = indigo.server.getTime()
			#startTime = datetime.datetime.strptime (parent.states["sprinklerStartTime"], "%Y-%m-%d %H:%M:%S")
			endTime = datetime.datetime.strptime (parent.states["sprinklerEndTime"], "%Y-%m-%d %H:%M:%S")
			
			#started = dtutil.dateDiff ("minutes", d, startTime)
			ends = dtutil.dateDiff ("minutes", endTime, d)
			
			perc = int(round(ends / parent.states["sprinklerSchedule"], 2) * 100)
			
			if parent.states["brightnessLevel"] != perc: parent.updateStateOnServer ("brightnessLevel", perc)
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	#
	# Process a child device's change
	#
	def changeParentFromChild_Alias (self, parent, child, changeInfo, getStatusMethod):
		try:
			states = []
			
			if parent.pluginProps["treatAs"] == "dimmer" and type(child) != indigo.SprinklerDevice:
				if "onOffState" in child.states: states = iutil.updateState ("onOffState", child.states["onOffState"], states)
				if "brightnessLevel" in child.states: states = iutil.updateState ("brightnessLevel", child.states["brightnessLevel"], states)
				
			elif parent.pluginProps["treatAs"] == "dimmer" and type(child) == indigo.SprinklerDevice:	
				return # we are handling this with our raised events
				
			elif parent.pluginProps["treatAs"] == "switch" or parent.pluginProps["treatAs"] == "sensor":
				if "onOffState" in child.states: states = iutil.updateState ("onOffState", child.states["onOffState"], states)
					
			if len(states) > 0:
				parent.updateStatesOnServer (states)	
				
			# Make sure the icon gets changed too
			self._setDeviceIcon (parent)	
			
			# Tell HB-Indigo to refresh this device
			self.homebridgeForceUpdate (parent, child)	
					
		except Exception as e:
			self.logger.error (ext.getException(e))			
					
	#
	# Process a child device's change
	#
	def changeParentFromChild (self, parent, child, changeInfo, getStatusMethod):
		if parent.deviceTypeId == "Homebridge-Alias": 
			self.changeParentFromChild_Alias (parent, child, changeInfo, getStatusMethod)
			return
		
		# Find out what commands are influenced by this state
		changedMethod = []
		isPassthrough = True # Assume we don't have an action to set brightness
		
		try:		
			for i in range (1, self.TOTALDIMMING + 2 + 1): # Dimmers + On + Off + 1 (since we aren't starting at 0)
				method = "Dim" + str(i)
				if i == self.TOTALDIMMING + 1: method = "On"
				if i == self.TOTALDIMMING + 2: method = "Off"
				
				#indigo.server.log(unicode(changeInfo))
			
				if ext.valueValid (parent.pluginProps, "getStatusFrom" + method) == False: continue # not configured
				if parent.pluginProps["getStatusFrom" + method] != getStatusMethod: continue # wrong event
				
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
						if propValue[0:len(childValue)] == childValue: changedMethod.append(method)
						
				elif parent.pluginProps["valueOperator" + method] == "notin":
					stringIsIn = string.find (propValue, childValue)
					if stringIsIn > -1: 
						pass	
					else:
						# See if it's in the first position
						if propValue[0:len(childValue)] == childValue: 
							pass
						else:
							changedMethod.append(method)
		
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
					
				# Failsafe to make sure brightness and state update together
				if stateName == "onOffState" and stateVal and parent.states["brightnessLevel"] == 0:
					parent.updateStateOnServer("brightnessLevel", 100)
				
				elif stateName == "onOffState" and stateVal == False and parent.states["brightnessLevel"] != 0:
					parent.updateStateOnServer("brightnessLevel", 0)
					
				elif stateName == "brightnessLevel" and stateVal == 0 and parent.states["onOffState"]:
					parent.updateStateOnServer("onOffState", False)
					
				elif stateName == "brightnessLevel" and stateVal > 0 and parent.states["onOffState"] == False:
					parent.updateStateOnServer("onOffState", True)
	
			# If we had no brightness changes and we are passing through then update			
			if isPassthrough and getStatusMethod == "state" and ext.valueValid (child.states, "brightnessLevel"):
				self.logger.threaddebug ("Passing through brightness from child to the parent")
				parent.updateStateOnServer("brightnessLevel", child.states["brightnessLevel"])
				parent.updateStateOnServer("onOffState", child.states["onOffState"]) # Failsafe
				
			# Make sure the icon gets changed too
			self._setDeviceIcon (parent)
				
			# Tell HB-Indigo to refresh this device
			self.homebridgeForceUpdate (parent, child)
							
		except Exception as e:
			self.logger.error (ext.getException(e))	
		
	################################################################################	
	# DEVICE ACTIONS
	################################################################################				

	#
	# Force a device on or off
	#
	def forceState (self, action):
		try:
			#indigo.server.log(unicode(action))
			if action.pluginTypeId == "forceOff":
				dev = indigo.devices[action.deviceId]
				dev.updateStateOnServer ("onOffState", False)
				dev.updateStateOnServer ("brightnessLevel", 0)
				
			if action.pluginTypeId == "forceOn":
				dev = indigo.devices[action.deviceId]
				dev.updateStateOnServer ("onOffState", True)
				dev.updateStateOnServer ("brightnessLevel", 100)
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	#
	# Server commands
	#
	def serverActions (self, action):
		try:
			if action.pluginTypeId == "startHomebridge":
				dev = indigo.devices[action.deviceId]
				self.homebridgeStart (dev)
				
			if action.pluginTypeId == "stopHomebridge":
				dev = indigo.devices[action.deviceId]
				self.homebridgeStop (dev)
				
			if action.pluginTypeId == "reloadHomebridge":
				dev = indigo.devices[action.deviceId]
				self.homebridgeRestart(dev)
				
			if action.pluginTypeId == "saveHomebridge":
				dev = indigo.devices[action.deviceId]
				
				valuesDict = {}
				valuesDict["server"] = str(dev.id)
									
				ret = self.menuSave(valuesDict, dev.deviceTypeId)
				
			if action.pluginTypeId == "saveReloadHomebridge":
				dev = indigo.devices[action.deviceId]
				
				valuesDict = {}
				valuesDict["server"] = str(dev.id)
									
				ret = self.menuSave(valuesDict, dev.deviceTypeId)
				
				self.menuReload(valuesDict, dev.deviceTypeId)
				
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	#
	# Alias commands
	#
	def aliasActions (self, action):
		try:
			dev = indigo.devices[action.deviceId]
			props = dev.pluginProps
			
			if action.pluginTypeId == "turnonIgnore": props["ignore"] = True
			if action.pluginTypeId == "turnoffIgnore": props["ignore"] = True
			if action.pluginTypeId == "toggleIgnore": 
				if props["ignore"] == False:
					props["ignore"] = True
				else:
					props["ignore"] = False
				
			dev.replacePluginPropsOnServer (props)
			
		except Exception as e:
			self.logger.error (ext.getException(e))			
			
	################################################################################
	# MENU ACTIONS
	################################################################################
	
	#
	# Migrate beta 3 plugin prefs to a new HB server device
	#
	def migrateV4 (self):
		try:
			if ext.valueValid (self.pluginPrefs, "devinclude"):
				msg = eps.ui.debugHeader ("BETA 5 UPGRADE")
				msg += eps.ui.debugLine (" ")
				msg += eps.ui.debugLine ("Upgrading your plugin configuration to beta 5")
				msg += eps.ui.debugLine ("check release notes for more information")
				msg += eps.ui.debugHeaderEx ()		
			
				self.logger.error (msg)
			
				# Beta 4 configuration, migrate to a new server
				try:
					newFolder = indigo.devices.folder.create("Homebridge Companion")
				except ValueError, e:
					if e.message == "NameNotUniqueError":
						newFolder = indigo.devices.folders["Homebridge Companion"]
					else:
						# We don't care, create it in the root
						pass
						
				props = indigo.Dict()	
						
				for key, value in self.pluginPrefs.iteritems():
					props[key] = value
					
				props["hbpin"] = "031-45-154"
					
				if "itemcount" in props: del props["itemcount"]
				if "lastUpdateCheck" in props: del props["lastUpdateCheck"]
				if "latestVersion" in props: del props["latestVersion"]
				if "logLevel" in props: del props["logLevel"]
				if "monitorChanges" in props: del props["monitorChanges"]
				if "pollingFrequency" in props: del props["pollingFrequency"]
				if "pollingInterval" in props: del props["pollingInterval"]
				if "pollingMode" in props: del props["pollingMode"]
				
				if "platform" in props: del props["platform"]
				if "protocol" in props: del props["protocol"]
				if "host" in props: del props["host"]
				if "port" in props: del props["port"]
				if "path" in props: del props["path"]
				if "username" in props: del props["username"]
				if "password" in props: del props["password"]
					
				if "-all-" in props["devinclude"]:
					pass
				else:
					props["devexclude"] = ["-none-"]
					
				if "-all-" in props["actinclude"]:
					pass
				else:
					props["actexclude"] = ["-none-"]
				
				server = indigo.device.create(protocol=indigo.kProtocol.Plugin,
					address = 'Server',
					name = 'Homebridge Server', 
					description = 'Migrated from pre-beta 5 prefs', 
					pluginId = self.pluginId,
					deviceTypeId = 'Homebridge-Server',
					props=props,
					folder=newFolder.id)
					
				for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Wrapper"):
					props = dev.pluginProps
					props["serverDevice"] = str(server.id)
					dev.replacePluginPropsOnServer (props)
					
				# Remove from the plugin prefs
				for key, value in server.pluginProps.iteritems():
					if key in self.pluginPrefs: 
						del self.pluginPrefs[key]
						
										
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	#
	# Stop the HB process
	#
	def menuStop (self, valuesDict, typeId):
		errorsDict = indigo.Dict()
		success = True
		
		try:
			if valuesDict["server"] == "" or valuesDict["server"] == "-line-":
				errorsDict["server"] = "Please select a server"
				errorsDict["showAlertText"] = "This job will be much easier if you select a server you want to stop!"
				success = False
				
			elif valuesDict["server"] == "-all-":
				for devId in self.SERVERS:
					self.homebridgeStop (indigo.devices[int(devId)])
					
			else:
				self.homebridgeStop (indigo.devices[int(valuesDict["server"])])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return (success, valuesDict, errorsDict)	 
			
	#
	# Start the HB process
	#
	def menuStart (self, valuesDict, typeId):
		errorsDict = indigo.Dict()
		success = True
		
		try:
			if valuesDict["server"] == "" or valuesDict["server"] == "-line-":
				errorsDict["server"] = "Please select a server"
				errorsDict["showAlertText"] = "This job will be much easier if you select a server you want to start!"
				success = False
				
			elif valuesDict["server"] == "-all-":
				for devId in self.SERVERS:
					self.homebridgeStart (indigo.devices[int(devId)])
					
			else:
				self.homebridgeStart (indigo.devices[int(valuesDict["server"])])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return (success, valuesDict, errorsDict)
			
	#
	# Development testing
	#
	def devTest (self):
		try:
			indigo.server.log ("These are not the droids you are looking for.  Move along.  Move along.")

			dev = indigo.devices[848501866]
			server = False
			
			
					
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	
	#
	# Reload HB
	#
	def menuReload (self, valuesDict, typeId):
		errorsDict = indigo.Dict()
		success = True
		
		try:
			if valuesDict["server"] == "" or valuesDict["server"] == "-line-":
				errorsDict["server"] = "Please select a server"
				errorsDict["showAlertText"] = "This job will be much easier if you select a server you want to restart!"
				success = False
				
			elif valuesDict["server"] == "-all-":
				for devId in self.SERVERS:
					self.homebridgeRestart (indigo.devices[int(devId)])
					
			else:
				self.homebridgeRestart (indigo.devices[int(valuesDict["server"])])
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return (success, valuesDict, errorsDict)
		
			
	#
	# Save and reload
	#
	def menuSaveReload (self, valuesDict, typeId):
		try:
			ret = self.menuSave(valuesDict, typeId)
			if ret[0] == False: return ret
			
			self.menuReload(valuesDict, typeId)
			if ret[0] == False: return ret
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return True
		
	#
	# Output the built in server log
	#
	def menuLog (self, valuesDict, typeId):	
		errorsDict = indigo.Dict()
		success = True
		
		try:
			if valuesDict["server"] == "" or valuesDict["server"] == "-line-":
				errorsDict["server"] = "Please select a server"
				errorsDict["showAlertText"] = "This job will be much easier if you select a server you want to get the log for!"
				success = False
		
			else:		
				dev = indigo.devices[int(valuesDict["server"])]
				
				#home = self.plugindir + "/bin/hb/homebridge/" + str(dev.id)
				home = expanduser("~") + "/.hbb/" + str(dev.id)
				
				if os.path.exists(home + "/homebridge.log"):
					file = open(home + "/homebridge.log", 'r')
					logdetails = file.read()
					
					self.logger.info (logdetails)
				
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
		return (success, valuesDict, errorsDict)
		
	#
	# Output the built in server config
	#
	def menuConfig (self, valuesDict, typeId):	
		errorsDict = indigo.Dict()
		success = True
		
		try:
			if valuesDict["server"] == "" or valuesDict["server"] == "-line-":
				errorsDict["server"] = "Please select a server"
				errorsDict["showAlertText"] = "This job will be much easier if you select a server you want to get the config for!"
				success = False
		
			else:		
				dev = indigo.devices[int(valuesDict["server"])]
				
				#home = self.plugindir + "/bin/hb/homebridge/" + str(dev.id)
				home = expanduser("~") + "/.hbb/" + str(dev.id)
				
				if os.path.exists(home + "/config.json"):
					file = open(home + "/config.json", 'r')
					logdetails = file.read()
					
					self.logger.info (logdetails)
				
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
		return (success, valuesDict, errorsDict)	
	
	#
	# Build and save the configuration
	#
	def menuSave (self, valuesDict, typeId):
		errorsDict = indigo.Dict()
		success = True
		
		try:
			if valuesDict["server"] == "" or valuesDict["server"] == "-line-":
				errorsDict["server"] = "Please select a server"
				errorsDict["showAlertText"] = "This job will be much easier if you select a server you want to restart!"
				success = False
				
			elif valuesDict["server"] == "-all-":
				for devId in self.SERVERS:
					self.homebridgeRestart (indigo.devices[int(devId)])
					
			else:
				config = self.buildServerConfig (indigo.devices[int(valuesDict["server"])])
				if config == "":
					errorsDict["showAlertText"] = "The configuration did not generate, please check the logs for more information."
					success = False
					return (success, valuesDict, errorsDict)

				dev = indigo.devices[int(valuesDict["server"])]
				
				if self.homebridgeSaveConfig (dev, config):
					pass
				else:
					errorsDict["showAlertText"] = "Unable to save the configuration, please check the logs for more information."
					success = False
					return (success, valuesDict, errorsDict)
				
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return (success, valuesDict, errorsDict)
	
	
	def menuSaveEx (self):
		try:
			for server in indigo.devices.iter(self.pluginId + ".Homebridge-Server"):
				self.logger.info ("Building configuration for '{0}'".format(server.name))
				
				config = self.buildConfigDict (server.pluginProps, server.id)
				
				idCount = config["actCount"] + config["devCount"]
				
				if idCount > 99:
					msg = eps.ui.debugHeader ("WARNING")
					msg += eps.ui.debugLine (" ")
					msg += eps.ui.debugLine ("You have {0} items for Homebridge but it only supports 99, you".format(str(idCount)))
					msg += eps.ui.debugLine ("will be unable to use some of your items!")
					msg += eps.ui.debugHeaderEx ()		
				
					self.logger.error (msg)
					
				idTotal = len(indigo.devices)
				if config["actCount"] > 0: idTotal = idTotal + len(indigo.actionGroups)
					
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
				msg += eps.ui.debugHeaderEx ()
				self.logger.info (msg)
				
				cfg =	'{\n'
				cfg += 	'\t"bridge": {\n'
			
				cfg +=	'\t\t"name": "Homebridge",\n'
				cfg +=	'\t\t"username": "{0}",\n'.format(server.pluginProps["hbuser"])
				cfg +=	'\t\t"port": 51826,\n'
				cfg +=	'\t\t"pin": "{0}"\n'.format(server.pluginProps["hbpin"])
			
				cfg +=	'\t},\n\n'
			
				cfg += 	'\t"description": "Homebridge-Indigo configuration generated by EPS Homebridge Companion on {1} for device {0}",\n\n'.format(server.name, indigo.server.getTime().strftime("%Y-%m-%d %H:%M:%S"))
			
				cfg += 	'\t"platforms": [\n'
				cfg +=	'\t\t{\n'
			
				cfg +=	'\t\t\t"platform": "{0}",\n'.format(self.pluginPrefs["platform"])
				cfg +=	'\t\t\t"name": "{0}",\n'.format(server.pluginProps["name"])
				cfg +=	'\t\t\t"protocol": "{0}",\n'.format(self.pluginPrefs["protocol"].lower())
				cfg +=	'\t\t\t"host": "{0}",\n'.format(self.pluginPrefs["host"])
				cfg +=	'\t\t\t"port": "{0}",\n'.format(self.pluginPrefs["port"])
				cfg +=	'\t\t\t"path": "{0}",\n'.format(self.pluginPrefs["path"])
				cfg +=	'\t\t\t"username": "{0}",\n'.format(self.pluginPrefs["username"])
				cfg +=	'\t\t\t"password": "{0}",\n'.format(self.pluginPrefs["password"])
				
				if config["actCount"] > 0:
					cfg +=	'\t\t\t"includeActions": true,\n'
				else:
					cfg +=	'\t\t\t"includeActions": false,\n'
					
				# Incorporate included devices
				if len(config["includes"]) > 0:
					cfg +=	'\t\t\t"includeIds": {0},\n'.format(self._addItemListToConfig (config["includes"]))
				
				# Incorporate excluded devices
				if len(config["excludes"]) > 0:
					cfg +=	'\t\t\t"excludeIds": {0},\n'.format(self._addItemListToConfig (config["excludes"]))
				
				# Incorporate switches
				if len(config["treatAs"]["switches"]) > 0:
					cfg +=	'\t\t\t"treatAsSwitchIds": {0},\n'.format(self._addItemListToConfig (config["treatAs"]["switches"]))
				
				# Incorporate locks
				if len(config["treatAs"]["locks"]) > 0:
					cfg +=	'\t\t\t"treatAsLockIds": {0},\n'.format(self._addItemListToConfig (config["treatAs"]["locks"]))
				
				# Incorporate doors
				if len(config["treatAs"]["doors"]) > 0:
					cfg +=	'\t\t\t"treatAsDoorIds": {0},\n'.format(self._addItemListToConfig (config["treatAs"]["doors"]))
				
				# Incorporate garages
				if len(config["treatAs"]["garages"]) > 0:
					cfg +=	'\t\t\t"treatAsGarageDoorIds": {0},\n'.format(self._addItemListToConfig (config["treatAs"]["garages"]))
				
				# Incorporate windows
				if len(config["treatAs"]["windows"]) > 0:
					cfg +=	'\t\t\t"treatAsWindowIds": {0},\n'.format(self._addItemListToConfig (config["treatAs"]["windows"]))
				
				# Incorporate drapes
				if len(config["treatAs"]["drapes"]) > 0:
					cfg +=	'\t\t\t"treatAsWindowCoveringIds": {0},\n'.format(self._addItemListToConfig (config["treatAs"]["drapes"]))
					
				# Incorporate drapes
				if len(config["treatAs"]["fans"]) > 0:
					cfg +=	'\t\t\t"treatAsFanIds": {0},\n'.format(self._addItemListToConfig (config["treatAs"]["fans"]))	
				
				cfg +=	'\t\t\t"thermostatsInCelsius": {0},\n'.format(unicode(server.pluginProps["celsius"]).lower())

				cfg +=	'\t\t\t"accessoryNamePrefix": "{0}"\n'.format(server.pluginProps["accessory"])			
				cfg +=	'\t\t}\n'
				cfg += 	'\t],\n\n'
			
				cfg += 	'\t"accessories": [\n'
				cfg += 	'\t]\n'
			
				cfg += 	'}'
				
				self.logger.debug (cfg)
				
				home = expanduser("~") + "/.homebridge"
			
				if os.path.exists(home):
					if os.path.exists (home + "/config.json"):
						self.logger.debug ("Found '{0}/config.json', saving the Homebridge configuration".format(home))
					
						with open(home + "/config.json", 'w') as file_:
							file_.write(cfg)
					else:
						self.logger.error ("Unable to find the config.json file in '{0}', are you sure Homebridge is installed?  Unable to save configuration".format(home))
						return
				else:
					self.logger.error ("Unable to find '{0}', are you sure Homebridge is installed?  Unable to save configuration".format(home))
					return
					
				self.logger.info ("Homebridge configuration saved")
			
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	################################################################################
	# CUSTOM LISTS
	################################################################################
	
	#
	# List of devices wrapped by our wrapper
	#
	def getWrappedDevices (self, valuesDict):
		retList = []
		if len(valuesDict) == 0: return valuesDict
		
		try:
			if valuesDict["hideWrappedItems"]:
				for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Wrapper"):
					for i in range (1, self.TOTALDIMMING + 2 + 1): # Dimmers + On + Off + 1 (since we aren't starting at 0)
						method = "Dim" + str(i)
						if i == self.TOTALDIMMING + 1: method = "On"
						if i == self.TOTALDIMMING + 2: method = "Off"
			
						if dev.pluginProps["method" + method] == "device": 
							if ext.valueValid (dev.pluginProps, "device" + method, True): 
								objId = int(dev.pluginProps["device" + method])
								if objId in retList:
									pass
								else:
									retList.append (objId)
												
						if dev.pluginProps["method" + method] == "action": 
							if ext.valueValid (dev.pluginProps, "action" + method, True): 
								objId = int(dev.pluginProps["action" + method])
								if objId in retList:
									pass
								else:
									retList.append (objId)
									
				for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Alias"):
					if ext.valueValid (dev.pluginProps, "device", True): 
						objId = int(dev.pluginProps["device"])
						if objId in retList:
							pass
						else:
							retList.append (objId)
							
			return retList
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return []
			
	#
	# List of HB servers
	#
	def listServers (self, args, valuesDict):
		ret = [("default", "No servers found")]
		
		try:
			retList = []
			if len(self.SERVERS) == 0: return ret
			
			for devId in self.SERVERS:
				retList.append ((str(devId), indigo.devices[int(devId)].name))
				
			return retList
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return ret
			
	#
	# List of HB servers
	#
	def listServersEx (self, args, valuesDict):
		ret = [("default", "No servers found")]
		
		try:
			retList = []
			if len(self.SERVERS) == 0: return ret
			
			for devId in self.SERVERS:
				if indigo.devices[int(devId)].deviceTypeId == "Homebridge-Server" or indigo.devices[int(devId)].deviceTypeId == "Homebridge-Guest":
					retList.append ((str(devId), indigo.devices[int(devId)].name))
				
			return retList
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return ret		
	
	#
	# List of HB friendly devices
	#
	def listHBFriendly (self, args, valuesDict):
		ret = [("default", "No data")]
		
		try:
			retList = []
			
			retList = self._friendlyDevices (retList, self.getWrappedDevices(valuesDict), True)
				
			if len(retList) > 0:
				retList.insert(0, ("-all-", "All Indigo Devices"))
				retList.insert(0, ("-none-", "Don't Include Any Devices"))
				retList = eps.ui.insertLine (retList, 2)
				
			return retList
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return ret
	
	#
	# List of included HB devices to exclude
	#		
	def listHBExclude (self, args, valuesDict):
		ret = [("default", "No data")]
		
		try:
			retList = []
		
			if "devinclude" in valuesDict:
				if "-all-" in valuesDict["devinclude"]:
					retList.append(("-none-", "Don't Exclude Anything"))
					retList = eps.ui.addLine(retList)
					retList += self._friendlyDevices (retList, self.getWrappedDevices(valuesDict))
				else:
					retList.append(("-none-", "Include ALL devices to see this list"))
							
			return retList
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return ret
			
	#
	# List of HB action groups
	#
	def listHBActionGroups (self, args, valuesDict):
		ret = [("default", "No data")]
		
		try:
			retList = []
			
			retList = self._friendlyActionGroups (retList, self.getWrappedDevices(valuesDict), True)
				
			if len(retList) > 0:
				retList.insert(0, ("-all-", "All Indigo Action Groups"))
				retList.insert(0, ("-none-", "Don't Include Any Action Groups"))
				retList = eps.ui.insertLine (retList, 2)
				
			return retList
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return ret
			
	#
	# List of HB action groups to exclude
	#
	def listHBActionGroupsExclude (self, args, valuesDict):
		ret = [("default", "No data")]
		
		try:
			retList = []
			
			if "actinclude" in valuesDict:
				if "-all-" in valuesDict["actinclude"]:
					retList.append(("-none-", "Don't Exclude Anything"))
					retList = eps.ui.addLine(retList)
					retList += self._friendlyActionGroups (retList, self.getWrappedDevices(valuesDict))
				else:
					retList.append(("-none-", "Include ALL action groups to see this list"))
							
			return retList
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return ret
			
	#
	# List of all included devices
	#
	def listHBIncluded (self, args, valuesDict):	
		ret = [("default", "No data")]
			
		try:
			retList = []
			
			if "devinclude" in valuesDict:
				for devId in valuesDict["devinclude"]:
					if devId[0:1] == "-": continue
					if devId == "default": continue
					
					retList.append ((str(devId), indigo.devices[int(devId)].name))
					
			return retList
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return ret
			
	#
	# Get all devices and actions for the selected HB server(s) in a guest server device
	#
	def listHBGuestDevices (self, args, valuesDict):	
		ret = [("default", "No data")]
			
		try:
			retList = []
			
			if "servers" in valuesDict:
				# Read in the JSON for the server (easier than parsing everything in Indigo)
				config = self.buildServerConfig (indigo.devices[int(valuesDict["servers"])])
				json_data = json.loads(config)
				
				for platform in json_data["platforms"]:
					if platform["platform"] == "Indigo":
						if "includeIds" in platform and len(platform["includeIds"]) > 0:
							for includeId in platform["includeIds"]:
								if int(includeId) in indigo.devices:
									devtype = "Device"
									
									if indigo.devices[int(includeId)].deviceTypeId == "Homebridge-Wrapper": devtype = "Wrapper"
									if indigo.devices[int(includeId)].deviceTypeId == "Homebridge-Alias": devtype = "Alias"
									
									retList.append ((str(includeId), indigo.devices[int(includeId)].name + " ({0})".format(devtype)))
									
								if int(includeId) in indigo.actionGroups:
									retList.append ((str(includeId), indigo.actionGroups[int(includeId)].name + " (Action)"))	
									
									
				#retList.append ((str(devId), indigo.devices[int(devId)].name))
					
			return retList
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return ret		
			
	
	#
	# List of HB included items to set as a type
	#
	def listHBTreatAs (self, args, valuesDict):
		ret = [("default", "No data")]
		
		try:
			retList = []
			
			devExclude = []
			devInclude = []
			devList = []
			
			actExclude = []
			actInclude = []
			actList = []
			
			thisType = args["list"].replace("_", "")
			
			if "devinclude" in valuesDict:
				for devId in valuesDict["devinclude"]:
					if devId[0:1] == "-": continue
					if devId == "default": continue
					
					devInclude.append (int(devId))	
					
			if "devexclude" in valuesDict:
				for devId in valuesDict["devexclude"]:
					if devId[0:1] == "-": continue
					if devId == "default": continue
					
					devExclude.append (int(devId))	
					
			if "actinclude" in valuesDict:
				for actId in valuesDict["actinclude"]:
					if actId[0:1] == "-": continue
					if actId == "default": continue
					
					actInclude.append (int(actId))	
					
			if "actexclude" in valuesDict:
				for actId in valuesDict["actexclude"]:
					if actId[0:1] == "-": continue
					if actId == "default": continue
					
					actExclude.append (int(actId))	
					
			typeLists = ["treataslock", "treatasdoor", "treataswindows", "treatasswitch", "treatasdrapes", "treatasgarage", "treatasfans"]

			for devId in devInclude:
				canAdd = True
				
				if devId in devExclude:
					continue
				else:
					for t in typeLists:
						if t == thisType:
							continue
						else:
							if str(devId) in valuesDict[t]:
								canAdd = False
								break
							else:
								continue
								
				if canAdd:
					devList.append ((str(devId), indigo.devices[devId].name))
					
			for actId in actInclude:
				canAdd = True
				
				if actId in actExclude:
					continue
				else:
					for t in typeLists:
						if t == thisType:
							continue
						else:
							if str(actId) in valuesDict[t]:
								canAdd = False
								break
							else:
								continue
								
				if canAdd:
					actList.append ((str(actId), indigo.actionGroups[actId].name))

			
			if len(devList) > 0 and len(actList) > 0:
				retList = eps.ui.addLine (retList)
				retList.append (("-devices-", "AVAILABLE DEVICES"))
				retList = eps.ui.addLine (retList)
				retList += devList
				
				retList = eps.ui.addLine (retList)
				retList.append (("-actions-", "AVAILABLE ACTIONS"))
				retList = eps.ui.addLine (retList)
				retList += actList
				
			elif len(devList) > 0:
				retList += devList
				
			elif len(actList) > 0:
				retList += actList
			
			
			return retList
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return ret						
			
			
	################################################################################
	# SUPPORTING ROUTINES
	################################################################################			
	
	#
	# Return methods appropriate for the device AsType
	#
	def listSettingSelect (self, filter="", valuesDict=None, typeId="", targetId=0):
		ret = []

		try:
			# Common
			#ret.append (("cnd", "Conditions"))
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
			
				if valuesDict["deviceActionOn"] == "":
					# Set defaults
					valuesDict["deviceActionOn"] = "indigo_setBinaryOutput"
					valuesDict["optionLabelOn1"] = "Binary output number"
					valuesDict["optionGroupOn1"] = "textfield"
					valuesDict["strValueOn1"] = "1"
					valuesDict["deviceStateOn"] = "binaryInput1"
					valuesDict["valueOn"] = "false"
					
				if valuesDict["deviceActionOff"] == "":
					# Set defaults
					valuesDict["deviceActionOff"] = "indigo_setBinaryOutput"
					valuesDict["deviceStateOff"] = "binaryInput1"
					valuesDict["valueOff"] = "true"
			
			elif type(dev) is indigo.SprinklerDevice:
				valuesDict["showStatusFrom" + method] = True
				valuesDict["showValueAndOperator" + method] = True
				valuesDict["showStateFromDevice" + method] = True
			
				if valuesDict["deviceActionOn"] == "":
					# Set defaults
					valuesDict["deviceActionOn"] = "indigo_schedule"
					valuesDict["optionLabelOn1"] = "Duration for all zones separated by commas"
					valuesDict["optionGroupOn1"] = "textfield"
					valuesDict["strValueOn1"] = "0,0,0,0,0,0,0"
					valuesDict["deviceStateOn"] = "activeZone"
					valuesDict["valueOn"] = "0"
					valuesDict["valueOperatorOn"] = "notequal"
					
				if valuesDict["deviceActionOff"] == "":
					# Set defaults
					valuesDict["deviceActionOff"] = "indigo_stop"
					valuesDict["deviceStateOff"] = "activeZone"
					valuesDict["valueOperatorOff"] = "equal"
					valuesDict["valueOff"] = "0"		
				
			
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
				
			
			# Debug summary
			for i in range (1, self.TOTALDIMMING + 2 + 1): # Dimmers + On + Off + 1 (since we aren't starting at 0)
				m = "Dim" + str(i)
				if i == self.TOTALDIMMING + 1: m = "On"
				if i == self.TOTALDIMMING + 2: m = "Off"
				
				self.logger.threaddebug ("For method {0} the device is {1} and state is {2}".format(m, valuesDict["device" + m], valuesDict["deviceState" + m]))
			
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
		return valuesDict
	
	#
	# Build config dictionary (future use)
	#
	def buildConfigData (self, server):
		try:
			self.logger.info ("Building configuration for '{0}'".format(server.name))
			
			config = {}
			bridge = {}
			platforms = []
			accessories = []
			
			# Bridge properties
			bridge["name"] = server.name
			bridge["username"] = server.pluginProps["hbuser"]
			bridge["port"] = server.pluginProps["hbport"]
			bridge["pin"] = server.pluginProps["hbpin"]
			
			config["bridge"] = bridge
			
			# Description
			if server.deviceTypeId == "Homebridge-Server":
				config["description"] = "Homebridge-Indigo configuration configuration generated by EPS Homebridge Buddy on {1} for device {0}".format(server.name, indigo.server.getTime().strftime("%Y-%m-%d %H:%M:%S"))

				# HB-Indigo
				hbindigo = {}
				
				hbindigo["platform"] = self.pluginPrefs["platform"]
				hbindigo["name"] = server.name
				hbindigo["protocol"] = self.pluginPrefs["protocol"].lower()
				
				if server.pluginProps["indigoServer"]:
					hbindigo["host"] = "127.0.0.1"
				else:
					hbindigo["host"] = self.pluginPrefs["host"]
				
				hbindigo["port"] = self.pluginPrefs["port"]
				hbindigo["path"] = self.pluginPrefs["path"]
				hbindigo["username"] = self.pluginPrefs["username"]
				hbindigo["password"] = self.pluginPrefs["password"]
				
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
				inverts = []
				fans = []
				
				for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Wrapper"):
					if dev.pluginProps["serverDevice"] != str(server.id): continue
					
					includeDev.append (str(dev.id))
					
					if ext.valueValid (dev.pluginProps, "treatAs", True):
						if dev.pluginProps["treatAs"] == "switch": switches.append (dev.id)
						if dev.pluginProps["treatAs"] == "lock": locks.append (dev.id)
						if dev.pluginProps["treatAs"] == "door": doors.append (dev.id)
						if dev.pluginProps["treatAs"] == "garage": garages.append (dev.id)
						if dev.pluginProps["treatAs"] == "window": windows.append (dev.id)
						if dev.pluginProps["treatAs"] == "drape": drapes.append (dev.id)
						if dev.pluginProps["treatAs"] == "fan": fans.append (dev.id)
						
					# We only need to exclude wrapped items if they selected that option AND we are including all objects,
					# otherwise why exclude something that was never included in the first place?
					if server.propsDict["hideWrappedItems"]:			
						for i in range (1, self.TOTALDIMMING + 2 + 1): # Dimmers + On + Off + 1 (since we aren't starting at 0)
							method = "Dim" + str(i)
							if i == self.TOTALDIMMING + 1: method = "On"
							if i == self.TOTALDIMMING + 2: method = "Off"
					
							if dev.pluginProps["method" + method] == "device" and "-all-" in propsDict["devinclude"]: 
								if ext.valueValid (dev.pluginProps, "device" + method, True): 
									objId = int(dev.pluginProps["device" + method])
									if objId in excludeDev:
										pass
									else:
										excludeDev.append(objId)
							
							if dev.pluginProps["method" + method] == "action" "-all-" in propsDict["actinclude"]:
								if ext.valueValid (dev.pluginProps, "action" + method, True): 
									objId = int(dev.pluginProps["action" + method])
									if objId in excludeDev:
										pass
									else:
										excludeDev.append(objId)	

				
				hbindigo["includeIds"] = includeDev

				platforms.append (hbindigo)
				
				

			elif server.deviceTypeId == "Homebridge-Custom":
				config["description"] = "Homebridge custom server configuration generated by EPS Homebridge Buddy on {1} for device {0}".format(server.name, indigo.server.getTime().strftime("%Y-%m-%d %H:%M:%S"))	
			
			# Final compilation
			config["platforms"] = platforms
			
			return config
			
		except Exception as e:
			self.logger.error (ext.getException(e))		
		
	#
	# Build config dictionary (Pre-release version)
	#
	def buildConfigDict (self, propsDict, serverId):
		config = indigo.Dict()
		
		try:
			config["devCount"] = 0
			config["actCount"] = 0
			config["wrapCount"] = 0
			
			# Count up add-ons
			config["addons"] = 0
			config["camera"] = 0
			
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
			sensors = []
			inverts = []
			
			for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Camera"):
				if dev.pluginProps["serverDevice"] != str(serverId): continue
				
				config["addons"] = config["addons"] + 1
				config["camera"] = config["camera"] + 1
				
			
			for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Wrapper"):
				if dev.pluginProps["serverDevice"] != str(serverId): continue
				
				includeDev.append (dev.id)
				config["wrapCount"] = config["wrapCount"] + 1
				
				if ext.valueValid (dev.pluginProps, "treatAs", True):
					if dev.pluginProps["treatAs"] == "switch": switches.append (dev.id)
					if dev.pluginProps["treatAs"] == "lock": locks.append (dev.id)
					if dev.pluginProps["treatAs"] == "door": doors.append (dev.id)
					if dev.pluginProps["treatAs"] == "garage": garages.append (dev.id)
					if dev.pluginProps["treatAs"] == "window": windows.append (dev.id)
					if dev.pluginProps["treatAs"] == "drape": drapes.append (dev.id)
					if dev.pluginProps["treatAs"] == "sensor": sensors.append (dev.id)
					
				# We only need to exclude wrapped items if they selected that option AND we are including all objects,
				# otherwise why exclude something that was never included in the first place?
				if propsDict["hideWrappedItems"]:			
					for i in range (1, self.TOTALDIMMING + 2 + 1): # Dimmers + On + Off + 1 (since we aren't starting at 0)
						method = "Dim" + str(i)
						if i == self.TOTALDIMMING + 1: method = "On"
						if i == self.TOTALDIMMING + 2: method = "Off"
					
						if dev.pluginProps["method" + method] == "device" and "-all-" in propsDict["devinclude"]: 
							if ext.valueValid (dev.pluginProps, "device" + method, True): 
								objId = int(dev.pluginProps["device" + method])
								if objId in excludeDev:
									pass
								else:
									excludeDev.append(objId)
							
						if dev.pluginProps["method" + method] == "action" "-all-" in propsDict["actinclude"]:
							if ext.valueValid (dev.pluginProps, "action" + method, True): 
								objId = int(dev.pluginProps["action" + method])
								if objId in excludeDev:
									pass
								else:
									excludeDev.append(objId)
									
			for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Alias"):						
				if dev.pluginProps["serverDevice"] != str(serverId): continue
				
				includeDev.append (dev.id)
				config["wrapCount"] = config["wrapCount"] + 1
				
				if ext.valueValid (dev.pluginProps, "treatAs", True):
					if dev.pluginProps["treatAs"] == "switch": switches.append (dev.id)
					if dev.pluginProps["treatAs"] == "lock": locks.append (dev.id)
					if dev.pluginProps["treatAs"] == "door": doors.append (dev.id)
					if dev.pluginProps["treatAs"] == "garage": garages.append (dev.id)
					if dev.pluginProps["treatAs"] == "window": windows.append (dev.id)
					if dev.pluginProps["treatAs"] == "drape": drapes.append (dev.id)
					if dev.pluginProps["treatAs"] == "sensor": sensors.append (dev.id)
					
				if dev.pluginProps["invertonoff"]: inverts.append (dev.id)
					
				if propsDict["hideWrappedItems"]:			
					if ext.valueValid (dev.pluginProps, "device", True): 
						objId = int(dev.pluginProps["device"])
						if objId in excludeDev:
							pass
						else:
							excludeDev.append (objId)	
								
			# Add in each list
			excludeDev = self._addPrefIdToList (propsDict, "devexclude", excludeDev)
			excludeAct = self._addPrefIdToList (propsDict, "actexclude", excludeAct)
			switches = self._addPrefIdToList (propsDict, "treatasswitch", switches)
			locks = self._addPrefIdToList (propsDict, "treataslock", locks)
			doors = self._addPrefIdToList (propsDict, "treatasdoor", doors)
			garages = self._addPrefIdToList (propsDict, "treatasgarage", garages)
			windows = self._addPrefIdToList (propsDict, "treataswindows", windows)
			drapes = self._addPrefIdToList (propsDict, "treatasdrapes", drapes)
			sensors = self._addPrefIdToList (propsDict, "treatassensors", sensors)
			inverts = self._addPrefIdToList (propsDict, "invertonoff", inverts)

							
			# See if we are including all devices if this is a built in server type (will have devinclude)
			if "devinclude" in propsDict:
				if "-all-" in propsDict["devinclude"]:	
					config["devCount"] = 0
					includeDev = [] # If we are including everything then we don't need to include our wrappers
				
					for dev in indigo.devices:			
						# Don't include devices that HB can't handle, like custom plugins, IO's, etc and don't include our own devices either
						if self.canHomeBridgeSupportDevice(dev) and dev.pluginId != self.pluginId and dev.enabled:
							config["devCount"] = config["devCount"] + 1
						
				else:
					excludeDev = []
					includeDev = self._addPrefIdToList (propsDict, "devinclude", includeDev)
					config["devCount"] = config["devCount"] + len(includeDev)
			
			
				# See if we are including all actions
				if "-all-" in propsDict["actinclude"]:	
					config["actCount"] = 0
				
					for dev in indigo.actionGroups:			
						config["actCount"] = config["actCount"] + 1
						
				else:
					excludeAct = []
					includeAct = self._addPrefIdToList (propsDict, "actinclude", includeAct)
					config["actCount"] = config["actCount"] + len(includeAct)

				# Re-tally with excludes
				config["devCount"] = config["devCount"] - len(excludeDev)
				config["actCount"] = config["actCount"] - len(excludeAct)
				
														
			treatAs = indigo.Dict()
			treatAs["switches"] = switches
			treatAs["locks"] = locks
			treatAs["doors"] = doors
			treatAs["garages"] = garages
			treatAs["windows"] = windows
			treatAs["drapes"] = drapes
			treatAs["inverts"] = inverts
			treatAs["sensors"] = sensors
			
			config["treatAs"] = treatAs
			config["includeDev"] = includeDev
			config["excludeDev"] = excludeDev
			config["includeAct"] = includeAct
			config["excludeAct"] = excludeAct
			
			config["includes"] = includeDev + includeAct
			config["excludes"] = excludeDev + excludeAct
		
		except Exception as e:
			self.logger.error (ext.getException(e))			
	
		return config
		
	#
	# Add prefs array of ID's to a config list
	#
	def _addPrefIdToList (self, propsDict, prefName, listValue):
		try:
			if prefName in propsDict:
				for id in propsDict[prefName]:
					if id == "-line-":
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
					elif int(id) in listValue:
						continue
					else:
						listValue.append(int(id))
					
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
		
	#
	# Refresh device count in configuration
	#
	def btnRefreshDeviceCount (self, valuesDict, typeId, devId):
		try:
			config = self.buildConfigDict (valuesDict, devId)
			
			# In case they switched prefs, force defaults
			valuesDict = self.onAfter_formFieldChanged_Server (valuesDict, typeId, devId)
			
			# Populate the fields
			valuesDict["wrappercount"] = str(config["wrapCount"])
			valuesDict["itemcount"] = str(config["devCount"] + config["actCount"] - config["wrapCount"])
			valuesDict["totalcount"] = str(config["devCount"] + config["actCount"])
			
			
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return valuesDict
		
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
					if len(wrappers) > 0 and dev.id in wrappers:
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
				if len(wrappers) > 0 and dev.id in wrappers:
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
	# HOMEBRIDGE SERVER FILE
	################################################################################	
	
	
		
	#
	# Build server config
	#
	def buildServerConfig (self, server):
		cfg = ""
		
		# If this is a guest device we actually build the config for the server and then post-process it
		if server.deviceTypeId == "Homebridge-Guest": server = indigo.devices[int(server.pluginProps["servers"])]
		
		try:
			self.logger.info ("Building configuration for '{0}'".format(server.name))
			
			cfg =	'{\n'
			cfg += 	'\t"bridge": {\n'
	
			cfg +=	'\t\t"name": "{0}",\n'.format(server.name)
			cfg +=	'\t\t"username": "{0}",\n'.format(server.pluginProps["hbuser"])
			cfg +=	'\t\t"port": {0},\n'.format(server.pluginProps["hbport"])
			cfg +=	'\t\t"pin": "{0}"\n'.format(server.pluginProps["hbpin"])
	
			cfg +=	'\t},\n\n'
	
			if server.deviceTypeId == "Homebridge-Custom":
				cfg += 	'\t"description": "Homebridge custom server configuration generated by EPS Homebridge Buddy on {1} for device {0}",\n\n'.format(server.name, indigo.server.getTime().strftime("%Y-%m-%d %H:%M:%S"))
				
			
			if server.deviceTypeId == "Homebridge-Server":
				cfg += 	'\t"description": "Homebridge-Indigo configuration generated by EPS Homebridge Buddy on {1} for device {0}",\n\n'.format(server.name, indigo.server.getTime().strftime("%Y-%m-%d %H:%M:%S"))
					
				
			config = self.buildConfigDict (server.pluginProps, server.id)
		
			idCount = config["actCount"] + config["devCount"] + config["addons"]
		
			if idCount > 99:
				msg = eps.ui.debugHeader ("WARNING")
				msg += eps.ui.debugLine (" ")
				msg += eps.ui.debugLine ("You have {0} items for Homebridge but it only supports 99, you".format(str(idCount)))
				msg += eps.ui.debugLine ("will be unable to use some of your items!")
				msg += eps.ui.debugHeaderEx ()		
		
				self.logger.error (msg)
			
			idTotal = len(indigo.devices)
			if config["actCount"] > 0: idTotal = idTotal + len(indigo.actionGroups)
			
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
			msg += eps.ui.debugHeaderEx ()
			self.logger.info (msg)
		
			# This is only for the BETA since this field didn't exist in pre beta 8
			#if ext.valueValid (server.pluginProps, "hbuser", True) == False:
			#	server.pluginProps["hbuser"] = "CC:22:3D:E3:CE:30"
		
			cfg += 	'\t"platforms": [\n'
			cfg +=	'\t\t{\n'
	
			cfg +=	'\t\t\t"platform": "{0}",\n'.format(self.pluginPrefs["platform"])
			cfg +=	'\t\t\t"name": "{0}",\n'.format(server.name)
			cfg +=	'\t\t\t"protocol": "{0}",\n'.format(self.pluginPrefs["protocol"].lower())
		
			if server.pluginProps["indigoServer"]:
				cfg +=	'\t\t\t"host": "127.0.0.1",\n'
			else:
				cfg +=	'\t\t\t"host": "{0}",\n'.format(self.pluginPrefs["host"])
		
			cfg +=	'\t\t\t"port": "{0}",\n'.format(self.pluginPrefs["port"])
			cfg +=	'\t\t\t"path": "{0}",\n'.format(self.pluginPrefs["path"])
			cfg +=	'\t\t\t"username": "{0}",\n'.format(self.pluginPrefs["username"])
			cfg +=	'\t\t\t"password": "{0}",\n'.format(self.pluginPrefs["password"])
		
			if config["actCount"] > 0:
				cfg +=	'\t\t\t"includeActions": true,\n'
			else:
				cfg +=	'\t\t\t"includeActions": false,\n'
			
			# Incorporate included devices
			if len(config["includes"]) > 0:
				cfg +=	'\t\t\t"includeIds": {0},\n'.format(self._addItemListToConfig (config["includes"]))
		
			# Incorporate excluded devices
			if len(config["excludes"]) > 0:
				cfg +=	'\t\t\t"excludeIds": {0},\n'.format(self._addItemListToConfig (config["excludes"]))
		
			# Incorporate switches
			if len(config["treatAs"]["switches"]) > 0:
				cfg +=	'\t\t\t"treatAsSwitchIds": {0},\n'.format(self._addItemListToConfig (config["treatAs"]["switches"]))
		
			# Incorporate locks
			if len(config["treatAs"]["locks"]) > 0:
				cfg +=	'\t\t\t"treatAsLockIds": {0},\n'.format(self._addItemListToConfig (config["treatAs"]["locks"]))
		
			# Incorporate doors
			if len(config["treatAs"]["doors"]) > 0:
				cfg +=	'\t\t\t"treatAsDoorIds": {0},\n'.format(self._addItemListToConfig (config["treatAs"]["doors"]))
		
			# Incorporate garages
			if len(config["treatAs"]["garages"]) > 0:
				cfg +=	'\t\t\t"treatAsGarageDoorIds": {0},\n'.format(self._addItemListToConfig (config["treatAs"]["garages"]))
		
			# Incorporate windows
			if len(config["treatAs"]["windows"]) > 0:
				cfg +=	'\t\t\t"treatAsWindowIds": {0},\n'.format(self._addItemListToConfig (config["treatAs"]["windows"]))
		
			# Incorporate drapes
			if len(config["treatAs"]["drapes"]) > 0:
				cfg +=	'\t\t\t"treatAsWindowCoveringIds": {0},\n'.format(self._addItemListToConfig (config["treatAs"]["drapes"]))
				
			# Incorporate sensors
			if len(config["treatAs"]["sensors"]) > 0:
				cfg +=	'\t\t\t"treatAsMotionSensorIds": {0},\n'.format(self._addItemListToConfig (config["treatAs"]["sensors"]))	
			
			# Incorporate inversions
			if len(config["treatAs"]["inverts"]) > 0:
				cfg +=	'\t\t\t"invertOnOffIds": {0},\n'.format(self._addItemListToConfig (config["treatAs"]["inverts"]))	
		
			if "celsius" in server.pluginProps: cfg +=	'\t\t\t"thermostatsInCelsius": {0},\n'.format(unicode(server.pluginProps["celsius"]).lower())

			if "accessory" in server.pluginProps: 
				cfg +=	'\t\t\t"accessoryNamePrefix": "{0}"\n'.format(server.pluginProps["accessory"])			
			else:
				# If we don't have this key then it's a custom server so this next line is just so we properly close up the JSON structure, 
				# otherwise we'll get an error when parsing it - this is totally a kluge, not something we want around later on
				cfg += '\t\t\t"customServer": true' # Meaningless setting to simply close the JSON statement
				
			#cfg +=	'\t\t}\n'
		
			# 0.13 - If we are defining plugin devices they get added here
		
			if config["addons"] == 0:
				cfg +=	'\t\t}\n'
			else:
				cfg +=	'\t\t},\n'
			
			# Homebridge-Camera-FFMPEG
			if config["camera"] > 0:
				cfg +=	'\t\t{\n'		
				cfg +=	'\t\t\t"platform": "{0}",\n'.format('Camera-ffmpeg')
				cfg +=	'\t\t\t"cameras": [\n'
			
				for dev in indigo.devices.iter(self.pluginId + ".Homebridge-Camera"):
					if dev.pluginProps["serverDevice"] != str(server.id): continue
				
					cfg +=	'\t\t\t\t{\n'
				
					cfg +=	'\t\t\t\t\t"name": "{0}",\n'.format(dev.pluginProps["name"])
				
					cfg +=	'\t\t\t\t\t"videoConfig": {\n'
				
					cfg +=	'\t\t\t\t\t\t"source": "{0}",\n'.format(dev.pluginProps["videoSource"])
					cfg +=	'\t\t\t\t\t\t"stillImageSource": "{0}",\n'.format(dev.pluginProps["stillSource"])
					cfg +=	'\t\t\t\t\t\t"maxStreams": {0},\n'.format(dev.pluginProps["maxStreams"])
					cfg +=	'\t\t\t\t\t\t"maxWidth": {0},\n'.format(dev.pluginProps["maxWidth"])
					cfg +=	'\t\t\t\t\t\t"maxHeight": {0},\n'.format(dev.pluginProps["maxHeight"])
					cfg +=	'\t\t\t\t\t\t"maxFPS": {0}\n'.format(dev.pluginProps["maxFPS"])
				
					cfg +=	'\t\t\t\t\t}\n'
				
					config["addons"] = config["addons"] - 1
					config["camera"] = config["camera"] - 1
				
					if config["camera"] == 0:
						cfg +=	'\t\t\t\t}\n'
					else:
						cfg +=	'\t\t\t\t},\n'
				
				
				cfg +=	'\t\t\t]\n'
			
				cfg +=	'\t\t}\n'
			
			cfg += 	'\t],\n\n'
	
			cfg += 	'\t"accessories": [\n'
			cfg += 	'\t]\n'
	
			cfg += 	'}'
		
			self.logger.debug (cfg)			
	
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
		return cfg
			
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
	def getDeviceDisplayStateId(self, dev): return eps.plug.getDeviceDisplayStateId (dev)
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
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	