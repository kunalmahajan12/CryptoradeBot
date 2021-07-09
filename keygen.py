def getKeys():
    keys = open('keys.txt', "r")
    publicKey = keys.readline().rstrip()
    secretKey = keys.readline()
    return publicKey, secretKey
