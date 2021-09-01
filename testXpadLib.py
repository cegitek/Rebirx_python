#!/usr/bin/env python3

#Author 	: Frederic BOMPARD
#Date		: 19 september 2019
#Compatible : RebirX SERVER 3.2.x
#email 		: frederic.bompard@cegitek.com
#Version	: 1.4
#Python version	: 3.4.3

import struct
import sys
import os
import threading
import time

# Xpad Camera
from libXpad import XpadCamera
#This is the class exception from XpadCamera library 
from libXpad import Xpad_Error
from libXpad import AcqMode
from libXpad import TriggerMode
from libXpad import OutSignal
from libXpad import CalibrationType

# This function save raw image in binary int32 by pixels 
def writeRawFile(FileName, data):
	name = FileName + ".bin"
	fd = open(name,'wb')
	fd.write(data)
	fd.close()

#this function save image in text File
def writeDatFile(fileName, height, weight, data):	
	name = fileName + ".dat"
	fd = open(name,'w')
	for h in range(0,height):
		for w in range(0,weight):
			index = h*weight*4+w*4			
			buf = struct.unpack('i', data[index:index+4])
			fd.write(str(int(buf[0])))
			fd.write(" ")
		fd.write("\n")
	fd.close()

def expose():
	#Image Acquisition 
	try :
		nbImage = xpad.getImageNumber()
		print("\n Exposure in progress .....")
		xpad.startExposure()
		for i in range (0,nbImage):
			FName = "Images/test%d" %(i)
			print ("Image Number = %d" %(i))
			try:
				#Read Image
				data = xpad.readOneImage()				
				#Save image
				writeDatFile(FName,xpad.getImageHeight(),xpad.getImageWidth(),data)
				#writeRawFile(FName,data)	
		
			except Xpad_Error as e:# ABORT DETECTED
				print (e)
				break
				
		# End of transmision		
		ret = xpad.endExposure()
		if  ret == 1:
			print ("Exposure Aborted !!!!")
		elif ret == 0: 
			print ("Exposure done !!!!")
	except Xpad_Error as e:
		exposure_flag = False
		print(e)		
	
	
#**********************************************************
#*******              start Program                  ******
#**********************************************************	
os.system('cls' if os.name=='nt' else 'clear')
ip_server='192.168.0.15'
port_server=3456


if not os.path.exists("Images"):
	os.makedirs("Images")

if not os.path.exists("Calib"):
	os.makedirs("Calib")


#Connection of REBIRX SERVER 
#                     IP          PORT  
try:	
	xpad = XpadCamera(ip_server,port_server)
	print("\nConnected on XpadServer:", ip_server, "/ Port:", port_server, "")
except:	
	print ("Can not connect to the Server !!!")
	print ("IP =" ,ip_server, "and Port =",port_server)
	print ("Verify if the server is stated")

try:
	#init parameters of connection
	try:
		xpad.init()
	except:
		print ("ERROR init")
	#Set default value of Acquisition
	try:
		xpad.setGeometricalCorrectionFlag(False)
	except:
		print ("setGeometricalCorrectionFlag init error")
	xpad.setFlatFieldCorrectionFlag(False)
	xpad.setOutputSignal(OutSignal.EXPOSURE_BUSY)
	xpad.getAcquisitionMode(AcqMode.STANDARD)
except e:
	print (e)
	print("ERROR => init ")
	print("Abort or reset detector!!!!!!!!!")
	time.sleep(2)
	
#print type of detector
detector_status = xpad.getDetectorStatus()
print(detector_status)


# Menu 
ans=True
while ans:	
	sys.stdout.flush()
	print ("\n\n**********************************")
	print ("******        MENU          ******")
	print ("**********************************")   
	print ("""
	1. Detecteur status
	2. Ask Ready
	3. Digital Test
	4. Calibration OTN
	5. Calibration OTN Pulse
	6. Calibration Beam
	7. Reset Detecteur
	8. Expose parameters
	9. Start exposure
	10.Save Calibration
	11.Load Calibration
	12.Abort Currrent Process
	13.Help
	14.Asyn Exposure
	15.Read CTN
	0. Exit/Quit
		""")
			
	#print(xpad.getImageHeight, xpad.getImageWidth)
	try:
		ans=input("What would you like to do ?  " )	
		if type(ans) == int:
			ans = str(ans)	
	except:
		continue
		
	
	os.system('cls' if os.name=='nt' else 'clear')
	print(ans)
	print("\n")
	detector_status = xpad.getDetectorStatus()
	os.system('cls' if os.name=='nt' else 'clear')
	# Detector free or close program or abort process asked 
	if 'Idle.' in  detector_status or ans=="0" or ans=="12":
		
		if ans=="1": 
			# Check the camera status
			print ("Detector Status is :",detector_status)
			# Check the numbers of module respond
			
		elif ans=="2":
			if xpad.askReady(): 	
				ret = xpad.getModuleNumber()
				print ("Numbers of modules activated :", ret) 
			else:
				print ("ERROR => ask Ready")
				
		elif ans=="3":
			# Test digital part of camera
			try:
				fname = "DigitalTest"
				print("Digital Test in progress")
				buf = xpad.digitalTest("gradient")
				writeDatFile(fname,xpad.getImageHeight(),xpad.getImageWidth(),buf)
				print("Digital Test Done !!!")
				print("File saved in :", fname) 
			except Xpad_Error as e:
				print(e)
				
		elif ans=="4":
			# Make the Over the noise calibration 
			print("Calibration OTN in progress")
			try:
				ret = xpad.calibrationOTN(CalibrationType.SLOW)
				if(ret == 0):
					print("Calibration OTN Done !!!")
				elif(ret == 1):
					print("Calibration OTN Aborted !!!\n")
			except Xpad_Error as e:
				print(e)
				
		elif ans=="5":
			# Make the Over the noise calibration with pulse recomanded
			print("Calibration OTN Pulse in progress")
			try:
				ret = xpad.calibrationOTNPulse(CalibrationType.SLOW)
				if(ret == 0):
					print("Calibration OTN pulse Done !!!")
				elif(ret == 1):
					print("Calibration OTN pulse Aborted !!!")
			except Xpad_Error as e:
				print(e)
						
		elif ans=="6":
			#Make beam calibration, minimum hits by pixels ~1000 	
			exptime  = input("What would you like expose time in us  = " )
			th_max   = input("What would you like th max max value 100 = " )
			cal_type = input("What would you like speed of preample (default 1) : " )
			
			print("\n Calibration Beam in progress")
			try :
				ret = xpad.calibrationBeam(int(exptime),int(th_max), cal_type)
				if(ret == 0):
					print("Calibration Beam Done !!!")
				elif(ret == 1):
					print("Calibration Beam Aborted !!!")
			except Xpad_Error as e:
				print(e)
		
		elif ans=="7":
			# Reset the detector
			try:
				xpad.resetDetector() 
				print ("Reset Detector done !!!!")
			except Xpad_Error as e:
				print(e)	
							
		elif ans=="8":
			# Set the main parameters of acquisition
			exptime  = input("What would you like expose time in us  = " )
			xpad.setExposureTime(int(exptime))
			nbImages = input("What would you like Numbers of images = " )		
			xpad.setNumbersOfImages(int(nbImages))
		 
		elif ans=="9":
			expose()
		elif ans=="10":
			#Save the calibration File
			Name  = input("What would you like Calibration name : " )
			FileName = "Calib/" + str(Name)
			try:
				xpad.saveCalibration(FileName)
				print ("Save Calibration done !!!!")	 
			except:
				print(e)

		elif ans=="11":
			#load the calibration File
			Name  = input("What would you like Load Calibration name : " )
			FileName = "Calib/" + Name
			print("Load Calibration in progress .....")
			try:
				xpad.loadCalibration(FileName) 
				print ("Load Calibration done !!!!")	 
			except Xpad_Error as e:
				print(e)
				
		elif ans=="12":		
			#Abort process Current process( Calibration, Acquisition
			if xpad.abortCurrentProcess() :
				print ("abort Current Process done !!!!")
			else:
				print("ERROR => abort Current Process !!!")
				
		elif ans=="13":		
			#Print Help menu
			print ("\n\nHelp menu : ")
			print ("For more information about Documentation_RebirX_Server.pdf:")
			

		elif ans=="14":
		
			t1 = threading.Thread(target=expose)
			t1.start()
			detector_status = xpad.getDetectorStatus()
			
			#check detector status 
			while 'Idle.' in  detector_status:
				detector_status = xpad.getDetectorStatus()
				time.sleep(0.1)
				pass
			
			while True:
				detector_status = xpad.getDetectorStatus()
				if 'Idle.' in  detector_status:
					print ( "Detector is free ")
					break
				else:
					print("Detector status = ",detector_status)
				
				time.sleep(1)
		
			print("Waiting the TCP transfert !!!!") 
			t1.join()
		elif ans=="15":
			ret = xpad.readCtnTemperature()
			value = ret.split(';')	
			for jj in range (0, len(value)-1):
				print(value[jj].split('=')) # or print(value[jj].split('=')[1])
				

		elif ans=="0":
			#Close the menu
			print("\n Goodbye") 
			break
		else:
			print("\n Not Valid Choice Try again") 
	
	else:
		print("\nDetector BUSY !!!")
		print("Status is : ", detector_status, "!!!")
		print("Try later or Abort current process.")
		 
	ans = True	

#disconnect from server
xpad.close()
print("CLOSE TCP CONNECTION")






