import csv
import json
import copy
import random
import string
import traceback
import datetime

from file import *
from db import *

baseTime = datetime.datetime.now()
# 전역적으로 사용하는 company class 인스턴스
companyInstance = None
# 전역적으로 사용하는 maliciousPlayers class 인스턴스
maliciousPlayersInstance = None
# 전역적으로 사용하는 OneShotQueue : [(time, (action params))]
oneShotQueue = []


def setBaseTime(inBaseTime):
    global baseTime
    baseTime = inBaseTime


def setCompany(inCompany):
    global companyInstance
    companyInstance = inCompany


def setMaliciousPlayers(inMaliciousPlayers):
    global maliciousPlayersInstance
    maliciousPlayersInstance = inMaliciousPlayers


def setOneShotQueue(inOneShotQueue):
    global oneShotQueue
    oneShotQueue = inOneShotQueue


# oneShotQueue 병합
def mergeOneShotQueue(inOneShotQueue):
    global oneShotQueue
    idx = 0
    inIdx = 0

    newOneShotQueue = []

    while idx < len(oneShotQueue) and inIdx < len(inOneShotQueue):
        if oneShotQueue[idx][0] <= inOneShotQueue[inIdx][0]:
            newOneShotQueue.append(oneShotQueue[idx])
            idx += 1

        else:
            newOneShotQueue.append(inOneShotQueue[inIdx])
            inIdx += 1

    if idx < len(oneShotQueue):
        newOneShotQueue = newOneShotQueue + oneShotQueue[idx:]

    if inIdx < len(inOneShotQueue):
        newOneShotQueue = newOneShotQueue + inOneShotQueue[inIdx:]

    setOneShotQueue(newOneShotQueue)


# oneShotObject 실행
def runOneShotObject(inOneShotObject):
    time, actPerson, action, actParam, maliciousPlayersTag = inOneShotObject
    tmpMaliciousPlayersTag = actPerson.maliciousPlayersTag
    actPerson.maliciousPlayersTag = maliciousPlayersTag

    try:
        if action.actType == 'fileCreate':
            inNewFile = None
            if 'inNewFile' in actParam:
                inNewFile = actParam['inNewFile']

            copyFile = None
            if 'copyFile' in actParam:
                copyFile = actParam['copyFile']

            actPerson.fileCreate(action.actDetail, time, inNewFile=inNewFile, copyFile=copyFile)

        elif action.actType == 'fileRead':
            selectedLocalFile = None
            if 'selectedLocalFile' in actParam:
                selectedLocalFile = actParam['selectedLocalFile']

            fileDBKey = None
            if 'fileDBKey' in actParam:
                fileDBKey = actParam['fileDBKey']

            emailFileID = None
            if 'emailFileID' in actParam:
                emailFileID = actParam['emailFileID']

            actPerson.fileRead(action.actDetail, time, selectedLocalFile=selectedLocalFile, fileDBKey=fileDBKey, emailFileID=emailFileID)

        elif action.actType == 'fileWrite':
            selectedLocalFile = None
            if 'selectedLocalFile' in actParam:
                selectedLocalFile = actParam['selectedLocalFile']

            actPerson.fileWrite(action.actDetail, time, selectedLocalFile=selectedLocalFile)

        elif action.actType == 'fileDelete':
            selectedLocalFile = None
            if 'selectedLocalFile' in actParam:
                selectedLocalFile = actParam['selectedLocalFile']

            actPerson.fileDelete(action.actDetail, time, selectedLocalFile=selectedLocalFile)

        elif action.actType == 'fileRegister':
            selectedLocalFile = None
            if 'selectedLocalFile' in actParam:
                selectedLocalFile = actParam['selectedLocalFile']

            registerFileHint = None
            if 'registerFileHint' in actParam:
                registerFileHint = actParam['registerFileHint']

            actPerson.fileRegister(action.actDetail, time, selectedLocalFile=selectedLocalFile, registerFileHint=registerFileHint)

        elif action.actType == 'fileChange':
            fileDBKey = None
            if 'fileDBKey' in actParam:
                fileDBKey = actParam['fileDBKey']

            targetPerson = None
            if 'targetPerson' in actParam:
                targetPerson = actParam['targetPerson']

            changeOwnership = False
            if 'changeOwnership' in actParam:
                changeOwnership = actParam['changeOwnership']

            actPerson.fileChange(action.actDetail, time, fileDBKey=fileDBKey, targetPerson=targetPerson, changeOwnership=changeOwnership)

        elif action.actType == 'fileSend':
            selectedLocalFile = None
            if 'selectedLocalFile' in actParam:
                selectedLocalFile = actParam['selectedLocalFile']

            fileDBKey = None
            if 'fileDBKey' in actParam:
                fileDBKey = actParam['fileDBKey']

            targetPerson = None
            if 'targetPerson' in actParam:
                targetPerson = actParam['targetPerson']

            sendAsID = ''
            if 'sendAsID' in actParam:
                sendAsID = actParam['sendAsID']

            actPerson.fileSend(action.actDetail, time, selectedLocalFile=selectedLocalFile, fileDBKey=fileDBKey, targetPerson=targetPerson, sendAsID=sendAsID)

        elif action.actType == 'fileRequest':
            fileDBKey = None
            if 'fileDBKey' in actParam:
                fileDBKey = actParam['fileDBKey']

            targetPerson = None
            if 'targetPerson' in actParam:
                targetPerson = actParam['targetPerson']

            actPerson.fileRequest(action.actDetail, time, fileDBKey=fileDBKey, targetPerson=targetPerson)

    except Exception as e:
        print('error on runOneShotObject')
        traceback.print_exc()

    actPerson.maliciousPlayersTag = tmpMaliciousPlayersTag


def runOneShotObjects(currentTime):
    global oneShotQueue

    idx = 0
    for oneShotObject in oneShotQueue:
        if oneShotObject[0] < currentTime:
            runOneShotObject(oneShotObject)
            idx += 1

        else:
            break

    setOneShotQueue(oneShotQueue[idx:])


def setDB():
    createFileServerTable()
    createEmailFileServerTable()
    createFileLogTable()
    createFileOwnershipsTable()

fileCount = 0
fileSubMax = 9999999999
personCount = 0
personSubMax = 99999

def fileIDGen():
    global fileCount, fileSubMax
    fileCount += 1
    if fileCount > fileSubMax:
        print('파일 숫자 임계 크기 초과')
        return ('F' + str(fileCount))

    else:
        zeroCount = len(str(fileSubMax)) - len(str(fileCount))
        return ('F' + '0' * zeroCount + str(fileCount))


def createFileName(fileID):
    retFileName = fileID

    baseString = string.ascii_uppercase + '0123456789'
    suffix = random.choices(baseString, k=6)

    for suffixChar in suffix:
        retFileName += suffixChar

    return retFileName


def createCopyFileName(fileName):
    suffixList = ['', '_cp', '_copy', 'Copy']
    suffix = random.choice(suffixList)

    retFileName = fileName + suffix

    return retFileName


def rewriteFileName(fileName):
    doRewrite = random.random()

    if doRewrite < 0.05:
        baseString = string.ascii_uppercase + '0123456789'
        suffix = random.choices(baseString, k=4)

        retFileName = fileName
        if fileName[-5] == '_':
            retFileName = fileName[:-5]

        retFileName += '_'
        for suffixChar in suffix:
            retFileName += suffixChar

        return retFileName

    else:
        return fileName


def addPersonCount():
    global personCount
    personCount += 1


def personIDGen():
    global personCount, personSubMax
    personCount += 1
    if personCount > personSubMax:
        print('직원 수 임계 크기 초과')
        return ('P' + str(personCount))

    else:
        zeroCount = len(str(personSubMax)) - len(str(personCount))
        return ('P' + '0' * zeroCount + str(personCount))


def setIrregularWorkListPattern(irregularWorkList, probDict):
    for irregularWork in irregularWorkList:
        # personCandidate의 personRankProb 세팅
        for personVar in irregularWork['personCandidate']:
            try:
                personRankProbKey = irregularWork['personCandidate'][personVar]['personRankProb']
                irregularWork['personCandidate'][personVar]['personRankProb'] = probDict['personRankProbs'][personRankProbKey]

            except Exception as e:
                print('There is no: ' + personRankProbKey + ' in personRankProbs')
                raise e

        # relatedFiles의 fileRankProb 세팅
        for fileVar in irregularWork['relatedFiles']:
            if 'fileRankProb' in irregularWork['relatedFiles'][fileVar]:
                try:
                    fileRankProbKey = irregularWork['relatedFiles'][fileVar]['fileRankProb']
                    irregularWork['relatedFiles'][fileVar]['fileRankProb'] = probDict['fileRankProbs'][fileRankProbKey]

                except Exception as e:
                        print('There is no: ' + fileRankProbKey + ' in fileRankProbs')
                        raise e


def setMaliciousIrregularWorkListPattern(irregularWorkList, probDict):
    for irregularWork in irregularWorkList:
        # relatedFiles의 fileRankProb 세팅
        for fileVar in irregularWork['relatedFiles']:
            if 'fileRankProb' in irregularWork['relatedFiles'][fileVar]:
                try:
                    fileRankProbKey = irregularWork['relatedFiles'][fileVar]['fileRankProb']
                    irregularWork['relatedFiles'][fileVar]['fileRankProb'] = probDict['fileRankProbs'][fileRankProbKey]

                except Exception as e:
                        print('There is no: ' + fileRankProbKey + ' in fileRankProbs')
                        raise e


def setPersonaPattern(personaDict, probDict, selfPartID):
    for work in personaDict:
        for act in work['actList']:
            if 'fileRankProb' in act['actDetail']:
                try:
                    fileRankProbKey = act['actDetail']['fileRankProb']
                    act['actDetail']['fileRankProb'] = probDict['fileRankProbs'][fileRankProbKey]

                except Exception as e:
                    print('There is no: ' + fileRankProbKey + ' in fileRankProbs')
                    raise e

            if 'partPersonProb' in act['actDetail']:
                try:
                    partPersonProbKey = act['actDetail']['partPersonProb']
                    tmpPartPersonProb = {}
                    for partID, personProb in probDict['partPersonProbs'][partPersonProbKey].items():
                        if partID == 'self':
                            tmpPartPersonProb[selfPartID] = personProb
                        else:
                            tmpPartPersonProb[partID] = personProb

                    act['actDetail']['partPersonProb'] = tmpPartPersonProb

                except:
                    print('There is no: ' + partPersonProbKey + ' in partPersonProbs')
                    raise e

            if 'fileShareProb' in act['actDetail']:
                try:
                    fileShareProbKey = act['actDetail']['fileShareProb']
                    tmpFileShareProb= {}
                    for partID, personProb in probDict['fileShareProbs'][fileShareProbKey].items():
                        if partID == 'self':
                            tmpFileShareProb[selfPartID] = personProb
                        else:
                            tmpFileShareProb[partID] = personProb

                    act['actDetail']['fileShareProb'] = tmpFileShareProb

                except:
                    print('There is no: ' + fileShareProbKey + ' in fileShareProbs')
                    raise e


def selectPersonRank(personRankProb):
    rankNum = random.random() # 0 <= actNum < 1
    selectedRank = None
    track = 0
    
    for rank in personRankProb:
        track += personRankProb[rank] # add 
        if rankNum < track:
            selectedRank = rank
            break

    return selectedRank


def selectFileRank(fileRankProb):
    rankNum = random.random() # 0 <= actNum < 1
    selectedRank = None
    track = 0
    
    for rank in fileRankProb:
        track += fileRankProb[rank] # add 
        if rankNum < track:
            selectedRank = rank
            break

    return selectedRank


def chooseFile(fileRank, fileExtractLoc, targetPerson=None, ownership=3):
    global baseTime
    if fileExtractLoc == 'email':
        personID = ''

        if not targetPerson:
            return (None, False)

        else:
            personID = targetPerson.personID

        fileDataList = selectEmailFilesWithReciver(personID)

        if fileDataList:
            fileData = random.choice(fileDataList)
            retFileInstance = file(fileData[0], fileData[1], fileData[2], fileData[4], fileData[4])
            retFileInstance.fileRankAssumption = fileData[3]

            return (retFileInstance, True)

        else:
            return (None, False)

    elif fileExtractLoc == 'server':
        # DB에서 파일을 선택한 후 해당 파일 정보를 토대로 파일 인스턴스 생성, 정보 복사 후 리턴
        # 단 실제 저장되거나 사용되면 안되며, act를 위한 정보를 담기 위해 일회용으로 사용되는 것이 전제임
        personID = '*'

        if targetPerson:
            personID = targetPerson.personID

        fileDataList = selectFilesWithRankAndOwnership(fileRank, personID, ownership)

        if fileDataList:
            fileData = random.choice(fileDataList)
            retFileInstance = file(fileData[0], fileData[1], fileData[2], fileData[3], fileData[4])
            retFileInstance.fileRankAssumption = fileData[2]

            return (retFileInstance, True)

        else:
            return (None, False)

    elif fileExtractLoc == 'local':
        if targetPerson:
            fileList = []

            for fileInstance in targetPerson.localFileList:
                if fileRank == fileInstance.fileRank:
                    fileList.append(fileInstance)

            if fileList:
                retFileInstance = random.choice(fileList)

                return (retFileInstance, True)

            else:
                return (None, False)

        else:
            return (None, False)

    else:
        fileID = fileIDGen()
        fileName = createFileName(fileID)
        retFileInstance = file(fileID, fileName, fileRank, baseTime, baseTime)

        return (retFileInstance, True)


def saveFileLog(eventTime, actionType, fileLocVal, subjectPerson, objectFile, objectPerson=None, ownershipChange=0):
    maliciousPlayersTag = subjectPerson.maliciousPlayersTag
    subjectPersonID = subjectPerson.personID
    subjectPersonRank = subjectPerson.personRank
    subjectPersonParts = ''
    for subPart in subjectPerson.partList:
        subjectPersonParts += subPart.partName
        subjectPersonParts += ', '

    subjectPersonParts = subjectPersonParts[:-2]

    objectFileID = objectFile.fileID
    objectFileName = objectFile.fileName
    objectFileRank = objectFile.fileRank
    objectFileRankAssumption = objectFile.fileRankAssumption
    objectFileCreatedTime = objectFile.createdTime
    objectFileLastModifiedTime = objectFile.lastModifiedTime

    objectPersonID=''
    objectPersonRank=''
    objectPersonParts=''

    if objectPerson:
        objectPersonID = objectPerson.personID
        objectPersonRank = objectPerson.personRank
        for subPart in objectPerson.partList:
            objectPersonParts += subPart.partName
            objectPersonParts += ', '

        objectPersonParts = objectPersonParts[:-2]


    insertFileLog(eventTime, actionType, maliciousPlayersTag, subjectPersonID, 
        subjectPersonRank, subjectPersonParts, objectFileID,
        objectFileName, fileLocVal, objectFileRank, objectFileRankAssumption,
        objectFileCreatedTime, objectFileLastModifiedTime, 
        ownershipChange=ownershipChange, objectPersonID=objectPersonID, objectPersonRank=objectPersonRank,
        objectPersonParts=objectPersonParts)


def checkFileCapability(fileID, personID):
    return getFileCapability(fileID, personID)


def checkFileOwnership(fileID, personID):
    return getFileOwnership(fileID, personID)


def tryChangeFileOwnership(fileID, personID, ownershipChange):
    canRead, canWrite = getFileOwnership(fileID, personID)

    #test is there ownership change
    doRead = canRead
    doWrite = canWrite

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

    if canRead == doRead and canWrite == doWrite:
        return False

    updateFileOwnership(fileID, personID, ownershipChange)
    return True


def changeFileContent(fileID, fileName, fileRank, currentTime):
    updateFileData(fileID, fileName, fileRank, currentTime)


def getFileWithID(fileID):
    fileData = selectFileWithID(fileID)

    if not fileData:
        return (None, False)

    else:
        retFileInstance = file(fileData[0], fileData[1], fileData[2], fileData[3], fileData[4])
        retFileInstance.fileRankAssumption = fileData[2]

        return (retFileInstance, True)


def getFileWithRankTimeOwnership(fileRank, personID, startTime, endTime, ownership):
    fileDataList = selectFilesWithRankAndTimeAndOwnership(fileRank, personID, startTime, endTime, ownership)

    if fileDataList:
        fileData = random.choice(fileDataList)
        retFileInstance = file(fileData[0], fileData[1], fileData[2], fileData[3], fileData[4])
        retFileInstance.fileRankAssumption = fileData[2]

        return (retFileInstance, True)

    else:
        return (None, False)


def getEmailFilesWithTime(personID, startTime, endTime):
    fileDataList = selectEmailFilesWithTime(personID, startTime, endTime)

    if fileDataList:
        fileData = random.choice(fileDataList)
        retFileInstance = file(fileData[0], fileData[1], fileData[2], fileData[4], fileData[4])
        retFileInstance.fileRankAssumption = fileData[3]

        return (retFileInstance, True)

    else:
        return (None, False)


def getEmailFilesWithID(personID, fileID):
    fileData = selectEmailFilesWithID(personID, fileID)

    if not fileData:
        return (None, False)

    else:
        retFileInstance = file(fileData[0], fileData[1], fileData[2], fileData[4], fileData[4])
        retFileInstance.fileRankAssumption = fileData[3]

        return (retFileInstance, True)


def getPersonWithFileOwnerships(fileID, ownership):

    selectedIDList = selectPersonsWithFileOwnership(fileID, ownership)
    personIDList = []

    for personID in selectedIDList:
        if not personID == '*':
            personIDList.append(personID)

    if not personIDList:
        return (None, False)

    targetPersonID = random.choice(personIDList)
    targetPerson = companyInstance.personDict[targetPersonID]
    return (targetPerson, True)


def registerEmailFile(sendFile, currentTime, reciverPersonID, senderPersonID, sendAsID=''):
    fileID = ''
    fileName = sendFile.fileName
    fileRank = sendFile.fileRank
    fileRankAssumption = sendFile.fileRankAssumption

    sendedTime = currentTime

    if not sendAsID:
        fileID = fileIDGen()
        
    else:
        fileID = sendAsID

    insertToEmailFileServer(reciverPersonID, senderPersonID, fileID, fileName, fileRank, fileRankAssumption, sendedTime)

    emailSendedFile = file(fileID, fileName, fileRank, currentTime, currentTime)
    emailSendedFile.fileRankAssumption = fileRankAssumption
    return emailSendedFile


def registerLocalFile(registerFile, currentTime, personID, registerFileHint=None, newFileRank=None):
    fileID = ''
    fileName = registerFile.fileName
    fileRank = registerFile.fileRank
    if newFileRank:
        fileRank = newFileRank

    createdTime = currentTime

    registerFile.fileRankAssumption = fileRank
    registerFile.hasUploaded = True

    if not registerFileHint:
        fileID = fileIDGen()
        
    else:
        fileID = registerFileHint.fileID

    insertToFileServer(fileID, fileName, fileRank, createdTime, personID)
    updateFileOwnership(fileID, personID, 3)

    serverSavedFile = file(fileID, fileName, fileRank, createdTime, createdTime)
    serverSavedFile.fileRankAssumption = fileRank
    return serverSavedFile
