import struct
import csv
from time import sleep
from threading import Event, Thread
from config import Uart, Oven, PID, ambient_temperature
from datetime import datetime

pid_value = 0 
int_temp = 0 
ref_temp = 0 
amb_temp = 0 

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

def send_ambient_temp():
    sendind.set()
    global amb_temp
    amb_temp = ambient_temperature()
    
    val = struct.pack('!f', amb_temp)
    val = val[::-1]
    message = b'\x01\x16\xd6\x09\x00\x00\x06' + val

    uart.send(message, 11)

    sendind.clear()

def main_function():
    while True:
        sendind.set()

        message = b'\x01\x16\xd4\x09\x00\x00\x06\x00'

        uart.send(message, len(b'\x01\x16\xd4\x09\x00\x00\x06\x00'))
        data = uart.receive()

        if data is not None:
            stop()
            turned_on.set()

        sendind.clear()
        
        receive_dashboard_commands()
        get_int_temp()
        get_ref_temp()
        send_ambient_temp()
        handler()
        sleep(1)
        print("\nTemp Interna:", int_temp)
        print("Temp referencia:", ref_temp)
        print("Temp ambiente:", amb_temp, "\n")

        with open('logs.csv','a') as csvfile:
            if pid_value < 0:
                ventoinha = pid_value
                resistor = 0
            else:
                resistor = pid_value
                ventoinha = 0 

            msg = f'Temperatura Referencial = {ref_temp},Temperatura Interna={int_temp},Temperatura Ambiente = {ambient_temperature}, Ventoinha = {ventoinha}%,Resistor = {resistor}%' 
            writer = csv.writer(csvfile, delimiter = ',')
            print(datetime.now().strftime('%d/%m/%Y %H:%M')+',',msg,file = csvfile)

def handle_exit():
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
  print('Você deseja:\n')
  print('1 - Controlar o forno pelo Dashboard\n')
  print('2 - Controlar o forno pela curva de referência\n')
  option = int(input('Digite a opção escolhida\n'))
  return option

def main_function_curve():
    counter = 0
    while True:
        receive_dashboard_commands()
        get_ref_temp()
        get_int_temp()
        send_ambient_temp()
        handler()
        sleep(1)
        print("\nTemp Interna:", int_temp)
        print("Temp referencia:", ref_temp)
        print("Temp ambiente:", amb_temp, "\n")

        if counter >= 0 and counter < 60:    
            ref_temp = 25
            reflow = struct.pack('f', 25)
            message = b'\x01\x16\xd2\x09\x00\x00\x06' + reflow
            uart.send(message, len(message))
        elif counter >= 60 and counter < 120:
            ref_temp = 38
            reflow = struct.pack('f', 38)
            message = b'\x01\x16\xd2\x09\x00\x00\x06' + reflow
            uart.send(message, len(message))
        elif counter >= 120 and counter < 240:
            ref_temp = 46
            reflow = struct.pack('f', 46)
            message = b'\x01\x16\xd2\x09\x00\x00\x06' + reflow
            uart.send(message, len(message))                
        elif counter >= 240 and counter < 260:
            ref_temp = 54
            reflow = struct.pack('f', 54)
            message = b'\x01\x16\xd2\x09\x00\x00\x06' + reflow
            uart.send(message, len(message))
        elif counter >= 260 and counter < 300:
            ref_temp=57
            reflow = struct.pack('f', 57)
            message = b'\x01\x16\xd2\x09\x00\x00\x06' + reflow
            uart.send(message, len(message))
        elif counter >= 300 and counter < 360:
            ref_temp = 61
            reflow = struct.pack('f', 61)
            message = b'\x01\x16\xd2\x09\x00\x00\x06' + reflow
            uart.send(message, len(message))
        elif counter >= 360 and counter < 420:
            ref_temp = 63
            reflow = struct.pack('f', 63)
            message = b'\x01\x16\xd2\x09\x00\x00\x06' + reflow
            uart.send(message, len(message))
        elif counter >= 420 and counter < 480:
            ref_temp = 54
            reflow = struct.pack('f', 54)
            message = b'\x01\x16\xd2\x09\x00\x00\x06' + reflow
            uart.send(message, len(message))
        elif counter >= 480 and counter < 600:
            ref_temp = 33
            reflow = struct.pack('f', 33)
            message = b'\x01\x16\xd2\x09\x00\x00\x06' + reflow
            uart.send(message, len(message))
        elif counter >= 600:
            ref_temp = 25
            reflow = struct.pack('f', 25)
            message = b'\x01\x16\xd2\x09\x00\x00\x06' + reflow
            uart.send(message, len(message))
            
        with open('logs.csv','a') as csvfile:
            if pid_value < 0:
                ventoinha = pid_value
                resistor = 0
            else:
                resistor = pid_value
                ventoinha = 0 

            msg = f'Temperatura Referencial = {ref_temp},Temperatura Interna={int_temp},Temperatura Ambiente = {ambient_temperature}, Ventoinha = {ventoinha}%,Resistor = {resistor}%' 
            writer = csv.writer(csvfile, delimiter = ',')
            print(datetime.now().strftime('%d/%m/%Y %H:%M')+',',msg,file = csvfile)
        # if counter >= 0 and counter < 60:

        counter += 1

def handle_curve_control():
  sendind.set()

  message = b'\x01\x16\xd4\x09\x00\x00\x06\x01'

  uart.send(message, len(b'\x01\x16\xd4\x09\x00\x00\x06\x01'))
  data = uart.receive()

  if data is not None:
      stop()
      turned_on.set()

  sendind.clear()

  inputed_temp = float(input('Digite o Valor da temperatura \n'))
  inputed_temp_bin = struct.pack('f', inputed_temp)

  sendind.set()
  message = b'\x01\x16\xd2\x09\x00\x00\x06' + inputed_temp_bin

  uart.send(message, len(message))
  data = uart.receive()

  if data is not None:
      started.set()

  sendind.clear()

  turn_on()

  start()

  thread_handle_exit = Thread(target=handle_exit, args=())
  thread_handle_exit.start()    

  thread_main_function_curve = Thread(target=main_function_curve, args=())
  thread_main_function_curve.start() 

if __name__ == '__main__':
    should_change_vars = input('Gostaria de mudar as variáveis do PID? S(Sim) ou N(não) \n')
    if should_change_vars != 'N':
      change_vars()

    menuOption = menu()

    if(menuOption != 1):
      handle_curve_control()
    else:
      turn_on()

      main_thread = Thread(target=main_function, args=())
      main_thread.start()

      thread_handle_exit = Thread(target=handle_exit, args=())
      thread_handle_exit.start()       