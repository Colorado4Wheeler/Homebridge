# lib.eps - The factory that starts everything
#
# Copyright (c) 2016 ColoradoFourWheeler / EPS
#

import indigo
import logging

import ext

from plug import plug
from update import update
from ui import ui
from support import support


class eps:
	VERSION = "2.10"
	
	#
	# Initialize the  class
	#
	def __init__(self, plugin):
		if plugin is None: return # pre-loading before init
		
		try:
			self.plugin = plugin
		
			# Sets the log format in the plugin and across all modules that can reference the plugin
			logformat = logging.Formatter('%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s\t%(funcName)-25s\t%(msg)s', datefmt='%Y-%m-%d %H:%M:%S')
			plugin.plugin_file_handler.setFormatter(logformat)
		
			# Sets the localized logger with the module name appended
			self.logger = logging.getLogger ("Plugin.factory")
		
			# Initialize prefs and libraries
			self._prefInit ()
			plugin.indigo_log_handler.setLevel(int(plugin.pluginPrefs["logLevel"]))
			self._libInit ()
		
			# Do any previous generation cleanup
			self._cleanUp(plugin)
		
			# Done with init
			self.logger.threaddebug("EPS Factory {0} initialization complete".format(self.VERSION))
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
		
		
	#
	# See what libraries are needed and initialize them
	#
	def _libInit (self):
		try:
			# Initialize the main plugin engine
			self.plug = plug (self)
			self.update = update (self)
			self.ui = ui (self)
			self.support = support (self)
		
			self.logger.threaddebug("Dynamic libraries complete")
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	#
	# Load libraries
	#
	def loadLibs (self, lib):
		liblist = []
		
		if type(lib) is list:
			liblist = lib
		else:
			liblist = [list]
			
		for lib in liblist:
			if lib == "cache":
				self.logger.threaddebug("Loading cache library")
				from cache import cache #, cacheDev
				self.cache = cache(self)
				
			if lib == "plugcache":
				self.logger.threaddebug("Loading plugin cache")
				from plugcache import plugcache
				self.plugcache = plugcache (self)
				
			if lib == "actions":
				self.logger.threaddebug("Loading actions library")
				from actions import actions
				self.act = actions (self)
				
			if lib == "devices":
				self.logger.threaddebug("Loading device extensions library")
				from devices import devices
				self.devices = devices (self)
								
			if lib == "conditions":
				self.logger.threaddebug("Loading conditions library")
				from conditions import conditions
				self.cond = conditions(self)
				
				# Conditions require plug cache
				if "plugcache" in dir(self):
					if self.plugcache is None:
						X = 1				
				else:
					self.logger.threaddebug("Loading plugin cache")
					from plugcache import plugcache
					self.plugcache = plugcache (self)
					
		self.logger.threaddebug("User libraries complete")
		
	#
	# Initialize the default preferences
	#
	def _prefInit (self):
		# Set any missing prefs
		self.plugin.pluginPrefs = ext.validateDictValue (self.plugin.pluginPrefs, "logLevel", "20", True)
		self.plugin.pluginPrefs = ext.validateDictValue (self.plugin.pluginPrefs, "pollingMode", "realTime", True)
		self.plugin.pluginPrefs = ext.validateDictValue (self.plugin.pluginPrefs, "pollingInterval", 1, True)
		self.plugin.pluginPrefs = ext.validateDictValue (self.plugin.pluginPrefs, "pollingFrequency", "s", True)
		
	#
	# If we are cleaning up from previous generations do that here
	#
	def _cleanUp (self, plugin):
		if ext.valueValid (plugin.pluginPrefs, "debugMode"): 
			self.logger.info(u"Upgraded plugin preferences from pre-Indigo 7, depreciated preferences removed")
			del plugin.pluginPrefs["debugMode"]
				
		
	#
	# Call back a plugin method if it exists
	#
	def raiseEvent (self, method, args):
		retval = None
		
		try:
			if method in dir(self.plugin):
				func = getattr(self.plugin, method)
				
				if len(args) > 0: 
					retval = func(*args)
				else:
					retval = func()
					
		except Exception as e:
			self.logger.error (ext.getException(e))			
			
		return retval
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				