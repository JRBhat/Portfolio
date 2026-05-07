# $Id: StandardLogger.py 13366 2022-08-05 13:06:26Z ndrews $
"""
###############################################################################
standard_logger.py
###############################################################################

Purpose
===============================================================================

Create standard logging facility:

    1. logging to file
    2. logging to commandline


Usage
===============================================================================

Should be included in all python files as follows

In modules/libraries/API (already done when using python_module_template in VS)::

    import logging

    LOGGER = logging.getLogger(__name__)
    LOGGER.setLevel(logging.INFO)
    LOGGER.info("Importing %s, version %s" % (__name__, __svnData__()['id'])

In scripts (already done when using python_script_template in VS)::

    import standard_logger

    OUTPUTPATH = os.getcwd()
    LOGGER_NAME = os.path.splitext(os.path.split(inspect.getfile(
    inspect.currentframe()))[1])[0]
    LOGGER = standard_logger.create_standard_logger(LOGGER_NAME, os.path.join(OUTPUTPATH,
        LOGGER_NAME + ".log"), create_newfile = True)
    LOGGER.setLevel(logging.INFO) #can be used to change level of detail 
                                  #messages in commandline
    LOGGER.info("SVNId: %s" % __svnData__()['id'])

"""

import logging
import datetime
import os.path
import os
import sys
import shutil
import logging.handlers
__version__ = "$Revision: 13366 $"


def __svnData__():
    """
    | $Author: ndrews $
    | $Date: 2022-08-05 15:06:26 +0200 (Fr., 05. Aug 2022) $
    | $Rev: 13366 $
    | $URL: http://sw-server:8090/svn/ImageProcessingLibrary/Python/proDERM_ImageAnalysisLibrary/ImageAnalysis/StandardLogger.py $
    | $Id: StandardLogger.py 13366 2022-08-05 13:06:26Z ndrews $
    """
    # only for documentation purpose
    return {
        'author': "$Author: ndrews $".replace('$', '').replace('Author:', '').strip(),
        'date': "$Date: 2022-08-05 15:06:26 +0200 (Fr., 05. Aug 2022) $".replace('$', '').replace('Date:', '').strip(),
        'rev': "$Rev: 13366 $".replace('$', '').replace('Rev:', '').strip(),
        'id': "$Id: StandardLogger.py 13366 2022-08-05 13:06:26Z ndrews $".replace('$', '').replace('Id:', '').strip()
    }


def __backup_file(inFile: str, backupExtension: str = ".bck", maxBackup: int = -1) -> str:
    """creates backupfile, older files are saved with timestamp
    :param inFile: filename of file to backup, defaults to ".bck"
    :type inFile: str, optional
    :param backupExtension: extension added to backupfiles, defaults to 1
    :type backupExtension: int
    :param maxBackup: number of kept backupfiles, -1 is all, defaults to -1
    :type maxBackup: int, optional
    :return:  filename of backup file
    :rtype: str
    """
    LOGGER = logging.getLogger(__name__)
    if not(os.path.exists(inFile)):
        LOGGER.info("No Backup possible, %s does not exist" % (inFile))
        return
    backupFileName = inFile + backupExtension
    if maxBackup != 0:
        ct = 0
        while os.path.exists(backupFileName) and ((maxBackup < 0) or (ct < maxBackup)):
            backupFileName = inFile + ".%d" % ct + backupExtension
            ct += 1
    LOGGER.info("copy %s -> %s" % (inFile, backupFileName))
    try:
        shutil.copy(inFile, backupFileName)
    except Exception as inst:
        LOGGER.error("Could copy '%s -> %s', Exception: %s" %
                     (inFile, backupFileName, inst))
        sys.exit(1)
    return backupFileName


def __create_directory(dirname: str) -> bool:
    """creates directory structure if not existing
    .. warning:: Quits program if directory could not be created
    :param dirname:  name of directory to create
    :type dirname: str
    :return: True if directory was created/existed, exits program if not
    :rtype: Bool
    """
    LOGGER = logging.getLogger(__name__)
    if not os.path.exists(dirname):
        LOGGER.info("Create path %s" % dirname)
        try:
            os.makedirs(dirname)
        except Exception as inst:
            LOGGER.critical(
                "Could nor create directory '%s', Exception: %s" % (dirname, inst))
            sys.exit(1)
            return False
    LOGGER.info("Path %s exist" % dirname)
    return True


def create_standard_logger(logger_name: str, logger_filename: str, create_newfile: bool = False) -> logging.Logger:
    """creates standard logger for python
    file logger:
        includes all (DEBUG) messages
    command-line logger:
        imcludes WARN, ERROR, CRITICAL messages
    .. warning:: not multithreaded!
    :param logger_name: name of logger (typically script name)
    :type logger_name: str
    :param logger_filename: filename of log-file
    :type logger_filename: st
    :param create_newfile: if True, create always a new log file, older are backed up, defaults to False
    :type create_newfile: bool, optional
    :return: logger with 
    :rtype: logging.Logger
    """
    try:
        if os.path.exists(logger_filename):
            os.rename(logger_filename, logger_filename + "test.log")
            os.rename(logger_filename + "test.log", logger_filename)
    except:
        logger_filename_name, logger_filename_ext = os.path.splitext(
            logger_filename)
        logger_filename = logger_filename_name + \
            "_%d" % os.getpid() + logger_filename_ext
    if create_newfile and os.path.exists(logger_filename):
        __backup_file(logger_filename, "_%s.bck" % str(datetime.date.today()))
        os.remove(logger_filename)
    outputdir = os.path.split(logger_filename)[0]
    __create_directory(outputdir)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logger_filename, 'w')
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter_file = logging.Formatter(
        '%(asctime)s - %(name)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s')
    formatter = logging.Formatter(
        '%(name)s:%(funcName)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter_file)
    # add the handlers to logger
    logging.getLogger('').addHandler(ch)
    logging.getLogger('').addHandler(fh)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.info("Importing Module standardLogger")
    logger.info("SVNID: %s" % __svnData__()['id'])
    return logger


def create_network_logger(logger_name: str, host: str = 'localhost', debug: bool = False) -> logging.Logger:
    """creates standard logger for python
    file logger:
        includes all (DEBUG) messages
    command-line logger:
        imcludes WARN, ERROR, CRITICAL messages
    .. warning:: not multithreaded!

    :param logger_name: name of the logger
    :type logger_name: str
    :param host: socket host , defaults to 'localhost'
    :type host: str, optional
    :param debug: sets logging level to debug, defaults to False
    :type debug: bool, optional
    :return: configurated logger
    :rtype: logging.Logger
    """
    socketHandler = logging.handlers.SocketHandler(host,
                                                   logging.handlers.DEFAULT_TCP_LOGGING_PORT)
    ch = logging.StreamHandler()
    if debug:
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(name)s:%(funcName)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logging.getLogger('').addHandler(socketHandler)
    logging.getLogger('').addHandler(ch)
    logger = logging.getLogger(logger_name)
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    # logger.setLevel(logging.INFO)
    logger.debug("Importing Module standardLogger")
    logger.debug("SVNID: %s" % __svnData__()['id'])
    return logger


def create_internal_logger(logger_name: str, log_file: str = None, log_file_for_all:bool=False) -> logging.Logger:
    """create logging for internal messages

    :param logger_name: name of the logger
    :type logger_name: str
    :param log_file: file to store logs in, if None no logs will be saved, defaults to None
    :type log_file: str, optional
    :param log_file_for_all: all known loggers will log in log_file, defaults to None
    :type log_file_for_all: bool
    :return: logger
    :rtype: logging.Logger
    """
    print(f"Created {logger_name}")
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        # Prevent logging from propagating to the root logger
        logger.propagate = 0
        # create logging format
        logging_formatter = logging.Formatter(
            fmt="%(levelname)s %(asctime)s:%(name)s:%(module)s:%(funcName)s: %(message)s", datefmt='%H:%M:%S')
        # create logger for console
        logging_console_handler = logging.StreamHandler(sys.stdout)
        logging_console_handler.setFormatter(logging_formatter)
        logging_console_handler.setLevel(logging.DEBUG)
        logger.addHandler(logging_console_handler)
        # add file handler if wanted
        if log_file:
            file_handler = logging.FileHandler(log_file, mode='w+')
            file_handler.setFormatter(logging_formatter)
            file_handler.setLevel(logging.DEBUG)
            if log_file_for_all:
                for logger in [logging.getLogger(name) for name in logging.root.manager.loggerDict]:
                    logger.addHandler(file_handler)
            else:
                logger.addHandler(file_handler)
    return logger
