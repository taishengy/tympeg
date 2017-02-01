from tools import list_files
from os import path


source_prefixes = ['SHANA', 'youiv', '52.iv', '52iv', '3xplanet', 'zzz', 'u15xx', 'u15x', 'Hotidols', 'hotidols',
                   'Thz', 'thz', '21bt']

url_stuff = ['www.', '.com', '.pw', '.in', '.net', '.NET', '.la', '.cc']

vid_info = ['[LQ]', '[HQ]', '480p', '480', '720p', '720', '1080p', '1080', 'FHD', 'HD', '60fps', '60 fps']

specialty = ['[]', '-.', '_', '.']

prefix_stragglers = ['_', '-', '.']


def clean_file_names(dir_path, primary_scrub_list, secondary_scrub_list, prefix_scrub_list, ext_list=[], test=False):

    def split_ext(file_name_s):
        index = file_name_s.rfind('.')
        name_s = file_name_s[:index]
        ext_s = file_name_s[index:]
        return name_s, ext_s

    def scrub_string(s, scrub_list):
        clean_cycle = False
        while not clean_cycle:
            clean_cycle = True
            for sub in scrub_list:
                index = s.find(sub)
                if index > -1:
                    clean_cycle = False
                    pre = s[:index]
                    post = s[index + len(sub):]
                    s = pre + post
        return s

    def clean_first_char(s, scrub_list):
        clean_cycle = False
        while not clean_cycle:
            clean_cycle = True
            try:
                if s[0] in scrub_list:
                    clean_cycle = False
                    s = s[1:]
            except IndexError as IE:
                print("index error at: " + s)
        return s

    def capitalize_code(s, capitalize_error, no_hyp):
        splits = s.split('-')
        if len(splits) == 2 and s.find(' ') < 0:
            s = splits[0].upper() + '-' + splits[1]
        elif len(splits) == 1:
            no_hyp.append(s)
        else:
            capitalize_error.append(s)
        return s

    def auto_hyphen(s, cant):
        name, ext = s.split('.')
        transitions = 0
        previous = False
        position = 0

        if not name[0].isdigit():  # Make sure name doesn't start with number
            for i in name:
                current = i.isdigit()
                if current == previous:
                    transitions += 1
                    position = i
                previous = current

        if transitions == 1:
            s = s[:position] + '-' + s[position:]
        else:
            cant.append(s)

        return s

    if len(ext_list) < 1:
        ext_list = ['.mp4', '.mkv', '.avi', '.m4v', '.wmv', '.webm', '.flv', '.mov', '.mpg', '.mpeg', '.ogg', '.ogv']

    file_names = []
    scrubbed_file_names = []
    for file_path in list_files(dir_path):
        paths, file_name = path.split(file_path)
        file_names.append(file_name)
        scrubbed_file_names.append('')

    # scrub file names, exclude improper extensions, build max_len for printing stuff later
    max_len = 0
    for file_name in file_names:
        name, ext = split_ext(file_name)

        if ext in ext_list:
            scrubbed_file_names[file_names.index(file_name)] = scrub_string(name, primary_scrub_list) + ext
            if scrubbed_file_names[file_names.index(file_name)] != file_names[file_names.index(file_name)]:
                max_len = max(len(file_name), max_len)
        else:
            file_names.remove(file_name)

    # second scrub for every item in scrubbed_file_names. Let's us do index increment instead of lookup
    print(file_names)
    print(scrubbed_file_names)
    print(len(file_names))
    print(len(scrubbed_file_names))
    index = 0
    for file_name in scrubbed_file_names:
        name, ext = split_ext(file_name)
        scrubbed_file_names[index] = scrub_string(name, secondary_scrub_list) + ext
        index += 1

    # final pass to clean up stragglers at front end of filename and capitalize alphabet code, catch hyphens
    index = 0
    cant_capitalize = []
    no_hyphen = []
    print(scrubbed_file_names)
    for file_name in scrubbed_file_names:
        file_name = clean_first_char(file_name, prefix_scrub_list)
        scrubbed_file_names[index] = capitalize_code(file_name, cant_capitalize, no_hyphen)
        index += 1

    # attempt to hyphenate file names
    cant_hyphen = []
    for file_name in no_hyphen:
        auto_hyphen(file_name, cant_hyphen)

    # print results
    if test:
        print("Longest file name was {} characters long!".format(max_len))
        for index in range(len(file_names)):
            old = file_names[index]
            new = scrubbed_file_names[index]
            if new != old:
                print("{0:>{width}} ==> {1}".format(old, new, width=max_len))

        if len(cant_hyphen) > 0:
            print("\nThese files {} can't be auto hyphened!".format(len(cant_hyphen)))
            for i in range(len(cant_hyphen)):
                print("\t{}".format(cant_hyphen[i]))

        if len(cant_capitalize) > 0:
            print("\nCouldn't capitalize {} files: ".format(len(cant_capitalize)))
            for i in range(len(cant_capitalize)):
                print("\t{}".format(cant_capitalize[i]))


main_scrub = source_prefixes + url_stuff + vid_info
second_scrub = specialty
polish = prefix_stragglers
clean_file_names("X:/Dem Gals/JAV/NN & Soft", main_scrub, second_scrub, polish, test=True)
