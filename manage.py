# Manages the overall process of downloading in sequence
import os
import os.path
import select
import socket
import sys

import client
import metainfo
import peer_connection
import torrent

class Manage(object):
  def __init__(self, meta_file, temp_file = 'temp.bytes'):
    # Parse and store the metafile into an object
    self.meta = metainfo.MetaInfoFile(meta_file)

    # Make a client for your PC
    self.client = client.Client()
    self.sock = 0

    # Get the host and port of the tracker
    self.host, self.port = self.meta.announce_url_and_port
    self.temp_file = temp_file

    # Make a torrent object
    self.torrent_download = torrent.Torrent(self.meta, self.temp_file)

    # make a bytes file where you write the data
    open(temp_file, 'w').close()

  def connect_to_tracker(self):
    timeout = 1

    # Make a socket and connet it to the tracker
    self.sock = client.open_socket_with_timeout(timeout)
    print 'Socket created'

    # Make a connection packet with client attributes and return the
    # response of the tracker
    conection_packet = self.client.make_connection_packet()
    response = self.client.send_packet(self.sock, self.host, self,port, conection_packet)
    return response

  def announce_to_tracker(self):
    announce_packet = self.client.make_announce_packet(self.meta.total_length,
                                                       self.meta.bencoded_info_hash)
    response = self.client.send_packet(self.sock, self.host, self.port, announce_packet)
    return response

  def get_torrent(self):
    # Manage the overall torrent downloading

    CONNECT_ID = 0
    ANNOUNCE_ID = 1

    connection_response = self.connect_to_tracker()
    self.client.check_packet(CONNECTION_ID, connection_response)

    announce_response = self.announce_to_tracker()
    self.client.check_packet(ANNOUNCE_ID, announce_response)

    # Extract peer list from announce response
    peer_list = self.client.get_list_of_peer()

    all_peers = []

    for(ip, port) in peer_list:
      peer = self.client.build_peer((ip, port), self.meta.num_pieces, self.bencoded_info_hash,
                                                self.torrent_download)
      peer.schedule_handshake(self.client.peer_id)
      all_peers.append(peer)

      # Try to connect to all peers
      try:
        peer.sock.connect((peer.ip, peer.port))
      except socket.error as e:
        print e

    # This is a continious loop which runs on all peers until the download is complete
    # downloads data from each readable peer and uploads to each writable peer
    while all_peers:
      redable, writeable, _ = select.select(all_peers, all_peers, [])
      print "\nSelected -- read: %i, write: %i" % (len(readable), len(writeable))

      for peer in writeable:
        print "Writing: " + str(peer)
        peer.send_from_out_buffer()

      for peer in readable:
        print "Reading: " + str(peer)
        status = peer.receive_to_in_buffer()
        if not status:
          all_peer.remove(peer)

      if self.torrent_download.status() == "complete":
        self.sock.close()
        return

  # Writes the downloaded bytes stored in temp file to appropriate files in the directory
  def transfer_file_contents(self, temp_filename, download_path):
    if self.meta.type == 'single':
      full_path = "Downloads/" + self.meta.base_file_name
      print "Writing to file %s" % full_path
      os.rename(temp_filename, full_path)
    else:
      current_location = 0
      for path_elements, length in self.meta.file_info_dict.values():
        path = os.path.join(download_path, self.meta.base_file_name)
        file_name = path_elements.pop()

        for d in path_elements:
          path = os.path.join(path, d)

        if not os.path.exists(path):
          os.makedirs(path)

        full_path = os.path.join(path, file_name)

        with open(temp_filename, "rb") as f:
          f.seek(current_location)
          file_data = f.read(length)

        print "Writing %i bytes to file %s" % (length, full_path)

        with open(full_path, "wb") as f:
          f.write(file_data)

        current_location += length

      # After writing to appropriate directories delete the temp file
      os.remove(temp_filename)

def main():
  if len(sys.argv) < 3 or sys.argv[1][-8:] != ".torrent":
    print "Correct format: python manage.py metainfo_file.torrent Download/Path"
  else:
    metainfo_filename = sys.argv[1]
    download_path = sys.argv[2]
    m = Manage(metainfo_filename)
    m.get_torrent()
    m.transfer_file_contents(m.temp_file, download_path)

if __name__ == '__main__':
  main()





















