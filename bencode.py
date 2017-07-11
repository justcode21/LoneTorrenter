from collections import OrderedDict
import re

# To encode a file to bencode recursively
def encode(message):
  if isinstance(message, list):
    encoded = "l"
    for item in message:
      encoded += encode(item)
    encoded += 'e'

  elif isinstance(message, OrderedDict):
    encoded = 'd'
    for key, value in message.iteritems():
      encoded += encode_string(key)
      encoded += encode(value)
    encoded += 'e'

  elif isinstance(message, str):
    encoded = encode_string(message)

  else:
    encoded = encode_int(message)
  return encoded


def encode_string(message):
  return str(len(message)) + ':' + message

def encode_int(message):
  return 'i' + str(message) + 'e'


# To decode a bencoded message
def decode(message):
  curr = message[0];
  if curr is 'd':
    start = 1
    token = OrderedDict()
    while message[start] is not 'e':
      key, rest = decode_string(message[start: ])
      value, rest = decode(rest)
      token[key] = value
      message = rest
      start = 0
    return token, rest[1: ] #skip the last e

  elif curr is 'l':
    start = 1
    token = []
    while message[start] is not 'e':
      key, rest = decode(message[start: ])
      token.append(key)
      message = rest
      start = 0
    return token, rest[1: ]

  else:
    return decode_single_unit(message)

def decode_single_unit(message):
  curr = message[0]
  if curr is 'i':
    return decode_integer(message)
  elif curr.isdigit():
    return decode_string(message)
  else:
    raise "Bencoding error"

def decode_string(message):
  length = re.match(r"^(\d*):", message).group(1)
  length = int(length)

  colon = message.find(':')
  token = message[(colon + 1) : (colon + length + 1)]
  rest = message[(colon + length + 1): ]
  return token, rest

def decode_integer(message):
  token = ''
  start = 1
  while message[start] is not 'e':
    token += message[start]
    start += 1
  return int(token), message[(start + 1): ]













