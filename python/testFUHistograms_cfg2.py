import FWCore.ParameterSet.Config as cms
import FWCore.ParameterSet.VarParsing as VarParsing
import DQMServices.Components.test.checkBooking as booking
import DQMServices.Components.test.createElements as c
import os,sys

cmsswbase = os.path.expandvars('$CMSSW_BASE/')

options = VarParsing.VarParsing ('analysis')

options.register ('runNumber',
                  1, # default value
                  VarParsing.VarParsing.multiplicity.singleton,
                  VarParsing.VarParsing.varType.int,          # string, int, or float
                  "Run Number")

options.register ('buBaseDir',
                  '/fff/BU0', # default value
                  VarParsing.VarParsing.multiplicity.singleton,
                  VarParsing.VarParsing.varType.string,          # string, int, or float
                  "BU base directory")

options.register ('dataDir',
                  '/fff/data', # default value
                  VarParsing.VarParsing.multiplicity.singleton,
                  VarParsing.VarParsing.varType.string,          # string, int, or float
                  "FU data directory")

options.register ('numThreads',
                  1, # default value
                  VarParsing.VarParsing.multiplicity.singleton,
                  VarParsing.VarParsing.varType.int,          # string, int, or float
                  "Number of CMSSW threads")

options.register ('numFwkStreams',
                  1, # default value
                  VarParsing.VarParsing.multiplicity.singleton,
                  VarParsing.VarParsing.varType.int,          # string, int, or float
                  "Number of CMSSW streams")



options.parseArguments()

process = cms.Process("HLT")

# load DQM
process.load("DQMServices.Core.DQM_cfg")
process.load("DQMServices.Components.DQMEnvironment_cfi")

#b = booking.BookingParams(sys.argv)
#b = booking.BookingParams(["CTOR","BJ","BR"])
#b.doCheck(testOnly=False)

elements = c.createElements()
readRunElements = c.createReadRunElements()
readLumiElements = c.createReadLumiElements()




process.maxEvents = cms.untracked.PSet(
    input = cms.untracked.int32(-1)
)

process.options = cms.untracked.PSet(
    numberOfThreads = cms.untracked.uint32(options.numThreads),
    numberOfStreams = cms.untracked.uint32(options.numFwkStreams),
    multiProcesses = cms.untracked.PSet(
    maxChildProcesses = cms.untracked.int32(0)
    )
)

process.MessageLogger = cms.Service("MessageLogger",
                                    destinations = cms.untracked.vstring( 'cout' ),
                                    cout = cms.untracked.PSet( FwkReport =
                                                               cms.untracked.PSet(reportEvery = cms.untracked.int32(10),
                                                                                  optionalPSet = cms.untracked.bool(True),
                                                                                  #limit = cms.untracked.int32(10000000)
                                                                                  ),
                                                               threshold = cms.untracked.string( "INFO" )
                                                               )
                                    )

process.FastMonitoringService = cms.Service("FastMonitoringService",
    sleepTime = cms.untracked.int32(1),
    microstateDefPath = cms.untracked.string( cmsswbase+'/src/EventFilter/Utilities/plugins/microstatedef.jsd' ),
    #fastMicrostateDefPath = cms.untracked.string( cmsswbase+'/src/EventFilter/Utilities/plugins/microstatedeffast.jsd' ),
    fastName = cms.untracked.string( 'fastmoni' ),
    slowName = cms.untracked.string( 'slowmoni' ))

process.EvFDaqDirector = cms.Service("EvFDaqDirector",
                                     buBaseDir = cms.untracked.string(options.buBaseDir),
                                     baseDir = cms.untracked.string(options.dataDir),
                                     directorIsBU = cms.untracked.bool(False ),
                                     testModeNoBuilderUnit = cms.untracked.bool(False),
                                     runNumber = cms.untracked.uint32(options.runNumber)
                                     )
process.PrescaleService = cms.Service( "PrescaleService",
                                       lvl1DefaultLabel = cms.string( "B" ),
                                       lvl1Labels = cms.vstring( 'A',
                                                                 'B'
                                                                 ),
                                       prescaleTable = cms.VPSet(
    cms.PSet(  pathName = cms.string( "p1" ),
               prescales = cms.vuint32( 0, 10)
               ),
    cms.PSet(  pathName = cms.string( "p2" ),
               prescales = cms.vuint32( 0, 100)
               )
    ))


process.source = cms.Source("FedRawDataInputSource",
                            getLSFromFilename = cms.untracked.bool(True),
                            testModeNoBuilderUnit = cms.untracked.bool(False),
                            eventChunkSize = cms.untracked.uint32(128),
                            numBuffers = cms.untracked.uint32(2),
                            eventChunkBlock = cms.untracked.uint32(128),
                            useL1EventID=cms.untracked.bool(True)
                            )


process.filter1 = cms.EDFilter("HLTPrescaler",
                               L1GtReadoutRecordTag = cms.InputTag( "hltGtDigis" )
                               )
process.filter2 = cms.EDFilter("HLTPrescaler",
                               L1GtReadoutRecordTag = cms.InputTag( "hltGtDigis" )
                               )

process.a = cms.EDAnalyzer("ExceptionGenerator",
                           defaultAction = cms.untracked.int32(0),
                           defaultQualifier = cms.untracked.int32(120))

process.b = cms.EDAnalyzer("ExceptionGenerator",
                           defaultAction = cms.untracked.int32(0),
                           defaultQualifier = cms.untracked.int32(0))


process.filler = cms.EDAnalyzer("DummyBookFillDQMStoreMultiThread",
                                folder = cms.untracked.string("TestFolder/"),
                                elements = cms.untracked.VPSet(*elements),
                                fillRuns = cms.untracked.bool(True),
                                fillLumis = cms.untracked.bool(True),
                                book_at_constructor = cms.untracked.bool(False),
                                book_at_beginJob = cms.untracked.bool(False),
                                book_at_beginRun = cms.untracked.bool(True))





process.p1 = cms.Path(process.a*process.filter1)
process.p2 = cms.Path(process.b*process.filter2)

process.dqmsave_step = cms.Path(process.filler*process.dqmSaver)

### global options Online ###
process.add_(cms.Service("DQMStore"))
process.DQMStore.LSbasedMode = cms.untracked.bool(True)
process.DQMStore.verbose = cms.untracked.int32(5)
process.DQMStore.enableMultiThread = cms.untracked.bool(True)

process.dqmSaver.workflow = ''
process.dqmSaver.convention = 'FilterUnit'
process.dqmSaver.saveByLumiSection = True
process.dqmSaver.fileFormat = cms.untracked.string('PB')
process.dqmSaver.fakeFilterUnitMode = cms.untracked.bool(False)


process.GlobalTag = cms.ESSource( "PoolDBESSource",
    globaltag = cms.string( "GR_H_V39::All" ),
    toGet = cms.VPSet(
    ),
    DBParameters = cms.PSet(
      authenticationPath = cms.untracked.string( "." ),
      connectionRetrialTimeOut = cms.untracked.int32( 60 ),
      idleConnectionCleanupPeriod = cms.untracked.int32( 10 ),
      messageLevel = cms.untracked.int32( 0 ),
      enablePoolAutomaticCleanUp = cms.untracked.bool( False ),
      enableConnectionSharing = cms.untracked.bool( True ),
      enableReadOnlySessionOnUpdateConnection = cms.untracked.bool( False ),
      connectionTimeOut = cms.untracked.int32( 0 ),
      connectionRetrialPeriod = cms.untracked.int32( 10 )
    ),
    RefreshAlways = cms.untracked.bool( False ),
    ReconnectEachRun = cms.untracked.bool( False ),
    RefreshEachRun = cms.untracked.bool( False ),
    RefreshOpenIOVs = cms.untracked.bool( False ),
    connect = cms.string( "frontier://(proxyurl=http://localhost:3128)(serverurl=http://localhost:8000/FrontierOnProd)(serverurl=http://localhost:8000/FrontierOnProd)(retrieve-ziplevel=0)/CMS_COND_31X_GLOBALTAG" ),
    BlobStreamerName = cms.untracked.string( "TBufferBlobStreamingService" )
)


process.hltTriggerJSONMonitoring = cms.EDAnalyzer('TriggerJSONMonitoring',
    triggerResults = cms.InputTag( 'TriggerResults','','HLT')
)


process.streamA = cms.OutputModule("EvFOutputModule",
                                   SelectEvents = cms.untracked.PSet(SelectEvents = cms.vstring( 'p1' ))
                                   )

process.streamDQM = cms.OutputModule("EvFOutputModule",
                                   SelectEvents = cms.untracked.PSet(SelectEvents = cms.vstring( 'p2' ))
                                   )

process.ep = cms.EndPath(process.streamA+process.streamDQM+process.hltTriggerJSONMonitoring)

process.GlobalTag.connect   = 'frontier://FrontierProd/CMS_COND_31X_GLOBALTAG'
process.GlobalTag.pfnPrefix = cms.untracked.string('frontier://FrontierProd/')

