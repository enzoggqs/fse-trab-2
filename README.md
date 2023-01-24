# FUNDAMENTOS DE SISTEMAS EMBARCADOS - PROJETO 2

## Aluno

|Matrícula | Aluno |
| :--: | :--: |
| 160119006 |  Enzo Gabriel |

## Configuração

### Conectando-se a RaspBerry Pi

Primeiro, deve-se conectar a placa Raspberry por meio de uma conexão SSH

```
    ssh enzosaraiva@164.41.98.27 -p 13508
```

Senha para acesso: 160119006

### Clonando o repositório

Após o acesso, clone o repositório na placa com o comando:

```
    git clone https://github.com/enzoggqs/fse-trab-2
```

### Baixando as bibliotecas necessárias para rodar o projeto
Use os seguintes comandos para poder rodar o projeto na sua máquina sem problemas

```
  pip3 install RPi.bme280
  pip3 install smbus
```

### Rodando o projeto

Entre do diretório onde se encontra o código fonte da main:

```
    cd fse-trab-2/src
```

Após ter acessado o diretório src do repositório clonado, basta usar o seguinte comando para rodar o projeto:
```
    python3 main.py
```