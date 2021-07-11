def getKeys():
    keys = open('keys.txt', "r")
    publicKey = keys.readline().rstrip()
    secretKey = keys.readline().rstrip()
    return publicKey, secretKey
