import time
from PN5180 import AbstractPN5180
from PN5180.definitions import *

class ISO14443(AbstractPN5180):
	def __init__(self, bus: int = 0, device: int = 0, debug=False):
		super().__init__(bus, device, debug)
		self.load_rf_config(0x00, 0x80) # Load IS014443 RF config
		self.rf_on()
		print(self.get_irq_status())
	
	def activate_type_a(self, kind: ISO14443InitCommand) -> dict:
		"""
		Internal method to activate Type A card and return full response
		Returns dict containing necessary data
		TODO:
			- Error checking
			- Refactor clear and enable CRC's RX and TX methods 
		"""
		uid_length = 0

		self.disable_crypto()
		self.disable_crc()
		self.clear_IRQ_STATUS()  # Clears the interrupt register IRQ_STATUS

		#Send REQA/WUPA
		self.send_data([kind.value], 0x07)

		buff = self.read_data(2)
		print(buff)
		
		print(self.get_irq_status())

		self.disable_crc()

		self.send_data([0x93, 0x20], 0x00)

		buff2 = self.read_data(5)

		self.write_register_with_or_mask(CRC_RX_CONFIG, 0x01)
		self.write_register_with_or_mask(CRC_TX_CONFIG, 0x01)
		
		self.send_data([0x93, 0x70]+buff2,0x00)

		buff = buff + self.read_data(1)
		print(buff)
		print(buff2)

		if (buff[2] & 0x04) == 0:
			buff = buff + buff2
			uid_length = 4
		else:
			if buff2[0] != 0x88:
				raise Exception("err comparing uid buffer")
			buff = buff + buff2[1:]
			self.write_register_with_and_mask(CRC_RX_CONFIG, 0xFFFFFFFE)
			self.write_register_with_and_mask(CRC_TX_CONFIG, 0xFFFFFFFE)
			self.send_data([0x95, 0x20], 0x00)
			buff3 = self.read_data(5)
			buff3 = buff3 + buff
			self.write_register_with_or_mask(CRC_RX_CONFIG, 0x01)
			self.write_register_with_or_mask(CRC_TX_CONFIG, 0x01)
			self.send_data([0x95, 0x70]+buff3,0x00)
			sak = self.read_data(1)
			uid_length = 7

		return {"atqa": buff[0], "sak": buff[2], "uid": buff2[:-1], "uid_length": uid_length}

	def rx_bytes_received(self) -> int:
		"""
		Returns the number of bytes received from the card
		"""
		rx_status = self.read_register(RX_STATUS)
		# Lower 9 bits contain the length
		length = rx_status & 0x000001ff
		return length

	def mifare_authenticate(self, key, key_type, blockno, uid) -> int:

		return 0x0

	def mifare_block_read(self, blockno: int) -> list:
		"""
		Read a 16-byte block from a Mifare card
		Returns the 16 bytes read from the block, or None if failed
		"""
		# Send mifare read command (0x30) with block number
		self.send_data([0x30, blockno], 0x00)

		# Wait a bit for the card to respond
		time.sleep(0.005)
		
		# Check if we received data
		length = self.rx_bytes_received()
		if length == 16:
			# Read 16 bytes
			data = self.read_data(16)
			return data
		
		return None

	def mifare_block_write16(self, blockno: int, data: list) -> int:
		"""
		Write 16 bytes to a Mifare block
		Returns the ACK/NAK byte from the card
		"""
		if len(data) != 16:
			raise ValueError("Data must be exactly 16 bytes")
		
		# Clear RX CRC for the write operation
		self.write_register_with_and_mask(CRC_RX_CONFIG, 0xFFFFFFFE)
		
		# Mifare write part 1 - send write command
		self.send_data([0xA0, blockno], 0x00)
		ack1 = self.read_data(1)
		
		# Mifare write part 2 - send the actual data
		self.send_data(data, 0x00)
		time.sleep(0.010)  # Wait 10ms
		
		# Read ACK/NAK
		ack2 = self.read_data(1)
		
		# Re-enable RX CRC calculation
		self.write_register_with_or_mask(CRC_RX_CONFIG, 0x01)
		
		return ack2[0] if ack2 else 0

	def mifare_halt(self) -> bool:
		"""
		Send halt command to the Mifare card
		"""
		# Send Mifare halt command
		self.send_data([0x50, 0x00], 0x00)
		return True

	def read_card_serial(self) -> tuple:
		"""
		Read card serial (UID) using WUPA command
		Returns tuple: (uid_bytes, uid_length) or (None, 0) if no valid card
		"""
		# Use WUPA (wake up) command
		uid_length = self.activate_type_a(ISO14443InitCommand.WupA)["uid_length"]
		
		if uid_length == 0:
			return (None, 0)
		
		# For this implementation, we'll need to extract the UID from the activation process
		# Since the existing activate_type_a doesn't return the actual UID bytes,
		# we'll need to re-implement the activation to capture the UID
		self.mifare_halt()
		
		response = self.activate_type_a(ISO14443InitCommand.WupA)
		if not response:
			return (None, 0)
		
		atqa, sak, uid_bytes = list(response.values())[:3]
		
		# Check for invalid responses
		if atqa == [0xFF, 0xFF]:
			return (None, 0)
		
		# Check for invalid UIDs (all zeros or all FFs)
		if all(b == 0x00 for b in uid_bytes) or all(b == 0xFF for b in uid_bytes):
			return (None, 0)
		
		self.mifare_halt()
		return (uid_bytes, len(uid_bytes))

	def is_card_present(self) -> bool:
		"""
		Check if a card is present
		Returns True if a valid card with UID >= 4 bytes is detected
		"""
		uid_bytes, uid_length = self.read_card_serial()
		return uid_length >= 4