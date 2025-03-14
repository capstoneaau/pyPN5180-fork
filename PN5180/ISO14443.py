import time
from PN5180 import AbstractPN5180
from PN5180.definitions import *

class ISO14443(AbstractPN5180):
	def __init__(self, bus: int = 0, device: int = 0, debug=False):
		super().__init__(bus, device, debug)

	def _anticollision(self, cascade_level=0x93, uid_cln=[], uid=[]):
		self.disable_crc()
		self._send([PN5180_WRITE_REGISTER_AND_MASK, SYSTEM_CONFIG, 0xF8, 0xFF, 0xFF, 0xFF])  # Sets the PN5180 into IDLE state
		self._send([PN5180_WRITE_REGISTER_OR_MASK, SYSTEM_CONFIG, 0x03, 0x00, 0x00, 0x00])  # Activates TRANSCEIVE routine
		self._send([PN5180_WRITE_REGISTER, IRQ_CLEAR, 0xFF, 0xFF, 0x0F, 0x00])  # Clears the interrupt register IRQ_STATUS
		self._send([PN5180_SEND_DATA, 0x00, cascade_level, 0x20])
		time.sleep(.5)
		if self._card_has_responded():
			self._send([PN5180_READ_DATA, 0x00])  # Command READ_DATA - Reads the reception Buffer
			data = self._read(5)  # We shall read the buffer from SPI MISO
			self._log("Buffer: ", self._log_format_hex(data))
			if self._collision_flag:
				self._log(f"Collision Occurred at position: {self._collision_position}")
			else:
				# No collision occurred
				self.enable_crc()
				self._send([PN5180_WRITE_REGISTER_AND_MASK, SYSTEM_CONFIG, 0xF8, 0xFF, 0xFF, 0xFF])  # Sets the PN5180 into IDLE state
				self._send([PN5180_WRITE_REGISTER_OR_MASK, SYSTEM_CONFIG, 0x03, 0x00, 0x00, 0x00])  # Activates TRANSCEIVE routine
				self._send([PN5180_WRITE_REGISTER, IRQ_CLEAR, 0xFF, 0xFF, 0x0F, 0x00])  # Clears the interrupt register IRQ_STATUS
				self._send([PN5180_SEND_DATA, 0x00, cascade_level, 0x70]+data)
				if self._card_has_responded():
					self._send([PN5180_READ_DATA, 0x00])  # Command READ_DATA - Reads the reception Buffer
					sak = self._read(3)  # We shall read the buffer from SPI MISO
					self._log("Buffer: ", self._log_format_hex(sak))
					if data[0] == 0x88:
						# Cascade bit set, need to dig deeper
						partial_uid = data[1:4]
						return data[1:4] + self._anticollision(cascade_level=cascade_level+2, uid_cln=uid_cln+partial_uid)
					else:
						return data[:-1]
		raise Exception

	def _format_uid(self, uid):
		return super()._format_uid(uid)

	def _inventory(self):
		"""
		Return UID when detected
		:return:
		"""
		uids = []
		# https://www.nxp.com/docs/en/application-note/AN12650.pdf
		# https://www.nxp.com/docs/en/application-note/AN10834.pdf
		self._send([PN5180_LOAD_RF_CONFIG, 0x00, 0x80])  # Loads the ISO 14443 - 106 protocol into the RF registers
		self._send([PN5180_RF_ON, 0x00])  # Switches the RF field ON.
		self.disable_crc()
		self._send([PN5180_WRITE_REGISTER, IRQ_CLEAR, 0xFF, 0xFF, 0x0F, 0x00])  # Clears the interrupt register IRQ_STATUS
		self._send([PN5180_WRITE_REGISTER_AND_MASK, SYSTEM_CONFIG, 0xF8, 0xFF, 0xFF, 0xFF])  # Sets the PN5180 into IDLE state
		self._send([PN5180_WRITE_REGISTER_OR_MASK, SYSTEM_CONFIG, 0x03, 0x00, 0x00, 0x00])  # Activates TRANSCEIVE routine
		time.sleep(0.005) # Wait 5 ms before sending REQA
		self._send([PN5180_SEND_DATA, 0x07, 0x26])  # Sends REQA command to check if at least 1 card in field

		if self._card_has_responded():
			self._send([PN5180_READ_DATA, 0x00])  # Command READ_DATA - Reads the reception Buffer
			atqa = self._read(self._bytes_in_card_buffer)  # We shall read the buffer from SPI MISO -  Everything in the reception buffer shall be saved into the UIDbuffer array.
			# uid_buffer = self._read(255)  # We shall read the buffer from SPI MISO
			self._log("Buffer:", self._log_format_hex(atqa))
			try:
				uid = self._anticollision()
				uids.append(uid)
			except Exception as e:
				pass
			#self._send([0x09, 0x07, 0x93, 0x20])
			#uid_buffer = self._read(self._bytes_in_card_buffer)  # We shall read the buffer from SPI MISO -  Everything in the reception buffer shall be saved into the UIDbuffer array.
			#self._log(uid_buffer)

		self._send([0x17, 0x00])  # Switch OFF RF field
		#GPIO.output(16, GPIO.HIGH)
		return uids