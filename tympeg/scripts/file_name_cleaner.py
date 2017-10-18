from os import path, rename

from .. import list_files


def clean_file_names(dir_path, primary_scrub_list, secondary_scrub_list, prefix_scrub_list, ext_list=[],
                     test=False, auto_confirm=False):

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

    def clean_first_last_char(s, scrub_list):
        clean_cycle = False
        na, ex = split_ext(s)
        while not clean_cycle:
            clean_cycle = True
            if na[0] in scrub_list:
                clean_cycle = False
                na = na[1:]
            if na[-1] in scrub_list:
                clean_cycle = False
                na = na[:-1]
        return na + ex

    def capitalize_code(s, capitalize_error, no_hyp):
        splits = s.split('-')
        if len(splits) == 2 and s.find(' ') < 0:
            s = splits[0].upper() + '-' + splits[1]
        elif len(splits) == 1:
            if s not in no_hyp:
                no_hyp.append(s)
        else:
            if s not in capitalize_error:
                capitalize_error.append(s)
        return s

    def auto_hyphen(s, cant):
        na, ex = split_ext(s)
        transitions = 0
        previous = False
        position = 0

        if not na[0].isdigit():  # Make sure na doesn't start with number
            for i in range(len(na)):
                current = na[i].isdigit()
                if current != previous:
                    transitions += 1
                    position = i
                previous = current

        if transitions == 1:
            s = s[:position] + '-' + s[position:]
        else:
            cant.append(s)

        return s

    def log(printer):
        printer()

    def save_log(log_file, old_names, new_names, max_name_length, cant_hyphen, cant_capitalize):
        with open(log_file, 'w', encoding='utf8') as log:
            directory, f = path.split(log_file)
            log.write("Log created for files in {}\n\n\n".format(directory))
            old = new = ''

            for index in range(len(old_names)):
                try:
                    old = file_names[index]
                except IndexError:
                    old = 'Index Error'
                    continue

                try:
                    new = scrubbed_file_names[index]
                except IndexError:
                    new = 'Index Error'
                    continue
                if new != old:
                    log.write("{0:>{width}} ==> {1}\n".format(old, new, width=max_name_length))

            if len(cant_hyphen) > 0:
                log.write("\n\nThese {} file(s) can't be auto hyphened!".format(len(cant_hyphen)))
                file_name = ''
                for i in range(len(cant_hyphen)):
                    try:
                        file_name = cant_hyphen[i]
                    except IndexError:
                        file_name = 'Index Error'
                        continue
                    log.write("\t{}\n".format(file_name))

            if len(cant_capitalize) > 0:
                log.write("\nCouldn't capitalize {} file(s): ".format(len(cant_capitalize)))
                file_name = ''
                for i in range(len(cant_capitalize)):
                    try:
                        file_name = cant_capitalize[i]
                    except IndexError:
                        file_name = 'Index Error'
                    log.write("\t{}\n".format(file_name))

            log.write("\n\nOLD FILE NAMES: {}\n".format(len(old_names)))
            log.write("NEW FILE NAMES: {}\n".format(len(new_names)))
            if len(old_names) != len(new_names):
                log.write("THE NUMBERS ABOVE MUST MATCH BEFORE PROCEEDING!!!\n")
            else:
                log.write("THE NUMBERS ABOVE MATCH, WHICH IS GOOD\n")

        log.close()

    log_file_name = 'renaming_log_file.txt'

    if len(ext_list) < 1:
        ext_list = ['.mp4', '.mkv', '.avi', '.m4v', '.wmv', '.webm', '.flv', '.mov', '.mpg', '.mpeg', '.ogg', '.ogv']

    all_files = []
    for file_path in list_files(dir_path):
        paths, file_name = path.split(file_path)
        all_files.append(file_name)

    # scrub file names, exclude improper extensions, build max_len for printing stuff later
    file_names = []
    scrubbed_file_names = []
    max_len = 0
    for file_name in all_files:
        name, ext = split_ext(file_name)

        if ext in ext_list:
            file_names.append(file_name)
            scrubbed_file_names.append(scrub_string(name, primary_scrub_list) + ext)

            if scrubbed_file_names[file_names.index(file_name)] != file_names[file_names.index(file_name)]:
                max_len = max(len(file_name), max_len)

    # second scrub for every item in scrubbed_file_names. Let's us do index increment instead of lookup
    index = 0
    for file_name in scrubbed_file_names:
        name, ext = split_ext(file_name)
        scrubbed_file_names[index] = scrub_string(name, secondary_scrub_list) + ext
        index += 1

    # final pass to clean up stragglers at front end of filename and capitalize alphabet code, catch hyphens
    index = 0
    cant_capitalize = []
    no_hyphen = []
    for file_name in scrubbed_file_names:
        file_name = clean_first_last_char(file_name, prefix_scrub_list)
        scrubbed_file_names[index] = capitalize_code(file_name, cant_capitalize, no_hyphen)
        index += 1

    # attempt to hyphenate file names
    cant_hyphen = []
    for file_name in no_hyphen:
        new = auto_hyphen(file_name, cant_hyphen)
        scrubbed_file_names[scrubbed_file_names.index(file_name)] = new
        scrubbed_file_names[scrubbed_file_names.index(new)] = capitalize_code(new, cant_capitalize, no_hyphen)


    #exact same stuff happens when writing to log, should probably consolidate
    print("Longest file name was {} characters long!".format(max_len))
    for index in range(len(file_names)):
        old = file_names[index]
        new = scrubbed_file_names[index]
        if new != old:
            print("{0:>{width}} ==> {1}".format(old, new, width=max_len))

    if len(cant_hyphen) > 0:
        print("\nThese {} file(s) can't be auto hyphened!".format(len(cant_hyphen)))
        for i in range(len(cant_hyphen)):
            print("\t{}".format(cant_hyphen[i]))

    if len(cant_capitalize) > 0:
        print("\nCouldn't capitalize {} file(s): ".format(len(cant_capitalize)))
        for i in range(len(cant_capitalize)):
            print("\t{}".format(cant_capitalize[i]))

    # ask for confirmation
    valid_input = False
    if auto_confirm:
        valid_input = True
        confirm = 'y'
    else:
        confirm = ''
    while not valid_input:
        confirm = input("Review file name changes. Rename? (y/n): ")
        if confirm == 'y' or confirm == 'n':
            valid_input = True

    if confirm == 'n':
        return
    elif confirm == 'y':
        save_log(path.join(dir_path, log_file_name), file_names, scrubbed_file_names, max_len, cant_hyphen,
                 cant_capitalize)
        if len(scrubbed_file_names) != len(file_names):
            # GTFO, something's not right
            message = "THERES A MISMATCH IN NUMBER OF OLD VS NEW FILENAMES"
            print("\n\n\n")
            print("\n{:-^{width}}\n".format('ABORTING', width=len(message) + 1))
            print(message)
            print("OLD FILE NAMES: {}".format(len(file_names)))
            print("NEW FILE NAMES: {}".format(len(scrubbed_file_names)))
            print("\n{:-^{width}}\n".format('ABORTING', width=len(message) + 1))

        else:
            for file_name in file_names:
                old_file_path = path.join(dir_path, file_name)
                new_file_path = path.join(dir_path, scrubbed_file_names[file_names.index(file_name)])

                if old_file_path != new_file_path:
                    if not test:
                        try:
                            rename(old_file_path, new_file_path)
                        except OSError:
                            with open(path.join(dir_path, log_file_name), 'a') as log:
                                log.write("\n File at {}\nalready exists. Not renaming\n".format(new_file_path))
                            log.close()
                            print("File at {}\nalready exists. Skipping.".format(new_file_path))
                            continue

                    elif test:
                        print(old_file_path)
                        print(new_file_path)
                        print("TESTING")
                        print()
                    else:
                        print("SOMETHING WENT WRONG RIGHT AT THE END, NOT FILES ABOVE")
                        print()
            print("\n\nDONE")



