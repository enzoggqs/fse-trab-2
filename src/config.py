import RPi.GPIO as GPIO
import smbus2
import bme280
import serial
from time import sleep
from crc import calcCRC

# Medicao da temperatura externa no barramento I2C
def ambient_temperature():
  port = 1
  address = 0x76
  bus = smbus2.SMBus(port)

  calibration_params = bme280.load_calibration_params(bus, address)
  data = bme280.sample(bus, address, calibration_params)
  
  return data.temperature

# Classe do forno, que possui seus atributos e métodos
class Oven:
  def __init__(self, res_pin, vent_pin):
    self.res_pin = res_pin
    self.vent_pin = vent_pin
    self._setup_gpio()
    self.vent_pwm = GPIO.PWM(vent_pin, 1000)
    self.res_pwm = GPIO.PWM(res_pin, 1000)

  def _setup_gpio(self):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(self.res_pin, GPIO.OUT)
    GPIO.setup(self.vent_pin, GPIO.OUT)

  def chill(self, pid):
    self.vent_pwm.ChangeDutyCycle(pid)
        
  def warm(self, pid):
    self.res_pwm.ChangeDutyCycle(pid)

# Classe da UART, que monitora a conexão e as mensagens recebidas e enviadas
class Uart:
  def __init__(self, port, baudrate, timeout=1):
      self.timeout = timeout
      self.port = port
      self.baudrate = baudrate

      self.serial = None

      self.connect()
      
  def connect(self):
    try:
      self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)

      print('Conexão realizada\n')
    except:
      print('Conexão não realizada\n')
          
  def receive(self):
    if self.serial and self.serial.isOpen():
      sleep(0.2)
      buffer = self.serial.read(9)
      buffer_size = len(buffer)

      if buffer_size == 9:
        received_crc16 = buffer[7:9]
        data = buffer[3:7]
        calculated_crc16 = calcCRC(buffer[0:7], 7).to_bytes(2, 'little')

        if received_crc16 == calculated_crc16:
          return data
        else:
          print('CRC16 inválido')
          return None
      else:
          print(f'Mensagem no formato incorreto, tamanho: {buffer_size}')
          return None
    else:
      self.connect()
      return None

  def send(self, message, size):
    if self.serial and self.serial.isOpen():
      aux = calcCRC(message, size).to_bytes(2, 'little')
      msg = message + aux
      self.serial.write(msg)
    else:
      self.connect()

# Classe PID, que possui o algoritmo de controle do PID de acordo com as variáveis fornecidas
class PID:
  def __init__(self, Kp, Ki, Kd, T, max_control_signal, min_control_signal):
    self.Kp = Kp
    self.Ki = Ki
    self.Kd = Kd
    self.T = T
    self.max_control_signal = max_control_signal
    self.min_control_signal = min_control_signal
    self.control_signal = 0.0
    self.error_total = 0.0
    self.previous_error = 0.0
      
  def pid_control(self, reference, measured_output):
    error = reference - measured_output
    self.error_total += error

    self.error_total = min(self.error_total, self.max_control_signal)
    self.error_total = max(self.error_total, self.min_control_signal)
    
    delta_error = error - self.previous_error
    self.control_signal = (self.Kp * error) + ((self.Ki * self.T) * self.error_total) + ((self.Kd / self.T) * delta_error)

    self.control_signal = min(self.control_signal, self.max_control_signal)
    self.control_signal = max(self.control_signal, self.min_control_signal)
    
    self.previous_error = error
    return self.control_signal