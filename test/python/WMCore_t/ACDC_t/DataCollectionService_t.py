#!/usr/bin/env python
# encoding: utf-8
"""
DataCollectionService_t.py

Created by Dave Evans on 2010-10-05.
Copyright (c) 2010 Fermilab. All rights reserved.
"""

import unittest

from WMCore.ACDC.DataCollectionService import DataCollectionService, mergeFakeFiles
from WMCore.DataStructs.File import File
from WMCore.DataStructs.LumiList import LumiList
from WMCore.DataStructs.Run import Run
from WMCore.Services.UUIDLib import makeUUID
from WMCore.WMBS.Job import Job
from WMQuality.TestInitCouchApp import TestInitCouchApp


class DataCollectionService_t(unittest.TestCase):
    def setUp(self):
        """bootstrap tests"""
        self.testInit = TestInitCouchApp(__file__)
        self.testInit.setLogging()
        self.testInit.setDatabaseConnection()
        self.testInit.setSchema(customModules=["WMCore.WMBS"],
                                useDefault=False)
        self.testInit.setupCouch("wmcore-acdc-datacollectionsvc", "GroupUser", "ACDC")
        return

    def tearDown(self):
        self.testInit.tearDownCouch()
        self.testInit.clearDatabase()
        return

    @staticmethod
    def getMinimalJob():
        job = Job()
        job["task"] = "/ACDCTest/reco"
        job["workflow"] = "ACDCTest"
        job["location"] = "cmssrm.fnal.gov"
        job["owner"] = "cmsdataops"
        job["group"] = "cmsdataops"
        return job

    def testChunking(self):
        """
        _testChunking_

        Insert a workload and files that have several distinct sets of
        locations.  Verify that the chunks are created correctly and that they
        only groups files that have the same set of locations.  Also verify that
        the chunks are pulled out of ACDC correctly.
        """
        dcs = DataCollectionService(url=self.testInit.couchUrl, database="wmcore-acdc-datacollectionsvc")

        testFileA = File(lfn=makeUUID(), size=1024, events=1024)
        testFileA.setLocation(["cmssrm.fnal.gov", "castor.cern.ch"])
        testFileA.addRun(Run(1, 1, 2))
        testFileB = File(lfn=makeUUID(), size=1024, events=1024)
        testFileB.setLocation(["cmssrm.fnal.gov", "castor.cern.ch"])
        testFileB.addRun(Run(1, 3, 4))
        testFileC = File(lfn=makeUUID(), size=1024, events=1024)
        testFileC.setLocation(["cmssrm.fnal.gov", "castor.cern.ch"])
        testFileC.addRun(Run(1, 5, 6))
        testJobA = self.getMinimalJob()
        testJobA.addFile(testFileA)
        testJobA.addFile(testFileB)
        testJobA.addFile(testFileC)

        testFileD = File(lfn=makeUUID(), size=1024, events=1024)
        testFileD.setLocation(["cmssrm.fnal.gov"])
        testFileD.addRun(Run(2, 1, 2))
        testFileE = File(lfn=makeUUID(), size=1024, events=1024)
        testFileE.setLocation(["cmssrm.fnal.gov"])
        testFileE.addRun(Run(2, 3, 4))
        testJobB = self.getMinimalJob()
        testJobB.addFile(testFileD)
        testJobB.addFile(testFileE)

        testFileF = File(lfn=makeUUID(), size=1024, events=1024, parents={"/some/parent/F"})
        testFileF.setLocation(["cmssrm.fnal.gov", "castor.cern.ch", "srm.ral.uk"])
        testFileF.addRun(Run(3, 1, 2))
        testFileG = File(lfn=makeUUID(), size=1024, events=1024, parents={"/some/parent/G"})
        testFileG.setLocation(["cmssrm.fnal.gov", "castor.cern.ch", "srm.ral.uk"])
        testFileG.addRun(Run(3, 3, 4))
        testFileH = File(lfn=makeUUID(), size=1024, events=1024, parents={"/some/parent/H"})
        testFileH.setLocation(["cmssrm.fnal.gov", "castor.cern.ch", "srm.ral.uk"])
        testFileH.addRun(Run(3, 5, 6))
        testJobC = self.getMinimalJob()
        testJobC.addFile(testFileF)
        testJobC.addFile(testFileG)
        testJobC.addFile(testFileH)

        testFileI = File(lfn=makeUUID(), size=1024, events=1024, merged=True)
        testFileI.setLocation(["cmssrm.fnal.gov", "castor.cern.ch"])
        testFileI.addRun(Run(4, 1, 2))
        testFileJ = File(lfn=makeUUID(), size=1024, events=1024, merged=True)
        testFileJ.setLocation(["cmssrm.fnal.gov", "castor.cern.ch"])
        testFileJ.addRun(Run(4, 3, 4))
        testFileK = File(lfn=makeUUID(), size=1024, events=1024, merged=True)
        testFileK.setLocation(["cmssrm.fnal.gov", "castor.cern.ch"])
        testFileK.addRun(Run(4, 5, 6))
        testJobD = self.getMinimalJob()
        testJobD.addFile(testFileI)
        testJobD.addFile(testFileJ)
        testJobD.addFile(testFileK)

        dcs.failedJobs([testJobA, testJobB, testJobC, testJobD])
        chunks = dcs.chunkFileset("ACDCTest", "/ACDCTest/reco", chunkSize=5)

        self.assertEqual(len(chunks), 4, "Error: There should be four chunks: %s" % len(chunks))

        goldenMetaData = {1: {"lumis": 2, "locations": ["castor.cern.ch", "cmssrm.fnal.gov"], "events": 1024},
                          2: {"lumis": 4, "locations": ["cmssrm.fnal.gov"], "events": 2048},
                          3: {"lumis": 6, "locations": ["castor.cern.ch", "cmssrm.fnal.gov", "srm.ral.uk"],
                              "events": 3072},
                          5: {"lumis": 10, "locations": ["castor.cern.ch", "cmssrm.fnal.gov"], "events": 5120}}

        testFiles = [testFileA, testFileB, testFileC, testFileI, testFileJ, testFileK]
        lastFile = testFileA
        for testFile in testFiles:
            if lastFile["lfn"] < testFile["lfn"]:
                lastFile = testFile

        testFiles.remove(lastFile)

        goldenFiles = {1: [lastFile],
                       2: [testFileD, testFileE],
                       3: [testFileF, testFileG, testFileH],
                       5: testFiles}

        for chunk in chunks:
            chunkMetaData = dcs.getChunkInfo("ACDCTest", "/ACDCTest/reco",
                                             chunk["offset"], chunk["files"])

            self.assertEqual(chunkMetaData["files"], chunk["files"])
            self.assertEqual(chunkMetaData["lumis"], chunk["lumis"])
            self.assertEqual(chunkMetaData["events"], chunk["events"])
            self.assertEqual(chunkMetaData["locations"], chunk["locations"])

            self.assertTrue(chunk["files"] in goldenMetaData.keys(), "Error: Extra chunk found.")
            self.assertEqual(chunk["lumis"], goldenMetaData[chunk["files"]]["lumis"],
                             "Error: Lumis in chunk is wrong.")
            self.assertEqual(chunk["locations"], goldenMetaData[chunk["files"]]["locations"],
                             "Error: Locations in chunk is wrong.")
            self.assertEqual(chunk["events"], goldenMetaData[chunk["files"]]["events"],
                             "Error: Events in chunk is wrong.")
            del goldenMetaData[chunk["files"]]

            chunkFiles = dcs.getChunkFiles("ACDCTest", "/ACDCTest/reco", chunk["offset"], chunk["files"])

            self.assertTrue(chunk["files"] in goldenFiles.keys(), "Error: Extra chunk found.")
            goldenChunkFiles = goldenFiles[chunk["files"]]
            self.assertEqual(len(chunkFiles), len(goldenChunkFiles))

            for chunkFile in chunkFiles:
                foundFile = None
                for goldenChunkFile in goldenChunkFiles:
                    if chunkFile["lfn"] == goldenChunkFile["lfn"]:
                        foundFile = goldenChunkFile
                        break

                self.assertIsNotNone(foundFile, "Error: Missing chunk file: %s, %s" % (chunkFiles, goldenChunkFiles))
                self.assertEqual(foundFile["parents"], chunkFile["parents"], "Error: File parents should match.")
                self.assertEqual(foundFile["merged"], chunkFile["merged"], "Error: File merged status should match.")
                self.assertEqual(foundFile["locations"], chunkFile["locations"], "Error: File locations should match.")
                self.assertEqual(foundFile["events"], chunkFile["events"])
                self.assertEqual(foundFile["size"], chunkFile["size"])
                self.assertEqual(len(foundFile["runs"]), len(chunkFile["runs"]), "Error: Wrong number of runs.")
                for run in foundFile["runs"]:
                    runMatch = False
                    for chunkRun in chunkFile["runs"]:
                        if chunkRun.run == run.run and chunkRun.lumis == run.lumis:
                            runMatch = True
                            break

                    self.assertTrue(runMatch, "Error: Run information is wrong.")

            del goldenFiles[chunk["files"]]

        singleChunk = dcs.singleChunkFileset("ACDCTest", "/ACDCTest/reco")
        self.assertEqual(singleChunk, {"offset": 0,
                                       "files": 11,
                                       "events": 11264,
                                       "lumis": 22,
                                       "locations": {"castor.cern.ch", "cmssrm.fnal.gov", "srm.ral.uk"}},
                         "Error: Single chunk metadata is wrong")

        return

    def testGetLumiWhitelist(self):
        """
        _testGetLumiWhitelist_

        Verify that the ACDC whitelist generation code works correctly.  We'll
        add jobs with the following lumi info:
          # Run 1, lumis [1, 2, 3], [4, 6], [7], [9], [11, 12]
          # Run 2, lumis [5, 6, 7], [10, 11, 12], [15]
          # Run 3, lumis [20]

        And should get out a whitelist that looks like this:
          {"1": [[1, 4], [6, 7], [9, 9], [11, 12]],
           "2": [[5, 7], [10, 12], [15, 15]],
           "3": [[20, 20]]}
        """
        dcs = DataCollectionService(url=self.testInit.couchUrl, database="wmcore-acdc-datacollectionsvc")

        testFileA = File(lfn=makeUUID(), size=1024, events=1024)
        testFileA.addRun(Run(1, 1, 2))
        testFileB = File(lfn=makeUUID(), size=1024, events=1024)
        testFileB.addRun(Run(1, 3))
        testJobA = self.getMinimalJob()
        testJobA.addFile(testFileA)
        testJobA.addFile(testFileB)

        testFileC = File(lfn=makeUUID(), size=1024, events=1024)
        testFileC.addRun(Run(1, 4, 6))
        testJobB = self.getMinimalJob()
        testJobB.addFile(testFileC)

        testFileD = File(lfn=makeUUID(), size=1024, events=1024)
        testFileD.addRun(Run(1, 7))
        testJobC = self.getMinimalJob()
        testJobC.addFile(testFileD)

        testFileE = File(lfn=makeUUID(), size=1024, events=1024)
        testFileE.addRun(Run(1, 11, 12))
        testJobD = self.getMinimalJob()
        testJobD.addFile(testFileE)

        testFileF = File(lfn=makeUUID(), size=1024, events=1024)
        testFileF.addRun(Run(2, 5, 6, 7))
        testJobE = self.getMinimalJob()
        testJobE.addFile(testFileF)

        testFileG = File(lfn=makeUUID(), size=1024, events=1024)
        testFileG.addRun(Run(2, 10, 11, 12))
        testJobF = self.getMinimalJob()
        testJobF.addFile(testFileG)

        testFileH = File(lfn=makeUUID(), size=1024, events=1024)
        testFileH.addRun(Run(2, 15))
        testJobG = self.getMinimalJob()
        testJobG.addFile(testFileH)

        testFileI = File(lfn=makeUUID(), size=1024, events=1024)
        testFileI.addRun(Run(3, 20))
        testJobH = self.getMinimalJob()
        testJobH.addFile(testFileI)

        testFileJ = File(lfn=makeUUID(), size=1024, events=1024)
        testFileJ.addRun(Run(1, 9))
        testJobI = self.getMinimalJob()
        testJobI.addFile(testFileJ)

        dcs.failedJobs([testJobA, testJobB, testJobC, testJobD, testJobE,
                        testJobF, testJobG, testJobH, testJobI])
        whiteList = dcs.getLumiWhitelist("ACDCTest", "/ACDCTest/reco")

        self.assertEqual(len(whiteList.keys()), 3,
                         "Error: There should be 3 runs.")
        self.assertEqual(whiteList["1"], [[1, 4], [6, 7], [9, 9], [11, 12]],
                         "Error: Whitelist for run 1 is wrong.")
        self.assertEqual(whiteList["2"], [[5, 7], [10, 12], [15, 15]],
                         "Error: Whitelist for run 2 is wrong.")
        self.assertEqual(whiteList["3"], [[20, 20]],
                         "Error: Whitelist for run 3 is wrong.")

        correctLumiList = LumiList(compactList={"1": [[1, 4], [6, 7], [9, 9], [11, 12]],
                                                "2": [[5, 7], [10, 12], [15, 15]],
                                                "3": [[20, 20]]})
        testLumiList = dcs.getLumilistWhitelist("ACDCTest", "/ACDCTest/reco")
        self.assertEqual(correctLumiList.getCMSSWString(), testLumiList.getCMSSWString())

        return

    def notestMergeFakeFiles(self):
        """
        _testMergeFakeFiles_

        Verify that we can merge MCFakeFiles together when a fileset contains
        several failures for the same input fake file.
        """
        originalFiles = [{'checksums': {},
                          'events': 500000,
                          'first_event': 1,
                          'id': 40,
                          'last_event': 0,
                          'lfn': 'MCFakeFile-File1',
                          'locations': ['T1_DE_KIT_Disk'],
                          'merged': '0',
                          'parents': [],
                          'runs': [{'lumis': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], 'run_number': 1}],
                          'size': 0},
                         {'checksums': {},
                          'events': 500000,
                          'first_event': 1000001,
                          'id': 40,
                          'last_event': 0,
                          'lfn': 'MCFakeFile-File2',
                          'locations': ['T1_DE_KIT_Disk'],
                          'merged': '0',
                          'parents': [],
                          'runs': [{'lumis': [21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31],
                                    'run_number': 1}],
                          'size': 0},
                         {'checksums': {},
                          'events': 500000,
                          'first_event': 2000001,
                          'id': 40,
                          'last_event': 0,
                          'lfn': 'MCFakeFile-File1',
                          'locations': ['T1_DE_KIT_Disk'],
                          'merged': '0',
                          'parents': [],
                          'runs': [{'lumis': [41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51],
                                    'run_number': 1}],
                          'size': 0},
                         {'checksums': {},
                          'events': 500000,
                          'first_event': 7000001,
                          'id': 40,
                          'last_event': 0,
                          'lfn': 'MCFakeFile-File3',
                          'locations': ['T1_DE_KIT_Disk'],
                          'merged': '0',
                          'parents': [],
                          'runs': [{'lumis': [81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91],
                                    'run_number': 1}],
                          'size': 0},
                         {'checksums': {},
                          'events': 500000,
                          'first_event': 4000001,
                          'id': 40,
                          'last_event': 0,
                          'lfn': 'MCFakeFile-File3',
                          'locations': ['T1_DE_KIT_Disk'],
                          'merged': '0',
                          'parents': [],
                          'runs': [{'lumis': [51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61],
                                    'run_number': 1}],
                          'size': 0}]

        mergedFiles = mergeFakeFiles(originalFiles)
        self.assertEqual(len(mergedFiles), 3, "Error: wrong number of files.")

        totalEvents = 0
        for job in mergedFiles:
            totalEvents += job['events']
        self.assertEqual(totalEvents, 2500000, "Error: wrong number of total events.")

        for job in mergedFiles:
            if job['lfn'] == 'MCFakeFile-File1':
                lumiList = job['runs'][0]['lumis']
                self.assertEqual(len(lumiList), 22)


if __name__ == '__main__':
    unittest.main()
