import sqlite3


'''
파일 로그 저장과, 파일 서버 모방을 위한 DB

실제 시스템이라면, 임직원 정보 또한 DB에 저장되어야 하지만,  
'''
con = sqlite3.connect('fileLogGenerator.db', isolation_level= None)
cur = con.cursor()

def createFileServerTable():
    global cur, con
    cur.execute('''CREATE TABLE ServerFiles (
               fileID TEXT PRIMARY KEY, 
               fileName TEXT, 
               fileRank TEXT, 
               createdTime TIMESTAMP, 
               lastModifiedTime TIMESTAMP,
               uploaderPersonID TEXT);''')

    con.commit()


# ownershipChange : 바꾸는 소유권 값
# PersonParts : partName을 partName1, partName2, ... 형식으로 바꾼 text
# isFileFromLocal : 0 or 1
def createFileLogTable():
    global cur, con
    cur.execute('''CREATE TABLE FileLogs (
               eventID INTEGER PRIMARY KEY AUTOINCREMENT,
               eventTime TIMESTAMP,
               actionType TEXT,
               ownershipChange INTEGER,
               maliciousPlayersTag TEXT,
               subjectPersonID TEXT,
               subjectPersonRank TEXT,
               subjectPersonParts TEXT,
               objectFileID TEXT,
               objectFileName TEXT,
               isFileFromLocal INTEGER,
               objectFileRank TEXT,
               objectFileRankAssumption TEXT,
               objectFileCreatedTime TIMESTAMP,
               objectFileLastModifiedTime TIMESTAMP,
               objectPersonID TEXT,
               objectPersonRank TEXT,
               objectPersonParts TEXT);''')

    con.commit()


def createFileOwnershipsTable():
    global cur, con
    cur.execute('''CREATE TABLE FileOwnerships (
               fileID TEXT, 
               personID TEXT,
               fileOnwership INTEGER, 
               FOREIGN KEY (fileID) REFERENCES ServerFiles(fileID));''')

    con.commit()


# createdTime : datetime 클래스 객체
def insertToFileServer(fileID, fileName, fileRank, createdTime, personID):
    global cur, con

    insertQuery = '''INSERT INTO ServerFiles
        (fileID, 
        fileName, 
        fileRank, 
        createdTime, 
        lastModifiedTime, 
        uploaderPersonID) VALUES 
        (?, ?, ?, ?, ?, ?);
        '''

    cur.execute(insertQuery, (fileID, fileName, fileRank, createdTime, createdTime, personID))
    con.commit()


def insertFileLog(eventTime, actionType, maliciousPlayersTag, subjectPersonID, 
    subjectPersonRank, subjectPersonParts, objectFileID,
    objectFileName, isFileFromLocal, objectFileRank, objectFileRankAssumption,
    objectFileCreatedTime, objectFileLastModifiedTime, 
    ownershipChange=0, objectPersonID='', objectPersonRank='',
    objectPersonParts=''):
    global cur, con

    insertQuery = '''INSERT INTO FileLogs
        (eventTime, 
        actionType, 
        ownershipChange, 
        maliciousPlayersTag,
        subjectPersonID, 
        subjectPersonRank,
        subjectPersonParts,
        objectFileID,
        objectFileName,
        isFileFromLocal,
        objectFileRank,
        objectFileRankAssumption,
        objectFileCreatedTime,
        objectFileLastModifiedTime,
        objectPersonID,
        objectPersonRank,
        objectPersonParts) VALUES 
        (?, ?, ?, ?,
        ?, ?, ?,
        ?, ?, ?,
        ?, ?, ?,
        ?, ?, ?, ?);
        '''

    cur.execute(insertQuery, (eventTime, 
        actionType, 
        ownershipChange, 
        maliciousPlayersTag,
        subjectPersonID, 
        subjectPersonRank,
        subjectPersonParts,
        objectFileID,
        objectFileName,
        isFileFromLocal,
        objectFileRank,
        objectFileRankAssumption, 
        objectFileCreatedTime,
        objectFileLastModifiedTime,
        objectPersonID,
        objectPersonRank,
        objectPersonParts))

    con.commit()


def updateFileOwnership(fileID, personID, ownershipChange):
    global cur, con

    checkQuery = '''SELECT fileOnwership FROM FileOwnerships 
        WHERE fileID = ? and personID = ?;
        '''
    cur.execute(checkQuery, (fileID, personID))

    out = cur.fetchone()

    if out:
        currentOnwership = out[0]
        doRead = True if currentOnwership // 2 == 1 else False
        doWrite = True if currentOnwership % 2 == 1 else False

        if ownershipChange > 0:
            addRead = True if ownershipChange // 2 == 1 else False
            addwrite = True if ownershipChange % 2 == 1 else False

            doRead = doRead or addRead
            doWrite = doWrite or addwrite

        else:
            ownershipChange = ownershipChange * -1
            removeRead = True if ownershipChange // 2 == 1 else False
            removewrite = True if ownershipChange % 2 == 1 else False

            doRead = doRead and (not removeRead)
            doWrite = doWrite and (not removewrite)

        newOnwership = 0
        if doWrite:
            newOnwership += 2

        if doRead:
            newOnwership += 1

        updateQuery = '''UPDATE fileOnwerships SET fileOnwership = ?
            WHERE fileID = ? and personID = ?;
            '''

        cur.execute(updateQuery, (newOnwership, fileID, personID))

    else:
        if ownershipChange > 0:
            insertQuery = '''INSERT INTO FileOwnerships
                (fileID,
                personID,
                fileOnwership) VALUES (?, ?, ?)
                '''
        cur.execute(insertQuery, (fileID, personID, ownershipChange))

    con.commit()


def getFileCapability(fileID, personID):
    global cur, con

    selectQuery = '''SELECT fileOnwership FROM FileOwnerships 
        WHERE fileID = ? and personID = ?;
        '''

    cur.execute(selectQuery, (fileID, '*'))
    outA = cur.fetchone()

    cur.execute(selectQuery, (fileID, personID))
    outB = cur.fetchone()

    doRead = False
    doWrite = False

    if outA:
        onwershipA = outA[0]
        doReadA = True if onwershipA // 2 == 1 else False
        doWriteA = True if onwershipA % 2 == 1 else False

        doRead = doRead or doReadA
        doWrite = doWrite or doWriteA

    if outB:
        onwershipB = outB[0]
        doReadB = True if onwershipB // 2 == 1 else False
        doWriteB = True if onwershipB % 2 == 1 else False

        doRead = doRead or doReadB
        doWrite = doWrite or doWriteB

    return (doRead, doWrite)


def getFileOwnership(fileID, personID):
    global cur, con

    selectQuery = '''SELECT fileOnwership FROM FileOwnerships 
        WHERE fileID = ? and personID = ?;
        '''

    cur.execute(selectQuery, (fileID, personID))
    outB = cur.fetchone()

    doRead = False
    doWrite = False

    if outB:
        onwershipB = outB[0]
        doReadB = True if onwershipB // 2 == 1 else False
        doWriteB = True if onwershipB % 2 == 1 else False

        doRead = doRead or doReadB
        doWrite = doWrite or doWriteB

    return (doRead, doWrite)


def updateFileData(fileID, fileName, fileRank, lastModifiedTime):
    global cur, con

    updateQuery = '''UPDATE ServerFiles SET fileName = ?, fileRank = ?, lastModifiedTime = ?
        WHERE fileID = ?;
        '''

    cur.execute(updateQuery, (fileName, fileRank, lastModifiedTime, fileID))

    con.commit()


def selectFileWithID(fileID):
    global cur, con

    selectQuery = '''SELECT fileID, fileName, fileRank, createdTime, lastModifiedTime FROM ServerFiles 
        WHERE fileID = ?;
        '''
    cur.execute(selectQuery, (fileID, ))
    out = cur.fetchone()

    return out


def selectFilesWithRankAndOwnership(fileRank, personID, fileOnwership = 3):
    global cur, con

    if fileOnwership == 1 or 2:
        selectQuery = '''SELECT fileID, fileName, fileRank, createdTime, lastModifiedTime 
            FROM ServerFiles JOIN FileOwnerships USING(fileID)
            WHERE fileRank = ? and personID = ? and (fileOnwership = ? or fileOnwership = 3);
            '''
        cur.execute(selectQuery, (fileRank, personID, fileOnwership))
        out = cur.fetchall()

        return out

    elif ownership == 3:
        selectQuery = '''SELECT fileID, fileName, fileRank, createdTime, lastModifiedTime 
            FROM ServerFiles JOIN FileOwnerships USING(fileID)
            WHERE fileRank = ? and personID = ? and fileOnwership = ?;
            '''
        cur.execute(selectQuery, (fileRank, personID, fileOnwership))
        out = cur.fetchall()

        return out

    else:
        return []


def selectFilesWithRankAndTimeAndOwnership(fileRank, personID, startTime, endTime, ownership):
    global cur, con
    
    if ownership == 1 or ownership == 2:
        if startTime >= endTime:
            selectQuery = '''SELECT fileID, fileName, fileRank, createdTime, lastModifiedTime 
                FROM ServerFiles JOIN FileOwnerships USING(fileID)
                WHERE fileRank = ? and personID = ? and lastModifiedTime < ? 
                and (fileOnwership = ? or fileOnwership = 3);
                '''
            cur.execute(selectQuery, (fileRank, personID, endTime, ownership))
            out = cur.fetchall()

            return out

        else:
            selectQuery = '''SELECT fileID, fileName, fileRank, createdTime, lastModifiedTime 
                FROM ServerFiles JOIN FileOwnerships USING(fileID)
                WHERE fileRank = ? and personID = ? and lastModifiedTime >= ? and lastModifiedTime < ? 
                and (fileOnwership = ? or fileOnwership = 3);
                '''
            cur.execute(selectQuery, (fileRank, personID, startTime, endTime, ownership))
            out = cur.fetchall()

            return out

    elif ownership == 3:
        if startTime >= endTime:
            selectQuery = '''SELECT fileID, fileName, fileRank, createdTime, lastModifiedTime 
                FROM ServerFiles JOIN FileOwnerships USING(fileID)
                WHERE fileRank = ? and personID = ? and lastModifiedTime < ? 
                and fileOnwership = 3;
                '''
            cur.execute(selectQuery, (fileRank, personID, endTime))
            out = cur.fetchall()

            return out

        else:
            selectQuery = '''SELECT fileID, fileName, fileRank, createdTime, lastModifiedTime 
                FROM ServerFiles JOIN FileOwnerships USING(fileID)
                WHERE fileRank = ? and personID = ? and lastModifiedTime >= ? and lastModifiedTime < ? 
                and fileOnwership = 3;
                '''
            cur.execute(selectQuery, (fileRank, personID, startTime, endTime))
            out = cur.fetchall()

            return out

    else:
        return []


def selectFilesWithOwnership(personID):
    global cur, con

    selectQuery = '''SELECT fileID, fileName, fileRank, createdTime, lastModifiedTime 
        FROM ServerFiles JOIN FileOwnerships USING(fileID)
        WHERE personID = ? and fileOnwership = 3;
        '''
    cur.execute(selectQuery, (fileRank, personID))
    out = cur.fetchall()

    return out


def selectPersonsWithFileOwnership(fileID, ownership):
    global cur, con

    if ownership == 1 or ownership == 2:
        selectQuery = '''SELECT personID FROM FileOwnerships 
            WHERE fileID = ? and (fileOnwership = ? or fileOnwership = 3);
            '''

    elif ownership == 3:
        selectQuery = '''SELECT personID FROM FileOwnerships 
            WHERE fileID = ? and fileOnwership = ?;
            '''

    else:
        return []

    cur.execute(selectQuery, (fileRank, personID, fileOnwership))
    out = cur.fetchall()

    return out