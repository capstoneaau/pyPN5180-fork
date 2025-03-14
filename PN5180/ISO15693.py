from PN5180 import AbstractPN5180
from PN5180.definitions import *

class ISO15693(AbstractPN5180):
	def __init__(self, bus: int = 0, device: int = 0, debug=False):
		super().__init__(bus, device, debug)

	def _format_uid(self, uid):
		return super()._format_uid(uid, reverse=True)

	def _inventory(self):
		"""
		Return UID when detected
		:return:
		"""
		uids = []
		# https://www.nxp.com/docs/en/application-note/AN12650.pdf
		self._send([PN5180_LOAD_RF_CONFIG, 0x0D, 0x8D])  # Loads the ISO 15693 protocol into the RF registers
		self.rf_on()
		self._send([PN5180_WRITE_REGISTER, IRQ_CLEAR, 0xFF, 0xFF, 0x0F, 0x00])  # Clears the interrupt register IRQ_STATUS
		self._send([PN5180_WRITE_REGISTER_AND_MASK, SYSTEM_CONFIG, 0xF8, 0xFF, 0xFF, 0xFF])  # Sets the PN5180 into IDLE state
		self._send([PN5180_WRITE_REGISTER_OR_MASK, SYSTEM_CONFIG, 0x03, 0x00, 0x00, 0x00])  # Activates TRANSCEIVE routine
		self._send([PN5180_SEND_DATA, 0x00, 0x06, 0x01, 0x00])  # Sends an inventory command with 16 slots

		for slot_counter in range(0, 16):  # A loop that repeats 16 times since an inventory command consists of 16 time slots
			if self._card_has_responded():  # The function CardHasResponded reads the RX_STATUS register, which indicates if a card has responded or not.
				#GPIO.output(16, GPIO.LOW)
				self._send([PN5180_READ_DATA, 0x00])  # Command READ_DATA - Reads the reception Buffer
				uid_buffer = self._read(self._bytes_in_card_buffer)  # We shall read the buffer from SPI MISO -  Everything in the reception buffer shall be saved into the UIDbuffer array.
				# uid_buffer = self._read(255)  # We shall read the buffer from SPI MISO
				self._log("Buffer:", self._log_format_hex(uid_buffer))
				# uid = uid_buffer[0:10]
				uids.append(uid_buffer)
			self._send([0x02, 0x18, 0x3F, 0xFB, 0xFF, 0xFF])  # Send only EOF (End of Frame) without data at the next RF communication.
			self._send([PN5180_WRITE_REGISTER_AND_MASK, SYSTEM_CONFIG, 0xF8, 0xFF, 0xFF, 0xFF])  # Sets the PN5180 into IDLE state
			self._send([PN5180_WRITE_REGISTER_OR_MASK, SYSTEM_CONFIG, 0x03, 0x00, 0x00, 0x00])  # Activates TRANSCEIVE routine
			self._send([PN5180_WRITE_REGISTER, IRQ_CLEAR, 0xFF, 0xFF, 0x0F, 0x00])  # Clears the interrupt register IRQ_STATUS
			self._send([PN5180_SEND_DATA, 0x00])  # Send EOF
		self.rf_off()
		#GPIO.output(16, GPIO.HIGH)
		return uids
		