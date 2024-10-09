import json
import random

import util

#로컬에서 저장되는 파일 형식
class file:
    def __init__(self, fileID, fileName, fileRank, createdTime, lastModifiedTime):
        self.fileID = fileID
        self.fileName = fileName
        self.fileDBKey = ''         #파일이 서버에 저장된 경우의 키 값. 로컬과 서버의 파일의 추적 관련, 
                                    #값이 있다면, fileDBKey == fileID

        self.fileRank = fileRank        #파일이 실제 처리되어야 하는 rank (ideal)
        self.fileRankAssumption = ''    #로컬 파일의 rank 추정 값. 로컬 파일을 서버에서 받았을 때 추적 관련
        
        self.createdTime = createdTime                #파일 생성시각
        self.lastModifiedTime = lastModifiedTime      #최종 수정 시각

        self.hasUploaded = False          # 이 파일이 서버에 업로드 되었는지(send로 받은 경우 ownership이 없으면 false)

    # 파일 복사본 생성, fileName은 부분적 복사 fileDBKey랑 fileRank, fileRankAssumption은 복사
    # lastModifiedTime = createdTime(는 현재 시간), hasUploaded는 fileDBKey랑 personID로 소유권 검사
    # newFile가 있다면 거기에 덮어쓰기, 없으면 새로 생성
    def copy(self, newFile=None, currentTime=None, personID=''):
        if not currentTime:
            currentTime = baseTime
        
        if newFile:
            newFile.fileName = util.createCopyFileName(self.fileName)
            newFile.fileRank = self.fileRank
            newFile.fileRankAssumption = self.fileRankAssumption

            newFile.createdTime = currentTime
            newFile.lastModifiedTime = currentTime

        else:
            fileID = util.fileIDGen()
            fileName = util.createCopyFileName(self.fileName)
            fileRank = self.fileRank

            newFile = file(fileID, fileName, fileRank, currentTime, currentTime)
            newFile.fileRankAssumption = self.fileRankAssumption

        return newFile

