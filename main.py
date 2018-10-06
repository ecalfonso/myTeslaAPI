import sys

from joinApi import *
from teslaApi import *

# Get and Verify Command Argument
if len(sys.argv) < 2:
	print("No command specified!\n Usage: python3 main.py cmd\n")
	exit()

title, text = apiAccess(sys.argv[1])
joinPush(title, text)
