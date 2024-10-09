import json
import random
import datetime

import util
from act import *
from file import *

class person:
    def __init__(self, personID=None, personName=None, personRank=None, personActWeight=10, personActSigma=0.7, actNoneWorkTime=False, actNoneWorkTimeProb=0, partList=[], inPersona=None):
        self.persona = inPersona
        self.personaBackup = None
        self.regularWorkCount = -1

        self.personID = personID
        self.personName = personName
        self.personRank = personRank
        self.personActWeight = personActWeight
        self.personActWeightBackup = personActWeight

        self.personActSigma = personActSigma
        self.personActSigmaBackup = personActSigma

        # 악의적 행동 관련(업무 시간 외 활동)
        self.actNoneWorkTime = actNoneWorkTime
        self.actNoneWorkTimeProb = actNoneWorkTimeProb
        # 업무 시간 외 활동 backup
        self.actNoneWorkTimeBackup = actNoneWorkTime
        self.actNoneWorkTimeProbBackup = actNoneWorkTimeProb


        self.partList = partList
        # 로컬에 저장된 파일 리스트, stack과 유사하게 오래될 수록 앞에 존재
        self.localFileList = []

        # 파일 공유 요청 리스트
        # [(fileID, personID), ... ]
        self.fileRequestList = []
        # 파일 공유 대상 목록 dict
        # {fileID : [personID, ...], ...}
        self.fileShareDict = {}

        # 로컬로 보내진 파일 리스트
        self.sendedFileList = []
        # 전달 받은 파일 저장 목록 dict
        # 전달받은 파일을 사전 생성된 특정한 파일로 저장하도록 지정 (비정기 work 관련)
        # {fileID : [saveFile, ...], ...}
        self.sendedFileSaveDict = {}

        # 어떤 행동을 위해 누구로부터 받은 어떤 파일이 필요한지
        # {fileID : { personID : [act1], ...}, ...}
        self.neededFileForActDict = {}

        # 악의적 행동 시 태그
        # 공백인 경우 악의적 행위중이 아님
        self.maliciousPlayersTag = ''


    def neededFileHandle(self, actFileID, personID=None):
        try:
            if actFileID in self.neededFileForActDict:
                actList = []
                if personID:
                    if None in self.neededFileForActDict[actFileID]:
                        actList += self.neededFileForActDict[actFileID].pop(None, [])
                actList += self.neededFileForActDict[actFileID].pop(personID, [])

                for action in actList:
                    action.fileReady(actFileID, personID=personID)

                # 비여있으면 key 값 actFileID 삭제
                if not self.neededFileForActDict[actFileID]:
                    self.neededFileForActDict.pop(actFileID)
        except Exception as e:
            print(e)
            pass


    #파일 이름으로 로컬 파일 가져오기
    def getFileFromName(self, fileName):
        for localFile in self.localFileList:
            if localFile.fileName == fileName:
                return localFile


    #파일 ID으로 로컬 파일 가져오기
    def getFileFromID(self, fileID):
        for localFile in self.localFileList:
            if localFile.fileID == fileID:
                return localFile


    def singleWorkWeightChange(self):
        idxWeightList = []
        for idx, workWeight in enumerate(self.persona.workWeightList):
            checkWork = workWeight[0]

            if checkWork.singleActFlag:
                checkAct = checkWork.actList[0]

                if checkAct.actType == 'fileRequestManage':
                    changedWeight = len(self.fileRequestList) * checkWork.originalWeight
                    idxWeightList.append((idx, changedWeight))

                elif checkAct.actType == 'fileSendManage':
                    changedWeight = len(self.sendedFileList) * checkWork.originalWeight
                    idxWeightList.append((idx, changedWeight))

        for idxWeight in idxWeightList:
            idx = idxWeight[0]
            changedWeight = idxWeight[1]

            self.persona.workWeightList[idx][1] = changedWeight


    def randomWorkSelect(self):
        totalWorkWeight = 0
        for workWeight in self.persona.workWeightList:
            totalWorkWeight += workWeight[1]

        workNum = totalWorkWeight * random.random() # 0 <= actNum < 1
        selectedWork = None
        track = 0
        outIdx = 0

        for idx, workWeight in enumerate(self.persona.workWeightList):
            track += workWeight[1] # add weight
            if workNum < track:
                selectedWork = workWeight[0]
                outIdx = idx
                break
                
        return (selectedWork, outIdx)


    def doPlay(self, currentTime):
        self.singleWorkWeightChange()

        toDoWork, idx = self.randomWorkSelect()
        workSuccess = toDoWork.doWork(self, currentTime)

        if not toDoWork.regularWorkFlag:
            if workSuccess:
                toDoWork.failCount = 0
                #모든 작업 내용을 수행한 경우
                if not toDoWork.actList:
                    self.persona.workWeightList = self.persona.workWeightList[:idx] + self.persona.workWeightList[idx+1:]

            else:
                toDoWork.failCount = toDoWork.failCount + 1
                #임의로 연속 실패 횟수 상한을 10로 설정
                if toDoWork.failCount > 10:
                    self.persona.workWeightList = self.persona.workWeightList[:idx] + self.persona.workWeightList[idx+1:]
    
    
    # 단일 행동 관련 메소드들
    # 행동 불가 시 행동 없음
    def fileCreate(self, actDetail, currentTime, inNewFile=None, copyFile=None):
        # 로컬에 파일 생성
        # 랜덤 생성 시 조건에 따라 파일 랭크 결정
        # copyFile이 있다면 해당 파일 내용 저장(복합행동 관련)
        if not copyFile:
            if inNewFile:
                newFile = inNewFile
                newFile.createdTime = currentTime
                newFile.lastModifiedTime = currentTime

            else:
                fileRankProb = actDetail['fileRankProb']

                randNum = random.random()
                selectedRank = None
                track = 0

                for rank, prob in fileRankProb.items():
                    track += prob
                    if randNum < track:
                        selectedRank = rank
                        break

                newFileID = util.fileIDGen()
                newFileName = util.createFileName(newFileID)
                newFile = file(newFileID, newFileName, selectedRank, currentTime, currentTime)

        else:
            if inNewFile:
                newFile = copyFile.copy(newFile=inNewFile, currentTime=currentTime, personID=self.personID)

            else:
                newFile = copyFile.copy(currentTime=currentTime, personID=self.personID)

            if 'newFileRank' in actDetail:
                newFile.fileRank = actDetail['newFileRank']

        self.localFileList.append(newFile)
        
        #db에 로그 저장
        util.saveFileLog(currentTime, 'fileCreate', 1, self, newFile)
        return True
    
    
    def fileRead(self, actDetail, currentTime, selectedLocalFile=None, fileDBKey=None):
        # 가지고 있는 파일 중 하나 조회(실행파일 X)
        # 파일을 지정해서 조회하거나 일정 조건에 따라 랜덤하게 선택하여 조회
        # 파일 서버에 저장된 파일을 읽거나 로컬 파일을 읽는 것을 선택 후 조건에 따라 추출(각 1/2)
        # 조건1: 파일 랭크에 따른 확률 조건
        # 조건2: 특정 시간 이후/이전에 마지막으로 수정된 파일
            
        # 로컬에 읽을 파일이 지정되어있는가?
        if selectedLocalFile:
            # selectedLocalFile이 진짜로 로컬에 있는지 확인
            fileInFlag = False
            readFile = None
            for localFile in self.localFileList:
                if localFile.fileID == selectedLocalFile.fileID:
                    readFile = localFile
                    fileInFlag = True
                    break

            if not fileInFlag:
                return False
            # selectedLocalFile로 들어온 File 정보를 토대로 db에 로그 저장
            util.saveFileLog(currentTime, 'fileRead', 1, self, readFile)
            return True
        
        # 파일 서버에 읽을 파일이 지정되어있는가?
        elif fileDBKey:
            # selectedFileKey로 파일 서버에 해당 파일 찾고 저장된 정보를 토대로 db에 로그 저장
            canRead, canWrite = util.checkFileOwnership(fileDBKey, self.personID)
            if not canRead:
                return False
            
            readFile, fileFound = util.getFileWithID(fileDBKey)
            if not fileFound:
                return False

            util.saveFileLog(currentTime, 'fileRead', 0, self, readFile)
            return True
        
        else:
            fileRankProb = actDetail['fileRankProb']
            timeStartDist = actDetail['timeStartDist'] * datetime.timedelta(seconds=1)
            timeEndDist = actDetail['timeEndDist'] * datetime.timedelta(seconds=1)
            
            randNum = random.random()
            selectedRank = None
            track = 0

            for rank, prob in fileRankProb.items():
                track += prob
                if randNum < track:
                    selectedRank = rank
                    break
            
            localOrServer = random.random()
            if localOrServer < 0.5:
                #selectedRank, timeStartDist, timeEndDist 조건에 맞는 로컬 파일 찾고 랜덤 선택
                #이후 선택한 파일을 읽는 행위 db에 로그 저장
                startTime = currentTime - timeStartDist
                endTime = currentTime - timeEndDist
                # startTime <= 타겟 파일 시간 < endTime
                # endTime <= startTime이면 endTime 이전 시간 전체
                filePool = []
                for idx, localFile in enumerate(self.localFileList):
                    if localFile.lastModifiedTime >= endTime:
                        continue

                    elif localFile.fileRank == selectedRank:
                        if startTime <= localFile.lastModifiedTime or endTime <= startTime:
                            filePool.append((idx, localFile))

                # filePool에서 파일 하나 찾고 읽기
                if not filePool:
                    return False

                readIdx, readFile = random.choice(filePool)
                util.saveFileLog(currentTime, 'fileRead', 1, self, readFile)
                return True

            else:
                #selectedRank, timeStartDist, timeEndDist 조건에 맞는 서버 파일 찾고 랜덤 선택
                #이후 선택한 파일을 읽는 행위 db에 로그 저장
                startTime = currentTime - timeStartDist
                endTime = currentTime - timeEndDist
                # startTime <= 타겟 파일 시간 < endTime
                # endTime <= startTime이면 endTime 이전 시간 전체

                readFile, fileFound = util.getFileWithRankTimeOwnership(selectedRank, self.personID, startTime, endTime, 2)
                if not fileFound:
                    return False

                util.saveFileLog(currentTime, 'fileRead', 0, self, readFile)
                return True
    
    
    def fileWrite(self, actDetail, currentTime, selectedLocalFile=None):
        # 로컬에 있는 파일 중 하나 수정(실행파일 X)
        # 파일을 지정해서 수정하거나 일정 조건에 따라 랜덤하게 선택하여 수정
        # 조건1: 파일 랭크에 따른 확률 조건
        # 조건2: 특정 시간 이후/이전에 마지막으로 수정된 파일
        
        # 로컬에 Write할 파일이 지정되어있는가?
        if selectedLocalFile:
            # selectedLocalFile 정보 수정
            # 마지막 write 시간 갱신
            # selectedLocalFile로 들어온 File 정보를 토대로 쓰는 행위 db에 로그 저장
            fileInFlag = False
            writeFile = None
            writeIdx = 0
            for idx, localFile in enumerate(self.localFileList):
                if localFile.fileID == selectedLocalFile.fileID:
                    writeFile = localFile
                    writeIdx = idx
                    fileInFlag = True
                    break

            if not fileInFlag:
                return False
            # selectedLocalFile로 들어온 File 정보를 토대로 db에 로그 저장
            writeFile.fileName = util.rewriteFileName(writeFile.fileName)
            writeFile.lastModifiedTime = currentTime
            self.localFileList = [writeFile] + self.localFileList[:writeIdx] + self.localFileList[writeIdx+1:]

            util.saveFileLog(currentTime, 'fileWrite', 1, self, writeFile)
            return True

        else:
            fileRankProb = actDetail['fileRankProb']
            timeStartDist = actDetail['timeStartDist'] * datetime.timedelta(seconds=1)
            timeEndDist = actDetail['timeEndDist'] * datetime.timedelta(seconds=1)
            
            randNum = random.random()
            selectedRank = None
            track = 0

            for rank, prob in fileRankProb.items():
                track += prob
                if randNum < track:
                    selectedRank = rank
                    break
            
            # selectedRank, lastModifiedTimeTerm, timeDirection 조건에 맞는 로컬 파일 찾고 랜덤 선택
            # 선택한 파일 정보 수정
            # 파일 이름이 바뀔수도 아닐수도 있음 + 마지막 write 시간 갱신
            # 이후 선택한 파일을 쓰는 행위 db에 로그 저장
            startTime = currentTime - timeStartDist
            endTime = currentTime - timeEndDist
            # startTime <= 타겟 파일 시간 < endTime
            # endTime <= startTime이면 endTime 이전 시간 전체
            filePool = []
            for idx, localFile in enumerate(self.localFileList):
                if localFile.lastModifiedTime >= endTime:
                    continue

                elif localFile.fileRank == selectedRank:
                    if startTime <= localFile.lastModifiedTime or endTime <= startTime:
                        filePool.append((idx, localFile))

            # filePool에서 파일 하나 찾고 쓰기, 이후 lastModifiedTime 갱신 후 self.localFileList pop, 재배치
            if not filePool:
                return False

            writeIdx, writeFile = random.choice(filePool)
            writeFile.fileName = util.rewriteFileName(writeFile.fileName)
            writeFile.lastModifiedTime = currentTime
            self.localFileList = [writeFile] + self.localFileList[:writeIdx] + self.localFileList[writeIdx+1:]

            util.saveFileLog(currentTime, 'fileWrite', 1, self, writeFile)
            return True

    
    # 실행파일 실행 - 실제 구현및 고려를 위해서는 추가해야 하는 것이 많아 기획된 기능 없음
    # 컴파일을 어떤 식으로 로그에 반영해야 하는지 논의가 필요 (고려 안할것인지, 코드 파일만 고려해야 하는지 등)
    def fileExecute(self, actDetail, currentTime):
        pass
    
    def fileDelete(self, actDetail, currentTime, selectedLocalFile=None):
        # 로컬에 있는 파일 삭제
        # 시간 범위 

        # 로컬에 Delete할 파일이 지정되어있는가?
        if selectedLocalFile:
            #삭제작업
            fileInFlag = False
            deleteFile = None
            deleteIdx = 0
            for idx, localFile in enumerate(self.localFileList):
                if localFile.fileID == selectedLocalFile.fileID:
                    deleteFile = localFile
                    deleteIdx = idx
                    fileInFlag = True
                    break

            if not fileInFlag:
                return False
            # selectedLocalFile로 들어온 File 정보를 토대로 db에 로그 저장
            self.localFileList = self.localFileList[:deleteIdx] + self.localFileList[deleteIdx+1:]
            
            util.saveFileLog(currentTime, 'fileDelete', 1, self, deleteFile)
            return True

        # 로컬 파일 리스트 조회
        else:
            deleteUploadedProb = actDetail['deleteUploadedProb']
            timeStartDist = actDetail['timeStartDist'] * datetime.timedelta(seconds=1)
            timeEndDist = actDetail['timeEndDist'] * datetime.timedelta(seconds=1)

            deleteUploaded = False
            selectUploaded = random.random()
            if selectUploaded < deleteUploadedProb:
                deleteUploaded = True

            startTime = currentTime - timeStartDist
            endTime = currentTime - timeEndDist
            # startTime <= 타겟 파일 시간 < endTime
            # endTime <= startTime이면 endTime 이전 시간 전체
            filePool = []
            for idx, localFile in enumerate(self.localFileList):
                if localFile.lastModifiedTime >= endTime:
                    continue

                # deleteUploaded이 True라면 localFile.hasUploaded가 True인 것만
                # deleteUploaded이 False라면 localFile.hasUploaded가 False인 것만
                elif (deleteUploaded and localFile.hasUploaded) or not (deleteUploaded or localFile.hasUploaded):
                    if startTime <= localFile.lastModifiedTime or endTime <= startTime:
                        filePool.append((idx, localFile))

            # filePool에서 파일 하나 선택 후 삭제 작업
            if not filePool:
                return False

            deleteIdx, deleteFile = random.choice(filePool)
            self.localFileList = self.localFileList[:deleteIdx] + self.localFileList[deleteIdx+1:]

            util.saveFileLog(currentTime, 'fileDelete', 1, self, deleteFile)
            return True

    
    def fileRegister(self, actDetail, currentTime, selectedLocalFile=None, registerFileHint=None):
        # 중앙 파일 서버에 파일 등록
        # 등록되지 않은 로컬 파일을 올리거나, 이미 등록된 파일을 새롭게 등록(확률과 조건에 따라 결정)
        # 새롭게 등록하는 경우 로컬 파일의 기존 fileDBKey 버리고 새로 받은 fileDBKey 설정
        # registerFileHint: 등록 시 해당 파일 ID로 등록, registerFileHint에 파일 내용 복사(서버 파일 정보를 임시 저장하는 인스턴스)

        # 로컬에 Register할 파일이 지정되어있는가?
        serverSavedFile = None
        if selectedLocalFile:
            #등록작업
            fileInFlag = False
            registerFile = None

            for idx, localFile in enumerate(self.localFileList):
                if localFile.fileID == selectedLocalFile.fileID:
                    registerFile = localFile
                    fileInFlag = True
                    break

            if not fileInFlag:
                return False

            # 파일 랭크를 다르게 업로드 하는 경우
            newFileRank = None
            if 'newFileRank' in actDetail:
                newFileRank = actDetail['newFileRank']

            # selectedLocalFile로 들어온 File 정보를 토대로 db에 로그 저장
            if not registerFileHint:
                serverSavedFile = util.registerLocalFile(registerFile, currentTime, self.personID, newFileRank=newFileRank)

            else:
                serverSavedFile = util.registerLocalFile(registerFile, currentTime, self.personID, registerFileHint=registerFileHint, newFileRank=newFileRank)
            
            util.saveFileLog(currentTime, 'fileRegister', 1, self, serverSavedFile)
            return True

        # 로컬 파일 리스트 조회(등록 안된 오래된 파일 먼저 등록하기 위해)
        else:
            registerUploadedProb = actDetail['registerUploadedProb']
            timeStartDist = actDetail['timeStartDist'] * datetime.timedelta(seconds=1)
            timeEndDist = actDetail['timeEndDist'] * datetime.timedelta(seconds=1)

            registerUploaded = False
            selectUploaded = random.random()
            if selectUploaded < registerUploadedProb:
                registerUploaded = True

            startTime = currentTime - timeStartDist
            endTime = currentTime - timeEndDist
            # startTime <= 타겟 파일 시간 < endTime
            # endTime <= startTime이면 endTime 이전 시간 전체
            filePool = []
            for idx, localFile in enumerate(self.localFileList):
                if localFile.lastModifiedTime >= endTime:
                    continue

                # registerUploaded True라면 localFile.hasUploaded가 True인 것만
                # registerUploaded False라면 localFile.hasUploaded가 False인 것만
                elif (registerUploaded and localFile.hasUploaded) or not (registerUploaded or localFile.hasUploaded):
                    if startTime <= localFile.lastModifiedTime or endTime <= startTime:
                        filePool.append((idx, localFile))

            # filePool에서 파일 하나 선택 후 등록 작업
            if not filePool:
                return False

            # 파일 랭크를 다르게 업로드 하는 경우
            newFileRank = None
            if 'newFileRank' in actDetail:
                newFileRank = actDetail['newFileRank']

            registerIdx, registerFile = random.choice(filePool)
            if not registerFileHint:
                serverSavedFile = util.registerLocalFile(registerFile, currentTime, self.personID, newFileRank=newFileRank)

            else:
                serverSavedFile = util.registerLocalFile(registerFile, currentTime, self.personID, registerFileHint=registerFileHint, newFileRank=newFileRank)

            util.saveFileLog(currentTime, 'fileRegister', 1, self, serverSavedFile)
            return True

    
    def fileChange(self, actDetail, currentTime, fileDBKey=None, targetPerson=None, changeOwnership=False):
        # 중앙 서버에 있는 파일 수정
        # 버전이 달라진 파일 중 하나를 선택
        # changeOwnership이 true이면 소유권의 변경만 수행
        # (unix like)read : 2, Write : 1 (execute는 제외), -인 경우 소유권 박탈
        ownershipChange = 0
        # changeOwnership이 True인 경우 ownershipChange, targetPerson 세팅
        if changeOwnership:
            if not 'givenOwnerships' in actDetail:
                return False

            if not targetPerson and not 'partPersonProb' in actDetail:
                return False

            ownershipChange = random.choice(actDetail['givenOwnerships'])
            ownershipValidationList = [-3, -2, -1, 0, 1, 2, 3]
            if ownershipChange not in ownershipValidationList:
                return False

            if not targetPerson:
                partPersonProb = actDetail['partPersonProb']
                partRandom = random.random()
                selectedPart = None
                selectedPartID = ''
                track = 0

                for partID in partPersonProb:
                    track += partPersonProb[partID]['prob']
                    if partRandom < track:
                        # util.companyInstance : util에 저장된 comapy 인스턴스 글로벌 변수
                        selectedPart = util.companyInstance.partDict[partID]
                        selectedPartID = partID
                        break

                if not selectedPart:
                    return False

                personRankRandom = random.random()
                selectedPersonRank = None
                track = 0

                for personRank in partPersonProb[selectedPartID]:
                    # key가 personRank가 아닌 경우
                    if personRank == 'prob':
                        continue

                    else:
                        track += partPersonProb[selectedPartID][personRank]['prob']
                        if personRankRandom < track:
                            selectedPersonRank = personRank
                            break

                if not selectedPersonRank:
                    return False

                personList = selectedPart.extractPersonsWithRank(selectedPersonRank)

                if not personList:
                    return False

                targetPerson = random.choice(personList)

        if fileDBKey:
            # 중앙 서버에 해당 파일 찾은 후 업데이트
            canRead, canWrite = util.checkFileOwnership(fileDBKey, self.personID)
            if not canWrite:
                return False
            
            writeFile, fileFound = util.getFileWithID(fileDBKey)
            if not fileFound:
                return False

            if changeOwnership:
                isOwnershipChanged = util.tryChangeFileOwnership(fileDBKey, targetPerson.personID, ownershipChange)

                if isOwnershipChanged:
                    util.saveFileLog(currentTime, 'fileChange', 0, self, writeFile, objectPerson=targetPerson, ownershipChange=ownershipChange)

                return True

            newFileName = util.rewriteFileName(writeFile.fileName)
            util.changeFileContent(writeFile.fileID, newFileName, writeFile.fileRank, currentTime)

            util.saveFileLog(currentTime, 'fileChange', 0, self, writeFile)
            return True

        # 파일 랭크, 주어진 시간 영역대, 파일 등록 여부
        else:
            fileRankProb = actDetail['fileRankProb']
            timeStartDist = actDetail['timeStartDist'] * datetime.timedelta(seconds=1)
            timeEndDist = actDetail['timeEndDist'] * datetime.timedelta(seconds=1)

            randNum = random.random()
            selectedRank = None
            track = 0

            for rank, prob in fileRankProb.items():
                track += prob
                if randNum < track:
                    selectedRank = rank
                    break

            # 중앙 파일 서버에서 내가 가진 파일 중 기간 범위 내 파일 랜덤 선택
            startTime = currentTime - timeStartDist
            endTime = currentTime - timeEndDist
            # startTime <= 타겟 파일 시간 < endTime
            # endTime <= startTime이면 endTime 이전 시간 전체
            fileFound = False
            writeFile = None

            if changeOwnership:
                writeFile, fileFound = util.getFileWithRankTimeOwnership(selectedRank, self.personID, startTime, endTime, 3)
                if not fileFound:
                    return False

            else:
                writeFile, fileFound = util.getFileWithRankTimeOwnership(selectedRank, self.personID, startTime, endTime, 1)
                if not fileFound:
                    return False

            if changeOwnership:
                isOwnershipChanged = util.tryChangeFileOwnership(writeFile.fileID, targetPerson.personID, ownershipChange)

                if isOwnershipChanged:
                    util.saveFileLog(currentTime, 'fileChange', 0, self, writeFile, objectPerson=targetPerson, ownershipChange=ownershipChange)

                return True

            newFileName = util.rewriteFileName(writeFile.fileName)
            util.changeFileContent(writeFile.fileID, newFileName, writeFile.fileRank, currentTime)

            util.saveFileLog(currentTime, 'fileChange', 0, self, writeFile)
            return True
            
    
    def fileSend(self, actDetail, currentTime, selectedLocalFile=None, fileDBKey=None, targetPerson=None):
        # 로컬 파일이나 중앙 파일 서버에 존재하는 파일 직접전송
        # 파일과 대상을 지정해서 전송하거나 조건에 따라 전송
        # 조건1: 파일 랭크에 따른 확률 조건
        # 조건2: 대상 부서와 직원 랭크에 따른 확률 조건
        # 조건2는 fileReqManageDict에 있는 조건 정보를 활용하거나 지정 가능
        if not 'partPersonProb' in actDetail:
            if not targetPerson:
                return False

            if not selectedLocalFile and not fileDBKey:
                return False

        sendFile = None
        isFileFromLocal = 0

        if not targetPerson:
            partPersonProb = actDetail['partPersonProb']
            partRandom = random.random()
            selectedPart = None
            selectedPartID = ''
            track = 0

            for partID in partPersonProb:
                track += partPersonProb[partID]['prob']
                if partRandom < track:
                    # util.companyInstance : util에 저장된 comapy 인스턴스 글로벌 변수
                    selectedPart = util.companyInstance.partDict[partID]
                    selectedPartID = partID
                    break

            if not selectedPart:
                return False

            personRankRandom = random.random()
            selectedPersonRank = None
            track = 0

            for personRank in partPersonProb[selectedPartID]:
                # key가 personRank가 아닌 경우
                if personRank == 'prob':
                    continue

                else:
                    track += partPersonProb[selectedPartID][personRank]['prob']
                    if personRankRandom < track:
                        selectedPersonRank = personRank
                        break

            if not selectedPersonRank:
                return False

            personList = selectedPart.extractPersonsWithRank(selectedPersonRank)

            if not personList:
                return False

            targetPerson = random.choice(personList)

            # 자기 자신을 추출했는지 검증(랜덤의 경우 자기 자신은 제외)
            if targetPerson.personID == self.personID:
                return False

        # 지정 파일이 없는 경우
        if not selectedLocalFile and not fileDBKey:
            selectedPart = random.choice(targetPerson.partList)
            selectedPartID = selectedPart.partID

            selectedPersonRank = targetPerson.personRank

            randNum = random.random()
            selectedRank = None
            track = 0

            for rank, prob in partPersonProb[selectedPartID][selectedPersonRank].items():
                # key가 fileRank가 아닌 경우
                if rank == 'prob':
                    continue

                else:
                    track += prob
                    if randNum < track:
                        selectedRank = rank
                        break

            localOrServer = random.random()
            if localOrServer < 0.5:

                filePool = []
                for idx, localFile in enumerate(self.localFileList):
                    if localFile.fileRank == selectedRank:
                        filePool.append((idx, localFile))

                # filePool에서 파일 하나 찾고 보낼 파일 세팅
                if not filePool:
                    return False

                sendIdx, sendFile = random.choice(filePool)
                isFileFromLocal = 1

            else:
                # 읽기 권한을 가진 파일 찾고 세팅
                sendFile, fileFound = util.chooseFile(selectedRank, 'server', self, ownership=2)
                if not fileFound:
                    return False

                isFileFromLocal = 0

        # 지정된 send할 파일이 DB에 있는 경우
        elif fileDBKey:
            canRead, canWrite = util.checkFileCapability(fileDBKey, self.personID)

            if not canRead:
                return False

            sendFile, fileFound = util.getFileWithID(fileDBKey)
            if not fileFound:
                return False

            isFileFromLocal = 0

        elif selectedLocalFile:
            # selectedLocalFile이 진짜로 로컬에 있는지 확인 후 sendFile 세팅
            fileInFlag = False
            for localFile in self.localFileList:
                if localFile.fileID == selectedLocalFile.fileID:
                    sendFile = localFile
                    fileInFlag = True
                    break

            if not fileInFlag:
                return False

            isFileFromLocal = 1

        if not sendFile:
            return False

        #sendFile을 targetPerson에게 전송 후 로깅
        targetPerson.sendedFileList.append((sendFile, self.personID))
        util.saveFileLog(currentTime, 'fileSend', isFileFromLocal, self, sendFile, objectPerson=targetPerson)
        #파일 전송의 경우 수신자에게 필요한 파일을 줬다고 알려주어야 함
        targetPerson.neededFileHandle(sendFile.fileID, personID=self.personID)

        return True

    
    def fileRequest(self, actDetail, currentTime, fileDBKey=None, targetPerson=None):
        # 다른 사람이 가진 중앙 파일 서버에 있는 파일 요청
        # 파일과 대상을 지정해서 요청하거나 조건에 따라 요청(주는 관계라면 받을 가능성이 높다는 가정)
        # 조건1: 파일 랭크에 따른 확률 조건
        # 조건2: 대상 부서와 직원 랭크에 따른 확률 조건
        # 조건2는 fileReqManageDict에 있는 조건 정보를 활용하거나 지정 가능
        requestFile = None
        partPersonProb = None

        # targetPerson이 없는 경우 세팅
        # targetPerson도 fileDBKey도 없는 경우
        if not targetPerson and not fileDBKey:
            partPersonProb = actDetail['partPersonProb']
            partRandom = random.random()
            selectedPart = None
            selectedPartID = ''
            track = 0

            for partID in partPersonProb:
                track += partPersonProb[partID]['prob']
                if partRandom < track:
                    # util.companyInstance : util에 저장된 comapy 인스턴스 글로벌 변수
                    selectedPart = util.companyInstance.partDict[partID]
                    selectedPartID = partID
                    break

            if not selectedPart:
                return False

            personRankRandom = random.random()
            selectedPersonRank = None
            track = 0

            for personRank in partPersonProb[selectedPartID]:
                # key가 personRank가 아닌 경우
                if personRank == 'prob':
                    continue

                else:
                    track += partPersonProb[selectedPartID][personRank]['prob']
                    if personRankRandom < track:
                        selectedPersonRank = personRank
                        break

            if not selectedPersonRank:
                return False

            personList = selectedPart.extractPersonsWithRank(selectedPersonRank)

            if not personList:
                return False

            targetPerson = random.choice(personList)

            # 자기 자신을 추출했는지 검증(랜덤의 경우 자기 자신은 제외)
            if targetPerson.personID == self.personID:
                return False

        # targetPerson이 없는 경우 세팅
        # targetPerson은 없고 fileDBKey는 있는 경우
        elif not targetPerson and fileDBKey:
            targetPerson, personFound = util.getPersonWithFileOwnerships(fileDBKey, 2)
            if not personFound:
                return False

        # 지정 파일이 없는 경우
        if not fileDBKey:
            selectedPart = random.choice(targetPerson.partList)
            selectedPartID = selectedPart.partID

            selectedPersonRank = targetPerson.personRank

            randNum = random.random()
            selectedRank = None
            track = 0

            if not partPersonProb:
                partPersonProb = actDetail['partPersonProb']

            for rank, prob in partPersonProb[selectedPartID][selectedPersonRank].items():
                # key가 fileRank가 아닌 경우
                if rank == 'prob':
                    continue

                else:
                    track += prob
                    if randNum < track:
                        selectedRank = rank
                        break

            # 읽기 권한을 가진 파일 찾고 세팅
            requestFile, fileFound = util.chooseFile(selectedRank, 'server', targetPerson, ownership=2)
            if not fileFound:
                return False

        # 지정된 request할 파일이 DB에 있는 경우
        elif fileDBKey:
            canRead, canWrite = util.checkFileCapability(fileDBKey, targetPerson.personID)

            if not canRead:
                return False

            requestFile, fileFound = util.getFileWithID(fileDBKey)
            if not fileFound:
                return False

        #request할 fileID를 targetPerson에게 전송 후 로깅
        targetPerson.fileRequestList.append((requestFile.fileID, self.personID))
        util.saveFileLog(currentTime, 'fileRequest', 0, self, requestFile, objectPerson=targetPerson)

        return True
        
    # request -> send
    # 하나의 Request에 대응하는 함수
    # fileRequestList에 있는 요청을 처리하기 위한 행동
    def fileRequestManage(self, actDetail, currentTime, fileRequest):
        fileID, personID = fileRequest
        # fileShareDict: 이 파일은 이 사람에게 보내기로 정해졌다고 관리하기 위한 Dict
        # 권한 검사
        canRead, canWrite = util.checkFileOwnership(fileID, self.personID)
        if not canRead:
            return False

        if fileID in self.fileShareDict and personID in self.fileShareDict[fileID]:
            self.fileShareDict[fileID].remove(personID)

            # self.fileShareDict[fileID]가 empty list인 경우 키 삭제
            if not self.fileShareDict[fileID]:
                self.fileShareDict.pop(fileID, None)

            # 파일 전송 시작
            targetPerson = util.companyInstance.personDict[personID]
            sendFile, fileFound = util.getFileWithID(fileID)
            if not fileFound:
                return False

            targetPerson.sendedFileList.append((sendFile, self.personID))
            util.saveFileLog(currentTime, 'fileSend', 0, self, sendFile, objectPerson=targetPerson)
            
            return True
        
        else:
            fileShareProb = actDetail['fileShareProb']
            targetPerson = util.companyInstance.personDict[personID]
            targetPersonParts = targetPerson.partList

            # targetPerson 부서 선택
            canSend = False
            if 'default' in fileShareProb:
                canSend = True

            inDictParts = []
            for targetPersonPart in targetPersonParts:
                if targetPersonPart.partID in fileShareProb:
                    canSend = True
                    inDictParts.append(targetPersonPart.partID)

            if not canSend:
                return False

            partKey = ''
            if not inDictParts:
                partKey = 'default'

            else:
                partKey = random.choice(inDictParts)

            # targetPerson personRank 검사
            if not targetPerson.personRank in fileShareProb[partKey]:
                return False
            targetPersonRank = targetPerson.personRank

            prob = 0
            sendFile, fileFound = util.getFileWithID(fileID)
            if not fileFound:
                return False

            if not sendFile.fileRank in fileShareProb[partKey][targetPersonRank]:
                return False

            else:
                prob = fileShareProb[partKey][targetPersonRank][sendFile.fileRank]

            sendOrNot = random.random()
            if sendOrNot < prob:
                targetPerson.sendedFileList.append((sendFile, self.personID))
                util.saveFileLog(currentTime, 'fileSend', 0, self, sendFile, objectPerson=targetPerson)
                
                return True

            else:
                return False


    # 하나의 send에 대응하는 함수
    # fileSendList로 전달받은 파일들을 처리하기 위한 행동
    def fileSendManage(self, actDetail, currentTime, fileSend):
        inFile, personID = fileSend
        sendedFileID = inFile.fileID

        if sendedFileID in self.sendedFileSaveDict:
            if len(self.sendedFileSaveDict[sendedFileID]) > 0:
                newFile = self.sendedFileSaveDict[sendedFileID].pop()

                self.fileCreate(actDetail, currentTime, inNewFile=newFile, copyFile=inFile)
                self.neededFileHandle(newFile.fileID, personID=self.personID)

                if len(self.sendedFileSaveDict[sendedFileID]) <= 0:
                    self.sendedFileSaveDict.pop(sendedFileID, None)

                return True

            else:
                self.sendedFileSaveDict.pop(sendedFileID, None)


        #아닌 경우 단순 확률 값으로 저장할지 말지 설정하기를 원함
        fileSaveProb = actDetail['fileSaveProb']
        saveOrNot = random.random()
        if saveOrNot < fileSaveProb:
            self.fileCreate(actDetail, currentTime, copyFile=inFile)

            return True

        else:
            return False
    