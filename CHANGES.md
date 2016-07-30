Release Notes
==========

Everything is still in BETA.  Some stuff won't work.  Overall the program works, just a few areas that haven't been enabled yet and lots of optimization yet to do.  Make sure you keep a backup copy of your existing config.json file just in case something doesn't work as planned.

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

* In my environment (and this could be the result of just development, still investigating) when I went back into the plugin config all of the "treat as" lists showed nothing at all.  Worst case scenario they can be re-assigned again since it's easy to do but I need to get to the root of the problem and fix it
* The plugin config window is a little slow, there are lots of custom lists being generated so caching needs to get added there
* Conditions are not yet configured, waiting until the rest of the Switch Wrapper is done and working before adding more complexity
* Everything is getting cached but we aren't doing anything interesting with restarting Homebridge when names or addresses change
* Anything NOT a Wrapper device isn't currently being cached for changes to name or address
* There's no feedback on Homebridge start/stop/restart/save and restart actions, just running in the blind - need to get feedback so we can test for success and failure
* Need to add a way to check if Homebridge is running on the server, right now if you try to start it and it's running it will work because HB is configured to check for itself be we should be doing this ourselves
* Need to watch action groups so we know if one of our On or Off action groups got ran so we can change the device state
* When setting up a new device it doesn't immediately pick up the state of what it is wrapping, it doesn't do that until you change the Wrapper or the device being wrapped
* When creating a new device if you don't go into On AND Off then warnings will log about not being able to find state '', the workaround for now is to make sure you define both On and Off instead of just letting the UI handle it
* Multi I/O (IOLinc) devices don't set defaults like relays, dimmers and sensors in the UI, you have to hand configure the settings
* While the icons are (somewhat) appropriate now, still need to tweak the actual display value since everything is essentially an Indigo dimmer we need the values to reflect the Wrapper type (i.e., open/closed, locked/unlocked, etc)
* The device count shown in save config doesn't match the device count showin in the plugin config UI - its only off by one or two but need to tighten that up
* After saving a device configuration the default view of the device is supposed to reset to the On config, but it's staying at where ever you left off

Wish List
---------------

* Variable manipulation as On/Off/Dim commands.  It would be nice to say "turn on Ajax" and have the Ajax variable set itself to whatever you define
* Speed up the Wrapper Device configuration form, it's a little slow because of so many calculations.  Why?  Because in order to "alias" or "wrap" a device for Homekit you need to make sure you mirror every aspect of that device so when you use Homekit enabled applications (like Eve) it shows you the current and correct state for your device - that takes some UI magic.
* Create a auto-create menu option to create aliases for all HB friendly devices in a special folder to cut down on time to create everything by hand
* Create an option window for running the various support dumps, they are pretty massive in this plugin and could use some fine tuning (general core factory work)
* Create an option window for the different Homebridge commands to shorten up the plugin menu

