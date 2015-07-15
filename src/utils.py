from __future__ import with_statement

import fcntl
import getopt
import os
import struct
import subprocess
import sys
import json
import logging

TUNSETIFF = 0x400454ca
TUNSETOWNER = TUNSETIFF + 2
IFF_TUN = 0x0001
IFF_TAP = 0x0002
IFF_NO_PI = 0x1000

def tun_open(name, ip):
	# Open the tun device first
	tun = open('/dev/net/tun', 'r+b')

	# Create the interface
	ifr = struct.pack('16sH', name, IFF_TUN | IFF_NO_PI)
	fcntl.ioctl(tun, TUNSETIFF, ifr)
	fcntl.ioctl(tun, TUNSETOWNER, 1000)

	# Bring it up
	subprocess.check_call('ifconfig %s %s netmask 255.255.255.0 up' % (name, ip), shell=True)

	# Log
	logging.info('Interface %s is up with ip %s' % (name, ip))

	return tun

def iptables_setup(ip, device):
	cmd = 'iptables -t nat -A POSTROUTING -s %s/8 -o %s -j MASQUERADE' % (ip, device)
	logging.info('Setting up iptables with %s' % cmd)
	subprocess.check_call(cmd, shell=True)

def iptables_reset(ip, device):
	cmd = 'iptables -t nat -D POSTROUTING -s %s/8 -o %s -j MASQUERADE' % (ip, device)
	logging.info('Resetting iptables with %s' % cmd)
	subprocess.check_call(cmd, shell=True)

def fork_workers(workers):
	if workers > 1:
		for i in range(1, workers):
			v = os.fork()
			if v != 0:
				# Then I'm a worker -_-
				break;
			logging.info('Statred worker %d' % i)

def get_config():
	logging.basicConfig(level=logging.INFO, format='%(levelname)-s: %(message)s')

	shortopts = "vc:"
	longopts = ["version", "config="]
	config_path = "config.json"
	opts, args = getopt.getopt(sys.argv[1:], shortopts, longopts)
	for key, value in opts:
		if key == '-c' or key == '--config':
			config_path = value

	config = {}
	with open(config_path, 'rb') as f:
		try:
			config = json.loads(f.read().decode('utf8'))
		except:
			# No config? Too bad!
			logging.error('Cannot load config')
			sys.exit(1)

	config['interface'] = config.get('interface', 'tun0').encode('utf-8')
	config['virtual_ip'] = config.get('virtual_ip', '10.0.0.1')
	config['server'] = config.get('server', '0.0.0.0')
	config['port'] = int(config.get('port', '2333'))
	config['output'] = config.get('output', 'eth0')
	config['timeout'] = int(config.get('timeout', '600'))
	config['workers'] = int(config.get('workers', '1'))

	return config
