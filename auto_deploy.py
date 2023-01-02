import ftplib
from dotenv import load_dotenv
from pathlib import Path
from ftplib import FTP
import requests_html
import subprocess
import traceback
import logging
import shutil
import yaml
import log
import os
import io
logger = logging.getLogger('robot')
load_dotenv(encoding='utf-8')  # 載入 .env 檔案


class Deploy:
    download_url = ''
    ftp_url = ''
    ftp_account = ''
    ftp_password = ''

    # 打包
    @classmethod
    def pyinstaller(cls):
        try:
            subprocess.check_output('pyinstaller -y main.spec')
            logger.info("打包成功")
            logger.info("====================")
            return True
        except Exception as e:
            logger.critical('\n' + traceback.format_exc())
            logger.info("打包失敗,請重新確認檔案")
            logger.info("====================")
            return False

    # 建立自解壓縮檔.exe
    @classmethod
    def auto_7z(cls, app_name):
        path = Path('.').absolute()
        try:
            path_7z = str(path / '7Z' / '7z.exe') # 7z壓縮檔位置
            path_file = str(path / 'dist' / f'{app_name}') # 要執行壓縮的檔案
            path_exe = str(path / 'dist' / f'{app_name}.exe') # 完成的路徑與檔名
            subprocess.check_output(f'"{path_7z}" a -sfx7z.sfx "{path_exe}" "{path_file}"')
            logger.info(f"壓縮成功，檔案路徑:{str(path / 'dist' / f'{app_name}.exe')}")
            return True
        except Exception as e:
            logger.critical('\n' + traceback.format_exc())
            logger.info("壓縮失敗,請手動壓縮並上傳FTP")
            return False

    # 上傳FTP
    @classmethod
    def update_ftp(cls, local_filename, remote_path, remote_filename):
        while True:
            try:
                ftp = FTP()
                ftp.connect(cls.ftp_url)
                ftp.login(cls.ftp_account, cls.ftp_password)
                ftp.encoding = 'utf-8'

                # 上傳檔案
                ftp.cwd(remote_path)
                local_filename = Path(local_filename)
                with local_filename.open('rb') as f:
                    ftp.storbinary(f"STOR {remote_filename}", f, 1024)

                logger.info(f'下載連結： {cls.download_url}{remote_path}/{remote_filename}')
                return True
            except ftplib.error_temp as e:
                logger.info(f'{e.__class__.__name__}: {e}')
                continue
            except Exception as e:
                logger.critical('\n' + traceback.format_exc())
                logger.info("上傳FTP失敗,請手動上傳FTP")
                return False


def main():
    # 自動打包
    result_install = Deploy.pyinstaller()
    if not result_install:
        return

    # 讀取使用自動更新的所有機器人
    with open('auto_deploy.yaml', 'r', encoding='utf8') as f:
        deploy_config = yaml.load(f.read(), yaml.SafeLoader)
    # 所有機器人逐一寫入config檔並進行壓縮上傳
    for app_name, app_url in deploy_config.items():
        logger.info(f'開始 {app_name} 更新')
        # 複製打包好的檔案
        if Path(f'dist/{app_name}').exists():
            shutil.rmtree(f'dist/{app_name}')
        shutil.copytree(f'dist/自動更新機器人', f'dist/{app_name}')
        # 寫入對應的設定檔
        with Path(f'dist/{app_name}/config.yaml').open('w', encoding='utf8') as f:
            config = {'CHUNK_SIZE': 512, 'CONFIG_URL': f'{Deploy.download_url}{app_url.split("botdownload/")[1]}/config.yaml', 'CURRENT': {}}
            yaml.dump(config, f, allow_unicode=True)
        with Path(f'dist/{app_name}/.env').open('w', encoding='utf8') as f:
            f.write((
                f'APP_NAME={app_name}\n'
                f'VERSION={os.getenv("VERSION")}'
            ))

        # 壓縮
        result_7z = Deploy.auto_7z(app_name)
        if not result_7z:
            return

        # 上傳FTP
        result_ftp = Deploy.update_ftp(
            local_filename=f'dist/{app_name}.exe',
            remote_path=f'{app_url}',
            remote_filename=f'{app_name}.exe'
        )
        if not result_ftp:
            return
        logger.info(f'{app_name} 更新完成------------')

    logger.info("載點更新成功!!!")


if __name__ == '__main__':
    result = main()
