import time


class PID:
	def __init__(self, p, i, d, sp):
		self.kP = p
		self.kI = i
		self.kD = d
		self.setpoint = sp
		self.clear()

	# reset everything to original values
	def clear(self):
		self.lastError = 0
		self.input = self.setpoint
		self.p = 0
		self.i = 0
		self.d = 0
		self.lastTime = time.time()

	def changeSetpoint(self, sp):
		self.setpoint = sp

	# calculates the gain using previous values and the input (current value)

	def calcVal(self, input):
		error = self.setpoint - input
		currentTime = time.time()

		timeChange = currentTime - self.lastTime
		errorChange = error - self.lastError

		self.p = error

		self.i += timeChange*error

		if timeChange != 0:
			self.d = errorChange/timeChange

		return self.kP*self.p + self.kI*self.i + self.kD*self.d
