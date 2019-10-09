#
# getKeys.py - use pwndfu to get IV and key associated with firmware KBAGs
#
# use --csv option to write output to csv file
#
# made by dayt0n
#

import os
import sys
import subprocess
import time
from zipfile import ZipFile
import plistlib
import shutil
import csv

class Stats(): # plist stuff
	deviceClass = -1
	def __init__(self,manifest):
		self.manifest = manifest
		fp = open(manifest,'rb')
		if fp:
			self.plistobj = plistlib.readPlist(fp)
		else:
			return -1

	def getBuildNumber(self):
		ids = self.plistobj["BuildIdentities"][0]
		info = ids['Info']
		return str(info['BuildNumber'])

	def getVersion(self):
		ids = self.plistobj["BuildIdentities"][0]
		return str(ids['ProductMarketingVersion'])

	def getAvailableDeviceClasses(self):
		ids = self.plistobj["BuildIdentities"]
		classes = []
		for i in ids:
			iclass = i['Info']['DeviceClass']
			if iclass not in classes:
				classes.append(iclass)
		return classes

	def getDeviceClass(self):
		ids = self.plistobj["BuildIdentities"][self.deviceClass]
		classes = []
		return str(ids['Info']['DeviceClass'])

	def getFirmwareLocations(self):
		locs = {}
		if self.deviceClass < 0:
			print("Error parsing plist")
			return -1
		ids = self.plistobj["BuildIdentities"][self.deviceClass]
		#print("Gathering info for " + ids['Info']['DeviceClass'])
		man = ids['Manifest']
		locs['logo'] = man['AppleLogo']['Info']['Path']
		locs['chg0'] = man['BatteryCharging0']['Info']['Path']
		locs['chg1'] = man['BatteryCharging1']['Info']['Path']
		locs['batF'] = man['BatteryFull']['Info']['Path']
		locs['bat0'] = man['BatteryLow0']['Info']['Path']
		locs['bat1'] = man['BatteryLow1']['Info']['Path']
		locs['glyP'] = man['BatteryPlugin']['Info']['Path']
		locs['dtre'] = man['DeviceTree']['Info']['Path']
		locs['krnl'] = man['KernelCache']['Info']['Path']
		locs['illb'] = man['LLB']['Info']['Path']
		locs['recm'] = man['RecoveryMode']['Info']['Path']
		locs['rdsk'] = man['RestoreRamDisk']['Info']['Path']
		#locs['sepi'] = man['RestoreSEP']['Info']['Path']
		locs['ibec'] = man['iBEC']['Info']['Path']
		locs['ibss'] = man['iBSS']['Info']['Path']
		locs['ibot'] = man['iBoot']['Info']['Path']
		return locs

def chooseDeviceClass(stat):
	classes = stat.getAvailableDeviceClasses()
	for i in range(len(classes)):
		print("[" + str((i+1)) + "] " + classes[i])
	dev = input("Which device are you using?: ")
	if dev < len(classes):
		return dev-1
	else:
		print("Incorrect input")
		sys.exit(-1)

def isValidIPSW(ipsw):
	with ZipFile(ipsw,'r') as obj:
		nameList = obj.namelist()
		if "BuildManifest.plist" in nameList:
			# this is a valid iOS firmware update file
			obj.extract("BuildManifest.plist")
			return True
		else:
			print("This does not look like a valid iOS firmware update file")
			return False

def extractIPSW(ipsw,outdir):
	if os.path.exists(outdir):
		print("Firmware already extracted")
		return 0
	print("Extracting firmware...")
	with ZipFile(ipsw,'r') as obj:
		obj.extractall(outdir)
	return 1

def getKBAGS(firmDir,locs):
	kbags = {}
	for key in locs:
		try:
			p = subprocess.Popen(['img4','-i',firmDir+'/'+locs[key],'-b'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
			p = p.strip().split('\n')
			if p[0] != '':
				kbags[key] = p[0]
		except:
			pass
	return kbags

writeout = False
csv_file = ''
csv_writer = ''
if len(sys.argv) < 2:
	print("Incorrect usage\nusage: %s [ipsw] [--csv]" % sys.argv[0])
	sys.exit(-1)
if (len(sys.argv) == 3) and (sys.argv[2] == "--csv"):
	writeout = True
ipsw = sys.argv[1]

if not isValidIPSW(ipsw): # check if we can actually work with this
	sys.exit(-1)

stat = Stats("BuildManifest.plist") 
os.remove("BuildManifest.plist") 
buildnum = stat.getBuildNumber()
version = stat.getVersion()
stat.deviceClass = chooseDeviceClass(stat)
locs = stat.getFirmwareLocations()
firmDir = stat.getDeviceClass() + "_" + version.replace('.','-') + "_" + buildnum
extractIPSW(ipsw,firmDir)
KBAGS = getKBAGS(firmDir,locs)

if writeout:
	csv_file = open("KEYS_"+firmDir+".csv",'w')
	writer = csv.writer(csv_file)
	writer.writerow(['img4','kbag','iv','key'])
try:
	p = subprocess.check_output(['./ipwndfu','-p'])
except:
	print "failed"
	exit(-1)
print p
if "ERROR" in p:
	exit(-1)
time.sleep(3)
print("Keys for: %s on %s (%s)" % (stat.getDeviceClass(),version,buildnum))
print("==========================================\n")
for item in KBAGS:
	try:
		p = subprocess.check_output(['./ipwndfu','--decrypt-gid=' + KBAGS[item]])
		p = p.split('\n')[1]
		print(item + "\n====")
		iv = p[:32]
		key = p[-64:]
		print ("KBAG: " + KBAGS[item] + "\nIV:  " + iv + "\nKEY: " + key + "\n")
		if writeout:
			writer.writerow([item,KBAGS[item],iv,key])
	except: 
		pass
	time.sleep(1)
if writeout:
	csv_file.close()