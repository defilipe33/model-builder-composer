import struct


class GeometryError(ValueError):
    pass


def read_wkb(blob):
    if blob is None:
        return None

    data = bytes(blob)
    if len(data) < 5:
        raise GeometryError("WKB inválido.")

    if data[0] == 0:
        endian = ">"
    elif data[0] == 1:
        endian = "<"
    else:
        raise GeometryError("Byte order WKB inválido.")

    geometry_type = struct.unpack_from(endian + "I", data, 1)[0]
    offset = 5

    if geometry_type == 1:
        x, y = struct.unpack_from(endian + "dd", data, offset)
        return (x, y)

    if geometry_type == 2:
        count = struct.unpack_from(endian + "I", data, offset)[0]
        offset += 4
        points = []
        for _ in range(count):
            x, y = struct.unpack_from(endian + "dd", data, offset)
            offset += 16
            points.append((x, y))
        return points

    raise GeometryError(f"Tipo WKB não suportado: {geometry_type}")
