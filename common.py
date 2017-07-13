def read_int_32(data, cursor):
    bits = data[cursor:cursor+4]
    return int.from_bytes(bits, byteorder="big")

def read_int_16(data, cursor):
    bits = data[cursor:cursor+2]
    return int.from_bytes(bits, byteorder="big")

def read_int_8(data, cursor):
    bits = data[cursor:cursor+1]
    return int.from_bytes(bits, byteorder="big")

def get_variables(A):
    return {
        key:value
        for key, value in A.__dict__.items()
        if not key.startswith('__') and not callable(key)
        }

def indent(block):
    indentation = '    '
    return indentation + ('\n' + indentation).join(block.split('\n'))
