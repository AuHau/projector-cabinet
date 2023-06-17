"""
Update firmware written in MicroPython over the air.

MIT license; Copyright (c) 2021 Martin Komon
MIT license; Copyright (c) 2023 Adam Uhlir
"""

import gc
import uos
import urequests
import uzlib
import utarfile as tarfile
from micropython import const

GZDICT_SZ = const(31)


class Logging:
    def critical(self, entry):
        print('CRITICAL: ' + entry)

    def error(self, entry):
        print('ERROR: ' + entry)

    def warning(self, entry):
        print('WARNING: ' + entry)

    def info(self, entry):
        print('INFO: ' + entry)

    def debug(self, entry):
        print('DEBUG: ' + entry)


class UOta:
    def __init__(self, github_repo, release_tar_name="source.tar.gz", logger=None, version_file='version.txt',
                 excluded_files=None):
        self.repo = github_repo.rstrip('/').replace('https://github.com/', '')
        self.release_tar_name = release_tar_name
        self.version_file_path = version_file
        self.logger = logger or Logging()
        self.excluded_files = set(excluded_files or [])

    def check_free_space(self, min_free_space: int) -> bool:
        """
        Check available free space in filesystem and return True/False if there is enough free space
        or not.

        min_free_space is measured in kB
        """
        if not any([isinstance(min_free_space, int), isinstance(min_free_space, float)]):
            self.logger.warning('min_free_space must be an int or float')
            return False

        fs_stat = uos.statvfs('/')
        block_sz = fs_stat[0]
        free_blocks = fs_stat[3]
        free_kb = block_sz * free_blocks / 1024
        return free_kb >= min_free_space

    def get_current_version(self):
        try:
            with open(self.version_file_path) as f:
                version = f.read()
                return version
        except OSError as e:  # File does not exists
            return '0.0.0'
        except Exception as e:
            self.logger.debug(f'Version retrieving error: {e}')
            return '0.0.0'

    def get_latest_version(self):
        info = self.get_latest_version_info()
        return "0.0.0" if info is None else info["version"]

    def get_latest_version_info(self):
        response = urequests.get(
            'https://api.github.com/repos/{}/releases/latest'.format(self.repo),
            headers={"User-Agent": "MicroPython uOta"})

        try:
            release_json = response.json()
            release_json["tag_name"]
        except (ValueError, KeyError):
            self.logger.error("Release not found!")
            self.logger.debug(f"Response content: {response.text}")
            response.close()
            return None


        self.logger.info(f"Found latest release with version: {release_json['tag_name']}")

        try:
            release_asset = next(filter(lambda asset: asset["name"] == self.release_tar_name, release_json["assets"]))
        except StopIteration:
            self.logger.error(f"Release does not contain release asset {self.release_tar_name}!")
            response.close()
            return None

        return {
            "version": release_json['tag_name'],
            "size": release_asset["size"],
            "url": release_asset["browser_download_url"]
        }

    def check_for_update(self) -> bool:
        gc.collect()

        remote_version = self.get_latest_version()
        local_version = self.get_current_version()

        return remote_version > local_version

    def download_update(self) -> bool:
        """
        Check for available updates, download new firmware if available and return True/False whether
        it's ready to be installed, there is enough free space.
        """
        gc.collect()

        latest_release_info = self.get_latest_version_info()
        remote_version = latest_release_info["version"]
        local_version = self.get_current_version()

        if remote_version > local_version:
            self.logger.info(f'New version {remote_version} is available')
            if not self.check_free_space(latest_release_info["size"]):
                self.logger.error('Not enough free space for the new firmware')
                return False

            response = urequests.get(latest_release_info["url"],
                                     headers={"User-Agent": "MicroPython uOta"})
            with open(self.release_tar_name, 'wb') as f:
                while True:
                    chunk = response.raw.read(512)
                    if not chunk:
                        break
                    f.write(chunk)
            return True

        return False

    def install_new_firmware(self):
        """
        Unpack new firmware that is already downloaded and perform a post-installation cleanup.
        """
        gc.collect()

        try:
            uos.stat(self.release_tar_name)
        except OSError:
            self.logger.info('No new firmware file found in flash.')
            return False

        with open(self.release_tar_name, 'rb') as f1:
            f2 = uzlib.DecompIO(f1, GZDICT_SZ)
            f3 = tarfile.TarFile(fileobj=f2)
            for _file in f3:
                file_name = _file.name
                if file_name in self.excluded_files:
                    item_type = 'directory' if file_name.endswith('/') else 'file'
                    self.logger.info(f'Skipping excluded {item_type} {file_name}')
                    continue

                if file_name.endswith('/'):  # is a directory
                    try:
                        self.logger.debug(f'Creating directory {file_name} ... ')
                        uos.mkdir(file_name[:-1])  # without trailing slash or fail with errno 2
                        self.logger.debug('ok')
                    except OSError as e:
                        if e.errno == 17:
                            self.logger.debug('Already exists')
                        else:
                            raise e
                    continue
                file_obj = f3.extractfile(_file)
                with open(file_name, 'wb') as f_out:
                    written_bytes = 0
                    while True:
                        buf = file_obj.read(512)
                        if not buf:
                            break
                        written_bytes += f_out.write(buf)
                    self.logger.info(f'file {file_name} ({written_bytes} B) written to flash')

        uos.remove(self.release_tar_name)
        return True
