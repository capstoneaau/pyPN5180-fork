import spidev
import RPi.GPIO as GPIO
from gpiozero import DigitalInputDevice
import time
import sys
from abc import ABC, abstractmethod

from .definitions import *

class AbstractPN5180(ABC):
	def __init__(self, bus: int = 0, device: int = 0, debug=False):
		self._spi = spidev.SpiDev()
		self._spi.open(bus, device)
		self._spi.max_speed_hz = 7000000
		GPIO.setmode(GPIO.BCM)
		GPIO.setup(25, GPIO.IN)  # GPIO 25 is the Busy pin (Header 22)
		self.__debug = debug

	def _log(self, *args):
		if self.__debug:
			print(args)

	@staticmethod
	def _log_format_hex(data: [bytes]):
		return ' '.join(f"0x{i:02x}" for i in data)

	def _wait_ready(self):
		#self._log("Check Card Ready")
		if GPIO.input(25):
			while GPIO.input(25):
				self._log("Card Not Ready - Waiting for Busy Low")
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

	@abstractmethod
	def _inventory(self):
		"""
		Return UID when detected
		:return:
		"""
		raise NotImplementedError("Method needs to be subclassed for each protocol.")

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

	def inventory(self, raw=False):
		"""
		Send inventory command for initialized protocol, returns a list of cards detected.
		'raw' parameter can be set to False to return the unstructured UID response from the card.
		:param raw:
		:return:
		"""
		cards = self._inventory()
		# print(f"{len(cards)} card(s) detected: {' - '.join([self._format_uid(card) for card in cards])}")
		if raw:
			return cards
		else:
			return [self._format_uid(card) for card in cards]




