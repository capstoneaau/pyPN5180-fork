import time
from PN5180 import AbstractPN5180
from PN5180.definitions import *

class ISO14443(AbstractPN5180):
	def __init__(self, bus: int = 0, device: int = 0, debug=False):
		super().__init__(bus, device, debug)
		self.load_rf_config(0x00, 0x80) # Load IS014443 RF config
		self.rf_on()
		print(self.get_irq_status())
	
	def activate_type_A(self, kind: ISO14443InitCommand) -> int:
		'''
		Determines length of UID (currently only 4 and 7 byte UIDs are supported)
		TODO:
			- Error checking
			- Refactor clear and enable CRC's RX and TX methods 
		'''
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

		print(uid_length)
		return(uid_length)
