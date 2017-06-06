

def split_timecode(time_code):
    """ Takes a timecode string and returns the hours, minutes and seconds. Does not simplify timecode.

    :param time_code: String of format "HH:MM:SS.S" ex. "01:23:45.6"
    :return: HH (float), MM (float), SS (float)
    """
    hh, mm, ss = time_code.split(':')

    hh = float(hh)
    mm = float(mm)
    ss = float(ss)
    return hh, mm, ss


def concat_timecode(HH, MM, SS):
    """ Takes hours, minutes, and seconds, and returns a timecode string in the format of "HH:MM:SS.S".

    :param HH: int, hours
    :param MM: int, minutes
    :param SS: float, seconds
    :return: String of timecode
    """
    seconds = float(SS)
    seconds += 60 * (float(MM) + (float(HH) * 60))

    return seconds_to_timecode(seconds)


def add_timecodes(time_code_1, time_code_2):
    """ Adds to timecodes together and returns the sum of them.

    :param time_code_1: string, timecode
    :param time_code_2: string, timecode
    :return: string, timecode sum
    """
    summation = timecode_to_seconds(time_code_1) + timecode_to_seconds(time_code_2)

    return seconds_to_timecode(summation)


def subtract_timecodes(start_time, end_time):
    """ Subtracts two timecode strings from each other. Returns a timecode. If remaining time is less than one it
        returns '0:00:00.0'

    :param start_time: String of a timecode that will be subtracted from.
    :param end_time: String of a  timecode that will be subtracting.
    :return: String of a timecode that is the remaining time.
    """
    result = timecode_to_seconds(end_time) - timecode_to_seconds(start_time)
    if result < 0:
        result = 0
        print("Warning: The result of subtract_timecodes is less than 0 seconds:")
        print("\twill return '00:00:00' as timecode.")

    return seconds_to_timecode(result)


def timecode_to_seconds(time_code):
    """ Takes a time code and returns the total time in seconds.

    :param time_code: String of a timecode.
    :return: int, seconds equivalent of the timecode
    """
    HH, MM, SS = split_timecode(time_code)

    SS += 60 * (MM + (HH * 60))

    return SS


def seconds_to_timecode(seconds):
    """
    Converts seconds into a conditioned and simplified timecode string
    :param seconds: float, seconds
    :return: string, timecode in 'HH:MM:SS.SSS' format
    """
    h, s = divmod(seconds, 3600)
    m, s = divmod(s, 60)

    s = round(s * 1000)/1000

    hh = str(int(h))
    mm = str(int(m))
    ss = str(s)

    if len(hh) < 2:
        hh = '0' + hh
    if len(mm) < 2:
        mm = '0' + mm

    if ss.find('.') > 1:
        wholes, decimals = ss.split('.')
    else:
        wholes = ss

    if len(wholes) < 2:
        ss = '0' + ss

    return '{0}:{1}:{2}'.format(hh, mm, ss)


def simplify_timecode(time_code):
    """
    Simplifies a timecode to hours: int, minutes: int [0,59], seconds: float(3 decimals) [0, 59.999]
    :param time_code:
    :return:
    """
    return seconds_to_timecode(timecode_to_seconds(time_code))