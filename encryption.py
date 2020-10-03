key = 98

def encryptChar(ch):
    ich = ord(ch)
    return chr(ich + key)


def encrypt(value):
    if value == None:
        return ""
    encrypted = ""
    for ch in str(value):
        encrypted += encryptChar(ch)
    return encrypted

def decryptChar(sIntCode):
    intCode = ord(sIntCode)
    return chr(intCode - key)

def decrypt(encrypted):
    decrypted = ""
    for ch in encrypted:
        decrypted += decryptChar(ch)
    return decrypted

'''
if __name__ == "__main__":
    start = "Sekretny komunikat: !\"#$%&'()*+??-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~ ąęćśżźóĄĘĆŻŹŚÓ"
    print("Start: \t\t" + start)

    encrypted = encrypt(start)
    print("Encrypted:\t" + encrypted)

    decrypted = decrypt(encrypted)
    print("Decrypted:\t" + decrypted)

    print("TEST:\t\t" + str(decrypted == start))
'''
