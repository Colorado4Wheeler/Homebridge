Release Notes
==========

Everything is still in BETA.  Some stuff won't work.  Overall the program works, just a few areas that haven't been enabled yet and lots of optimization yet to do.  Make sure you keep a backup copy of your existing config.json file just in case something doesn't work as planned.

Version 0.5
---------------

* NOTE: The first time you reload the plugin under Beta 5 it will migrate your plugin preferences into a new Homebridge Server device located in the Homebridge Companion folder.
* NOTE: Even though you currently CAN create multiple servers, don't!  It's not yet coded in and may cause problems if you try.
* Added actions to the Wrapper to force a device state on/off/brightness in case you have something that can't determine it's own state and need to schedule a turn off for it (my TV Wrapper for instance stays on because the TV doesn't feedback it's current state and since both the On and Off commands for my TV are the same thing I cannot "turn it off" again without actually sending a power command to the TV)
* Removed development template stuff from the Actions.xml
* Added new Homebridge Server device to replace most of the HB plugin prefs.  When you start the plugin after this upgrade the plugin prefs will be migrated into a new Server device.  Plugin prefs now only show the HB parameters that are common to all HB servers
* HB server lists (previously in plugin prefs) are now cached and load considerably faster on field changes
* Fixed UI caching issue where the method was returning false negatives
* Sped up the initial plugin load time
* HB config save no longer excludes all devices that are the child of a Wrapper device in the configuration, it was not needed and just added more data to the config.json needlessly
* Changed logic so that nothing can be excluded unless you select ALL for devices or actions
* Fixed problem where the server device count mis-matched the config saving device counts
* All devices being used with Homebridge are now monitored for any changes to their name (we aren't yet doing anything interesting with them but this is the start of that)
* Removed Switch Wrappers from the plugin entirely now that general Wrappers have taken their place
* The Server devices (really only one device right now) On/Off state will reflect if the Homebridge server is running or not
* Enabled using the Server device's On/Off commands to turn on or off the Homebridge server

Version 0.4
---------------

* Fixed problem with plugin config where re-opening it didn't repopulate the lists properly and left the "treat as" lists empty

Version 0.3
---------------

* UPGRADE NOTE: Delete your old "Switch Wrappers" since those are now defunct, there is now just a universal Wrapper device, the Switch Wrappers are still in Devices.xml for now to prevent any big issues but they mostly don't work and will be removed before the next beta release
* Action groups can now be used in Wrappers
* Added some fields to the wrapper device to help toggle visibility on new devices
* Conditions top menu should now default to "no conditions" for new devices
* Ditched the idea of Switch Wrappers, opting instead to make a single all-encompassing wrapper that is a dimmer device because there was too much that had to be changed between the two devices.  Since Homebridge treats everything as a dimmer by default this works out well.  This means if you created some wrappers you will need to delete them and re-create them using the new device since the old one will be removed before final release.  It's a big boy too, the new Wrappers device is nearly 2,000 lines of XML.
* Wrappers now show their Homebridge type in the address field
* Custom Wrappers can determine their on/off/brightness by using user defined values so if you wanted to, say, fire an action group at brightness level 40 you can configure the device to consider itself at brightness level 40 if, say, a variable value is something particular.  This allows for outside influences on the target device to reflect properly on the Wrapper device
* If a brightness level is not explicitly defined in the device configuration and a brightness command is sent to a Wrapper then the Wrapper will use the device for On to send a brightness change to
* Action configuration "ConfigUI" fields increased to 5 to allow for a wide variety of options on a given command (or plugin action)
* Passthrough removed from Wrappers, it added too much complexity and was no longer needed with the new Wrapper device
* Removed hard coded caching for onOffState that caused warnings in the startup
* Indigo device icons are more reflective of the type of Homebridge device the Wrapper is (within Indigos limited icon library at least)
* Cache now properly flushes after closing a device configuration dialog (this and TONS of other changes to the core factory)
* Wrapper Devices will not send an action if it results in the Wrapper being the same state as before (i.e., it won't turn On again if it's already On) unless the user defined state lookup is set to "No Way To Determine", in which case we'll submit it again since we have no way of knowing if it's really on or off
* Fixed an issue in the main configuration where if you had deleted devices that were previously in any of the lists it would error out, now it will detect those


Version 0.2
---------------

* Changed the version number to better reflect beta status, it's now at 0.2 rather than 1.0
* Selecting Pass Through or Use On State for the off state of switch wrappers now properly hides fields
* Removed "Same as On Method" from Off selection, it was a splitball placeholder anyway
* Code the "Use On Method", that should be working now - basically this just makes off the same as on


Development Notes
==========


Known Issues As Of The Most Current Release
---------------

* Conditions are not yet configured, waiting until the rest of the Switch Wrapper is done and working before adding more complexity
* Everything is getting cached but we aren't doing anything interesting with restarting Homebridge when names or addresses change
* There's no feedback on Homebridge start/stop/restart/save and restart actions, just running in the blind - need to get feedback so we can test for success and failure
* Need to add a way to check if Homebridge is running on the server, right now if you try to start it and it's running it will work because HB is configured to check for itself be we should be doing this ourselves
* Need to watch action groups so we know if one of our On or Off action groups got ran so we can change the device state
* When setting up a new device it doesn't immediately pick up the state of what it is wrapping, it doesn't do that until you change the Wrapper or the device being wrapped
* When creating a new device if you don't go into On AND Off then warnings will log about not being able to find state '', the workaround for now is to make sure you define both On and Off instead of just letting the UI handle it
* Multi I/O (IOLinc) devices don't set defaults like relays, dimmers and sensors in the UI, you have to hand configure the settings
* While the icons are (somewhat) appropriate now, still need to tweak the actual display value since everything is essentially an Indigo dimmer we need the values to reflect the Wrapper type (i.e., open/closed, locked/unlocked, etc)
* After saving a device configuration the default view of the device is supposed to reset to the On config, but it's staying at where ever you left off
* Need to remove Between and Contains from value operators, they won't be in the final release and are not coded in
* Device address not getting updated on device creation
* While the ability to have multiple servers is currently in the UI, it is not yet possible to manage multiple servers

Wish List
---------------

* Variable manipulation as On/Off/Dim commands.  It would be nice to say "turn on Ajax" and have the Ajax variable set itself to whatever you define
* Create a auto-create menu option to create aliases for all HB friendly devices in a special folder to cut down on time to create everything by hand
* Create an option window for running the various support dumps, they are pretty massive in this plugin and could use some fine tuning (general core factory work)
* Create an option window for the different Homebridge commands to shorten up the plugin menu
* Add a cross-plugin callback so that plugins can ask that they be defined as a certain type when included in Homebridge - this will be for when they are NOT wrapped (since wrapping overrides that kind of thing) but rather when they are just generally included.
