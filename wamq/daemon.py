# -*- coding: utf-8 -*-
'''
@author: vadim.isaev
'''

import logging
import signal
import sys
import time

from wamq import functions
from wamq.stomp_service import StompServiceException, StompService
from wamq.whats_app_service import WhatsAppService


#    filename='whatsapp_mq_service.log'
#    stream=sys.stdout
logging.basicConfig(filename='wamq.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')

logger = logging.getLogger(__name__)

class MainService(object):

    configs = ['wamq.conf', '~/wamq.conf', '/etc/wamq.conf']

    loopMustContinue = True

    whatsAppPhone = None  # mandatory
    whatsAppPassword = None  # mandatory
    whatsAppAutoReply = True  # non mandatory
    whatsAppReplyUnsupported = True  # non mandatory
    stompHost = None  # non mandatory
    stompPort = None  # non mandatory
    stompLogin = None  # mandatory
    stompPassword = None  # mandatory
    stompReconnectionAttemps = None # mandatory

    stompListeningDestinations = []
    stompWhatsAppDestinationInboxPrefix = None

    whatsAppService = None
    stompService = None

    def start(self):
        logger.info("Starting services...")
        try:
            if self.stompService:
                self.stompService.start()
            if self.whatsAppService:
                self.whatsAppService.start()
            return True
        except StompServiceException as e:
            logger.error(e.getMessage())
            return False

    def stopLoopGracefully(self):
        self.loopMustContinue = False

    def loop(self):
        self.loopMustContinue = True
        while self.loopMustContinue:
            try:
                self.stompService.checkAlive()
                self.whatsAppService.checkAlive()
                time.sleep(1)
            except (KeyboardInterrupt):
                logger.info("CLIENT: Interrupted")
                break
            except SystemExit:
                logger.info("SYSTEM: Interrupted")
                break

    def stop(self):
        logger.info("Stopping services...")
        if self.whatsAppService:
            self.whatsAppService.stop()
        if self.stompService:
            self.stompService.stop()

    def loadConfig(self):
        for config in self.configs:
            try:
                logger.info("Attemping to load configuration from %s" % config)
                f = open(config)
                param = {}
                for l in f:
                    line = l.strip()
                    if len(line) and line[0] not in ('#', ';'):
                        prep = line.split('#', 1)[0].split(';', 1)[0].split('=', 1)
                        varname = prep[0].strip()
                        val = prep[1].strip()
                        param[varname.replace('-', '_')] = val
                logger.info("Configuration from %s loaded" % config)
                logger.info("Configuration parameters is:\n%s" % functions.safeJsonEncode(param))
                return param
            except IOError:
                pass
        logger.fatal("Config load failed. Configuration files are not present")
        return None

    def config(self):
        param = self.loadConfig()
        if param == None:
            return False

        if 'whatsAppPhone' in param:
            self.whatsAppPhone = param['whatsAppPhone']
        if 'whatsAppPassword'  in param:
            self.whatsAppPassword = param['whatsAppPassword']
        if 'whatsAppAutoReply'  in param:
            self.whatsAppAutoReply = param['whatsAppAutoReply']
        if 'whatsAppReplyUnsupported'  in param:
            self.whatsAppReplyUnsupported = param['whatsAppReplyUnsupported']
        if 'stompHost'  in param:
            self.stompHost = param['stompHost']
        if 'stompPort' in param:
            self.stompPort = param['stompPort']
        if 'stompLogin' in param:
            self.stompLogin = param['stompLogin']
        if 'stompPassword'  in param:
            self.stompPassword = param['stompPassword']
        if 'stompReconnectionAttemps' in param:
            self.stompReconnectionAttemps = param['stompReconnectionAttemps']
        for i in range(1, 10):
            key = 'stompListeningDestination.%s' % i;
            if not key in param:
                break
            stompListeningDestination = param[key]
            self.stompListeningDestinations.append(stompListeningDestination)
        if 'stompWhatsAppDestinationInboxPrefix' in param:
            self.stompWhatsAppDestinationInboxPrefix = param['stompWhatsAppDestinationInboxPrefix']

        configOk = True
        if not self.whatsAppPhone:
            logger.error("Parameter 'whatsAppPhone' is not set")
            configOk = False
        if not self.whatsAppPassword:
            logger.error("Parameter 'whatsAppPassword' is not set")
            configOk = False
        if not self.whatsAppAutoReply:
            logger.error("Parameter 'whatsAppAutoReply' is not set")
            configOk = False
        if not self.whatsAppReplyUnsupported:
            logger.error("Parameter 'whatsAppReplyUnsupported' is not set")
            configOk = False
        if not self.stompHost:
            logger.error("Parameter 'stompHost' is not set")
            configOk = False
        if not self.stompPort:
            logger.error("Parameter 'stompPort' is not set")
            configOk = False
        if not self.stompLogin:
            logger.error("Parameter 'stompLogin' is not set")
            configOk = False
        if not self.stompPassword:
            logger.error("Parameter 'stompPassword' is not set")
            configOk = False
        if not self.stompReconnectionAttemps:
            logger.error("Parameter 'stompReconnectionAttemps' is not set")
            configOk = False
        if not self.stompWhatsAppDestinationInboxPrefix:
            logger.error("Parameter 'stompWhatsAppDestinationInboxPrefix' is not set")
            configOk = False
        if not len(self.stompListeningDestinations):
            logger.error("Parameter 'stompListeningDestination.N' is not set")
            configOk = False
        return configOk


    def init(self):
        self.stompService = StompService(
                                       self.stompHost,
                                       self.stompPort,
                                       self.stompLogin,
                                       self.stompPassword,
                                       self.stompReconnectionAttemps,
                                       self.stompListeningDestinations,
                                       self.stompWhatsAppDestinationInboxPrefix,
                                       self.whatsAppPhone)
        self.whatsAppService = WhatsAppService(
                                               self.whatsAppPhone,
                                               self.whatsAppPassword,
                                               self.whatsAppAutoReply,
                                               self.whatsAppReplyUnsupported)
        self.stompService.setWhatsAppService(self.whatsAppService)
        self.whatsAppService.setStompService(self.stompService)

    def run(self):
        signal.signal(signal.SIGTERM, signalHandler)  # SIGTERM    15    Завершение    Сигнал завершения (сигнал по умолчанию для утилиты kill)
        signal.signal(signal.SIGINT, signalHandler)  # SIGINT    2    Завершение    Сигнал прерывания (Ctrl-C) с терминала
        if not self.config():
            logger.error("Exiting")
            return False
        self.init()
        if not self.start():
            self.stop()
            logger.error("Exiting")
            return False
        self.loop()
        self.stop()
        return True

def signalHandler(signum, frame):
    global mainService
    logger.info("%s received. Stopping..." % functions.SIGNALS_TO_NAMES_DICT[signum])
    mainService.stopLoopGracefully()

def run():
    global mainService
    mainService = MainService()
    sys.exit(mainService.run())

if __name__ == "__main__":
    run()