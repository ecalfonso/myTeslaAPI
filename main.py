import sys

from joinApi import *
from teslaApi import *

# Get and Verify Command Argument
if len(sys.argv) < 2:
	print("No command specified!\n Usage: python3 main.py cmd\n")
	exit()

retval = apiAccess(sys.argv[1])

if retval == 1:
	joinPush("TeslaAPI Failure!", sys.argv[1])
else:
	joinPush("TeslaAPI Success", sys.argv[1])
