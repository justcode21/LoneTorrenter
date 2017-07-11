import math
import bencode
import byteconversion
from collections import OrderedDict

REQUEST_SIZE = 2**14

class MetaInfoFile(object):
    def __init__(self, file_name):
        # Text
        self.bencoded_text = byteconversion.read_binary_file(file_name)
        self.parsed_text = bencode.decode(self.bencoded_text)[0]
        self.parsed_info_hash = self.parsed_text['info']
        self.bencoded_info_hash = bencode.encode(self.parsed_info_hash)

        # File Information
        self.file_info_dict = self.get_file_info_dict()
        self.base_file_name = self.parsed_info_hash['name']
        self.type = "single" if len(self.file_info_dict.keys()) == 1 else "multiple"
        
        # Length and Piece information
        self.total_length = self.get_total_length()
        self.piece_length = self.parsed_info_hash['piece length']
        self.num_pieces = int(len(self.parsed_info_hash['pieces']) / 20)
        self.request_blocks_per_piece = int(math.ceil(float(self.piece_length) / REQUEST_SIZE))
        self.piece_hash = self.parsed_info_hash['pieces']

    # For the user to see the object in string format
    def __str__(self):
        decoded_text = ''
        for key, value in self.parsed_text.iteritems():
            if type(value) is not OrderedDict():
                decodec_text = decoded_text + key + ':' + str(value) + '\n'
            else:
                decoded_text = decoded_text + key + ':' + '\n'
                for key2, value2 in value.iteritems():
                    decoded_text = decoded_text + '---------' + key2 + ':' + str(value2) + '\n'
        return decoded_text           
            
    @property
    # Determines the url and the port of the first tracker
    def announce_url_and_port(self):
        parsed = self.parsed_text['announce'].rstrip('/announce')
        port_index = parsed.rfind(':')
        slash_index = parsed.rfind('/')
        url = parsed[slash_index + 1 : port_index]
        port = parsed[port_index + 1 :]
        try:
            port = int(port)
        except ValueError as e:
            port = 80
        return url, port

    # Save each file length and path in the torrent file
    def get_file_info_dict(self):
        d = OrderedDict()
        if 'length' in self.parsed_info_hash.keys():
            d[0] = [self.parsed_info_hash['name'], self.parsed_info_hash['files']]
        else:
            for i, file in enumerate(self.parsed_info_hash['files']):
                d[i] = [file['path'], file['length']]
        return d

    # Calculates the total length of all the files from each included file
    def get_total_length(self):
        total_length = 0
        for piece_index in self.file_info_dict.keys():
            total_length += self.file_info_dict[piece_index][1]
        return total_length
                
        
        
