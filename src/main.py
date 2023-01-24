import struct
from time import sleep
from threading import Event, Thread 
from config import Uart, Oven, PID, ambient_temperature

pid_value = 0 
int_temp = 0 
ref_temp = 0 
temperatura_ambiente = 0 

oven = Oven(23, 24)
uart = Uart('/dev/serial0', 9600, 0.5)
pid = PID(30.0, 0.2, 400.0, 1.0, 100.0, -100.0)

sendind = Event()
turned_on = Event()
started = Event()
warming = Event()
chilling = Event()

def stop():
  print('\nForno parado\n')
  sendind.set()
  message = b'\x01\x16\xd5\x09\x00\x00\x06\x00'

  uart.send(message, 8)
  data = uart.receive()

  if data is not None:
      started.clear()

  sendind.clear()

def turn_on():
  print('\nForno ligado\n')
  sendind.set()

  message = b'\x01\x16\xd3\x09\x00\x00\x06\x01'

  uart.send(message, 8)
  data = uart.receive()

  if data is not None:
      stop()
      turned_on.set()

  sendind.clear()

def turn_off():
    print('\nForno desligado\n')
    sendind.set()
    message = b'\x01\x16\xd3\x09\x00\x00\x06\x00'

    uart.send(message, 8)
    data = uart.receive()

    if data is not None:
        stop()
        turned_on.clear()

    sendind.clear()

def start():
    print('Forno iniciado\n')
    sendind.set()
    message = b'\x01\x16\xd5\x09\x00\x00\x06\x01'

    uart.send(message, 8)
    data = uart.receive()

    if data is not None:
        started.set()

    sendind.clear()

def control_signal(pid):
    sendind.set()
    val = (round(pid)).to_bytes(4, 'little', signed=True)
    message = b'\x01\x16\xd1\x09\x00\x00\x06' + val

    uart.send(message, 11)

    sendind.clear()

def handler():
    if turned_on.is_set():
        if started.is_set():
            print('entrou')

            pid_value = pid.pid_control(ref_temp, int_temp)
            control_signal(pid_value)

            if(int_temp < ref_temp):
                print("\nAquecimento\n")
                oven.warm(int(abs(pid_value)))
                oven.chill(0)
                warming.set()
                chilling.clear()

            elif(int_temp > ref_temp):
                print("\nResfriamento\n")
                if (pid_value < 0 and pid_value > -40):
                    oven.chill(40)
                else:
                    oven.chill(abs(int(pid_value)))
                
                oven.warm(0)
                warming.clear()
                chilling.set()


def receive_dashboard_commands():
    message = b'\x01\x23\xc3\x09\x00\x00\x06'
    
    uart.send(message, 7)
    data = uart.receive()

    if data:
        button = int.from_bytes(data, 'little')%10

        print('Botão: ')
        print(button)

        if button == 1:
            turn_on()

        if button == 2:
            turn_off()

        if button == 3:
            start()

        if button == 4:
            stop()

def get_int_temp():
    message = b'\x01\x23\xc1\x09\x00\x00\x06'

    uart.send(message, 7)
    data = uart.receive()

    if data is not None:
        temp = struct.unpack('f', data)[0]

        if temp > 0 and temp < 100:
            global int_temp
            int_temp = temp     

def get_ref_temp():
    message = b'\x01\x23\xc2\x09\x00\x00\x06'

    uart.send(message, 7)
    data = uart.receive()

    if data is not None:
        temp = struct.unpack('f', data)[0]

        if temp > 0 and temp < 100:
            global ref_temp
            ref_temp = temp     

def envia_temperatura_ambiente():
    sendind.set()
    global temperatura_ambiente
    temperatura_ambiente = ambient_temperature()
    
    val = struct.pack('!f', temperatura_ambiente)
    val = val[::-1]
    message = b'\x01\x16\xd6\x09\x00\x00\x06' + val

    uart.send(message, 11)

    sendind.clear()

def rotina():
    while True:

        receive_dashboard_commands()
        get_int_temp()
        get_ref_temp()
        envia_temperatura_ambiente()
        handler()
        sleep(1)

        print("\nTEMPERATURA INTERNA:", int_temp)
        print("TEMPERATURA DE REFERENCIA:", ref_temp)
        print("TEMPERATURA AMBIENTE:", temperatura_ambiente, "\n")

def trata_ctrl_c():
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        stop()
        turn_off()

def change_vars():
  pid.Kp = float(input('Digite o valor de Kp\n'))
  pid.Ki = float(input('Digite o valor de Ki\n'))
  pid.Kd = float(input('Digite o valor de Kd\n'))

def menu():
  print('Bem vindo! Você deseja:\n')
  print('1 - Controlar o forno pelo Dashboard\n')
  print('2 - Controlar o forno pela curva de referência\n')
  option = int(input('Digite a opção escolhida\n'))
  return option

if __name__ == '__main__':
    should_change_vars = input('Gostaria de mudar as variáveis do PID? S(Sim) ou N(não) \n')
    if should_change_vars != 'N':
      change_vars()

    

    menuOption = menu()

    turn_on()

    thread_rotina = Thread(target=rotina, args=())
    thread_rotina.start()

    thread_captura_encerramento = Thread(target=trata_ctrl_c, args=())
    thread_captura_encerramento.start()    