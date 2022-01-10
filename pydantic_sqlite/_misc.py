import os


def uniquify(path):
    filename, extension = os.path.splitext(path)
    counter = 1

    while os.path.exists(path):
        path = filename + "_(" + str(counter) + ")" + extension
        counter += 1

    return path

def iterable_in_type_repr(type_repr):
    if 'List' in type_repr: 
        return True
    else:
        return False
