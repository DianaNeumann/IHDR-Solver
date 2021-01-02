import sys
import zlib
import colorama
from colorama import Fore

colorama.init(autoreset=True)



PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
CHUNK_SIZE = 4
CHUNK_NAME = 4
CHUNK_CRC = 4  #  CRC A four-byte CRC (Cyclic Redundancy Code) calculated on the preceding bytes in the chunk,
               #  including the chunk type field and chunk data fields, but not including the length field 




def main():
    if len(sys.argv) < 2:
        print('[*] usage: python {} <image file name>'.format(sys.argv[0]))
        exit(-1)

    file_name = sys.argv[1]
    img = open(file_name, 'rb').read()

    if img[:8] != PNG_SIGNATURE:
        print('[-] Input file is not PNG')
        exit(-1)
    
    
    
    # analyzing IHDR chunk 
    ihdr_start = img.index(b'IHDR') - CHUNK_SIZE 
    ihdr_info = analyze_ihdr(img, ihdr_start)

    # if file corrupt 
    idat_start = img.index(b'IDAT') - CHUNK_SIZE 
    if idat_start < 0:
        print('[-] Input file is invalid')
        exit(-1)
    
    compressed_img = b''
    
    while True:
        # find IDAT size
        idat_content_size = int.from_bytes(img[idat_start:idat_start + CHUNK_SIZE], byteorder='big')
        name_start = idat_start + CHUNK_SIZE 
        name_end = name_start + CHUNK_SIZE 

        if img[name_start:name_end] != b'IDAT':
            break

        content_start = idat_start + CHUNK_SIZE + CHUNK_NAME
        content_end = content_start + idat_content_size
        idat_chunk_content = img[content_start:content_end]

       
        compressed_img += idat_chunk_content
       
        idat_start = content_end + CHUNK_CRC


    # decompress the compressed image using DEFLATE algorithm
    decompressed_img = zlib.decompressobj().decompress(compressed_img)
    scanline_length = calculate_scanline_length(ihdr_info)

    real_height = len(decompressed_img) // scanline_length

    # Oh those Russians...
    print(Fore.WHITE+ '[?]', end="") 
    print(' Height in the IHDR {}'.format(hex(ihdr_info['height'])))


    if ihdr_info['height'] == real_height:
        print( Fore.BLUE + '[*]', end="")
        print(' Real Height: {}'.format(hex(real_height)))

        print(Fore.RED + '[+]', end="")
        print(' Size matches\n') 
    else:
        print( Fore.BLUE + '[*]', end="")
        print(' Real Height: {}'.format(hex(real_height)))

        print(Fore.RED + '[!!]',end="")
        print(' Wrong size in the IHDR\n') 
        choice = input('Fix the IHDR? (Y/N)').upper()

        if choice == 'Y':
            height_start = ihdr_start + 12 # 12 bytes
            # content lenght of IHDR is always 13
            crc_start = ihdr_start + CHUNK_SIZE + CHUNK_NAME + 13

            fixed_image = bytearray(img)
            real_height_bytes = real_height.to_bytes(4, byteorder='big')

            fixed_image[height_start:height_start + 4] = real_height_bytes

            real_crc = calc_crc(fixed_image, ihdr_start)
            real_crc_bytes = real_crc.to_bytes(4, byteorder='big')

            fixed_image[crc_start: crc_start + 4] = real_crc_bytes

            # save fixed image
            fixed_file_name = file_name[:file_name.rindex('.')] + '_fixed.png'
            with open(fixed_file_name, 'wb') as fix_f:
                fix_f.write(bytes(fixed_image))
                print('[*] Fixed image save to {}'.format(fixed_file_name))
           





def analyze_ihdr(img, start):
    start = start + CHUNK_SIZE + CHUNK_NAME

    ihdr_info = {
        'width': int.from_bytes(img[start:start+4], byteorder='big'),
        'height': int.from_bytes(img[start+4:start+8], byteorder='big'),
        'bitdepth': int.from_bytes(img[start+8:start+9], byteorder='big'),
        'colortype': int.from_bytes(img[start+9:start+10], byteorder='big'),
        'compression': int.from_bytes(img[start+10:start+11], byteorder='big'),
        'filter': int.from_bytes(img[start+11:start+12], byteorder='big'),
        'interlaced': int.from_bytes(img[start+12:start+13], byteorder='big'),
        'crc': int.from_bytes(img[start+13:start+17], byteorder='big'),
    }

    return ihdr_info


def calculate_scanline_length(ihdr_info):
    colortypes= {
        0: 1,  # greyscale
        2: 3,  # RGB
        3: -1, # indexed: channel containing indices into a palette of colors. NOT IMPLEMENTED
        4: 2,  # grayscale and alpha: level of opacity for each pixel
        6: 4,  # RGB + alpha
    }

    if ihdr_info['colortype'] == 3:
        print("[-] I'm Lazy [-]")
        exit(-1)

    bits_per_pixel = ihdr_info['bitdepth'] * colortypes[ihdr_info['colortype']]
    bits_per_scanline = ihdr_info['width'] * bits_per_pixel

    scanline_length = bits_per_scanline // 8 + 1
    
    return scanline_length



def calc_crc(img, ihdr_start):
    ''' CRC generation algorithm:
        https://www.w3.org/TR/PNG-CRCAppendix.html 
        https://stackoverflow.com/questions/24082305/how-is-png-crc-calculated-exactly
    '''
    chunk = img[ihdr_start + CHUNK_SIZE: ihdr_start + CHUNK_SIZE + CHUNK_NAME + 13] # content lenght of IHDR is always 13
    crc_table = []

    for n in range(256):
        c = n
        for k in range(8):
            if (c & 1) == 1:
                c = 0xEDB88320 ^ ((c >> 1) & 0x7fffffff)
            else:
                c = ((c >> 1) & 0x7fffffff)

        crc_table.append(c)

    c = 0xffffffff

    for byte in chunk:
        c = crc_table[(c ^ byte) & 255] ^ ((c >> 8) & 0xffffff)

    return c ^ 0xffffffff
    




if __name__ == '__main__':
    main()
