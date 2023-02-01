# Name: Pixlovarr Prune
# Coder: Marco Janssen (twitter @marc0janssen)
# date: 2022-12-24 23:22:02
# update: 2022-12-24 23:22:10

import logging
import sys
import configparser
import shutil

from datetime import datetime
from arrapi import SonarrAPI, exceptions


class sonarrSync():

    def __init__(self):
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO)

        config_dir = "/config/"
        app_dir = "/app/"
        log_dir = "/logging/"

        self.config_file = "sonarr_sync.ini"
        self.exampleconfigfile = "sonarr_sync.ini.example"
        self.log_file = "sonarr_sync.log"

        self.config_filePath = f"{config_dir}{self.config_file}"
        self.log_filePath = f"{log_dir}{self.log_file}"

        try:
            with open(self.config_filePath, "r") as f:
                f.close()
            try:
                self.config = \
                    configparser.ConfigParser()
                self.config.read(self.config_filePath)

                # SONARR_SOURCE
                self.sonarrsource_url = self.config['SONARR_SOURCE']['URL']
                self.sonarrsource_token = self.config['SONARR_SOURCE']['TOKEN']

                # SONARR_DESTINATION
                self.sonarrdest_url = self.config['SONARR_DEST']['URL']
                self.sonarrdest_token = self.config['SONARR_DEST']['TOKEN']
                self.sonarrdest_rootfolder = \
                    int(self.config['SONARR_DEST']['ROOTFOLDER'])
                self.sonarrdest_qualityprofile = \
                    int(self.config['SONARR_DEST']['QUALITYPROFILE'])

                # SYNC
                self.dry_run = True if (
                    self.config['SYNC']['DRY_RUN'] == "ON") else False
                self.enabled_run = True if (
                    self.config['SYNC']['ENABLED'] == "ON") else False
                self.verbose_logging = True if (
                    self.config['SYNC']['VERBOSE_LOGGING'] == "ON") else False

            except KeyError as e:
                logging.error(
                    f"Seems a key(s) {e} is missing from INI file. "
                    f"Please check for mistakes. Exiting."
                )

                sys.exit()

            except ValueError as e:
                logging.error(
                    f"Seems a invalid value in INI file. "
                    f"Please check for mistakes. Exiting. "
                    f"MSG: {e}"
                )

                sys.exit()

        except IOError or FileNotFoundError:
            logging.error(
                f"Can't open file {self.config_filePath}"
                f", creating example INI file."
            )

            shutil.copyfile(f'{app_dir}{self.exampleconfigfile}',
                            f'{config_dir}{self.exampleconfigfile}')
            sys.exit()

    def writeLog(self, init, msg):
        try:
            if init:
                logfile = open(self.log_filePath, "w")
            else:
                logfile = open(self.log_filePath, "a")
            logfile.write(f"{datetime.now()} - {msg}")
            logfile.close()
        except IOError:
            logging.error(
                f"Can't write file {self.log_filePath}."
            )

    def run(self):
        txtMsg = "Sync - Sonarr Sync started"
        self.writeLog(True, f"{txtMsg}\n")
        if self.verbose_logging:
            logging.info(txtMsg)

        if not self.enabled_run:
            txtMsg = "Sync - Sonarr sync disabled"
            logging.info(txtMsg)
            self.writeLog(False, f"{txtMsg}\n")
            sys.exit()

        # Connect to Sonarr Source
        try:
            self.sonarrsourceNode = SonarrAPI(
                self.sonarrsource_url, self.sonarrsource_token)
        except exceptions.ArrException as e:
            logging.error(
                f"Can't connect to Sonarr source {e}"
            )

            sys.exit()

        # Connect to Sonarr Destination
        try:
            self.sonarrdestNode = SonarrAPI(
                self.sonarrdest_url, self.sonarrdest_token)
        except exceptions.ArrException as e:
            logging.error(
                f"Can't connect to Sonarr destination {e}"
            )

            sys.exit()

        if self.dry_run:
            logging.info(
                "****************************************************")
            logging.info(
                "**** DRY RUN, NOTHING WILL BE DELETED OR SYNCED ****")
            logging.info(
                "****************************************************")

        self.sourceMedia = self.sonarrsourceNode.all_series()
        self.destMedia = self.sonarrdestNode.all_series()

        boolSynced = False
        boolFound = False

        for source in self.sourceMedia:
            for destination in self.destMedia:
                if (source.tvdbId == destination.tvdbId and source.tvdbId):
                    boolFound = True
                    break

            if not boolFound:

                dest = self.sonarrdestNode.get_series(tvdb_id=source.tvdbId)

                if not dest.id:
                    boolSynced = True
                    txtMsg = (
                        f"Syncing the series: {source.title}({source.year})")
                    self.writeLog(False, f"{txtMsg}\n")
                    logging.info(txtMsg)

                    try:
                        if not self.dry_run:
                            dest.add(
                                self.sonarrdest_rootfolder,
                                self.sonarrdest_qualityprofile,
                                1,
                                "firstSeason",
                                True,
                                True,
                                True,
                                "standard",
                                source.tags
                            )

                    except exceptions.Exists:
                        logging.warning(
                                    f"Series {source.title}({source.year})"
                                    f" already exists on destination.")

            else:
                boolFound = False

        self.sourceMedia = self.sonarrsourceNode.all_series()
        self.destMedia = self.sonarrdestNode.all_series()

        boolFound = False

        for destination in self.destMedia:
            for source in self.sourceMedia:
                if (source.tvdbId == destination.tvdbId
                        and destination.tvdbId):
                    boolFound = True
                    break

            if not boolFound:

                source = self.sonarrsourceNode.get_series(
                    tvdb_id=destination.tvdbId)

                if not source.id:
                    boolSynced = True
                    txtMsg = (
                        f"Deleting the series: {source.title}({source.year})")
                    self.writeLog(False, f"{txtMsg}\n")
                    logging.info(txtMsg)

                    try:
                        if not self.dry_run:
                            self.sonarrdestNode.delete_series(
                                series_id=destination.id,
                                tvdb_id=None,
                                addImportListExclusion=False,
                                deleteFiles=True
                            )

                    except exceptions.NotFound:
                        logging.warning(
                                    f"Series {dest.title}({dest.year})"
                                    f" doesn't exists on destination.")

            else:
                boolFound = False

        if not boolSynced:
            txtMsg = "Sync - No series were synced."
            self.writeLog(False, f"{txtMsg}\n")
            if self.verbose_logging:
                logging.info(txtMsg)
        else:
            txtMsg = "Sync - Sonarr Sync Ended"
            self.writeLog(False, f"{txtMsg}\n")
            if self.verbose_logging:
                logging.info(txtMsg)


if __name__ == '__main__':

    sonarrsync = sonarrSync()
    sonarrsync.run()
    sonarrsync = None
