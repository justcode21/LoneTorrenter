# Facilitates message passing with each peer.

import bitstring
import hashlib
import socket
import warnings

import client
import byteconversion
import session
import torrent

MSEEAGE_TYPE_DICT = {
                        'choke' : 0,
                        'unchoke' : 1,
                        'interested' : 2,
                        'not-interested' : 3,
                        'have' : 4,
                        'bitfield' : 5,
                        'request' : 6,
                        'piece' : 7,
                        'cancel' : 8,
                        'port' : 9    }

class PeerConnection(object):

  def __init__(self, ip, port, sock, num_pieces, info_hash, torrent_download):
    self.ip = ip
    self.port.= port
    self.sock = sock
    self.status = 'unverified'
    self.last_message_scheduled = None
    self.in_buffer = ''
    self.out_buffer = ''
    self.pieces = [0] * (num_pieces)
    self.info_hash_digest = hashlib.sha1(info_hash).digest()
    self.torrent_download = torrent_download
    self.num_outstanding_requests = 0

  def fileno(self):
    return self.sock.fileno()

 # Methods to parse incoming peer-to-peer messages.
 # Peerconnection and torrent objects are updated regularly

 # Verify the respone received from the received handshake
 def verify_response_handshake(self, response_handshake):
  if len(response_handshake) < 68:
    return False
  pstrlen_received = byteconversion.unpack_binary_string('>B', response_handshake[0])[0]
  pstr_received = response_handshake[1: 20]
  reserved_received = byteconversion.unpack_binary_string('>8B', response_handshake[20:28])
  info_hash_received = response_handshake[28 : 48]

  if pstrlen_received != 19
    return False
  if pstr_received != 'BitTorrent protocol':
    return False
  if info_hash != self.info_hash_digest:
    return False
  return True

  def parse_choke(self, packet, length):
    self.status = 'chocked'

  def parse_and_respond_to_unchoke(self, packet, length):
    self.status = 'unchocked'
    status = self.schedule_request();

  def pare_bitfield(self, packet, length):
    bitstr = bitstring.BitArray(bytes = packet[5 : length + 4])

    for i, have_bit in enumerate(bitstr):
      try:
        self.pieces[i] = 1 if have_bit else 0
      except IndexError:
        if have_bit:
          warnings.warn("Spare bits set in bitfield.", RuntimeWarning)
    if i > len(self.pieces) + 8:
      warnings.warn("Incorrect sized bitfield.", RuntimeWarning)

  def parse_have(self, packet, length):
    piece_num = byteconversion.unpack_binary_string('>I', packet[5 : length + 4])[0]
    print "++++++++++++++++++++ have: " + str(piece_num)
    try:
      self.pieces[piece_num] = 1
    except IndexError:
      warnings.warn("Piece index out of range", RuntimeWarning)

  def parse_piece(self, packet, length):
    index, begin = byteconversion.unpack_binary_string('>II', packet[5 : 13])
    block = packet[13 : length + 4]
    print "++++++++++++++++++++ piece (length: %i, piece: %i, begin: %i)" % (len(block), index, begin)

    self.torrent_download.process_piece(index, begin, block)
    self.num_outstanding_requests -= 1
    status = self.schedule_request()
    self.last_message_scheduled = "request"

  # Function to cordinate and call each parsing function from each received message
  def parse_and_update_status_from_message(self, packet, length, message_id):
    MESSAGE_ID_DICT = {  0 : self.parse_choke,
                         1 : self.parse_and_respond_to_unchoke,
                         4 : self.parse_have,
                         5 : self.parse_bitfield,
                         7 : self.parse_piece }
    if int(message_id) in MESSAGE_ID_DICT:
      MESSAGE_ID_DICT[message_id](packet, length)
    else:
      print "++++++++++++++++++++ Message not implemented."


  # Methods for forming and scheduling outgoinf peer to peer messages, according
  # to the current status of the download(torrent object)

  # Peerconnection is updated accordingly

  # To make a handshake package to be send to other peers
  def make_handshake(self, client_peer_id):
    pstr = 'BitTorrent protocol'
    pstrlen = byteconversion.pack_binary_string('>B', len(pstr))
    reserved = byteconversion.pack_binary_string('>8B', 0, 0, 0, 0, 0, 0, 0, 0)
    handshake_packet = pstrlen + pstr + reserved + self.info_hash_digest + client_peer_id
    return handshake_packet

  # To make a handshake and record it in output buffer
  def schedule_handshake(self, client_peer_id):
    handshake = self.make_handshake(client_peer_id)
    self.out_buffer += handshake
    self.last_message_scheduled = 'handshake'

  def schedule_interested(self):
    interested_message = byteconversion.pack_binary_string('>IB', 1, 2)
    self.out_buffer += interested_message

  def schedule_request(self):
    # Wait until peer has returned a requested block before requesting another.
    if self.num_outstanding_requests < 1:
    peer_has_piece = False
    while not peer_has_piece:
      next = self.torrent_download.strategically_get_next_request()
      index, begin, length = next
      peer_has_piece = self.pieces[index]

    request_message = byteconversion.pack_binary_string('>IBIII', 13, 6, index, begin, length)
    print "....... scheduled request for piece %i, byte-offset %i (%i bytes)" % (index, begin, length)
    self.out_buffer += request_message
    self.num_outstanding_requests += 1

  #Manage the input and output buffer
  def handle_in_buffer(self):

    # Process first complete message (if one exists) in PeerConnection's incoming
    # message buffer. Remove bytes in this message from in-buffer.
    # Returns True if a complete message has been parsed, and False
    # if buffer did not contain a complete message.'''

    print "**** handle in buffer, length: %i\n" % len(self.in_buffer)

    if(self.in_buffer) <= 3:
      return False

    if self.verify_response_handshake(self.in_buffer):
      self.in_buffer = self.in_buffer[68 : ]
      print "Handhsake Verified"
      self.status = 'chocked'
      self.schedule_interested()
      self.last_message_scheduled = 'interested'
      return True

    if self.status == 'chocked':
      self.schedule_interested()
      self.last_message_scheduled = 'interested'

    if self.status == 'unchocked':
      status = self.schedule_interested()
      self.last_message_scheduled = "request"

    length = int(byteconversion.unpack_binary_string('>I', self.in_buffer[:4])[0])

    if len(self.in_buffer) < int(length) + 4:
      return False # Complete message not yet arrived

    # Keep alive message has length 0 -- and no id
    if length == 0:
      self.in_buffer = self.in_buffer[4:]
      return True

    message_id = int(byteconversion.unpack_binary_string('>B', self.in_buffer[4])[0])
    status = self.parse_and_update_status_from_message(self.in_buffer[: length + 4], length, message_id)

    self.in_buffer = self.in_buffer[length + 4:]
    return True

  # Sends from PeerConnection's buffer of scheduled messages, if possible.
  # Any successfully sent bytes are removed from buffer.
  def send_from_out_buffer(self):

   print "**** processing out buffer, length: %(length)i\n" % {"length" : len(self.out_buffer)}
   try:
    sent = self.sock.send(self.out_buffer)
    self.out_buffer = self.out_buffer[sent: ]
    print "Sent %i bytes" % sent
  except socket.error as e:
      print "Sent 0 bytes (" + repr(e) + ")"

  # Receive to the in buffer of the peer and dispatch to handle_in_buffer
  def receive_to_in_buffer(self):
    try:
      respone = self.sock.recv(1024)
      if not response:
        return False
      self.in_buffer += response
      status = self.handle_in_buffer()
      while status in True:
        status = self.handle_in_buffer()
    except socket.error as e:
      print "Receive failed (" + repr(e) + ")"
    return True
















