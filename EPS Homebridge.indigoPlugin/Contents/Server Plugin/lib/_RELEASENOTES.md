Release Notes
==========

Until 2.3.1 these changes were pseudo logged elsewhere, this represents the official library release notes since then.

Version 2.3.1
---------------

* Changed a devices divide by zero exception by checking for a zero/null condition before trying to calculate runtime percentage in runConcurrentThread (found in Homebridge Buddy, distributed change with 1.0.6)
