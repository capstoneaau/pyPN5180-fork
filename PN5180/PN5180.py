import spidev
import RPi.GPIO as GPIO
from gpiozero import DigitalInputDevice
import time
import sys
from abc import ABC, abstractmethod

from .definitions import *

class AbstractPN5180(ABC):
	def __init__(self, bus: int = 0, device: int = 0, debug=False):
		GPIO.cleanup()

		self._spi = spidev.SpiDev()
		self._spi.open(bus, device)
		self._spi.max_speed_hz = 7000000
		self._spi.lsbfirst = False
		self._spi.mode = 0b00
		GPIO.setmode(GPIO.BCM)
		GPIO.setup(GPIO_BUSY, GPIO.IN)  # GPIO 25 is the Busy pin (Header 22)
		GPIO.setup(GPIO_NSS, GPIO.OUT)
		GPIO.setup(GPIO_RST, GPIO.OUT)

		GPIO.output(GPIO_NSS, GPIO.HIGH)
		GPIO.output(GPIO_RST, GPIO.HIGH)
		self.__debug = debug

	def _log(self, *args):
		if self.__debug:
			print(args)

	@staticmethod
	def _log_format_hex(data: [bytes]):
		return ' '.join(f"0x{i:02x}" for i in data)

	def _wait_ready(self, low = True):
		#self._log("Check Card Ready")
		if low:
			if GPIO.input(GPIO_BUSY):
				while GPIO.input(GPIO_BUSY):
					#self._log("Card Not Ready - Waiting for Busy Low")
					time.sleep(.01)
		else:
			if GPIO.input(GPIO_BUSY):
				while not GPIO.input(GPIO_BUSY):
					#self._log("Card Not Ready - Waiting for Busy High")
					time.sleep(.01)
		#self._log("Card Ready, continuing conversation.")

	def _send(self, frame: [bytes]):
		self._wait_ready()
		self._spi.writebytes(frame)
		self._log("Sent Frame: ", self._log_format_hex(frame))
		self._wait_ready()

	def _read(self, length):
		return self._spi.readbytes(length)

	def _send_string(self, string: str):
		msg_array = [ord(letter) for letter in string]
		self._send(msg_array)

	def _write_register(self, address, content):
		self._send([0x00, address] + list(content))

	def _card_has_responded(self):
		"""
		The function CardHasResponded reads the RX_STATUS register, which indicates if a card has responded or not.
		Bits 0-8 of the RX_STATUS register indicate how many bytes where received.
		If this value is higher than 0, a Card has responded.
		:return:
		"""
		self._send([PN5180_READ_REGISTER, RX_STATUS])  # READ_REGISTER RX_STATUS -> Response > 0 -> Card has responded
		result = self._read(4)  # Read 4 bytes
		self._send([PN5180_READ_REGISTER, IRQ_STATUS])  # READ_REGISTER IRQ_STATUS
		result_irq = self._read(4)  # Read 4 bytes
		self._log("RX_STATUS", self._log_format_hex(result))
		self._log("IRQ_STATUS", self._log_format_hex(result_irq))
		collision_bit = int.from_bytes(result, byteorder='little', signed=False) >> 18 & 1
		collision_position = int.from_bytes(result, byteorder='little', signed=False) >> 19 & 0x3f
		self._collision_flag = collision_bit
		self._collision_position = collision_position
		if result[0] > 0:
			self._bytes_in_card_buffer = result[0]
			return True
		return False

	#@abstractmethod
	#def _inventory(self):
	#	"""
	#	Return UID when detected
	#	:return:
	#	"""
	#	raise NotImplementedError("Method needs to be subclassed for each protocol.")

	@staticmethod
	def _format_uid(uid, reverse=False):
		"""
		Return a readable UID from a LSB byte array
		:param uid:
		:return:
		"""
		uid_readable = list(uid)  # Create a copy of the original UID array
		if reverse:
			uid_readable.reverse()
		uid_readable = "".join([format(byte, 'x').zfill(2) for byte in uid_readable])
		# print(f"UID: {uid_readable}")
		return uid_readable

	def transcieve_command(self, send_data: list, receive_buffer_len = 0) -> list:
		receive_buffer = []

		self._wait_ready()
		GPIO.output(GPIO_NSS, GPIO.LOW)
		time.sleep(0.002)
		self._spi.xfer(send_data)
		self._log("Sent Frame: ", self._log_format_hex(send_data))
		self._wait_ready(low=False)
		GPIO.output(GPIO_NSS, GPIO.HIGH)
		time.sleep(0.001)
		self._wait_ready()

		if receive_buffer_len == 0: #Don't proceed with read
			return None

		self._log("Receiving SPI Frame")
		
		GPIO.output(GPIO_NSS, GPIO.LOW)
		time.sleep(0.002)

		send_mask = []
		for i in range(0,receive_buffer_len):
			send_mask.append(0xFF)
		receive_buffer = self._spi.xfer2(send_mask)
		self._log("Received: ", receive_buffer)
		self._wait_ready(low=False)	
		GPIO.output(GPIO_NSS, GPIO.HIGH)
		time.sleep(0.001)
		self._wait_ready()

		return receive_buffer

	def read_register(self, register: int) -> int:
		value_bytes = self.transcieve_command([PN5180_READ_REGISTER, register], 4)
		self._log(value_bytes)
		value = value_bytes[0] | (value_bytes[1] << 8) | (value_bytes[2] << 16) | (value_bytes[3] << 24)
		self._log(value)
		return value
	
	def get_transceive_state(self) -> PN5180TransceiveStat:
		rf_status = self.read_register(RF_STATUS)
		self._log("RF Status = ", rf_status)
		state = ((rf_status >> 24) & 0x07) & 0xFF
		self._log("Transceive state = ", state)
		return PN5180TransceiveStat(state)

	def send_data(self, data: list, valid_bits):
		if len(data) > 260:
			'''TODO: check if the lack of support still applies.'''
			raise Exception("Sendind data of length that's greater than 260 is not supported")
		
		buffer = [PN5180_SEND_DATA, valid_bits] + data

		self._send([PN5180_WRITE_REGISTER_AND_MASK, SYSTEM_CONFIG, 0xF8, 0xFF, 0xFF, 0xFF])  # Sets the PN5180 into IDLE state
		self._send([PN5180_WRITE_REGISTER_OR_MASK, SYSTEM_CONFIG, 0x03, 0x00, 0x00, 0x00])  # Activates TRANSCEIVE routine
		self.clear_IRQ_STATUS()

		if self.get_transceive_state() != PN5180TransceiveStat.PN5180_TS_WaitTransmit:
			raise Exception("not in wait transmit state :(")


		self.transcieve_command(buffer)
	
	def read_data(self, expected_length: int) -> list:
		if expected_length > 508:
			'''TODO: check if the lack of support still applies.'''
			raise Exception("Reading data of length that's greater than 508 is not supported")
		return self.transcieve_command([PN5180_READ_DATA, 0x00], expected_length)

	def load_rf_config(self, tx_conf, rx_conf):
		self.transcieve_command([PN5180_LOAD_RF_CONFIG, tx_conf, rx_conf])

	def get_irq_status(self) -> int:
		irq_status = self.read_register(IRQ_STATUS)
		self._log("IRQ status = ", irq_status)
		return irq_status

	def write_register_with_or_mask(self, reg: int, mask: int):
		p = mask.to_bytes(4, byteorder='little')
		buf = bytearray([PN5180_WRITE_REGISTER_OR_MASK, reg]) + p
		self.transcieve_command(list(buf))
	
	def write_register_with_and_mask(self, reg: int, mask: int):
		p = mask.to_bytes(4, byteorder='little')
		buf = bytearray([PN5180_WRITE_REGISTER_AND_MASK, reg]) + p
		self.transcieve_command(list(buf))

	def disable_crypto(self):
		self._send([PN5180_WRITE_REGISTER_AND_MASK, SYSTEM_CONFIG, 0xBF, 0xFF, 0xFF, 0xFF])

	def disable_crc(self):
			self._send([PN5180_WRITE_REGISTER_AND_MASK, CRC_TX_CONFIG, 0xFE, 0xFF, 0xFF, 0xFF])  #Switches the CRC extension off in Tx direction
			self._send([PN5180_WRITE_REGISTER_AND_MASK, CRC_RX_CONFIG, 0xFE, 0xFF, 0xFF, 0xFF])  #Switches the CRC extension off in Rx direction
	
	def enable_crc(self):
		self._send([PN5180_WRITE_REGISTER_AND_MASK, CRC_TX_CONFIG, 0x01])  #Switches the CRC extension on in Tx direction
		self._send([PN5180_WRITE_REGISTER_AND_MASK, CRC_RX_CONFIG, 0x01])  #Switches the CRC extension on in Rx direction
	
	def rf_on(self):
		self._send([PN5180_RF_ON, 0x00])  # Switches the RF field ON.
	
	def rf_off(self):
		self._send([PN5180_RF_OFF, 0x00])  # Switch OFF RF field

	def clear_IRQ_STATUS(self):
		self._send([PN5180_WRITE_REGISTER, IRQ_CLEAR, 0xFF, 0xFF, 0x0F, 0x00])





