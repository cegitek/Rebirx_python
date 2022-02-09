#!/usr/bin/env python3

# Author 	 : Frederic BOMPARD
# Date		 : 23/08/2021
# Compatible : RebirX SERVER 
# email 	 : frederic.bompard@cegitek.com
# Version	 : 1.6
# Python version	: 3.4.3

import socket 
import binascii
import functools
import struct
import os
import time 

BUFFER_SIZE = 2048


class DetectorStatus(object):
	IDLE					= "Idle."
	ACQUIRING				= "Acquiring."
	LOAD_SAVE_CALIBRATION	= "Loading/Saving_calibration."
	CALIBRATING				= "Calibrating."
	DIGITAL_TEST			= "Digital_Test."
	RESETTING				= "Resetting"


class AcqMode(object):
	STANDARD  			= "standard"
	DETECTOR_BURST 		= "detector_burst"
	COMPUTER_BURST 		= "computer_burst"
	STACKING_16BITS 	= "stacking_16_bits"
	STACKING_32BITS 	= "stacking_32_bits"
	SINGLE_BUNCH_16BITS = "single_bunch_16_bits"
	SINGLE_BUNCH_32BITS = "single_bunch_32_bits" 

class OutSignal(object):
	EXPOSURE_BUSY 			= "ExposureBusy"
	SHUTTER_BUSY			= "shutter_busy"
	BUSY_UPDATE_OVERFLOW 	= "busy_update_overflow"
	PIXEL_COUNTER_ENABLED 	= "pixel_counter_enabled"
	EXTERNAL_GATE 			= "external_gate"
	EXPOSURE_READ_ONE 		= "exposure_read_done"
	DATA_TRANSFER 			= "data_transfer"
	RAM_READY_IMAGE_BUSY 	= "RAM_ready_image_busy"
	XPAD_TO_LOCAL_DDR 		= "XPAD_to_Local-DDR"
	LOCAL_DDR_TO_PC 		= "Local-DDR_to_PC"

class TriggerMode(object):
	INTERNAL 				= "internal"
	EXTERNAL_SINGLE_TRIGGER = "external_trigger_single"
	EXTERNAL_MULTI_TRIGGER 	= "external_trigger_multiple"
	EXTERNAL_GATE 			= "external_stack_trigger"
	EXTERNAL_STACK_TRIGGER 	= "external_stack_trigger"


class DetInformation(object):
	SERIAL_NUMBER 			= "serialNumber"
	PART_ID 				= "partid"
	HV_CONSIGNE			 	= "HVConsigne"
	DAC_HV 					= "DacHV"

class CalibrationType(object):
	SLOW 				= "0"
	MEDIUM 				= "1"
	FAST			 	= "2"

class Global_Config(object):
	AMPTP   =  "AMPTP"
	IMFP    =  "IMFP"
	ITOA    =  "ITOA"
	IPRE    =  "IPRE"
	ITHL    =  "ITHL"
	ITUNE   =  "ITUNE"
	IBUFF   =  "IBUFF"


class Xpad_Error(BaseException):
	pass

class XpadCamera:
	def __init__(self,ip,port):
		#DefaultValue
		self.moduleMask  = 0
		self.ImageHeight = -1
		self.ImageWidth  = -1
		self.geometricalCorrectionFlag = True
		self.numberOfImages = 1
		self.expTime = 1000000
		self.waitingTime = 10000
		self.overflowTime = 4000
		self.inputSignal = 0
		self.outputSignal = 0
		self.flatFieldFlag = 1
		self.imageTransfertFlag = 1
		self.outputFormatFile = 0
		self.acquistionMode = 0
		self.nbStack = 1
		self.outputServerFilePath = "/opt/cegitek/tmp_corrected/"				
		self.recvBuffer = ""
		#Main socket
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.connect((ip, port))
		data  = self.sock.recv(BUFFER_SIZE)	

		#status and abort command
		self.sock_status = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock_status.connect((ip, port))
		data = self.sock_status.recv(BUFFER_SIZE)	


	def receiveResponse(self):
		#self.recvBuffer = ""
		try:
			ret = self.sock.recv(1)
			self.recvBuffer = ret
			while ret.decode() != ">":
				ret = self.sock.recv(1)
				self.recvBuffer += ret
		except:
			raise Xpad_Error("ERROR: Socket ERROR.")

	def clearInputMainSocket(self):
		self.sock.setblocking(False)
		try:
			while self.sock.recv(BUFFER_SIZE):
				pass
		except:
			pass
		self.sock.setblocking(True)

	def clearInputStatusSocket(self):
		self.sock_status.setblocking(False)
		try:
			while self.sock_status.recv(BUFFER_SIZE):
				pass
		except:
			pass
		self.sock_status.setblocking(True)

#This function is used to initialisate the detector. 
#The server will read the detector type and model from the configuration
#file that is stored server in the following location: /opt/imXPAD/XPAD_SERVER/detector_model.txt.
#Then the server will perform an AskReady operation to verify that all modules
#in the detector are responding correctly			
	def init(self):
		self.clearInputMainSocket()
		self.sock.send('Init\n'.encode())
		data = self.sock.recv(BUFFER_SIZE)
		
		
		if data.decode().find(">") == -1:
			self.sock.recv(BUFFER_SIZE)
		else:
			data.decode().replace(">","")
			
		self.sock_status.send('Init\n'.encode())
		data = self.sock_status.recv(BUFFER_SIZE)
		
		if data.decode().find(">") == -1:
			self.sock_status.recv(BUFFER_SIZE)
		else:
			data.decode().replace(">","")
			
			
		if self.getAckValue(data) == "0" :
			return True
		else:
			raise Xpad_Error("ERROR: No module Connected status socket.")



	def setDebugMode(self, flag):
		self.clearInputMainSocket()
		
		if flag == True : 
			str_str = "setdebugmode True\n"
		else :
			str_str = "setdebugmode False\n"		
		self.sock.send(str_str.encode())
		self.receiveResponse()
		data = self.recvBuffer
		return self.getAckValue(data)


	def getFirmwareID(self):		
		self.clearInputMainSocket()
		self.sock.send("getfirmwareID\n".encode())
		self.receiveResponse()
		data = self.recvBuffer
		return self.getAckValue(data)		
			
	def close(self):				
		self.sock.send("Exit\n".encode())
		self.sock.close()		
		self.sock_status.send("Exit\n".encode())
		self.sock_status.close()
		
		

	def askReady(self):
		self.clearInputMainSocket()
		self.sock.send("AskReady\n".encode())
		self.receiveResponse()
		data = self.recvBuffer

		if int(self.getAckValue(data)) > -1 :
			return True
		else:
			raise Xpad_Error("ERROR: No module Connected.")
		
#This function allows to retrieve the mask of the modules available in the detector.
#This mask is given as an integer.
#For example, for two modules, the mask in binary will be 0 0 1 1 which decimal interpretation is 3. 		
	def getModuleMask(self):	
		self.clearInputMainSocket()
		self.sock.send("getModuleMask\n".encode())
		self.receiveResponse()
		data = self.recvBuffer
		self.moduleMask = self.getAckValue(data)
			
		return int(self.getAckValue(data))
			
	def getModuleNumber(self):	
		self.clearInputMainSocket()
		self.sock.send("GetModuleNumber\n".encode())		
		self.receiveResponse()
		data = self.recvBuffer
		return int (self.getAckValue(data))


	def resetDetector(self):	
		self.clearInputMainSocket()
		self.sock.send("ResetDetector\n".encode())
		self.receiveResponse()
		data = self.recvBuffer
			
		if self.getAckValue(data) == "0" :
			return True
		else:
			raise Xpad_Error("ERROR: Command not recognized.")

	def getImageSize(self):	
		self.clearInputMainSocket()
		self.sock.send("GetImageSize\n".encode())
		self.receiveResponse()
		data = self.recvBuffer
		return self.getAckValue(data)	

	def receiveImage(self,dataSize):
			bytes_recd = 0
			while bytes_recd < dataSize:
				if bytes_recd == 0 :
					chunks = self.sock.recv(8192)
					bytes_recd = bytes_recd + len(chunks)
				else :
					chunk = self.sock.recv(8192)
					chunks += chunk
					bytes_recd = bytes_recd + len(chunk)
			return chunks

	def digitalTest(self, mode):
		loop = 0
		flagVal = self.geometricalCorrectionFlag
		self.setGeometricalCorrectionFlag(False)
		self.clearInputMainSocket()
		str_str = "DigitalTest " + mode + "\n"
		self.sock.send(str_str.encode())		
		data = self.readOneImage()
		
		tmp = self.sock.recv(BUFFER_SIZE)
		if tmp.decode().find(">") == -1:
			print(tmp)
			self.sock.recv(BUFFER_SIZE)
		else:
			print(tmp)
			tmp.decode().replace(">","")
			

		while(self.getDetectorStatus().find("Idle.") == -1 ):
			loop = loop + 1
			time.sleep(0.2)
			if loop == 10:
				break
				
		self.setGeometricalCorrectionFlag(flagVal)
		if data:
			return data
		else:
			raise Xpad_Error("ERROR => Digital Test")
		
	def getImageHeight(self):
		return self.ImageHeight
		
	def getImageWidth(self):
		return self.ImageWidth	
	
	def readOneImage(self):	
		ImageHeight = 0

		ImageSize        = int(struct.unpack('<i', self.sock.recv(4))[0])	
		self.ImageHeight = int(struct.unpack('<i', self.sock.recv(4))[0])
		self.ImageWidth  = int(struct.unpack('<i', self.sock.recv(4))[0])


		#ABORT DETECTED
		if ImageSize == 0 :
			self.sock.send("OK\n".encode())
			self.receiveResponse()
			data = self.recvBuffer
			
			raise Xpad_Error("Read Image Aborted")

		data = self.receiveImage(ImageSize)
		self.sock.send("OK\n".encode())			
		return bytes(data)
		
		

	def loadConfigG(self,reg,value):	
		self.clearInputMainSocket()
		self.sock.send(("LoadConfigG " + reg + " " + value + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
		return self.getAckValue(data)	

	def readConfigG(self,reg):	
		self.clearInputMainSocket()
		self.sock.send(("ReadConfigG " + reg + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
		return self.getAckValue(data)		

	def ITHLIncrease(self):	
		self.clearInputMainSocket()
		self.sock.send(("ITHLIncrease\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
		if self.getAckValue(data) == "0" :
			return True
		else:
			return False		
		
	def ITHLDecrease(self):	
		self.sock.send("ITHLDecrease\n".encode())
		self.receiveResponse()
		data = self.recvBuffer
		if self.getAckValue(data) == "0" :
			return True
		else:
			raise Xpad_Error("ERROR: Command not recognized.")				
		
	def loadFlatConfigL(self,value):	
		self.clearInputMainSocket()
		self.sock.send(("LoadFlatConfigL " + str(value) + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
		if self.getAckValue(data) == "0" :
			return True
		else:
			raise Xpad_Error("ERROR: Command not recognized.")		
	
	def calibrationOTNPulse(self,otnType):
		self.clearInputMainSocket()
		self.sock.send(("CalibrationOTNPulse " + str(otnType) + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
		ret  = int(self.getAckValue(data))
		if ret == -1:
			raise Xpad_Error("ERROR => Calibration OTN Pulse")
		else :	
			return ret

	def calibrationOTN(self,otnType):
		self.clearInputMainSocket()
		self.sock.send(("CalibrationOTN " + str(otnType) + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
		ret  = int(self.getAckValue(data))
		if ret == -1:
			raise Xpad_Error("ERROR => Calibration OTN")
		else :	
			return ret
			
	def calibrationBeam(self,exposureTime, ITHL_max, calibType):
		try:
			self.clearInputMainSocket()
			self.sock.send(("CalibrationBEAM " + str(exposureTime) + " " + str(ITHL_max) + " " + str(calibType) + "\n").encode())
			self.receiveResponse()
			data = self.recvBuffer
			ret  = int(self.getAckValue(data))
			if ret == -1:
				raise Xpad_Error("ERROR => Calibration Beam")
			else :	
				return ret
		except Xpad_Error as e:
			raise e

	def setExposeParameters(self):
		try:
			cmd = "SetExposureParameters "
			cmd += str(self.nbImages) + " " + str(self.ExpTime) + str(self.waitingTime) + " " + str(self.overflowTime) + " " + str(self.inputSignal) + " " + str(self.outputSignal)
			cmd += " " + str(self.geometricalFlag) + " " + str(self.flatFieldFlag) + " " + str(self.imageTransfertFlag) + " " 
			cmd += str(self.outputFormatFile) + " " + str(self.acquistionMode) + " " + str(self.nbStack) + " " + self.outputServerFilePath + "\n"
			self.clearInputMainSocket()
			self.sock.send(cmd.encode())
			self.receiveResponse()
			data = self.recvBuffer	
			
			ret =  int(self.getAckValue(data))		
			if ret == -1:
				raise Xpad_Error("ERROR: Command not recognized.")
			else :	
				return ret
		except Xpad_Error as e:
			raise e		
			
	def setNumbersOfImages(self,nbImages):
		try:
			self.clearInputMainSocket()
			self.sock.send(("SetImageNumber " + str(nbImages) + "\n").encode())
			self.receiveResponse()
			data = self.recvBuffer
			if self.getAckValue(data) == "0" :
				return True
			else:
				raise Xpad_Error("ERROR: Command not recognized.")	
		except Xpad_Error as e:
			raise e	

	def setExposureTime(self,usTime):
		self.clearInputMainSocket()
		self.sock.send(("SetExposureTime " + str(usTime) + " \n").encode())
		self.receiveResponse()
		data = self.recvBuffer
		if int(self.getAckValue(data)) > -1 :
			return True
		else:	
			raise Xpad_Error("ERROR: Command not recognized.")	


	def startExposure(self):
		self.clearInputMainSocket()
		self.sock.send("StartExposure\n".encode())
		
	def endExposure(self):
		#self.clearInputMainSocket()
		self.receiveResponse()
		return 0
		#data = self.sock.recv(BUFFER_SIZE)
		#if data.decode().find(">") == -1:
			#self.sock.recv(BUFFER_SIZE)
		#else:
			#data.decode().replace(">","")
		#ret = int(self.getAckValue(data))
		#if ret == -1:
			#raise Xpad_Error("ERROR => Exposure")
		#else :	
		#	return ret
		
		
	def getAckValue(self,data):
		ret = data.decode()
		index = 0
		
		tmp = ret.split()
		for j in range (0, len(tmp)-1):
			if tmp[j] == "*" :
				index = j
				break
			elif tmp[j] == "#" :
				index = j
				break
			elif tmp[j] == "!" :
				index = j
				break
		
		if(ret.split()[index] == "*"):
			for i in range(len(ret)):
				if ret[i] == '"':	
					return ret.split('"')[index+1]
			return ret.split()[index+1]
		elif(ret.split()[index] == "#"):
			return ret.split('#')[index+1]
		elif(ret.split()[index] == "!"):
			return ret.split('!')[index+1]

		else:
			raise Xpad_Error("BAD return ACK :",ret)

	
	def getDetectorType(self):	
		self.clearInputMainSocket()
		self.sock.send(("GetDetectorType\n").encode())
		data = self.sock.recv(BUFFER_SIZE)
		if data.decode().find(">") == -1:
			self.sock.recv(BUFFER_SIZE)
		else:
			data.decode().replace(">","")		
		return self.getAckValue(data)

	def getDetectorModel(self):	
		self.clearInputMainSocket()
		self.sock.send(("GetDetectorModel\n").encode())
		self.receiveResponse()
		data = self.recvBuffer	
		return self.getAckValue(data)

		
	def loadGlobalConfiguration(self,fileName):
		fName = fileName + ".cfg"
		if os.path.isfile(fName) :
			fd = open(fName,'r')
			buf = fd.read()	
			fd.close()
			self.clearInputMainSocket()
			self.sock.send("LoadConfigGFromFile\n".encode())		
			
			self.sock.send(struct.pack('i',len(buf)))
			self.sock.send(buf.encode())

			self.receiveResponse()
			data = self.recvBuffer	
			ret = 	int(self.getAckValue(data)) 
			if(ret == -1):
				raise Xpad_Error("ERROR: Command not recognized.")
			else:
				return ret
				
		else :
			raise Xpad_Error("Calibration File does not exist : " +  fileName)
			
	def loadLocalConfiguration(self,fileName):
		fName = fileName + ".cfl"		
		if os.path.isfile(fName) :
			
			fd = open(fName,'r')
			buf = fd.read()	
			fd.close()
			self.clearInputMainSocket()
			self.sock.send("LoadConfigLFromFile\n".encode())			
			self.sock.send(struct.pack('i',len(buf)))
			self.sock.send(buf.encode())

			self.sock.recv(BUFFER_SIZE)
			self.receiveResponse()
			data = self.recvBuffer
			ret = int(self.getAckValue(data))
			if( ret == "1"):
				raise Xpad_Error("ERROR: Command not recognized.")
			else:
				return ret
		else :
			raise Xpad_Error("Calibration File does not exist" )

	def loadCalibration(self,calibrationName):
			try:
				if( self.loadGlobalConfiguration(calibrationName) == 0): 
					self.loadLocalConfiguration(calibrationName) 
			except Xpad_Error as e :
				raise Xpad_Error(e)


	def saveOneConfigG(self,fdout,reg,regVal):
		data = self.readConfigG(reg)
		tab = data.split(';');
		
		if len(tab) != 1:
			ret = True
		else:
			raise Xpad_Error("ERROR => Read Global Register " + reg) 
			
		for i in range (0, len(tab)-1):
			tab[i] = tab[i].replace("_", " ")
			tab[i] = tab[i].replace(":", "")
			
		index = 0
		for i in range (0, len(tab)-1):
			tmp = tab[i].split()
			for j in range (0, len(tmp)-1):
				if tmp[j] == "Module" :
					index = j
					break
			
			mod = int(tmp[index+1])
			mask = 1 << mod			
			fdout.write(str(mask))
			fdout.write(" ")
			fdout.write(str(regVal))
			for j in range (0, 7):
				fdout.write(" ")
				fdout.write(tmp[index+2])
			fdout.write("\n")
		
		
	def saveConfigG(self,fileName):
		fd = open(fileName+".cfg",'w')		
		try :
			self.saveOneConfigG(fd,'AMPTP',31) 
			self.saveOneConfigG(fd,'IMFP',59)
			self.saveOneConfigG(fd,'IOTA',60)
			self.saveOneConfigG(fd,'IPRE',61)
			self.saveOneConfigG(fd,'ITHL',62)
			self.saveOneConfigG(fd,'ITUNE',63)
			self.saveOneConfigG(fd,'IBUFF',64)			
			fd.close()
			return True
		except Xpad_Error as e:
			fd.close()
			raise Xpad_Error(e)
		
	
	def saveConfigL(self,fileName):

		nbMod = int(self.getModuleNumber())
		self.clearInputMainSocket()
		self.sock.send("ReadConfigL\n".encode())
		
		dataSize = int(struct.unpack('<i', self.sock.recv(4))[0])				
		fileSize = int(struct.unpack('<i', self.sock.recv(4))[0])
		buf = self.receiveImage(fileSize)
		self.sock.send("OK\n".encode())			
		
		fd = open(fileName + ".cfl",'w')
		fd.write(buf.decode())
		fd.close()		
			
		self.receiveResponse()
		data = self.recvBuffer	
		if (int(self.getAckValue(data)) == -1):
			raise Xpad_Error("ERROR => load Config L File : " + fileName)
		else :
			return True

	
	def saveCalibration(self,calibrationName):
		try:	
			if(self.saveConfigG(calibrationName)):
				self.saveConfigL(calibrationName )
		except Xpad_Error as e:
			raise Xpad_Error(e)	


	def ITHLDecrease(self):	
		self.sock.send("ITHLDecrease\n".encode())
		data = self.sock.recv(BUFFER_SIZE)
		if data.decode().find(">") == -1:
			self.sock.recv(BUFFER_SIZE)
		else:
			data.decode().replace(">","")
		if int(self.getAckValue(data)) > -1  :
			return True
		else:
			raise Xpad_Error("ERROR: Command not recognized.")

	def getBurstNumber(self):	
		self.clearInputMainSocket()
		self.sock.send("GetBurstNumber\n".encode())
		self.receiveResponse()
		data = self.recvBuffer
		return int(self.getAckValue(data))
	

#This function return the current status of the detector. Six possible states are possible:
	#Idle.
	#Acquiring.
	#Loading/Saving_calibration.
	#Calibrating.
	#Digital_Test.
	#Resetting.
	def getDetectorStatus(self):	
		self.clearInputStatusSocket()
		self.sock_status.send("GetDetectorStatus\n".encode())
		data = self.sock_status.recv(BUFFER_SIZE)
		
		if data.decode().find(">") == -1:
			tmp = self.sock_status.recv(BUFFER_SIZE)
			if tmp.decode().find(">") == -1:
				tmp = self.sock_status.recv(BUFFER_SIZE)
		else:
			data.decode().replace(">","")
		
		try :
			val = self.getAckValue(data)
			return val
		except Exception as e:
			print(e)
			return "ERROR STATUS"


	def abortCurrentProcess(self):	
		self.clearInputStatusSocket()
		self.sock_status.send("AbortCurrentProcess\n".encode())
		data = self.sock_status.recv(BUFFER_SIZE)
		if data.decode().find(">") == -1:
			self.sock_status.recv(BUFFER_SIZE)
		else:
			data.decode().replace(">","")
		return True

	def getImageNumber(self):	
		self.clearInputMainSocket()
		self.sock.send("GetImageNumber\n".encode())
		self.receiveResponse()
		data = self.recvBuffer
		ret =  int(self.getAckValue(data))		
		if ret == -1:
			raise Xpad_Error("ERROR: Command not recognized.")
		else :	
			return ret

	def getExposureTime(self):	
		self.sock.send("GetExposureTime\n".encode())
		data = self.sock.recv(BUFFER_SIZE)
		if data.decode().find(">") == -1:
			self.sock.recv(BUFFER_SIZE)
		else:
			data.decode().replace(">","")
		return int(self.getAckValue(data))

	def getWaitingTimeBetweenImages(self):	
		self.clearInputMainSocket()
		self.sock.send("GetWaitingTimeBetweenImages\n".encode())
		self.receiveResponse()
		data = self.recvBuffer
		ret =  int(self.getAckValue(data))		
		if ret == -1:
			raise Xpad_Error("ERROR: Command not recognized.")
		else :	
			return ret

	def getGeometricalCorrectionFlag(self):	
		self.clearInputMainSocket()
		self.sock.send("GetGeometricalCorrectionFlag\n".encode())
		self.receiveResponse()
		data = self.recvBuffer
		ret =  int(self.getAckValue(data))
		if ret == -1:
			raise Xpad_Error("ERROR: Command not recognized.")
		else :	
			return ret

	def getFlatFieldCorrectionFlag(self):	
		self.clearInputMainSocket()
		self.sock.send("GetFlatFieldCorrectionFlag\n".encode())
		self.receiveResponse()
		data = self.recvBuffer
		ret =  int(self.getAckValue(data))
		if ret == -1:
			raise Xpad_Error("ERROR: Command not recognized.")
		else :	
			return ret

	def getNoisyPixelCorrectionFlag(self):	
		self.clearInputMainSocket()
		self.sock.send("GetNoisyPixelCorrectionFlag\n".encode())
		self.receiveResponse()
		data = self.recvBuffer
		ret =  int(self.getAckValue(data))	
		if ret == -1:
			raise Xpad_Error("ERROR: Command not recognized.")
		else :	
			return ret

	def getDeadPixelCorrectionFlag(self):	
		self.clearInputMainSocket()
		self.sock.send("GetDeadPixelCorrectionFlag\n".encode())
		self.receiveResponse()
		data = self.recvBuffer
		return self.getAckValue(data)
		
	def getImageTransferFlag(self):	
		self.sock.send("GetImageTransferFlag\n".encode())
		self.receiveResponse()
		data = self.recvBuffer
		return self.getAckValue(data)


	def getAcquisitionMode(self):	
		self.clearInputMainSocket()
		self.sock.send("GetAcquisitionMode\n".encode())
		self.receiveResponse()
		data = self.recvBuffer
		return self.getAckValue(data)
		
	def getOutputFileFormat(self):	
		self.sock.send("GetOutputFileFormat\n".encode())
		data = self.sock.recv(BUFFER_SIZE)
		if data.decode().find(">") == -1:
			self.sock.recv(BUFFER_SIZE)
		else:
			data.decode().replace(">","")
		return self.getAckValue(data)
		
	def getOutputFilePath(self):	
		self.clearInputMainSocket()
		self.sock.send("GetOutputFilePath\n".encode())
		self.receiveResponse()
		data = self.recvBuffer
		return self.getAckValue(data)
		
	def getInputSignal(self):	
		self.sock.send("GetInputSignal\n".encode())
		self.receiveResponse()
		data = self.recvBuffer
		return self.getAckValue(data)


	def getOutputSignal(self):	
		self.clearInputMainSocket()
		self.sock.send("GetOutputSignal\n".encode())
		self.receiveResponse()
		data = self.recvBuffer
		return self.getAckValue(data)


	def setOutputSignal(self,val):
		self.clearInputMainSocket()
		self.outputSignal = val
		self.sock.send(("SetOutputSignal " + val + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer	
		if self.getAckValue(data) == "0" :
			return True
		else:
			return False


	def setInputSignal(self,val):
		self.clearInputMainSocket()
		self.inputSignal = val
		self.sock.send(("SetInputSignal " + val + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer.decode()
		if self.getAckValue(data) == "0" :
			return True
		else:
			return False
		
	def setOutputFilePath(self,val):
		self.clearInputMainSocket()
		self.outputServerFilePath = val
		self.sock.send(("SetOutputFilePath " + val + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
		if self.getAckValue(data) == "0" :
			return True
		else:
			raise Xpad_Error("ERROR: Command not recognized.")

	def setOutputFileFormat(self,val):
		self.clearInputMainSocket()
		self.outputFormatFile = val
		self.sock.send(("SetOutputSignal " + val + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
		if self.getAckValue(data) == "0" :
			return True
		else:
			raise Xpad_Error("ERROR: Command not recognized.")
		
	def setAcquisitionMode(self,val):
		self.clearInputMainSocket()
		self.acquistionMode = val
		self.sock.send(("SetAcquisitionMode " + val + " \n").encode())
		self.receiveResponse()
		data = self.recvBuffer
		if int(self.getAckValue(data)) > -1 :
			return True
		else:
			raise Xpad_Error("ERROR: Command not recognized.")
		
	def setImageTransferFlag(self,val):
		self.clearInputMainSocket()
		self.imageTransfertFlag = val
		if(val):
			value = "true"
		else:
			value = "false"
		self.sock.send(("SetOutputSignal " + value + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
		if int (self.getAckValue(data)) > -1 :
			return True
		else:
			raise Xpad_Error("ERROR: Command not recognized.")
		
	def setDeadPixelFlag(self,val):
		self.clearInputMainSocket()
		if(val):
			value = "true"
		else:
			value = "false"
		self.sock.send(("SetDeadPixelCorrectionFlag " + value + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
				
		if int(self.getAckValue(data)) > -1 :
			return True
		else:
			raise Xpad_Error("ERROR: Command not recognized.")
		
	def getAcquisitionMode(self,val):
		self.clearInputMainSocket()
		self.sock.send(("GetAcquisitionMode " + val + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer	
		return self.getAckValue(data)

	def setNoisyPixelFlag(self,val):
		self.clearInputMainSocket()
		if(val):
			value = "true"
		else:
			value = "false"		
		self.sock.send(("SetNoisyPixelCorrectionFlag " + value + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
		if int(self.getAckValue(data)) > -1 :
			return True
		else:
			raise Xpad_Error("ERROR: Command not recognized.")


	def setFlatFieldCorrectionFlag(self,val):
		self.clearInputMainSocket()
		self.flatFieldFlag = val
		if(val):
			value = "true"
		else:
			value = "false"
		self.sock.send(("SetFlatFieldCorrectionFlag " + value + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
		if int(self.getAckValue(data)) > -1 :
			return True
		else:
			raise Xpad_Error("ERROR: Command not recognized.")

	def setGeometricalCorrectionFlag(self,val):
		self.clearInputMainSocket()
		self.geometricalCorrectionFlag = val
		if(val):
			value = "true"
		else:
			value = "false"
			
		self.sock.send(("SetGeometricalCorrectionFlag " + value + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
		if int(self.getAckValue(data)) > -1 :
			return True
		else:
			raise Xpad_Error("ERROR: Command not recognized.")

	def setWaitingTimeBetweenImage(self,val):
		self.clearInputMainSocket()
		self.waitingTime = val
		self.sock.send(("SetWaitingTimeBetweenImages " + val + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
				
		if int(self.getAckValue(data)) > -1 :
			return True
		else:
			raise Xpad_Error("ERROR: Command not recognized.")
		
		
	def setOverFlowTime(self,val):
		self.clearInputMainSocket()
		self.overflowTime = val
		self.sock.send(("SetDeadPixelFlag " + str(val) + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
			
		if int(self.getAckValue(data)) > -1 :
			return True
		else:
			raise Xpad_Error("ERROR: Command not recognized.")


	def createWhiteImage(self,whiteName):
		self.clearInputMainSocket()
		self.sock.send(("CreateWhiteImage " + whiteName + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
			
		if int(self.getAckValue(data)) > -1 :
			return True
		else:
			raise Xpad_Error("ERROR: Command not recognized.")

	def deleteWhiteImage(self,whiteName):
		self.clearInputMainSocket()
		self.sock.send(("DeleteWhiteImage " + whiteName + "\n").encode())
		data = self.sock.recv(BUFFER_SIZE)
		tmp = data.split()
		if(tmp[1] == "0"):
			self.sock.recv(BUFFER_SIZE)					
			return self.getAckValue(data) 
		else:
			data = self.sock.recv(BUFFER_SIZE)
			data = data.split(".")
			return data[0]

	def setWhiteImage(self,whiteName):
		self.clearInputMainSocket()
		self.sock.send(("SetWhiteImage " + whiteName + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
				
		if int(self.getAckValue(data)) > -1 :
			return True
		else:
			raise Xpad_Error("ERROR: Command not recognized.")


	def getWhiteImagesInDir(self):
		self.clearInputMainSocket()
		self.sock.send(("GetWhiteImagesInDir\n").encode())
		data = self.sock.recv(BUFFER_SIZE)
		tmp  = data.split("\"")
		if(tmp[1] == "Empty directory"):
			data = self.sock.recv(BUFFER_SIZE)
			return self.getAckValue(data) 
		else:	
			return self.getAckValue(data)
		
	def readDetectorTemperature(self):
		self.clearInputMainSocket()
		self.sock.send(("ReadDetectorTemperature\n").encode())
		data = self.sock.recv(BUFFER_SIZE)
		return self.getAckValue(data) 
	
	
	def readCtnTemperature(self):	
		self.clearInputMainSocket()
		self.sock.send(("readCtnTemperature\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
		ret = data.decode()
		index = 0
		
		tmp = ret.split()
		for j in range (0, len(tmp)-1):
			if tmp[j] == "*" :
				index = j
				break
		
		if(ret.split()[index] == "*"):
			for i in range(len(ret)):
				if ret[i] == '"':
					return ret.split('"')[1]
					
			return ret.split()[index+1]

		else:
			raise Xpad_Error("BAD return ACK :",ret)
		
	def getDetectorInformations(self,registerName):	
		self.clearInputMainSocket()
		self.sock.send(("GetDetInformation " + registerName + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
		ret = data.decode()
		index = 0
		
		tmp = ret.split()
		for j in range (0, len(tmp)-1):
			if tmp[j] == "*" :
				index = j
				break
		
		if(ret.split()[index] == "*"):
			for i in range(len(ret)):
				if ret[i] == '"':
					return ret.split('"')[1]
					
			return ret.split()[index+1]

		else:
			raise Xpad_Error("BAD return ACK :",ret)
		

	def SetDetectorInformations(self,registerName,value):
		self.clearInputMainSocket()
		self.sock.send(("SetDetInformation " + registerName + " " + value + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
				
		if int(self.getAckValue(data)) > -1 :
			return True
		else:
			raise Xpad_Error("ERROR: Command not recognized.")

	def SetDacHv(self,val):
		self.clearInputMainSocket()
		self.overflowTime = val
		self.sock.send(("SetHvValue " + str(val) + "\n").encode())
		self.receiveResponse()
		data = self.recvBuffer
			
		if int(self.getAckValue(data)) > -1 :
			self.resetDetector()
			return True
		else:
			print("ERROR SetDacHV")
			raise Xpad_Error("ERROR: Command not recognized.")
			

