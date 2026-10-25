FT_TO_M = 0.3048
FT_TO_MM = 304.8
CFS_TO_LPS = 28.316846592


def ft_to_m(value):
    return None if value is None else value * FT_TO_M


def ft_to_mm(value):
    return None if value is None else value * FT_TO_MM


def cfs_to_lps(value):
    return None if value is None else value * CFS_TO_LPS
