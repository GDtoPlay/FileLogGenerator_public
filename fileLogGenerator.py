import json
import random
import math
import datetime

import util
from part import *
from maliciousPlayers import *


def noneWorkTimeActionCountSelect():
    # (person, actCount)의 리스트
    personActCountList = []
    for actperson in util.companyInstance.personDict.values():
        if actperson.actNoneWorkTime:
            actNoneWorkTimeProb = actperson.actNoneWorkTimeProb
            doActNoneWorkTime = random.random()

            if doActNoneWorkTime < actNoneWorkTimeProb:
                actWeight = actperson.personActWeight

                # 각 직원의 정기 작업 수 정보가 없을 경우 카운트
                if actperson.regularWorkCount == -1:
                    regularWorkCount = 0

                    for actpersonWorkWeight in actperson.persona.workWeightList:
                        if not actpersonWorkWeight[0].regularWorkFlag:
                            regularWorkCount += 1

                    actperson.regularWorkCount = regularWorkCount

                regularWorkCount = actperson.regularWorkCount
                irregularWorkLen = max(len(actperson.persona.workWeightList) - regularWorkCount, 1)
                workLenWeight = math.log2((actWeight/10) * irregularWorkLen) * 3

                actWeight = actWeight + workLenWeight
                actSigma = actperson.personActSigma
                actCount = round(max(random.gauss(actWeight/10, actSigma),0))

                if actCount > 0:
                    personActCountList.append((actperson, actCount))

    return personActCountList


def actionCountSelect():
    # (person, actCount)의 리스트
    personActCountList = []
    for actperson in util.companyInstance.personDict.values():
        actWeight = actperson.personActWeight

        # 각 직원의 정기 작업 수 정보가 없을 경우 카운트
        if actperson.regularWorkCount == -1:
            regularWorkCount = 0

            for actpersonWorkWeight in actperson.persona.workWeightList:
                if not actpersonWorkWeight[0].regularWorkFlag:
                    regularWorkCount += 1

            actperson.regularWorkCount = regularWorkCount

        regularWorkCount = actperson.regularWorkCount
        irregularWorkLen = max(len(actperson.persona.workWeightList) - regularWorkCount, 1)
        workLenWeight = math.log2((actWeight/10) * irregularWorkLen) * 3

        actWeight = actWeight + workLenWeight
        actSigma = actperson.personActSigma
        actCount = round(max(random.gauss(actWeight/10, actSigma),0))

        if actCount > 0:
            personActCountList.append((actperson, actCount))

    return personActCountList


def companySetting(companySettingJsonFile, personaPresetJsonFile, probPresetJsonFile, irregularWorksJsonFile):
    generatorCompany = company()
    generatorCompany.setAllPerson(companySettingJsonFile, personaPresetJsonFile, probPresetJsonFile, irregularWorksJsonFile)

    util.setCompany(generatorCompany)


def maliciousPlayersSetting(maliciousPlayersJsonFile, personaPresetJsonFile, probPresetJsonFile):
    generatorMaliciousPlayers = maliciousPlayers()
    generatorMaliciousPlayers.setMaliciousPlayersDict(maliciousPlayersJsonFile, personaPresetJsonFile, probPresetJsonFile)

    util.setMaliciousPlayers(generatorMaliciousPlayers)


def runLoop(maxActCount, baseTime, timeInterval, workStartTime, workEndTime, cycleStartTime, cycleEndTime):
    util.companyInstance.irregularWorkEvent()

    if baseTime.time() >= cycleEndTime:
        baseTime = baseTime + datetime.timedelta(days=1)
        baseTime = baseTime.replace(hour=cycleStartTime.hour, minute=cycleStartTime.minute, second=cycleStartTime.second, microsecond=cycleStartTime.microsecond)

    personActCountList = []
    if baseTime.time() < workStartTime or baseTime.time() > cycleEndTime:
        personActCountList = noneWorkTimeActionCountSelect()

    else:
        personActCountList = actionCountSelect()

    actOrderList = []
    totalActCount = 0

    for personActCount in personActCountList:
        actPerson = personActCount[0]
        actCount = personActCount[1]
        
        totalActCount += actCount

        for i in range(actCount):
            actOrderList.append(actPerson)

    if totalActCount > maxActCount:
        random.shuffle(actOrderList)
        actOrderList = actOrderList[:maxActionCount]

    else:
        NoneList = [None] * (maxActCount - totalActCount)
        actOrderList = actOrderList + NoneList
        random.shuffle(actOrderList)

    for actPerson in actOrderList:
        baseTime = baseTime + timeInterval
        util.runOneShotObjects(baseTime)

        if actPerson:
            timeMove = random.uniform(-0.45, 0.45)
            currentTime = baseTime + timeMove * timeInterval
            actPerson.doPlay(currentTime)

    return baseTime


def setGeneratorSetting(generatorSettingJsonFile):
    generatorSettingJson = open(generatorSettingJsonFile, 'r')
    generatorSetting = json.load(generatorSettingJson)

    baseTime = datetime.datetime.strptime(generatorSetting['baseTime'], '%Y-%m-%d %H:%M:%S')
    util.setBaseTime(baseTime)
    generatorSetting['baseTime'] = baseTime

    workStartTime = datetime.datetime.strptime(generatorSetting['workStartTime'], '%H:%M:%S').time()
    workEndTime = datetime.datetime.strptime(generatorSetting['workEndTime'], '%H:%M:%S').time()
    generatorSetting['workStartTime'] = workStartTime
    generatorSetting['workEndTime'] = workEndTime

    cycleStartTime = datetime.datetime.strptime(generatorSetting['cycleStartTime'], '%H:%M:%S').time()
    cycleEndTime = datetime.datetime.strptime(generatorSetting['cycleEndTime'], '%H:%M:%S').time()
    generatorSetting['cycleStartTime'] = cycleStartTime
    generatorSetting['cycleEndTime'] = cycleEndTime

    timeInterval = datetime.timedelta(seconds=generatorSetting['timeInterval'])
    generatorSetting['timeInterval'] = timeInterval

    return generatorSetting


def main():
    generatorSettingJsonFile = 'setting\\generatorSetting.json'
    companySettingJsonFile = 'setting\\companySetting.json'
    maliciousPlayersJsonFile = 'setting\\maliciousPlayers.json'
    personaPresetJsonFile = 'setting\\personaPreset.json'
    probPresetJsonFile = 'setting\\probPreset.json'
    irregularWorksJsonFile = 'setting\\irregularWorks.json'

    generatorSetting = setGeneratorSetting(generatorSettingJsonFile)
    companySetting(companySettingJsonFile, personaPresetJsonFile, probPresetJsonFile, irregularWorksJsonFile)
    maliciousPlayersSetting(maliciousPlayersJsonFile, personaPresetJsonFile, probPresetJsonFile)

    baseTime = generatorSetting['baseTime']

    workStartTime = generatorSetting['workStartTime']
    workEndTime = generatorSetting['workEndTime']

    cycleStartTime = generatorSetting['cycleStartTime']
    cycleEndTime = generatorSetting['cycleEndTime']

    maxActCount = generatorSetting['maxActCount']
    timeInterval = generatorSetting['timeInterval']

    endLoopCount = generatorSetting['endLoopCount']

    util.setDB()

    loopCount = 0
    while loopCount <= endLoopCount:
        print(loopCount)
        util.maliciousPlayersInstance.startMaliciousPlayersCheck(loopCount)
        baseTime = runLoop(maxActCount, baseTime, timeInterval, workStartTime, workEndTime, cycleStartTime, cycleEndTime)
        util.maliciousPlayersInstance.endMaliciousPlayers(loopCount)
        loopCount += 1


if __name__ == '__main__':
    main()