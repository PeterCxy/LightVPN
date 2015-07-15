import socket
import select
import time
import utils
import logging
import os
import threading

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

def main_loop():
	while True:
		r, w, x = select.select([tunfd, udpfd], [], [], 1)
		if tunfd in r:
			data = os.read(tunfd, 32767)

			dst = data[16:20]
			if dst in clients.keys():
				udp.sendto(data, clients[dst]['ip'])
			else:
				logging.warn(dst + " not found")

			clearClients()

		if udpfd in r:
			data, src = udp.recvfrom(32767)
			os.write(tunfd, data)
			#logging.info('connection from %s:%d' % src)
			c = data[12:16] # The source
			if c in clients.keys():
				clients[c]['time'] = time.time()
				clients[c]['ip'] = src
			else:
				clients[c] = {
					'ip': src,
					'time': time.time()
				}

	# Oops, loop cancelled. Something goes wrong
	utils.iptables_reset(config['virtual_ip'], config['output'])


# Start workers
for i in range(1, config['workers']):
	t = threading.Thread(target=main_loop)
	t.daemon = True
	t.start()
	logging.info('Started worker %i' % i)

main_loop()
