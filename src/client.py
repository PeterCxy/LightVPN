import socket
import select
import utils
import logging
import os
import threading
from crypto import AESCipher

config = utils.get_config()

# Open a tun device
tun = utils.tun_open(config['interface'], config['virtual_ip'])

udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp.bind(('', 0))
udp.setblocking(0)

# Get descriptors
tunfd = tun.fileno()
udpfd = udp.fileno()

# Create the cipher
cipher = AESCipher(config['password'])

def main_loop():
	# The main loop
	while True:
		r, w, x = select.select([udpfd, tunfd], [], [], 1)

		if tunfd in r:
			try:
				data = os.read(tunfd, 32767)
			except:
				continue

			if len(data):
				udp.sendto(cipher.encrypt(data), (config['server'], config['port']))
				#logging.info('sent %d to %s:%d' % (len(data), config['server'], config['port']))

		if udpfd in r:
			try:
				data, src = udp.recvfrom(32767)
			except:
				continue

			os.write(tunfd, cipher.decrypt(data))
			#logging.info('received %d' % len(data))

# Start workers (disabled temporarily)
for i in range(1, config['workers']):
	t = threading.Thread(target=main_loop)
	t.daemon = True
	t.start()
	logging.info('Started worker %i' % i)

main_loop()
