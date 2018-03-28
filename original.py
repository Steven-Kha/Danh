from __future__ import print_function
from pathlib import Path
import socket
import sys
import pickle  # for receiving list data
import os.path

# Specifications
# The server shall be invoked as:
# python serv.py <PORT NUMBER>
# <PORT NUMBER> specifies the port at which ftp server accepts connection requests. For example: python serv.py 1234
# The ftp client is invoked as:
# cli <server machine> <server port>
# <server machine> is the domain name of the server (ecs.fullerton.edu). This will be converted into 32 bit IP address using DNS lookup. For example: python cli.py ecs.fullerton.edu 1234
# Upon connecting to the server, the client prints out ftp>, which allows the user to execute the following commands.
# ftp> get <file name> (downloads file <file name> from the server)
# ftp> put <filename> (uploads file <file name> to the server)
# ftp> ls (lists files on the server)
# ftp> quit (disconnects from the server and exits)

bufferSize = 4096
serverName = "localhost"
codingMethod = "UTF-32"


# idt$ = "    "  # Indent so that client feedback looks clean


# Receives a specified number of bytes over a TCP socket
def recvAll(sock, numBytes):
    # The buffer
    recvBuff = ''

    # Keep receiving till all is received
    while len(recvBuff) < numBytes:

        # Attempt to receive bytes
        tmpBuff = sock.recv(numBytes).decode(codingMethod)

        # The other side has closed the socket
        if not tmpBuff:
            break

        # Add the received bytes to the buffer
        recvBuff += tmpBuff

    return recvBuff


# this function creates a socket utilizing a provided port number and server
def createSocket(sportNum):
    # this is where you create a TCP socket
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # this helps us connect to the server
    clientSocket.connect((serverName, int(sportNum)))
    print('Connected to the server port # :', sportNum)

    # here we will return the created socket
    return clientSocket


# Function to upload a file to the server over an ephemeral port #
def uploadFileToServer(fileName, sportNum):
    # Generate an ephemeral port
    print("    ", end=' ')
    tempSocket = createSocket(sportNum)  # function call from create socket

    # Open file
    try:
        file_object = open(fileName, 'r')
    except OSError:
        print("    ", fileName + 'cannot open.')
        tempSocket.close()
        return False

    # file_object = Path(fileName)

    # if file_object.is_file():
    # 	return True
    # else:
    # 	print("    ", 'Cannot open file: ' + fileName)
    # 	tempSocket.close()
    # 	return False

    print("    ", 'Uploading ' + fileName + ' to the server')
    while True:
        # Read data
        data = file_object.read()

        # Make sure file is not empty by reading only EOF
        if data:

            # Get the size of the data read and convert it to string
            dataSize = str(len(data))

            # Prepend 0's to the size string until the size is 10 bytes
            while len(dataSize) < 10:
                dataSize = '0' + dataSize

            # Prepend the size of the data to the
            # file data.
            data = dataSize + data

            # The number of bytes sent
            byteSent = 0

            # Send the data!
            while len(data) > byteSent:
                byteSent += tempSocket.send(data[byteSent:].encode(codingMethod))

        # The file is completely empty
        else:
            break

        print("    ", 'Sent', byteSent, 'bytes.')

    # Close the socket and the file
    file_object.close()
    tempSocket.close()

    return True


# Function to download a file from the server over an ephemeral port #
def downloadFileFromServer(fileName, sportNum):
    # Generate an ephemeral port
    print("    ", end=' ')
    tempSocket = createSocket(sportNum)

    # Receive the first 10 bytes indicating the
    # size of the file
    fileSizeBuff = recvAll(tempSocket, 10)

    # Get the file size
    if fileSizeBuff == '':
        print("    ", 'Nothing received.')
        return False
    else:
        fileSize = int(fileSizeBuff)

    print("    ", 'The file size is', fileSize, 'bytes')

    # Get the file data
    data = recvAll(tempSocket, fileSize)

    # Open file to write to
    fileWriter = open(fileName, 'w+')

    # Write received data to file
    fileWriter.write(data)

    # Close file
    fileWriter.close()

    return True


# *******************************************************************
#							MAIN PROGRAM
# *******************************************************************
def main():
    # if client command line has 3 args. for ex: python client.py localhost 1234
    if len(sys.argv) < 2:
        print('python ' + sys.argv[0] + '<server_port>')

    serverName = 'ecs.fullerton.edu'
    serverPort = int(sys.argv[1])

    primarySocket = createSocket(serverPort)

    while True:
        ans = input('ftp> ')

        # Argument counting using spaces
        ftp_arg_count = ans.count(' ')

        if ftp_arg_count == 1:
            (command, fileName) = ans.split()
        elif ftp_arg_count == 0:
            command = ans

        # Process input
        if command == 'put' and ftp_arg_count == 1:
            # Send the entire command to server: put [file]
            primarySocket.send(ans.encode(codingMethod))

            # Receive an ephemeral port from server to upload the file over
            tempPort = primarySocket.recv(bufferSize).decode(codingMethod)

            print("    ", 'Received ephemeral port #', tempPort)
            success = uploadFileToServer(fileName, tempPort)

            if success:
                print("    ", 'Successfully uploaded file')
                # Get server report
                receipt = primarySocket.recv(1).decode(codingMethod)
                if receipt == '1':
                    print("    ", 'Server successfully received file')
                else:
                    print("    ", 'Server was unable to receive the file')
            else:
                print("    ", 'Unable to upload file')

        elif command == 'get' and ftp_arg_count == 1:
            # Send the entire command to server: get [file]
            primarySocket.send(ans.encode(codingMethod))

            # Receive an ephemeral port from server to download the file over
            tempPort = primarySocket.recv(bufferSize).decode(codingMethod)
            print("    ", 'Received ephemeral port #', tempPort)

            success = downloadFileFromServer(fileName, tempPort)

            # Send success/failure notification to server
            if success:
                print("    ", 'Successfully downloaded file')
                primarySocket.send('1'.encode(codingMethod))
            else:
                print("    ", 'Unable to download file')
                primarySocket.send('0'.encode(codingMethod))

        elif command == 'ls' and ftp_arg_count == 0:
            # Send the entire command to server: ls
            primarySocket.send(ans.encode(codingMethod))

            # Get ephemeral port generated by server
            tempPort = primarySocket.recv(bufferSize).decode(codingMethod)
            print("    ", 'Received ephemeral port #', tempPort)

            # Create ephemeral socket and wait for data
            print("    ", end=' ')
            eSocket = createSocket(tempPort)
            data = eSocket.recv(bufferSize)

            # Need 'pickle.loads' to extract list
            server_dir = pickle.loads(data)

            # Print out directory
            print('\n', "    " + 'Files on server:')
            for line in server_dir:
                print("    ", line)

            eSocket.close()

        elif command == 'quit' and ftp_arg_count == 0:
            print("    ", 'Closing now')

            primarySocket.send(ans.encode(codingMethod))
            primarySocket.close()
            break

        else:
            print("    ", 'Invalid command. Try: put [file], get [file], ls, or quit')


if __name__ == "__main__":
    main()
