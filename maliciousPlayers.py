import json
import random
import copy

import util
from act import *

class maliciousPlayers:
    def __init__(self):
        self.maliciousPlayersSetting = {}
        self.personaPreset = {}
        self.probPreset = {}

        self.runningMaliciousPlayersEndInfo = {}


    def setMaliciousPlayersDict(self, maliciousPlayersJsonFile, personaPresetJsonFile, probPresetJsonFile):
        maliciousPlayersJson = open(maliciousPlayersJsonFile, 'r')
        self.maliciousPlayersSetting = json.load(maliciousPlayersJson)

        personaPresetJson = open(personaPresetJsonFile, 'r')
        self.personaPreset = json.load(personaPresetJson)

        probPresetJson = open(probPresetJsonFile, 'r')
        self.probPreset = json.load(probPresetJson)


    def endMaliciousPlayers(self, roundCount):
        # 키 삭제용 리스트
        popMaliciousPlayersTags = []
        for maliciousPlayersTag in self.runningMaliciousPlayersEndInfo:
            endConditions = self.runningMaliciousPlayersEndInfo[maliciousPlayersTag]['endConditions']
            personIDList = self.runningMaliciousPlayersEndInfo[maliciousPlayersTag]['personIDList']

            allEndFlag = False

            if endConditions['round'] <= roundCount:
                for personID in personIDList:
                    maliciousPlayer = util.companyInstance.personDict[personID]

                    # 원복
                    maliciousPlayer.persona = maliciousPlayer.personaBackup
                    maliciousPlayer.personActWeight = maliciousPlayer.personActWeightBackup
                    maliciousPlayer.personActSigma = maliciousPlayer.personActSigmaBackup
                    maliciousPlayer.actNoneWorkTime = maliciousPlayer.actNoneWorkTimeBackup
                    maliciousPlayer.actNoneWorkTimeProb = maliciousPlayer.actNoneWorkTimeProbBackup
                    maliciousPlayer.regularWorkCount = -1
                    maliciousPlayer.maliciousPlayersTag = ''

                    allEndFlag = True

            elif 'worksLenOnOrBelow' in endConditions:
                worksLenOnOrBelow = endConditions['worksLenOnOrBelow']
                newPersonIDList = []
                for personID in personIDList:
                    maliciousPlayer = util.companyInstance.personDict[personID]

                    if len(maliciousPlayer.persona.workWeightList) <= worksLenOnOrBelow:
                        # workWeightList의 길이가 짧아 worksLenOnOrBelow가 충족된 경우 원복
                        maliciousPlayer.persona = maliciousPlayer.personaBackup
                        maliciousPlayer.personActWeight = maliciousPlayer.personActWeightBackup
                        maliciousPlayer.personActSigma = maliciousPlayer.personActSigmaBackup
                        maliciousPlayer.actNoneWorkTime = maliciousPlayer.actNoneWorkTimeBackup
                        maliciousPlayer.actNoneWorkTimeProb = maliciousPlayer.actNoneWorkTimeProbBackup
                        maliciousPlayer.regularWorkCount = -1
                        maliciousPlayer.maliciousPlayersTag = ''

                    else:
                        newPersonIDList.append(personID)

                if len(newPersonIDList) == 0:
                    allEndFlag = True

                elif len(personIDList) != len(newPersonIDList):
                    self.runningMaliciousPlayersEndInfo[maliciousPlayersTag]['personIDList'] = newPersonIDList

            # 모든 player가 제 역활을 한 경우 endInfo dict 키 삭제 필요, 키 삭제용 리스트에 추가
            if allEndFlag:
                popMaliciousPlayersTags.append(maliciousPlayersTag)

        for maliciousPlayersTag in popMaliciousPlayersTags:
            self.runningMaliciousPlayersEndInfo.pop(maliciousPlayersTag, None)


    def startMaliciousPlayersCheck(self, roundCount):
        for maliciousPlayersTag in list(self.maliciousPlayersSetting.keys()):
            startRoundCount = self.maliciousPlayersSetting[maliciousPlayersTag]['startCondition']['round']
            if startRoundCount <= roundCount:
                self.startMaliciousPlayers(maliciousPlayersTag)


    def startMaliciousPlayers(self, maliciousPlayersTag):
        maliciousPlayersInfo = self.maliciousPlayersSetting[maliciousPlayersTag]

        # 기본 페르소나 세팅
        personIDList = []
        for personID in maliciousPlayersInfo['players']:
            personIDList.append(personID)
            maliciousPlayer = util.companyInstance.personDict[personID]

            # 기존 정보 백업
            maliciousPlayer.personaBackup = maliciousPlayer.persona
            maliciousPlayer.personActWeightBackup = maliciousPlayer.personActWeight
            maliciousPlayer.personActSigmaBackup = maliciousPlayer.personActSigma
            maliciousPlayer.actNoneWorkTimeBackup = maliciousPlayer.actNoneWorkTime
            maliciousPlayer.actNoneWorkTimeProbBackup = maliciousPlayer.actNoneWorkTimeProb

            personaType = maliciousPlayersInfo['players'][personID]['personaPattern']
            personActWeight = maliciousPlayersInfo['players'][personID]['personActWeight']
            personActSigma = maliciousPlayersInfo['players'][personID]['personActSigma']
            actNoneWorkTime = maliciousPlayersInfo['players'][personID]['actNoneWorkTime']
            actNoneWorkTimeProb = maliciousPlayersInfo['players'][personID]['actNoneWorkTimeProb']

            maliciousPlayerPartIDWeights = []
            for maliciousPlayerPart in maliciousPlayer.partList:
                maliciousPlayerPartIDWeights.append((maliciousPlayerPart.partID, maliciousPlayerPart.partWeight))

            maliciousPersonaWorkWeightList = []
            for maliciousPlayerPartIDWeight in maliciousPlayerPartIDWeights:
                maliciousPlayerPartID = maliciousPlayerPartIDWeight[0]
                maliciousPlayerPartWeight = maliciousPlayerPartIDWeight[1]
                try:
                    loadedPersona = copy.deepcopy(self.personaPreset[personaType])
                    util.setPersonaPattern(loadedPersona, self.probPreset, maliciousPlayerPartID)

                except Exception as e:
                    print('There is no: ' + personaType + ' in personaPreset')
                    raise e

                for workData in loadedPersona:
                    singleActFlag = workData['singleActFlag']
                    regularWorkFlag = workData['regularWorkFlag']
                    workWeight = workData['workWeight'] * maliciousPlayerPartWeight
                    actList = []

                    for actData in workData['actList']:
                        actType = actData['actType']
                        actDetail = actData['actDetail']
                        tmpAct = act(actType=actType, actDetail=actDetail)

                        actList.append(tmpAct)

                    tmpWork = work(singleActFlag=singleActFlag, regularWorkFlag=regularWorkFlag, actList=actList, originalWeight=workWeight)
                    maliciousPersonaWorkWeightList.append([tmpWork, workWeight])

            newPersona = persona(workWeightList=maliciousPersonaWorkWeightList)

            # 새 페르소나 및 필요 값 세팅
            maliciousPlayer.persona = newPersona
            maliciousPlayer.personActWeight = personActWeight
            maliciousPlayer.personActSigma = personActSigma
            maliciousPlayer.actNoneWorkTime = actNoneWorkTime
            maliciousPlayer.actNoneWorkTimeProb = actNoneWorkTimeProb
            maliciousPlayer.regularWorkCount = -1
            maliciousPlayer.maliciousPlayersTag = maliciousPlayersTag

        # 비정기 작업 관련 세팅('irregularWorks' 키 값이 있는 경우)
        if 'irregularWorks' in self.maliciousPlayersSetting[maliciousPlayersTag]:
            irregularWorkList = self.maliciousPlayersSetting[maliciousPlayersTag]['irregularWorks']
            util.setMaliciousIrregularWorkListPattern(irregularWorkList, self.probPreset)

            for irregularWork in irregularWorkList:
                activeCountMin = irregularWork['activeCountMin']
                activeCountMax = irregularWork['activeCountMax']

                activeCount = random.randrange(activeCountMin, activeCountMax + 1)
                for count in range(activeCount):
                    self.irregularWorkSetting(irregularWork, personIDList)

        self.runningMaliciousPlayersEndInfo[maliciousPlayersTag] = {}
        self.runningMaliciousPlayersEndInfo[maliciousPlayersTag]['endConditions'] = self.maliciousPlayersSetting[maliciousPlayersTag]['endConditions']
        self.runningMaliciousPlayersEndInfo[maliciousPlayersTag]['personIDList'] = personIDList

        self.maliciousPlayersSetting.pop(maliciousPlayersTag, None)


    # part.py의 company class의 같은 이름의 메소드를 변형
    # 인물은 이미 지정되어있으니, partVarDict을 생성할 필요 없음
    # personVarDict도 그냥 아이디를 알고 있음으로 아이디 값으로 dict만 만들어 줌(랜덤 추출 필요 없음)
    def irregularWorkSetting(self, irregularWork, personIDList):
        personVarDict = {}
        for personID in personIDList:
            personVarDict[personID] = util.companyInstance.personDict[personID]

        #set file candidate
        #파일은 중복 가능
        fileVarDict = {}
        fullyExtracted = False
        while not fullyExtracted:
            initKeyList = list(fileVarDict.keys())
            for fileVar in irregularWork['relatedFiles']:
                if fileVar in fileVarDict:
                    continue

                extractInfo = irregularWork['relatedFiles'][fileVar]

                # 상위 변수에서 지정된 파일 중 몇개를 선택하는 경우
                # 또는 1대1 대응되는 새 파일 아이디 지정이 필요한 경우(랭크 동일)
                if 'upperVar' in extractInfo:
                    if not extractInfo['upperVar'] in fileVarDict:
                        continue

                    extractedFileList = []
                    if 'oneToOneNewVar' in extractInfo and extractInfo['oneToOneNewVar']:
                        try:
                            for upperFile in fileVarDict[extractInfo['upperVar']]:
                                extractedFile, isExtracted = util.chooseFile(upperFile.fileRank, '')

                                if not isExtracted:
                                    # 추출 실패
                                    return False

                                extractedFileList.append(extractedFile)

                        except:
                            return False

                    else:
                        extractCount = random.randrange(extractInfo['extractCountMin'], extractInfo['extractCountMax'] + 1)
                        extractCount = min(len(fileVarDict[extractInfo['upperVar']]), extractCount)
                        try:
                            extractedFileList = random.sample(fileVarDict[extractInfo['upperVar']], extractCount)

                        except:
                            # 갯수 지정 이상 존재
                            return False

                    fileVarDict[fileVar] = extractedFileList

                # 직접 파일은 선택해서 지정하는 경우
                else:
                    extractCount = random.randrange(extractInfo['extractCountMin'], extractInfo['extractCountMax'] + 1)
                    extractedFileList = []

                    for i in range(extractCount):
                        selectedFileRank = util.selectFileRank(extractInfo['fileRankProb'])
                        targetPerson = None

                        if extractInfo['fileSource'] in personVarDict:
                            targetPerson = personVarDict[extractInfo['fileSource']]

                        extractedFile, isExtracted = util.chooseFile(selectedFileRank, extractInfo['fileExtractLoc'], targetPerson=targetPerson)

                        if not isExtracted:
                            # 추출 실패
                            return False

                        extractedFileList.append(extractedFile)

                    fileVarDict[fileVar] = extractedFileList

            keyList = list(fileVarDict.keys())

            if len(initKeyList) == len(keyList):
                fullyExtracted = True

        # 완전 추출 성공 여부 검증
        for fileVar in irregularWork['relatedFiles']:
            if not fileVar in fileVarDict:
                return False

        # work 세팅 시작
        for personVar in irregularWork['personsWorksInfo']:
            workInfo = irregularWork['personsWorksInfo'][personVar]
            workingPerson = personVarDict[personVar]

            actList = []
            for actInfo in workInfo['actList']:
                # actTargetFiles가 비어있는 경우 act 추가 스킵
                if 'actTargetFiles' in actInfo and not fileVarDict[actInfo['actTargetFiles']]:
                    continue

                # fileSendPrepair의 경우에서도 newFiles가 비어있는 경우 act 추가 스킵
                elif 'newFiles' in actInfo and not fileVarDict[actInfo['newFiles']]:
                    continue

                # fileSendPrepair의 경우에서도 sendedFiles 비어있는 경우 act 추가 스킵
                elif 'sendedFiles' in actInfo and not fileVarDict[actInfo['sendedFiles']]:
                    continue

                # 어떤 사람이 어떤 파일들을 요청할 것이다 정보를 세팅
                if actInfo['actType'] == 'fileRequestPrepair':
                    actTargetFiles = fileVarDict[actInfo['actTargetFiles']]
                    sharePersonID = personVarDict[actInfo['actToWho']].personID
                    sendAsFiles = []
                    if 'sendAsFiles' in actInfo:
                        sendAsFiles = fileVarDict[actInfo['sendAsFiles']]

                    for actTargetFile in actTargetFiles:
                        targetFileID = actTargetFile.fileID
                        sendAsID = ''

                        if sendAsFiles:
                            sendAsID = sendAsFiles[0]
                            sendAsFiles = sendAsFiles[1:]

                        if targetFileID in workingPerson.fileShareDict:
                            workingPerson.fileShareDict[targetFileID].append((sharePersonID, sendAsID))

                        else:
                            workingPerson.fileShareDict[targetFileID] = [(sharePersonID, sendAsID)]

                # 어떤 파일을 받으면 어떤 파일로 저장할 것이다 정보를 세팅
                elif actInfo['actType'] == 'fileSendPrepair':
                    sendedFiles = fileVarDict[actInfo['sendedFiles']]
                    newFiles = fileVarDict[actInfo['newFiles']]

                    for newFile in newFiles:
                        if not sendedFiles:
                            break
                            
                        popIdx = random.randrange(len(sendedFiles))
                        sendedFileID = sendedFiles[popIdx].fileID
                        sendedFiles = sendedFiles[:popIdx] + sendedFiles[popIdx+1:]

                        if sendedFileID in workingPerson.sendedFileSaveDict:
                            workingPerson.sendedFileSaveDict[sendedFileID].append(newFile)

                        else:
                            workingPerson.sendedFileSaveDict[sendedFileID] = [newFile]

                # 실제 act들 
                else:
                    actType = actInfo['actType']

                    # value가 ''이든 personVar이든 key 값 actToWho는 있어야 함
                    actToWho = None
                    if actInfo['actToWho']:
                        actToWho = personVarDict[actInfo['actToWho']]

                    # key 값 actCount는 있어야 함(비정기 작업이기 때문에)
                    actCount = actInfo['actCount']

                    # key 값 actTargetFiles는 있어야 함
                    actingFileDict = {}
                    actTargetFiles = fileVarDict[actInfo['actTargetFiles']]
                    actTargetInfo = irregularWork['relatedFiles'][actInfo['actTargetFiles']]
                    idCrashTracker = 0
                    for actTargetFile in actTargetFiles:
                        actTargetID = str(actTargetFile.fileID)

                        # 작업 대상 파일 리스트에 같은 파일이 존재하는 경우
                        if actTargetID in actingFileDict:
                            actTargetID = str(actTargetFile.fileID) + '_T' + str(idCrashTracker)
                            idCrashTracker += 1

                        actingFileDict[actTargetID] = [actTargetFile, 0, actTargetInfo['fileLoc']]

                    # key 값이 존재하는 값들 세팅(없으면 기본 값)
                    actDetail = {}
                    if 'actDetail' in actInfo:
                        actDetail = actInfo['actDetail'].copy()

                    # fileRegister의 registerFileHint를 위한 actDetail 추가 설정
                    # newFiles 세팅과 비슷
                    if 'registerFileHints' in actInfo:
                        actDetail['registerFileHints'] = {}

                        registerFileHints = fileVarDict[actInfo['registerFileHints']]
                        randomActTargetIDs = list(actingFileDict.keys())
                        random.shuffle(randomActTargetIDs)
                        actTargetIDs = list(actingFileDict.keys())

                        for registerFileHint in registerFileHints:
                            objectKey = ''
                            if randomActTargetIDs:
                                objectKey = randomActTargetIDs[0]
                                randomActTargetIDs = randomActTargetIDs[1:]
                            else:
                                objectKey = random.choice(actTargetIDs)

                            actDetail['registerFileHints'][objectKey] = registerFileHint

                    # fileCreate의 copyFile를 위한 actDetail 추가 설정
                    if 'copyFiles' in actInfo:
                        actDetail['copyFiles'] = {}

                        copyFiles = fileVarDict[actInfo['copyFiles']]
                        randomActTargetIDs = list(actingFileDict.keys())
                        random.shuffle(randomActTargetIDs)
                        actTargetIDs = list(actingFileDict.keys())

                        for copyFile in copyFiles:
                            objectKey = ''
                            if randomActTargetIDs:
                                objectKey = randomActTargetIDs[0]
                                randomActTargetIDs = randomActTargetIDs[1:]
                            else:
                                objectKey = random.choice(actTargetIDs)

                            actDetail['copyFiles'][objectKey] = copyFile

                    # fileSend의 sendAsFiles를 위한 actDetail 추가 설정
                    if 'sendAsFiles' in actInfo:
                        actDetail['sendAsFiles'] = {}

                        sendAsFiles = fileVarDict[actInfo['sendAsFiles']]
                        straightActTargetIDs = list(actingFileDict.keys())
                        actTargetIDs = list(actingFileDict.keys())

                        for sendAsFile in sendAsFiles:
                            objectKey = ''
                            if straightActTargetIDs:
                                objectKey = straightActTargetIDs[0]
                                straightActTargetIDs = straightActTargetIDs[1:]
                            else:
                                objectKey = random.choice(actTargetIDs)

                            actDetail['sendAsFiles'][objectKey] = sendAsFile.fileID

                    # key 값이 존재하는 값들 세팅(없으면 기본 값)
                    actDoneProb=0
                    if 'actDoneProb' in actInfo:
                        actDoneProb = actInfo['actDoneProb']

                    doneMessageTargets = []
                    if 'doneMessageTargets' in actInfo:
                        for doneMessageTarget in actInfo['doneMessageTargets']:
                            doneMessageTargets.append(personVarDict[doneMessageTarget].personID)

                    needAllFileFlag = False
                    if 'needAllFileFlag' in actInfo:
                        needAllFileFlag = actInfo['needAllFileFlag']

                    needAllPreWorkFlag = True
                    if 'needAllPreWorkFlag' in actInfo:
                        needAllPreWorkFlag = actInfo['needAllPreWorkFlag']

                    passDoneFlag = False
                    if 'passDoneFlag' in actInfo:
                        passDoneFlag = actInfo['passDoneFlag']

                    oneShotActTag = ''
                    if 'oneShotActTag' in actInfo:
                        oneShotActTag = actInfo['oneShotActTag']

                    oneShotActTime = 0
                    if 'oneShotActTime' in actInfo:
                        oneShotActTime = actInfo['oneShotActTime']

                    # neededFiles(neededFileSet) 관련 작업
                    if 'neededFiles' in actInfo:
                        neededFileSet = set()
                        neededFileIDList = []

                        neededFilesFrom = None
                        if 'neededFilesFrom' in actInfo:
                            neededFilesFromVar = actInfo['neededFilesFrom']
                            neededFilesFrom = personVarDict[neededFilesFromVar].personID

                        for fileVar in actInfo['neededFiles']:
                            for neededFile in fileVarDict[fileVar]:
                                neededFileSet.add((neededFile.fileID, neededFilesFrom))
                                neededFileIDList.append(neededFile.fileID)

                        # 비정기 작업의 행동은 랜덤으로 행동의 디테일을 지정해주기 때문에 대부분 별도의 actDetail이 불필요
                        # 단 파일 권한 변경의 경우는 존재할 수 있음
                        newAct = act(actType=actType, 
                            actToWho=actToWho, 
                            actDetail=actDetail,
                            neededFileSet=neededFileSet, 
                            actingFileDict=actingFileDict, 
                            actCountLimit=actCount, 
                            actDoneProb=actDoneProb, 
                            doneMessageTargets=doneMessageTargets, 
                            needAllFileFlag=needAllFileFlag, 
                            needAllPreWorkFlag=needAllPreWorkFlag, 
                            passDoneFlag=passDoneFlag,
                            oneShotActTag=oneShotActTag,
                            oneShotActTime=oneShotActTime)

                        actList.append(newAct)

                        # 작업자의 neededFileForActDict 세팅
                        for neededFileID in neededFileIDList:
                            if neededFileID in workingPerson.neededFileForActDict:
                                if neededFilesFrom in workingPerson.neededFileForActDict[neededFileID]:
                                    workingPerson.neededFileForActDict[neededFileID][neededFilesFrom].append(newAct)

                                else:
                                    workingPerson.neededFileForActDict[neededFileID][neededFilesFrom] = [newAct]

                            else:
                                workingPerson.neededFileForActDict[neededFileID] = {}
                                workingPerson.neededFileForActDict[neededFileID][neededFilesFrom] = [newAct]

                    # neededFileSet이 없는 경우
                    else:
                        newAct = act(actType=actType, 
                            actToWho=actToWho, 
                            actDetail=actDetail,
                            actingFileDict=actingFileDict, 
                            actCountLimit=actCount, 
                            actDoneProb=actDoneProb, 
                            doneMessageTargets=doneMessageTargets, 
                            needAllFileFlag=needAllFileFlag, 
                            needAllPreWorkFlag=needAllPreWorkFlag, 
                            passDoneFlag=passDoneFlag,
                            oneShotActTag=oneShotActTag,
                            oneShotActTime=oneShotActTime)

                        actList.append(newAct)


            workWeight = workInfo['workWeight']

            singleActFlag = False
            if 'singleActFlag' in workInfo:
                singleActFlag = workInfo['singleActFlag']

            regularWorkFlag = False
            if 'regularWorkFlag' in workInfo:
                regularWorkFlag = workInfo['regularWorkFlag']

            if len(actList) != 0:
                newWork = work(singleActFlag=singleActFlag, regularWorkFlag=regularWorkFlag, actList=actList, originalWeight=workWeight)

                workingPerson.persona.workWeightList.append([newWork, workWeight])

        #모든 것이 세팅 됨
        return True