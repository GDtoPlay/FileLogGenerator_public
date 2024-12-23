import json
import random
import traceback
import datetime

import util

"""
페르소나:
    (확률1, 작업1)
        행위1, 행위2, ...
    (확률2, 작업2)
        행위1
"""

# work, weight
class persona:
    def __init__(self, workWeightList = []):
        self.workWeightList = workWeightList


class work:
    def __init__(self, singleActFlag=True, regularWorkFlag=True, actList=[], originalWeight=0):
        self.singleActFlag = singleActFlag
        self.regularWorkFlag = regularWorkFlag
        self.actList = actList
        self.originalWeight = originalWeight
        self.failCount = 0


    def actSelect(self, workPerson, currentTime):
        actWeightIdxList = []
        totalToDO = 0
        selectedAct = None
        selectedIdx = 0
        oneShotDone = False
        workSkip = False

        if len(self.actList) > 0 and self.actList[0].actType == 'actHold':
            if self.actList[0].actHoldTime < currentTime:
                self.actList = self.actList[1:]

            else:
                workSkip = True
                return (selectedAct, selectedIdx, oneShotDone, workSkip)

        if len(self.actList) > 0 and self.actList[0].oneShotActTag:
            oneShotActTag = self.actList[0].oneShotActTag
            oneShotActions = []
            idx = 0

            for action in self.actList:
                if action.oneShotActTag == oneShotActTag:
                    oneShotActions.append(action)
                    idx += 1

                else:
                    break

            # oneShotActions oneShot 큐에 추가 작업 수행
            holdTime = self.oneShotActSet(workPerson, currentTime, oneShotActions)

            # oneShotActions 삭제 및 이후 작업이 남아 있는 경우 actHold 추가
            if idx < len(self.actList):
                holdAct = act(actType='actHold', actHoldTime=holdTime)
                self.actList = [holdAct] + self.actList[idx:]

            else:
                self.actList = []

            oneShotDone = True

        else:
            for idx, action in enumerate(self.actList):
                # 사전에 모든 작업이 필요한 경우 이후 작업을 수행하지 않을 것이라고 추정
                # oneShotActions도 사전에 모든 작업 수행이 필요한 것으로 간주
                if (action.needAllPreWorkFlag or action.oneShotActTag) and idx != 0:
                    break
                actDoingLen = 0
                if len(action.neededFileSet) == 0:
                    actDoingLen = len(action.actingFileDict)

                elif not action.needAllFileFlag and 'copyFiles' in action.actDetail:
                    actDoingLen = max(int(len(action.actingFileDict) - len(action.neededFileSet)),0)

                elif not action.needAllFileFlag and len(action.neededFileSet) < action.neededFileTotal:
                    actDoingLen = int(len(action.actingFileDict) * (1 - (len(action.neededFileSet)/action.neededFileTotal)))

                if actDoingLen != 0:
                    totalToDO += actDoingLen
                    actWeightIdxList.append((action, actDoingLen, idx))

                elif self.regularWorkFlag:
                    totalToDO += 1
                    actWeightIdxList.append((action, 1, idx))


            #각 actToDoLen / totalToDO로 행동 추출
            randNum = random.random()
            track = 0
            for actWeightIdx in actWeightIdxList:
                track += actWeightIdx[1]
                if randNum * totalToDO < track:
                    selectedAct = actWeightIdx[0]
                    selectedIdx = actWeightIdx[2]
                    break

        return (selectedAct, selectedIdx, oneShotDone, workSkip)


    # oneShotAct는 regular work가 아님
    def oneShotActSet(self, workPerson, currentTime, oneShotActions):
        inOneShotQueue = []

        while oneShotActions:
            actWeightIdxList = []
            totalToDO = 0
            selectedAct = None
            selectedIdx = 0

            for idx, action in enumerate(oneShotActions):
                # 사전에 모든 작업이 필요한 경우 이후 작업을 수행하지 않을 것이라고 추정
                # oneShotActions도 사전에 모든 작업 수행이 필요한 것으로 간주
                if action.needAllPreWorkFlag and idx != 0:
                    break
                actDoingLen = 0
                if len(action.neededFileSet) == 0:
                    actDoingLen = len(action.actingFileDict)

                elif not action.needAllFileFlag and 'copyFiles' in action.actDetail:
                    actDoingLen = max(int(len(action.actingFileDict) - len(action.neededFileSet)),0)

                elif not action.needAllFileFlag and len(action.neededFileSet) < action.neededFileTotal:
                    actDoingLen = int(len(action.actingFileDict) * (1 - (len(action.neededFileSet)/action.neededFileTotal)))

                if actDoingLen != 0:
                    totalToDO += actDoingLen
                    actWeightIdxList.append((action, actDoingLen, idx))

                #각 actToDoLen / totalToDO로 행동 추출
                randNum = random.random()
                track = 0
                for actWeightIdx in actWeightIdxList:
                    track += actWeightIdx[1]
                    if randNum * totalToDO < track:
                        selectedAct = actWeightIdx[0]
                        selectedIdx = actWeightIdx[2]
                        break

            # selectedAct 유사 실행
            oneShotObject = selectedAct.doOneShotSet(workPerson, currentTime)
            inOneShotQueue.append(oneShotObject)

            # currentTime 변경
            timeInterval = datetime.timedelta(seconds=selectedAct.oneShotActTime)
            timeMove = 1 + random.uniform(-0.2, 0.2)

            currentTime = currentTime + timeMove * timeInterval

            # selectedAct 제거
            if not selectedAct.actingFileDict:
                oneShotActions = oneShotActions[:selectedIdx] + oneShotActions[selectedIdx + 1:]

        util.mergeOneShotQueue(inOneShotQueue)
        return currentTime


    def doWork(self, workPerson, currentTime):
        workSuccess = False
        workReSelect = False

        selectedAct, selectedIdx, oneShotDone, workSkip = self.actSelect(workPerson, currentTime)
        if oneShotDone:
            workSuccess = True
            return (workSuccess, workReSelect)

        if workSkip:
            workReSelect = True
            return (workSuccess, workReSelect)

        if not selectedAct:
            return (workSuccess, workReSelect)

        workSuccess = selectedAct.doAct(workPerson, currentTime)

        if workSuccess:
            if not self.regularWorkFlag and not selectedAct.actingFileDict:
                self.actList = self.actList[:selectedIdx] + self.actList[selectedIdx + 1:]

        return (workSuccess, workReSelect)


class act:
    def __init__(self, actType="", actToWho=None, actDetail={}, neededFileSet=None, actingFileDict={}, actCountLimit=-1, actDoneProb=0, doneMessageTargets=[], needAllFileFlag=False, needAllPreWorkFlag=True, passDoneFlag=False, oneShotActTag='', oneShotActTime=0, actHoldTime=None):
        self.actType = actType

        self.actToWho = actToWho

        # act를 위한 기타 데이터
        # peroson의 actDetail 관련(세부 조건 지정용 정보)
        self.actDetail = actDetail

        # files need to do action, and it original total count
        # set of (ID of file, ID of person from)
        # work 생성 시 어떤 작업과 관련된 파일은 내부적으로 미리 세팅됨 -> ID 지칭 가능
        if neededFileSet:
            self.neededFileSet = neededFileSet
        else:
            self.neededFileSet = set()
        self.neededFileTotal = len(self.neededFileSet)

        # files on working
        # actTargetID(작업 대상에 중복이 없는 경우 file ID) :  [file class instants, actCount, fileLoc]
        self.actingFileDict = actingFileDict

        # 한 act에서 파일 처리가 끝나는 확률과 최대 작업 횟수
        # Limit이 -1이면 상시 작업. 카운트 X, 끝나지도 않음 
        self.actCountLimit = actCountLimit
        self.actDoneProb = actDoneProb

        # 각 파일 작업이 끝나면 누구에게 메세지 보낼지
        # [personID1, personID2, ...]
        self.doneMessageTargets = doneMessageTargets

        # 사전에 필요한 파일 모든 것이 준비되어야 작업 가능
        self.needAllFileFlag = needAllFileFlag
        # 이전 단계 작업이 끝나지 않아도 작업을 수행할지
        self.needAllPreWorkFlag = needAllPreWorkFlag
        # 한 파일 작업 종류 시 작업이 끝났다고 알림을 보낼 지
        self.passDoneFlag = passDoneFlag

        # oneShotAct 관련 정보
        self.oneShotActTag = oneShotActTag
        self.oneShotActTime = oneShotActTime
        self.actHoldTime = actHoldTime


    def fileReady(self, fileID, personID=None):
        if personID:
            self.neededFileSet.discard((fileID, None))

        self.neededFileSet.discard((fileID, personID))


    def doAct(self, actPerson, currentTime):
        actTargetID = None
        actFile = None
        actCount = 0
        actFileLoc = ''

        #print(str(actPerson.personID) + " do: " + self.actType)
        neededFiles = []
        for neededFile in self.neededFileSet:
            if not neededFile[0] in neededFiles:
                neededFiles.append(neededFile[0])

        if self.actingFileDict:
            # neededFiles에 없는 파일들만 선택하도록 후보 선정
            candidateDict = {}
            for actTargetID in self.actingFileDict:
                # copy인 경우 파일 제외
                if 'copyFiles' in self.actDetail and actTargetID in self.actDetail['copyFiles']:
                    if not self.actDetail['copyFiles'][actTargetID].fileID in neededFiles:
                        candidateDict[actTargetID] = self.actingFileDict[actTargetID]

                elif not self.actingFileDict[actTargetID][0].fileID in neededFiles:
                    candidateDict[actTargetID] = self.actingFileDict[actTargetID]

            actTargetID, actObject = random.choice(list(candidateDict.items()))
            actFile, actCount, actFileLoc = actObject

        # 작업 수행 (actType, actToWho, actDetail 같은 것을 토대로 actDetail 생성 및 actPerson 행동)
        actSuccess = False
        try:
            if self.actType == 'fileCreate':
                if 'copyFiles' in self.actDetail and actTargetID in self.actDetail['copyFiles']:
                    copyFile = self.actDetail['copyFiles'][actTargetID]
                    actSuccess = actPerson.fileCreate(self.actDetail, currentTime, inNewFile=actFile, copyFile=copyFile)

                else:
                    actSuccess = actPerson.fileCreate(self.actDetail, currentTime, inNewFile=actFile)

            elif self.actType == 'fileRead':
                if actFileLoc == 'email':

                    fileID=None
                    if actFile:
                        fileID = actFile.fileID

                    actSuccess = actPerson.fileRead(self.actDetail, currentTime, emailFileID=fileID)

                elif actFileLoc == 'server':

                    fileID=None
                    if actFile:
                        fileID = actFile.fileID

                    actSuccess = actPerson.fileRead(self.actDetail, currentTime, fileDBKey=fileID)

                elif actFileLoc == 'local':
                    actSuccess = actPerson.fileRead(self.actDetail, currentTime, selectedLocalFile=actFile)

                else:
                    actSuccess = actPerson.fileRead(self.actDetail, currentTime)

            elif self.actType == 'fileWrite':
                actSuccess = actPerson.fileWrite(self.actDetail, currentTime, selectedLocalFile=actFile)

            elif self.actType == 'fileDelete':
                actSuccess = actPerson.fileDelete(self.actDetail, currentTime, selectedLocalFile=actFile)

            elif self.actType == 'fileRegister':
                if 'registerFileHints' in self.actDetail and actTargetID in self.actDetail['registerFileHints']:
                    registerFileHint = self.actDetail['registerFileHints'][actTargetID]
                    actSuccess = actPerson.fileRegister(self.actDetail, currentTime, selectedLocalFile=actFile, registerFileHint=registerFileHint)

                else:
                    actSuccess = actPerson.fileRegister(self.actDetail, currentTime, selectedLocalFile=actFile)

            elif self.actType == 'fileChange':
                changeOwnership = False
                if 'changeOwnership' in self.actDetail:
                    changeOwnership = self.actDetail['changeOwnership']

                fileID=None
                if actFile:
                    fileID = actFile.fileID

                actSuccess = actPerson.fileChange(self.actDetail, currentTime, fileDBKey=fileID, targetPerson=self.actToWho, changeOwnership=changeOwnership)

            elif self.actType == 'fileSend':
                sendAsID=''
                if 'sendAsFiles' in self.actDetail and actTargetID in self.actDetail['sendAsFiles']:
                    sendAsID = self.actDetail['sendAsFiles'][actTargetID]

                if actFileLoc == 'server':

                    fileID=None
                    if actFile:
                        fileID = actFile.fileID

                    actSuccess = actPerson.fileSend(self.actDetail, currentTime, fileDBKey=fileID, targetPerson=self.actToWho, sendAsID=sendAsID)

                elif actFileLoc == 'local':
                    actSuccess = actPerson.fileSend(self.actDetail, currentTime, selectedLocalFile=actFile, targetPerson=self.actToWho, sendAsID=sendAsID)

                else:
                    actSuccess = actPerson.fileSend(self.actDetail, currentTime, targetPerson=self.actToWho, sendAsID=sendAsID)

            elif self.actType == 'fileRequest':
                
                fileID=None
                if actFile:
                    fileID = actFile.fileID

                actSuccess = actPerson.fileRequest(self.actDetail, currentTime, fileDBKey=fileID, targetPerson=self.actToWho)

            elif self.actType == 'fileRequestManage':
                if len(actPerson.fileRequestList) > 0:
                    fileRequest = actPerson.fileRequestList[0]
                    actPerson.fileRequestList = actPerson.fileRequestList[1:]

                    actSuccess = actPerson.fileRequestManage(self.actDetail, currentTime, fileRequest)
                else:
                    actSuccess = False

            elif self.actType == 'fileSendManage':
                if len(actPerson.sendedFileList) > 0:
                    fileSend = actPerson.sendedFileList[0]
                    actPerson.sendedFileList = actPerson.sendedFileList[1:]

                    actSuccess = actPerson.fileSendManage(self.actDetail, currentTime, fileSend)
                else:
                    actSuccess = False

        except Exception as e:
            print(e)
            traceback.print_exc()
            actSuccess = False


        calcActDone = False
        # 파일 복사의 경우 len(self.neededFileSet) == 0이 아니여도 성공적으로 수행한 복사에 대해서 calcActDone 진행
        # 그 외에는act done은 모든 필요 file이 있을 때 부터 계산 시작
        if actSuccess and 'copyFiles' in self.actDetail:
            calcActDone = True
        elif actSuccess and len(self.neededFileSet) == 0 and self.actCountLimit >= 0:
            calcActDone = True

        # 행동 성공 시 완료 처리
        done = False
        if calcActDone:
            if actCount + 1 >= self.actCountLimit:
                self.actingFileDict.pop(actTargetID, None)
                done = True

            else:
                doneProb = random.random()
                if doneProb < self.actDoneProb:
                    self.actingFileDict.pop(actTargetID, None)
                    done = True

                else:
                    self.actingFileDict[actTargetID][1] = actCount + 1

        if self.passDoneFlag and done:
            # 우선 행동자 본인에게 파일 준비가 되었다고 전파
            actPerson.neededFileHandle(actFile.fileID, personID=actPerson.personID)
            for personID in self.doneMessageTargets:
                # Company에서 personID로 person을 찾아서 targetPerson으로 설정
                targetPerson = util.companyInstance.personDict[personID]
                targetPerson.neededFileHandle(actFile.fileID, personID=actPerson.personID)

        return actSuccess


    # oneShotActionSet
    def doOneShotSet(self, actPerson, currentTime):
        actTargetID = None
        actFile = None
        actCount = 0
        actFileLoc = ''

        #print(str(actPerson.personID) + " do: " + self.actType)
        neededFiles = []
        for neededFile in self.neededFileSet:
            if not neededFile[0] in neededFiles:
                neededFiles.append(neededFile[0])

        if self.actingFileDict:
            # neededFiles에 없는 파일들만 선택하도록 후보 선정
            candidateDict = {}
            for actTargetID in self.actingFileDict:
                if not self.actingFileDict[actTargetID][0].fileID in neededFiles:
                    candidateDict[actTargetID] = self.actingFileDict[actTargetID]

            actTargetID, actObject = random.choice(list(candidateDict.items()))
            actFile, actCount, actFileLoc = actObject

        # 작업 수행 (actType, actToWho, actDetail 같은 것을 토대로 actDetail 생성 및 actPerson 행동)
        actParam = {}
        if self.actType == 'fileCreate':
            if 'copyFiles' in self.actDetail and actTargetID in self.actDetail['copyFiles']:
                copyFile = self.actDetail['copyFiles'][actTargetID]

                actParam['inNewFile'] = actFile
                actParam['copyFile'] = copyFile

            else:
                actParam['inNewFile'] = actFile

        elif self.actType == 'fileRead':
            if actFileLoc == 'email':

                fileID=None
                if actFile:
                    fileID = actFile.fileID

                actParam['emailFileID'] = fileID

            elif actFileLoc == 'server':

                fileID=None
                if actFile:
                    fileID = actFile.fileID

                actParam['fileDBKey'] = fileID

            elif actFileLoc == 'local':
                actParam['selectedLocalFile'] = actFile

            else:
                pass

        elif self.actType == 'fileWrite':
            actParam['selectedLocalFile'] = actFile

        elif self.actType == 'fileDelete':
            actParam['selectedLocalFile'] = actFile

        elif self.actType == 'fileRegister':
            if 'registerFileHints' in self.actDetail and actTargetID in self.actDetail['registerFileHints']:
                registerFileHint = self.actDetail['registerFileHints'][actTargetID]

                actParam['selectedLocalFile'] = actFile
                actParam['registerFileHint'] = registerFileHint

            else:
                actParam['selectedLocalFile'] = actFile

        elif self.actType == 'fileChange':
            changeOwnership = False
            if 'changeOwnership' in self.actDetail:
                changeOwnership = self.actDetail['changeOwnership']

            fileID=None
            if actFile:
                fileID = actFile.fileID

            actParam['fileDBKey'] = fileID
            actParam['targetPerson'] = self.actToWho
            actParam['changeOwnership'] = changeOwnership

        elif self.actType == 'fileSend':
            sendAsID=''
            if 'sendAsFiles' in self.actDetail and actTargetID in self.actDetail['sendAsFiles']:
                sendAsID = self.actDetail['sendAsFiles'][actTargetID]

            if actFileLoc == 'server':

                fileID=None
                if actFile:
                    fileID = actFile.fileID

                actParam['fileDBKey'] = fileID
                actParam['targetPerson'] = self.actToWho
                actParam['sendAsID'] = sendAsID

            elif actFileLoc == 'local':
                actParam['selectedLocalFile'] = actFile
                actParam['targetPerson'] = self.actToWho
                actParam['sendAsID'] = sendAsID

            else:
                actParam['targetPerson'] = self.actToWho
                actParam['sendAsID'] = sendAsID

        elif self.actType == 'fileRequest':
            
            fileID=None
            if actFile:
                fileID = actFile.fileID

            actParam['fileDBKey'] = fileID
            actParam['targetPerson'] = self.actToWho

        # Manage류 Act들은 oneShot에 포함되지 않음 (수동적인 행위이기 때문에)
        oneShotObject = (currentTime, actPerson, self, actParam, actPerson.maliciousPlayersTag)


        calcActDone = False
        # 파일 복사의 경우 len(self.neededFileSet) == 0이 아니여도 성공적으로 수행한 복사에 대해서 calcActDone 진행
        # 그 외에는act done은 모든 필요 file이 있을 때 부터 계산 시작
        if 'copyFiles' in self.actDetail:
            calcActDone = True
        elif len(self.neededFileSet) == 0 and self.actCountLimit >= 0:
            calcActDone = True

        # 행동 성공 시 완료 처리
        done = False
        if calcActDone:
            if actCount + 1 >= self.actCountLimit:
                self.actingFileDict.pop(actTargetID, None)
                done = True

            else:
                doneProb = random.random()
                if doneProb < self.actDoneProb:
                    self.actingFileDict.pop(actTargetID, None)
                    done = True

                else:
                    self.actingFileDict[actTargetID][1] = actCount + 1

        if self.passDoneFlag and done:
            # 우선 행동자 본인에게 파일 준비가 되었다고 전파
            actPerson.neededFileHandle(actFile.fileID, personID=actPerson.personID)
            for personID in self.doneMessageTargets:
                # Company에서 personID로 person을 찾아서 targetPerson으로 설정
                targetPerson = util.companyInstance.personDict[personID]
                targetPerson.neededFileHandle(actFile.fileID, personID=actPerson.personID)

        return oneShotObject
