Release Notes
==========

This latest version is Release Candidate status, barring any significant issues this will represent version 1.0 of the plugin.  Make sure you keep a backup copy of your existing config.json file just in case something doesn't work as planned.

Version 0.20 (Version 1.0 RC8)
---------------

* Added support for motion sensors (as per HB-Indigo issue 15) to aliases, wrappers and the server configuration
* Released with latest HB-Indigo build to incorporate motion sensors
* Fixed bug with aliases where dimmers were properly turning on and off but switches were not

Version 0.19 (Version 1.0 RC7a)
---------------

* Changed plugin caching routine to add a bit more debugging and to not "raise" it's exception when it encounters one - this to specifically address Durosity's and one other users issue when starting HBB and getting XML errors for other plugins

Version 0.18 (Version 1.0 RC7)
---------------

* Fixed bug where saving a custom configuration was not retaining any customization done outside of the plugin
* Added new Guest Server device that will allow you to mirror a given server and exclude items you may want to share with a guest or roommate (or spouse) to make it simpler or more secure without sacrificing your preferred HomeKit configuration.  The concept of this is that you essentially duplicate one of your other servers that you can exclude items from and run it as a new HB instance that they can either add on their own to HomeKit or your can share to them.


Version 0.17 (Version 1.0 RC6c)
---------------

* Fixed bug where changing the HB user name would not take and instead the name would be generated automatically when saving the server config

Version 0.16 (Version 1.0 RC6b)
---------------

* Added menu option to output the log file for the built-in server selected
* Added menu option to output the config file for the built-in server selected

Version 0.15 (Version 1.0 RC6a)
---------------

* Bug squashed where HBB would try to reference a config.json on a custom server even if none existed
* Bug squashed where the configuration validation would look for a key field that doesn't exist on a custom server


Version 0.14 (Version 1.0 RC6)
---------------

* IMPORTANT CHANGE: Installing this version will utilize the new built-in version of HB and HB-Indigo and will effectively wipe out your current HomeKit database!  It is advised that before you re-add your Homebridge to HomeKit that you remove ALL of your current accessories tied to HomeBridge from your preferred HomeKit app so that you are starting with a clean slate.
* NOTE: Since Homebridge-Indigo won't be run on the hand-installed version of Homebridge any longer you may want to run "sudo npm uninstall -g homebridge-indigo"
* Added complete Homebridge and Homebridge-Indigo builds to the plugin pre-compiled and ready to run, as of this version you will no longer need to manually install Homebridge or Homebridge Indigo unless you want to incorporate non-Indigo Homebridge plugins
* Added new device called Homebridge Custom Server which will use the manually installed ~/.homebridge configuration and will NOT be used for Indigo devices.  This is for advanced users that want to use a custom 3rd party Homebridge plugin.  This is more or less the direct device replacement for RC5 and earlier installations.
* Changed the device Homebridge Server to become Homebridge Indigo Server as it's only purpose will be to serve Indigo devices to HomeKit and is 100% managed by the plugin.  It's just easier to let the plugin manage everything about the Indigo experience, but if you want to use Homebridge-Indigo on your custom server you can simply create an Indigo Server that never starts so you can copy and paste your ID's manually to your custom server.
* Added option to add to new HB-Indigo feature for inverting on and off commands in server configuration
* Added checkbox to Alias devices to invert the on and off commands for the device to utilize new HB-Indigo feature.  This was not added to Wrappers since they are hand configured anyway.
* Added Alias action to enable or disable the device commands
* Added migration routine that, upon starting RC6 for the first time, will automatically split your Homebridge servers up into Custom and Indigo server devices so you don't have to manually split your old configuration
* Changed Camera-FFMPEG device to only allow the user to select a custom server, not the built-in server
* Added ability for the plugin to merge accessories and platforms from the current ~/.homebridge/config.json file so long as they don't include Homebridge-Indigo or Homebridge-Camera-FFMPEG platforms - this effectively allows you to allow HBB to write your config file while also keeping your own custom platforms and accessories intact
* Changed the advanced settings of a Server device to only show the HB user as a field that can be manually changed since the plugin now handles all aspects of HB-Indigo
* Added tool tip warnings to the "Show Advanced Options" warning the user about changing those fields
* Added routine that will automatically assign a unique username and port to any Server device created
* Added new routine that automatically creates a new HB instance in the built-in build for the server that is currently starting in the plugin
* Added option in the Server device to start and stop Homebridge automatically upon loading and unloading the plugin.  If enabled then HB will stop itself when you unload the plugin and restart when you load the plugin, if you want to keep HB running regardless of if the plugin is running or not then disable this option and HB will continue to run even if you shut down HBB and/or Indigo.

Version 0.13 (Version 1.0 RC5)
---------------

* Changed the server web password field to be character hidden in the plugin configuration
* Unlocked the PIN field so the PIN could be changed if a user desires
* Added MANUAL addition of Homebridge-Camera configuration - this does not yet incorporate the actual plugin itself but allows the user to define a device that modifies the configuration file to utilize an already installed Homebridge-Camera configuration


Version 0.12 (Version 1.0 RC4)
---------------

* Expanded experimental HB-Indigo status updates to apply to Alias devices
* Added JSON exchange with HB-Indigo for more real-time updating

Version 0.11 (Version 1.0 RC3)
---------------

* Fixed oversight where a programming debug message of "P A U S E D" was being displayed when you resumed a sprinkler Alias
* Added ability to notify Homebridge-Indigo of device changes in Indigo so it can immediately poll Indigo for a status - this should make it more responsive and accurate.  You MUST enabled this in PLUGIN configuration to use it and have installed the experimental version of HB-Indigo to utilize it!
* Started coding on using Variables in Wrappers, just some of the basic code is there and not yet visible to the public as an option


Version 0.10 (Version 1.0 RC2)
---------------

* Added a new stripped down "Alias" device.  The Wrapper was originally intended to offer an easy way to rename Indigo devices but evolved into a much more complicated device that allows you to create complex devices for Homebridge, the Alias is stripped down and does nothing more than give you the ability to rename an Indigo device for the sake of Homebridge.
* Added special handling if an Alias device is a sprinkler to allow on/off and dim commands to control the sprinklers and each attached zone
* Added Auto Schedule to sprinkler Alias devices that will automatically set the durations to match whatever the last run schedule was (it will not remember if NO schedule was run and the max durations were used).  If a "zone schedule" is run on it's own this will also be ignored so as not to change the controller or zone durations as the result of running a special one-off schedule
* Added Auto Manage to sprinkler Alias devices that will create and maintain all zones attached to a sprinkler device if selected
* Added plugin configuration options to assist in controlling Sprinkler Aliases where you can set the brightness level of a Sprinkler Alias and it will either convert that to a percentage of the configured schedule, a percentage of max duration or a percentage of 100 minutes (allowing you to turn the brightness on to 20% and that equates to watering for 20 minutes)
* Fixed omission where a device on/off action was set to "do not implement" would cause an error (i.e., you turn On a device that has Do Not Implement would result in an error instead of successfully turning the device on)
* Fixed issue where sprinkler controllers would not display the fields for determining when the device is in that state (i.e., device is On when state XYZ = True)

Core Package Changes:

* Fixed bug where certain conditions could prevent the library from caching a watched state on devices that were cached for another reason (i.e., attributes)

Version 0.9 (Version 1.0 RC1)
---------------

* Fixed a typo in the code that would throw an error when deleting a device

Core Package Changes:

* Enable Duration and Delay By as fields when controlling a dimmer or relay device
* Allow using .UI states to determine on/off/dim state

Version 0.8 (Beta 8)
---------------

* NOTE: There is a minor glitch from some of the UI work done in the previous beta where a change in the status of a wrapped device may not get reflected in the wrapper, just go into each device and if you don't see any of the fields unlocked simply select the server again to show them then save the device, this should resolve the issue
* Resolved an issue where changing a Wrapper type didn't change it's address or icon properly
* Added ability that when a Wrapper type is changed it will re-save the config and queue a HB restart
* Reorganized the methods in the plugin.py, so the Git change history will look like a lot more happened than actually did
* Added plugin config options to control when automatic HB restarts happen
* Fixed an issue where when creating a new device if you don't go into On AND Off then warnings will log about not being able to find state '' because the other state parameters were empty
* Added ability to save and restart Homebridge if a monitored device is deleted from Indigo (Wrapper or otherwise)
* Tentatively renamed Homebridge Companion to Homebridge Buddy because the longer name made it hard to read the debug logs :).  This name may stick, maybe not, but I can read the logs now so for the moment I don't care.
* Wrapper devices will now properly set the default values for an IO device's On state
* Fixed issue where device address was not getting updated on device creation
* Got remote (and multiple) servers running after a lot of fiddling around to get a second copy of HB running (the trick is in the config file, something the plugin will handle - getting additional copies of HB installed and ready on other computers is no different than Webdeck's instructions)
* Rewrote the routine to check on Homebridge's current running status and streamlined the process considerably
* Homebridge process status is now much more accurate by checking for when the listening port is active rather than if the process is running - a much better indicator that HB is ready to receive commands or not
* Moved the gigantic development menu item to the bottom of the list and renamed it to Development Sandbox (this may stick around into the release phase since it's pretty handy to have for testing)
* Set the 'secure' flag on the remote server password field in server config
* Added a second password field in the Server config since the field value gets hidden by Indigo just to make sure the user typed it the same way twice
* Changed the Start, Stop and Restart menu items to show a list of servers
* Start, Stop and Restart menu items will control "local" and remote servers
* On startup the plugin will raise an error if there is a non-local HB server and the Indigo address is set for a loopback (localhost or 127.0.01)
* Removed Name from the server configuration, the HB config will use the name of the Server Device instead
* Made the Server PIN a read-only field, it will remain the same for all HB servers
* Save & Reload will now prompt for the server and perform the action locally or remotely
* NOTE: Save, Reload and Save & Reload all may cause Indigo plugin timeouts because of the time it takes for SSH to do it's thing, this should be OK but could cause confusion in end users, may require action groups to perform tasks on remote servers instead to avoid this but for now I'm not going to sweat it
* All automatic save/start/stop/reload actions for Homebridge pointed to new local/remote routines
* Fixed bug where the device state would change but the Wrapper device icon would not reflect the change properly
* Deleting a Server device will automatically re-home all attached Wrapper devices to the next Server device in Indigo if there is one, if there isn't then the Wrappers server will be set to nothing.  In either case the event log will show the devices being changed as a result of a server getting removed.
* Fixed bug in Server config that could generate an error if during list generation no wrappers were found that were assigned to the server
* Added ability to change the HB user name if needed - shouldn't be needed except in strange circumstances where there is a duplicate user on the HB network since we auto generate the user when the server is added but it's there just in case
* Adding a new server will now automatically assign the address of "SERVER @ Indigo Server" or "SERVER @ [ip address]" so it's easy to distinguish in the Indigo device list
* Changed Wrapper addresses to include the server name
* Added validation to Server device config to make sure that a remote server login is successful and that the user is not trying to create a duplicate Server device in Indigo
* Added server commands to the device actions (Start, Stop, Reload, etc).  One big benefit of this in a multiple HB server environment is that you can have an action on one server that restarts others - a handy use might be to put all security on one HB server and then you can tell Siri to turn that server off so there is no chance of it getting compromised by a hacker.


Version 0.7 (Beta 7)
---------------

* When a new Wrapper device is created it will raise an event telling it's connected Server Device to save the configuration and restart Homebridge in 5 minutes (giving the user time to add other devices, each add while the server is pending adds 5 minutes if the time remaining is less than 2 minutes)
* Creating a new Wrapper device will correctly set the address of the device (until now it was only being set when the plugin got restarted)
* NOTE TO SELF: Beta 6 was not tested well enough, several serious bugs popped up after releasing - bad developer...
* Fixed oversight bug from beta 6 that disabled the plugcache and generated errors when creating a new Wrapper device when it tried to find the available actions for that device
* Fixed a beta 6 bug that when adding the new server selection it broke the form automation where it would automatically select the default ON for on and OFF for off for a new Wrapper device
* Fixed a beta 6 issue where I forgot to tell a changed server config to SAVE before it restarted

Version 0.6 (Beta 6)
---------------

* The Server Wrapper will now automatically detect when the name of a device or action group it is managing has changed and schedule a restart of the Homebridge process in 1 minute, this will be extended by another minute if another name change is detected within 20 seconds of the restart just in case the user is changing the names of multiple devices
* The Server Wrapper will now detect if its configuration has changed and automatically restart the Homebridge process upon exiting the config dialog if it did
* Added a check for any Action Group name changes to raise an event to restart the Homebridge server(s) impacted by the name change
* Removed conditions from Wrappers as upon consideration I cannot think of any reason why a condition should be applied to a Wrapper
* Removed value operators Contains, Not Contains, Between and Not Between from Wrappers as they are not evaluated
* Fixed an issue where Not In was not being evaluated as an operator
* Fixed an issue with the server health check where it updated states on every pass (i.e., every concurrent thread run) needlessly
* Removed "Please select a device type" from the Wrappers combobox since the addition of the server selection negated the need to use that as a way to force the callback to run and set the device defaults
* Fixed an issue where after saving a device configuration the default view of the device is supposed to reset to the On config, but it instead stayed where you left off when you saved your configuration
* Fixed an issue where after saving a Server Wrapper the default view would not reset back to the server configuration


Version 0.5 (Beta 5)
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

Version 0.4 (Beta 4)
---------------

* Fixed problem with plugin config where re-opening it didn't repopulate the lists properly and left the "treat as" lists empty

Version 0.3 (Beta 3)
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


Version 0.2 (Beta 2)
---------------

* Changed the version number to better reflect beta status, it's now at 0.2 rather than 1.0
* Selecting Pass Through or Use On State for the off state of switch wrappers now properly hides fields
* Removed "Same as On Method" from Off selection, it was a splitball placeholder anyway
* Code the "Use On Method", that should be working now - basically this just makes off the same as on


Development Notes
==========


Known Issues As Of The Most Current Release
---------------

* When setting up a new device it doesn't immediately pick up the state of what it is wrapping, it doesn't do that until you change the device being wrapped or the state/attribute/variable that defines that state
* While the icons are (somewhat) appropriate now, still need to tweak the actual display value since everything is essentially an Indigo dimmer we need the values to reflect the Wrapper type (i.e., open/closed, locked/unlocked, etc) - note, this is not possible until the API changes since modifying the deviceState value cannot be done on non-custom Indigo devices
* Copying a device does not raise a new device event, therefor it does not auto-restart Homebridge - this is low priority because typically someone would then change the name of the device which DOES queue a restart
* setServerRestart doesn't seem to pass the description on new Wrapper devices
* Uploading a config to a remote computer is a little slow and Indigo will time out on ConfigUI actions, need to find a good way to upload that more efficiently - it works now so somewhat low priority
* Some devices (such as WeatherSnoop) build their states dynamically in the plugin, so on these devices it is impossible to resolve their full state descriptions and we will end up with the raw state name instead - nothing can be done about this at the moment
* When using a sprinkler device as an alias some advanced handling isn't supported such as changing zones mid-schedule, it will count down the percentage of time remaining based on the original schedule, the same applies to pausing and then resuming a schedule
* Certain conditions may cause Sprinkler Alias device icons to stick in an ON state even though it is off
* Not all Alias types are enabled yet, currently the Alias only supports Dimmer, Relay and Sprinkler devices (the rest are coming, just not yet ready)
* Plugin configuration options for how to treat Sprinkler Alias brightness currently only controls when a brightness level is set but should also control what is displayed in the Indigo list
* When selecting an irrigation controller as a Wrapper device it does not default to the correct "default" action
* Guest Server device currently does not support using a server that specified ALL in devices or actions, use of this device is currently dependent upon having hand-selected your devices and actions and/or using wrappers and alias devices
* Need to check alias device on/off commands, only dimmers were specifically accounted for and this caused problems with switches, need to check all remaining alias types to see if any others have problems
* When added to wrapper devices, motion sensors don't show any actions, they should show on and off commands

User Requested 3rd Party Integrations
---------------

* iTunes
* Netatmo Weather Station
* Foscam
* Envisalink

Wish List
---------------

* Watch action groups so we know if one of our On or Off action groups got ran so we can change the device state
* Variable manipulation as On/Off/Dim commands.  It would be nice to say "turn on Ajax" and have the Ajax variable set itself to whatever you define
* Create a auto-create menu option to create aliases for all HB friendly devices in a special folder to cut down on time to create everything by hand
* Create an option window for running the various support dumps, they are pretty massive in this plugin and could use some fine tuning (general core factory work)
* Create an option window for the different Homebridge commands to shorten up the plugin menu
* Add a cross-plugin callback so that plugins can ask that they be defined as a certain type when included in Homebridge - this will be for when they are NOT wrapped (since wrapping overrides that kind of thing) but rather when they are just generally included.
* Have Homebridge restart if a device wrapped device is added
* Add ability to have a Wrapper run something for each percentage of a brightness requested - i.e., an amplifier that is controlled via I/R if told to set to 50% will run the command to send that I/R as many times as is needed to get to 50%
* User request: Being able to mass ignore based on criteria (i.e., ignore all devices of a certain type)
* When the plugin is first installed have it automatically assume an Indigo server based HB server and create that device so users don't have to
* Get the various HB commands to run in the background and return back to Indigo right away so that the plugin doesn't time out, this will also allow for those various commands to include "All Servers" as an option instead of doing them each one-by-one
* Finish testing and implementation of Homebridge installation in the plugin
* Expand on/off/dim detection for Wrapper devices to include device attributes/properties instead of just states
* Add field to all devices to let the user select the icon values they want to use
* For menu options if they have just one server then default to that server instead of presenting a list 
* Automatically back up 3 generations of the config.json file whenever overwriting it - this also helps new users that already had HB running
* Add failsafe to Homebridge migration routine to check for a duplicate server name and loop through possible iterations until successful
