Release Notes
==========

Everything is still in BETA.  Some stuff won't work.  Overall the program works, just a few areas that haven't been enabled yet and lots of optimization yet to do.  Make sure you keep a backup copy of your existing config.json file just in case something doesn't work as planned.

Known Issues
---------------
* The plugin config window is a little slow, there are lots of custom lists being generated so caching needs to get added there
* Conditions are not yet configured, waiting until the rest of the Switch Wrapper is done and working before adding more complexity
* Action groups in Switch Wrappers not yet enabled
* Passthrough works on Switch Wrappers but only for true Indigo relay devices at the moment that respond to turnOn and turnOff
* Everything is getting cached but we aren't doing anything interesting with restarting Homebridge when names or addresses change
* Caching has some hard coded onOffState states it's watching so anything added without that will throw a warning in startup, it's not critical and doesn't impact anything
* Need to create dimmer wrapper - waiting for switch wrapper to be 100% done and tested before getting into that because dimmers are about a thousand times more complicated

Version 0.2
---------------

* Changed the version number to better reflect beta status, it's now at 0.2 rather than 1.0
* Selecting Pass Through or Use On State for the off state of switch wrappers now properly hides fields
* Removed "Same as On Method" from Off selection, it was a splitball placeholder anyway
* Code the "Use On Method", that should be working now - basically this just makes off the same as on
