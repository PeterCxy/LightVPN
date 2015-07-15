import socket
import select
import utils
import logging
import os

config = utils.get_config()

# Open a tun device
tun = utils.tun_open(config['interface'], config['virtual_ip'])

udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp.bind(('', 0))

# Get descriptors
tunfd = tun.fileno()
udpfd = udp.fileno()

# The main loop
while True:
	r, w, x = select.select([udpfd, tunfd], [], [], 1)

	if tunfd in r:
		data = os.read(tunfd, 32767)
		if len(data):
			udp.sendto(data, (config['server'], config['port']))
			logging.info('sent %d to %s:%d' % (len(data), config['server'], config['port']))

	if udpfd in r:
		data, src = udp.recvfrom(32767)
		os.write(tunfd, data)
		logging.info('received %d' % len(data))
