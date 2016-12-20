# lib.ext - Some useful extended commands and generic exception handler
#
# Copyright (c) 2016 ColoradoFourWheeler / EPS
#

import indigo
import linecache # exception reporting
import sys # exception reporting

plugin = None

#
# Check validity of a value in a dictionary
#
def valueValid (dict, value, ifBlank = False):
	if dict:
		if value != "":
			if value in dict:
				if ifBlank:
					if unicode(dict[value]) != "": return True
				else:
					return True
					
	return False
	
#
# Check validity of a value in a dictionary, setting to the default value if invalid and returning dict - 2.06
#
def validateDictValue (dict, value, default, ifBlank=False):
	try:
		if valueValid (dict, value, ifBlank) == False:
			dict[value] = default
			return dict
				
	except Exception as e:
		printException(e)
		
	return dict
	
#
# Get exception details
#
def getException (e):
	exc_type, exc_obj, tb = sys.exc_info()
	f = tb.tb_frame
	lineno = tb.tb_lineno
	filenameEx = f.f_code.co_filename
	filename = filenameEx.split("/")
	filename = filename[len(filename)-1]
	filename = filename.replace(".py", "")
	filename = filename.replace(".pyc","")
	linecache.checkcache(filename)
	line = linecache.getline(filenameEx, lineno, f.f_globals)
	exceptionDetail = "Exception in %s.%s line %i: %s\n\t\t\t\t\t\t\t CODE: %s" % (filename, f.f_code.co_name, lineno, str(e), line.replace("\t",""))
	
	return exceptionDetail
		
#
# Print exception details
#
def printException (e, logger = None):
	if logger is None:
		if plugin is not None:
			plugin.logger.error (e)
			
		else:
			indigo.server.log (e, isError=True)	
			
	else:
		logger.error (e)