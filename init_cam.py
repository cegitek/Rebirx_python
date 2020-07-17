# Xpad Camera
from libXpad import XpadCamera
#This is the class exception from XpadCamera library 
from libXpad import Xpad_Error

ip_server='192.168.0.9'
port_server=3456
#Connection of ImXPAD SERVER 
#                     IP          PORT  

xpad = XpadCamera(ip_server,port_server)
xpad.init()
print "Test setAqc mode"

