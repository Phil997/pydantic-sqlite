import os


def remove_file(name):
    if os.path.isfile(name):
        os.remove(name)

def uniquify(path):
    filename, extension = os.path.splitext(path)
    counter = 1

    while os.path.exists(path):
        path = filename + "_(" + str(counter) + ")" + extension
        counter += 1

    return path
