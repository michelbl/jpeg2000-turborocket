from common import read_int_32, read_int_16, read_int_8, get_variables, indent


# Read file

def read_jp2(filename):
    with open(filename, 'rb') as f:
        data = f.read()
    return data


# Box bytes (unparsed box)

class BoxBytes(object):
    def __init__(self, data, cursor):
        self.LBox = read_int_32(data, cursor)
        self.TBox = data[cursor+4:cursor+8]
        if self.LBox >= 8:
            pass
        elif self.LBox == 0:
            self.LBox = len(data) - cursor
        else:
            raise ValueError(self.LBox)

        self.DBox = data[cursor+8:cursor+self.LBox]


def read_boxes(data):
    boxes_bytes = []
    cursor = 0
    while cursor < len(data):
        box_bytes = BoxBytes(data, cursor)
        boxes_bytes.append(box_bytes)
        cursor += box_bytes.LBox
    return boxes_bytes



# Boxes

class Box(object):
    SIGNATURE_BOX_TYPE = b'jP  '
    FILE_TYPE_BOX_TYPE = b'ftyp'
    HEADER_BOX_TYPE = b'jp2h'
    IMAGE_HEADER_BOX_TYPE = b'ihdr'
    COLOUR_SPECIFICATION_BOX_TYPE = b'colr'
    RESOLUTION_BOX_TYPE = b'res '
    DEFAULT_DISPLAY_RESOLUTION_BOX_TYPE = b'resd'
    CODESTREAM_BOX_TYPE = b'jp2c'
    UUID_BOX_TYPE = b'uuid'

    @classmethod
    def factory(cls, box_bytes):
        TBox = box_bytes.TBox
        if TBox == cls.SIGNATURE_BOX_TYPE:
            return SignatureBox(box_bytes)
        elif TBox == cls.FILE_TYPE_BOX_TYPE:
            return FileTypeBox(box_bytes)
        elif TBox == cls.HEADER_BOX_TYPE:
            return HeaderBox(box_bytes)
        elif TBox == cls.IMAGE_HEADER_BOX_TYPE:
            return ImageHeaderBox(box_bytes)
        elif TBox == cls.COLOUR_SPECIFICATION_BOX_TYPE:
            return ColourSpecificationBox(box_bytes)
        elif TBox == cls.RESOLUTION_BOX_TYPE:
            return ResolutionBox(box_bytes)
        elif TBox == cls.DEFAULT_DISPLAY_RESOLUTION_BOX_TYPE:
            return DefaultDisplayResolutionBox(box_bytes)
        elif TBox == cls.CODESTREAM_BOX_TYPE:
            return CodestreamBox(box_bytes)
        elif TBox == cls.UUID_BOX_TYPE:
            return UUID_Box(box_bytes)
        else:
            return UnknownBox(box_bytes)

    def __repr__(self):
        return "A " + type(self).__name__ + " filled with the data :\n" + '\n'.join(
            [indent("{}: {}".format(k, v)) for k, v in get_variables(self).items()])

           
class SuperBox(Box):
    def __init__(self, box_bytes):
        content = box_bytes.DBox
        boxes_bytes = read_boxes(content)
        self.boxes = parse_boxes_bytes(boxes_bytes)

    def __repr__(self):
        return "A " + type(self).__name__ + " containing :\n" + '\n'.join(
            [indent(str(e)) for e in self.boxes])


class SignatureBox(Box):
    SIGNATURE_BOX_CONTENT = b'\r\n\x87\n'
    
    def __init__(self, box_bytes):
        assert(box_bytes.TBox == self.SIGNATURE_BOX_TYPE), "ISO 15444-1 p.154"
        assert(box_bytes.LBox == 12), "ISO 15444-1 p.154"
        assert(box_bytes.DBox == self.SIGNATURE_BOX_CONTENT), "ISO 15444-1 p.154"
    
    def __repr__(self):
        return "A quiet signature box"

    
class FileTypeBox(Box):
    BRAND = b'jp2 '
    VERSION = 0
    def __init__(self, box_bytes):
        assert(box_bytes.TBox == self.FILE_TYPE_BOX_TYPE)
        
        content = box_bytes.DBox
        
        self.BR_brand = content[0:4]
        assert self.BR_brand == self.BRAND, "ISO 15444-1 p.155"
        
        self.MinV = read_int_32(content, 4)
        assert self.MinV == self.VERSION, "ISO 15444-1 p.155"

        assert len(content) % 4 == 0
        self.nb_compatibility_list = (len(content) - 8) // 4
        compatibility_list = []
        for i in range(self.nb_compatibility_list):
            compatibility_element = content[8+4*i:12+4*i]
            compatibility_list.append(compatibility_element)
        self.compatibility_list = compatibility_list

    def __repr__(self):
        return "A type box claiming compatibility with " + ', '.join([str(e) for e in self.compatibility_list])


class HeaderBox(SuperBox):
    def __init__(self, box_bytes):
        assert(box_bytes.TBox == self.HEADER_BOX_TYPE)
        
        super().__init__(box_bytes)

class ImageHeaderBox(Box):
    COMPRESSION_TYPE = 7
    
    def __init__(self, box_bytes):
        assert(box_bytes.TBox == self.IMAGE_HEADER_BOX_TYPE)
        
        content = box_bytes.DBox
        assert len(content) == 14
        
        self.height = read_int_32(content, 0)
        self.width = read_int_32(content, 4)
        self.NC_nb_components = read_int_16(content, 8)
        self.BPC_bits_per_components = read_int_8(content, 10)
        
        self.C_compression_type = read_int_8(content, 11)
        assert self.C_compression_type == self.COMPRESSION_TYPE, "ISO 15444-1 p.158"

        self.UnkC_colourspace_unknown = read_int_8(content, 12)
        assert self.UnkC_colourspace_unknown in {0, 1}, "ISO 15444-1 p.159"

        self.IPR_intellectual_property = read_int_8(content, 13)
        assert self.UnkC_colourspace_unknown in {0, 1}, "ISO 15444-1 p.159"


class ColourSpecificationBox(Box):
    def __init__(self, box_bytes):
        assert(box_bytes.TBox == self.COLOUR_SPECIFICATION_BOX_TYPE)
        
        content = box_bytes.DBox
        
        self.METH_specification_method = read_int_8(content, 0)
        assert self.METH_specification_method in {1, 2}, "ISO 15444-1 p.161"

        self.PREC_precedence = read_int_8(content, 1)
        assert self.PREC_precedence == 0, "ISO 15444-1 p.161"

        self.APPROX_colourspace_approximation = read_int_8(content, 2)
        assert self.APPROX_colourspace_approximation == 0, "ISO 15444-1 p.161"
        
        if self.METH_specification_method == 1:
            assert len(content) == 7
            
            self.EnumCS_enumerated_colourspace = read_int_32(content, 3)
            assert self.EnumCS_enumerated_colourspace in {16, 17}, "ISO 15444-1 p.161"
            
        elif self.METH_specification_method == 2:
            self.PROFILE_ICC_profile = content[3:]

    
class ResolutionBox(SuperBox):
    def __init__(self, box_bytes):
        assert(box_bytes.TBox == self.RESOLUTION_BOX_TYPE)

        super().__init__(box_bytes)

    
class DefaultDisplayResolutionBox(Box):
    def __init__(self, box_bytes):
        assert(box_bytes.TBox == self.DEFAULT_DISPLAY_RESOLUTION_BOX_TYPE)
        
        content = box_bytes.DBox
        assert len(content) == 10, "ISO 15444-1 p.173"
        
        self.VRdN = read_int_16(content, 0)
        self.VRdD = read_int_16(content, 2)
        self.HRdN = read_int_16(content, 4)
        self.HRdD = read_int_16(content, 6)
        self.VRdE = read_int_8(content, 8)
        self.HRdE = read_int_8(content, 9)

    
class CodestreamBox(Box):
    def __init__(self, box_bytes):
        assert(box_bytes.TBox == self.CODESTREAM_BOX_TYPE)
        
        self.data = box_bytes.DBox
    
    def __repr__(self):
        return "A mysterious codestream box of length {}".format(len(self.data))
    
    
class UUID_Box(Box):
    def __init__(self, box_bytes):
        assert(box_bytes.TBox == self.UUID_BOX_TYPE)
        
        content = box_bytes.DBox

        self.ID = content[:16]
        
        self.data = content[16:]

    def __repr__(self):
        return "A UUID box with ID {} and DATA {}".format(self.ID, self.data)


class UnknownBox(Box):
    def __init__(self, box_bytes):
        self.box_bytes = box_bytes
        pass
    
    def __repr__(self):
        TBox = self.box_bytes.TBox
        LBox = self.box_bytes.LBox
        return "Unknown TBox {} of length {}".format(TBox, LBox)


def parse_boxes_bytes(boxes_bytes):
    boxes = []
    for box_bytes in boxes_bytes:
        box = Box.factory(box_bytes)
        boxes.append(box)
    return boxes