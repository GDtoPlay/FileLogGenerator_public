import json
import random
import copy

import util
from act import *
from person import *


class part:
    def __init__(self, partName='', partID='', personaPatterns={}, partWeight=1):
        self.partName = partName
        self.partID = partID
        self.personList = []
        
        # 부서 내 직원들에게 전파되는 행동들
        # 직원이 여러 부서(N게)에 속해있다면 기본적으로 (1/N)의 확률로 나누어저 전파됨
        self.personaPatterns=personaPatterns
        # 여러 부서인 경우 가중치(기본 1)
        self.partWeight=partWeight
        
    def addPerson(self):
        pass
    def deletePerson(self):
        pass
    def changePerson(self):
        pass

    def extractPersonsWithRank(self, personRank):
        returnPersons = []
        for partPerson in self.personList:
            if partPerson.personRank == personRank:
                returnPersons.append(partPerson)

        return returnPersons


class company:
    def __init__(self):
        self.partDict = {}
        self.personDict = {}

        self.irregularWorkList = []


    def setAllPerson(self, companySettingJsonFile, personaPresetJsonFile, probPresetJsonFile, irregularWorksJsonFile):
        companySettingJson = open(companySettingJsonFile, 'r')
        companySetting = json.load(companySettingJson)

        personaPresetJson = open(personaPresetJsonFile, 'r')
        personaPreset = json.load(personaPresetJson)

        probPresetJson = open(probPresetJsonFile, 'r')
        probPreset = json.load(probPresetJson)

        irregularWorksJson = open(irregularWorksJsonFile, 'r')
        irregularWorkList = json.load(irregularWorksJson)

        # set irregularWorkList
        util.setIrregularWorkListPattern(irregularWorkList, probPreset)
        self.irregularWorkList = irregularWorkList

        # set parts
        for partInfo in companySetting['parts']:
            partName = partInfo['partName']
            partID = partInfo['partID']
            partWeight = partInfo['partWeight']

            personaPatterns = {}
            for personRank, personaType in partInfo['personaPatterns'].items():
                try:
                    loadedPersona = copy.deepcopy(personaPreset[personaType])
                    util.setPersonaPattern(loadedPersona, probPreset, partID)
                    personaPatterns[personRank] = loadedPersona
                except Exception as e:
                    print('There is no: ' + personaType + ' in personaPreset')
                    raise e

            tmpPart = part(partName=partName, partID=partID, personaPatterns=personaPatterns, partWeight=partWeight)
            self.partDict[partID] = tmpPart

        # set persons
        for personSetting in companySetting['persons']:
            personID = ''
            if 'personID' in personSetting:
                personID = personSetting['personID']
                util.addPersonCount()
            else:
                personID = util.personIDGen()
            personName = personSetting['personName']
            personRank = personSetting['personRank']

            # 행동 횟수 가중치
            personActWeight = 10
            if 'personActWeight' in personSetting:
                personActWeight = personSetting['personActWeight']

            # 행동 횟수 분산
            personActSigma = 0.7
            if 'personActSigma' in personSetting:
                personActSigma = personSetting['personActSigma']

            actNoneWorkTime = False
            if 'actNoneWorkTime' in personSetting:
                actNoneWorkTime = personSetting['actNoneWorkTime']

            actNoneWorkTimeProb = 0
            if 'actNoneWorkTimeProb' in personSetting:
                actNoneWorkTimeProb = personSetting['actNoneWorkTimeProb']

            partList = []
            for partID in personSetting['partList']:
                try:
                    partList.append(self.partDict[partID])
                except Exception as e:
                    print('There is no: ' + partID + ' in partList of ' + personName)
                    raise e

            PersonaPatterns = []
            for partObj in partList:
                tmpPersonaPatterns = None
                # 특별히 지정한 페르소나 패턴이 있는 경우
                if 'personPersonaPattern' in personSetting:
                    try:
                        personaType = personSetting['personPersonaPattern']
                        loadedPersona = copy.deepcopy(personaPreset[personaType])
                        util.setPersonaPattern(loadedPersona, probPreset, part.partID)
                        tmpPersonaPatterns = loadedPersona

                    except Exception as e:
                        print('There is no: ' + personaType + ' in personaPreset')
                        raise e
                # 부서 랭크 별 지정 페르소나 패턴을 사용하는 경우
                else:
                    tmpPersonaPatterns = copy.deepcopy(partObj.personaPatterns[personRank])

                partWeight = partObj.partWeight

                for workInfo in tmpPersonaPatterns:
                    workInfo['workWeight'] = workInfo['workWeight'] * partWeight

                PersonaPatterns.extend(tmpPersonaPatterns)

            workWeightList = []
            for workData in PersonaPatterns:
                singleActFlag = workData['singleActFlag']
                regularWorkFlag = workData['regularWorkFlag']
                workWeight = workData['workWeight']
                actList = []
                for actData in workData['actList']:
                    actType = actData['actType']
                    actDetail = actData['actDetail']
                    tmpAct = act(actType=actType, actDetail=actDetail)

                    actList.append(tmpAct)

                tmpWork = work(singleActFlag=singleActFlag, regularWorkFlag=regularWorkFlag, actList=actList, originalWeight=workWeight)
                workWeightList.append([tmpWork, workWeight])

            inPersona = persona(workWeightList=workWeightList)
            tmpPerson = person(personID=personID, personName=personName, personRank=personRank, personActWeight=personActWeight, personActSigma=personActSigma, actNoneWorkTime=actNoneWorkTime, actNoneWorkTimeProb=actNoneWorkTimeProb, partList=partList, inPersona=inPersona)
            
            self.personDict[personID] = tmpPerson
            for partObj in partList:
                partObj.personList.append(tmpPerson)

        
    # 부서내외 협업 이벤트/비정기 업무를 패턴에 따라 랜덤하게 활성화
    # work 생성 시 필요한 파일들 (내부적 사용을 위해)preCreate할 필요가 있음
    def irregularWorkEvent(self):
        for irregularWork in self.irregularWorkList:
            activeWork = random.random()
            if activeWork < irregularWork['activeProb']:
                self.irregularWorkSetting(irregularWork)

                # 생성 횟수가 1 이상인 경우
                if irregularWork['activeCount'] > 1:
                    additionalCount = random.randrange(0, irregularWork['activeCount'])

                    for count in range(additionalCount):
                        self.irregularWorkSetting(irregularWork)


    # 사전 정의된 work objet에서 비정기 작업 세팅
    # 확률값을 포함해서 필요한 정보는 세팅되어 있다고 전제됨
    def irregularWorkSetting(self, irregularWork):
        #set part candidate
        #part는 조건부로 중복 허용
        partVarDict = {}
        if not irregularWork['partOverlap']:
            popedSet = set()
            for partVar in irregularWork['partCandidate'].keys():
                partCandidate = [partID for partID in irregularWork['partCandidate'][partVar] if partID not in popedSet]
                partID = random.choice(partCandidate)

                partVarDict[partVar] = self.partDict[partID]
                popedSet.add(partID)

        else:
            for partVar in irregularWork['partCandidate'].keys():
                partID = random.choice(irregularWork['partCandidate'][partVar])

                partVarDict[partVar] = self.partDict[partID]

        #set person candidate
        #person의 경우는 무조건 종복 허용 X
        personVarDict = {}
        popedSet = set()
        for personVar in irregularWork['personCandidate']:
            selectedPersonRank = util.selectPersonRank(irregularWork['personCandidate'][personVar]['personRankProb'])

            personCandidate = []
            for personInPart in partVarDict[irregularWork['personCandidate'][personVar]['part']].personList:
                if personInPart.personRank == selectedPersonRank:
                    personCandidate.append(personInPart.personID)

            personCandidate = [personID for personID in personCandidate if personID not in popedSet]

            # 후보자 선정 실패
            if not personCandidate:
                return False

            personID = random.choice(personCandidate)
            personVarDict[personVar] = self.personDict[personID]
            popedSet.add(personID)

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
                if "upperVar" in extractInfo:
                    if not extractInfo["upperVar"] in fileVarDict:
                        continue

                    extractCount = random.randrange(extractInfo['extractCountMin'], extractInfo['extractCountMax'] + 1)
                    extractCount = min(len(fileVarDict[extractInfo["upperVar"]]), extractCount)
                    extractedFileList = []
                    try:
                        extractedFileList = random.sample(fileVarDict[extractInfo["upperVar"]], extractCount)

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

                    for actTargetFile in actTargetFiles:
                        targetFileID = actTargetFile.fileID

                        if targetFileID in workingPerson.fileShareDict:
                            workingPerson.fileShareDict[targetFileID].append(sharePersonID)

                        else:
                            workingPerson.fileShareDict[targetFileID] = [sharePersonID]

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

                    # value가 ""이든 personVar이든 key 값 actToWho는 있어야 함
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
                            passDoneFlag=passDoneFlag)

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
                            passDoneFlag=passDoneFlag)

                        actList.append(newAct)


            workWeight = workInfo['workWeight']

            singleActFlag = False
            if 'singleActFlag' in workInfo:
                singleActFlag = workInfo['singleActFlag']

            regularWorkFlag = False
            if 'regularWorkFlag' in workInfo:
                regularWorkFlag = workInfo['regularWorkFlag']

            newWork = work(singleActFlag=singleActFlag, regularWorkFlag=regularWorkFlag, actList=actList, originalWeight=workWeight)

            workingPerson.persona.workWeightList.append([newWork, workWeight])

        #모든 것이 세팅 됨
        return True
