import socket
import select
import time
import utils
import logging
import os

config = utils.get_config()

# Open a tun device
tun = utils.tun_open(config['interface'], config['virtual_ip'])
utils.iptables_setup(config['virtual_ip'], config['output'])

# Now let's bind a UDP socket
udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp.bind((config['server'], config['port']))
logging.info('Listenning at %s:%d' % (config['server'], config['port']))

# Get descriptors
tunfd = tun.fileno()
udpfd = udp.fileno()

clients = {}

# Must remove timeouted clients
def clearClients():
	cur = time.time();

	for key in clients.keys():
		if cur - clients[key]['time'] >= config['timeout']:
			logging.info('client %s:%s timed out.' % clients[key]['ip'])
			del clients[key]


while True:
	r, w, x = select.select([tunfd, udpfd], [], [], 1)
	if tunfd in r:
		data = os.read(tunfd, 2048)

		dst = data[16:20]
		if dst in clients:
			udp.sendto(data, clients[dst]['ip'])

			# Update the last active time
			clients[dst]['time'] = time.time()
		else:
			logging.warn(dst + " not found")

		clearClients()

	if udpfd in r:
		data, src = udp.recvfrom(2048)
		os.write(tunfd, data)
		logging.info('connection from %s:%d' % src)
		clients[data[12:16]] = {
			'ip': src,
			'time': time.time()
		}

# Oops, loop cancelled. Something goes wrong
utils.iptables_reset(config['virtual_ip'], config['output'])
