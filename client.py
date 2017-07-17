# Look deeply to the unofficial spec for the protocol
import hashlib
import os
import random
import socket
import struct
import sys
import time

import byteconversion
import peer_connection

class ClientException(Exception):
  pass

class Client(object):
  def __init__(self):

    # Set initials for a client
    self.connection_id = int('41727101980', 16)
    self.current_transaction_id = random.getrandbits(31)
    self.peer_id = os.urandom(20)
    self.key = random.getrandbits(31)

    # Define a retry function which call a given function again and again and
    # returns the response
  def retry(function_to_repeat):
    def repeated(*args, **kwargs):
      for _ in range(10):
        try:
          response = function_to_repeat(*args, **kwargs)
          print 'Sent'
          return response
        except socket.error as e:
          print "Error\n"
          print e
    return repeated

  @retry
  # Send a given packet to given ip and port and return the response
  def send_packet(self, sock, host, port, packet):
    sock.sendto(packet, (host, port))
    response = sock.recv(1024)
    return response

  # Make a packet which is required to set a connection
  def make_connection_packet(self):
    action = 0
    connection_packet = byteconversion.pack_binary_string('>qii', self.connection_id, action,
                                                          self.current_transaction_id)
    return connection_packet

  # check if the recieved packet after sending is valid or not
  def check_packet(self, action_sent, response):
    action_recieved = byteconversion.unpack_binary_string('>i', response[:4])[0]
    if(action_recieved != action_sent):
      raise ClientException("Action Error")

    current_transaction_id_recieved = byteconversion.unpack_binary_string('>i', response[4:8])[0]
    if(self.current_transaction_id != current_transaction_id_recieved):
      raise ClientException("Transaction id does not match")
    else:
      if action_recieved == 0:
        print 'Connect packet recieved -- Reseting connection id'
        self.connection_id = byteconversion.unpack_binary_string('>q', response[8:])[0]
      elif action_recieved == 1:
        print 'Announce packet recieved'
      else:
        raise 'Action packet not recieved'


  # Make the announce packet needed to be send to the tracker address
  def make_announce_packet(self, total_file_length, bencoded_info_hash):
    action = 1
    self.current_transaction_id = random.getrandbits(31)
    bytes_downloaded = 0
    bytes_left = total_file_length - bytes_downloaded
    bytes_uploaded = 0
    event = 0
    ip = 0
    num_want = -1
    info_hash = hashlib.sha1(bencoded_info_hash).digest()
    preamble = byteconversion.pack_binary_string('>qii',
                                                 self.connection_id,
                                                 action,
                                                 self.current_transaction_id)
    download_info = byteconversion.pack_binary_string('>qqqiiiih',
                                                      bytes_downloaded,
                                                      bytes_left,
                                                      bytes_uploaded,
                                                      event,
                                                      ip,
                                                      self.key,
                                                      num_want,
                                                      6881)
    return preamble + info_hash + self.peer_id + download_info

  # Get the peer list from the response from thr tracker
  def get_list_of_peers(self, response):
    num_bytes = len(response)
    if num_bytes < 20:
      raise ClientException("Error in getting peers")
    else:
      interval, leechers, peers = byteconversion.unpack_binary_string('iii', response[8:20])
      peers_list = []
      for i in range(peers):
        start_index = (20 + 6 * i)
        end_index = start_index + 6
        ip, port = byteconversion.unpack_binary_string('>IH', response[start_index : end_index])
        ip = socket.inet_ntoa(struct.pack('I', ip))
        print (ip, port)
        peer_list.append((ip, port))
      return peers_list

  # Build a peer for this using the ip and port of this client to exchange data
  # with other peers
  def build_peer(self, (ip, port), num_pieces, info_hash, torrent_download):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(0)
    return peer_connection.PeerConnection(ip, port, sock, num_pieces, info_hash, torrent_download)

# create a socket with the given timeout and type
def open_socket_with_timeout(timeout, type = 'udp'):
  if type == 'tcp':
    type = socket.SOCK_STREAM
  else:
    type = socket.SOCK_DGRAM
  try:
    sock = socket.socket(socket.AF_INET, type)
    sock.settimeout(1)
    return sock
  except socket.error:
    print timeout
    print 'Could not create socket'
    sys.exit()
