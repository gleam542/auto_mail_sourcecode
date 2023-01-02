from tkinter import messagebox
from pathlib import Path
from tkinter import ttk
import tkinter as tk
import subprocess
import traceback
import threading
import requests
import filetype
import builtins
import logging
import shutil
import socket
import py7zr
import yaml
import copy
import time
import log
import re
logger = logging.getLogger('robot')
RETRY_TIMES = 3
ver_pattern = re.compile('(?P<major>.+)\.(?P<minor>.+)\.(?P<micro>.+)')


class HeaderError(Exception):
    pass


class MainWindow(tk.Frame):
    def __init__(self, root, setting):
        tk.Frame.__init__(self, root)
        self.root = root
        self._var_txt = []
        self.setting = setting
        # 畫面設定
        self.pack(expand=1, fill='both')
        # 畫面設定 主要 - 文字顯示
        self.top = tk.Frame(self)
        self.top.pack(side='top', expand=1, fill='both', padx=5, pady=5)
        self.txt = tk.Text(self.top, height=5, width=90, padx=10, pady=10)
        self.txt.pack(side='left', expand=1, fill='both')
        self.scrollbar = tk.Scrollbar(self.top, orient='vertical')
        self.scrollbar.pack(side='right', fill='y')
        self.scrollbar.configure(command=self.txt.yview)
        self.txt.configure(yscrollcommand=self.scrollbar.set, state='disabled')
        # 畫面設定 中間 - 進度條
        self.middle = tk.Frame(self)
        self.middle.pack(side='top', fill='x', padx=5)
        self.progressbar = ttk.Progressbar(self.middle, orient='horizontal')
        self.progressbar.pack(fill='x')
        # 畫面設定 底下 - 按鈕
        self.bottom = tk.Frame(self)
        self.bottom.pack(side='bottom', fill='x', padx=5, pady=5)
        self.btn_update = tk.Button(self.bottom, text='更新')
        self.btn_update.pack(anchor='e', side='left', expand=1, padx=5)
        self.btn_update.configure(command=lambda: threading.Thread(target=self.fn_update).start())
        # 略過更新按鈕設定
        is_debug = (setting['major'] is setting['minor'] is True) and (setting['micro'] is False)
        require = not bool(setting['CURRENT']) or setting['LASTEST']['REQUIRE'] or is_debug
        self.btn_ignore = tk.Button(self.bottom, text='忽略本次更新')
        self.btn_ignore.pack(anchor='w', side='right', expand=1, padx=5)
        self.btn_ignore.configure(state='disabled' if require else 'normal')
        self.btn_ignore.configure(command=lambda: self.start_robot(setting['CURRENT']) and self.root.quit())
        # 當CURRENT無資料，代表首次啟動機器人，需要下載最新版，顯示相關說明文字
        if not setting['CURRENT']:
            # 說明文字
            self.var_txt = f'最新版机器人版本为: {setting["LASTEST"]["VERSION"]}。'
            self.var_txt = f'您首次启动机器人，请点选【下载】，下载最新版本机器人。'
            # 按鈕文字、位置調整
            self.btn_update.configure(text='下载')
        else:
            # 說明文字
            self.var_txt = f'当前版机器人版本为: {setting["CURRENT"]["VERSION"]}。'
            self.var_txt = f'最新版机器人版本为: {setting["LASTEST"]["VERSION"]}。'
            if not require:
                self.var_txt = '提醒您，如选择不更新，以下系统可能无法正常运行：'
            else:
                self.var_txt = '请点选【更新】，更新以下系统：'
            for ver, info in self.setting['VERSIONS'].items():
                curr = int(self.setting['CURRENT']['VERSION'].replace('.', ''))
                new = int(ver.replace('.', ''))
                if new > curr:
                    self.var_txt = f'- {info["SYSTEM"]}'

    @property
    def var_txt(self):
        return '\n'.join(self._var_txt)
    @var_txt.setter
    def var_txt(self, txt):
        logger.info(txt)
        self.txt.configure(state='normal')
        self.txt.insert('end', ('\n' if self.var_txt else '') + txt)
        self.txt.configure(state='disabled')
        self.txt.see('end')
        self._var_txt.append(txt)

    @classmethod
    def update_config(cls, setting):
        '''更新設定檔'''
        logger.info('=== 更新设定档 ====')
        logger.info(f'设定档位置: {setting["CONFIG_URL"]}')
        for i in range(RETRY_TIMES):
            try:
                logger.info(f'第 {i+1} 次嘗試 ...')
                # 下載新版設定檔
                new_setting = requests.get(setting['CONFIG_URL'], verify=False, timeout=5)
                new_setting = yaml.load(new_setting.content, yaml.SafeLoader)
                logger.info(f'最新版本为: {new_setting["LASTEST"]["VERSION"]}')
                # 保留舊版設定檔 CURRENT 屬性
                if setting.get('CURRENT', {}):
                    new_setting['CURRENT'] = setting['CURRENT']
                return new_setting
            except requests.exceptions.ConnectionError as e:
                logger.warning(f'--- {e.__class__.__name__}： {e} ----------')
                time.sleep(1)
        # 連線異常無法更新設定檔，重試三次後跳出異常視窗，結束程式
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title='错误', message='更新设定档失败，请检查连线是否正常')
        root.quit()
        return
    @classmethod
    def load_config(cls):
        '''讀取設定檔'''
        with open('config.yaml', 'r', encoding='utf-8') as f:
            logger.info('=== 读取设定档 ====')
            setting = yaml.load(f, yaml.SafeLoader)
            # 記錄檔、畫面 紀錄版本是否改版的內容
            if setting.get('CURRENT'):
                logger.info(f'当前版本为: {setting["CURRENT"]["VERSION"]}')
            else:
                logger.info('首次启用，未绑定当前版本')
        return setting
    @classmethod
    def save_config(cls, setting):
        '''保存設定檔'''
        with open('config.yaml', 'w', encoding='utf-8') as f:
            logger.info('=== 保存设定档 ====')
            yaml.dump(setting, f, allow_unicode=True)
    @classmethod
    def compare_version(cls, new_version, curr_version):
        # 比較版本號三個項目
        # 當micro為False且major、minor為True，不可忽略更新
        major, minor, micro =  [int(new) <= int(curr) for new, curr in zip(
            ver_pattern.search(new_version).groups(),
            ver_pattern.search(curr_version).groups()
        )]
        return {'major': major, 'minor': minor, 'micro': micro}
    @classmethod
    def check_lastest_version(cls):
        '''檢查是否有新版本需要更新，並保存相關訊息在設定檔中'''
        # 讀取本地設定檔
        setting = MainWindow.load_config()
        # 按照設定檔 CONFIG_URL 下載新版設定檔
        new_setting = MainWindow.update_config(setting)
        if not new_setting:
            return
        # 保存新版設定檔，僅保留 CURRENT 屬性
        MainWindow.save_config(new_setting)

        # 首次啟動，無 CURRENT
        if not setting['CURRENT']:
            new_setting['major'] = False
            new_setting['minor'] = False
            new_setting['micro'] = False
            return new_setting
        # 將最新版與當前版本比較，紀錄版本變更訊息
        new_setting =  {
            **new_setting,
            **cls.compare_version(
                new_setting['LASTEST']['VERSION'],
                new_setting['CURRENT']['VERSION']
            )
        }
        return new_setting

    @classmethod
    def start_robot(cls, version):
        try:
            subprocess.Popen(
                version['FILE_PATH'],
                shell=True, 
                cwd=Path(f'data/{version["DIR_PATH"]}').absolute(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            return True
        except (FileNotFoundError, NotADirectoryError) as e:
            print(e)
            return False

    def download_robot(self, i, download_path):
        while True:
            try:
                with open(str(download_path), 'ab+') as f:
                    f.seek(0)
                    file_size = len(f.read())
                    i = file_size // int(self.setting['CHUNK_SIZE'])
                    self.var_txt = f'=== 下载机器人 === V{self.setting["LASTEST"]["VERSION"]}'

                    headers = {'Range': f'bytes={file_size}-'}
                    resp = requests.get(self.setting['LASTEST']['DATA_URL'], stream=True, verify=False, timeout=5, headers=headers)
                    # 已經載完，Range帶超過時回傳416
                    if resp.status_code == 416:
                        self.var_txt = '=== 机器人下载完毕(416) === '
                        resp.close()
                        return True
                    # 使用Range功能續傳時，status_code為206
                    if resp.status_code not in [200, 206]:
                        raise HeaderError((
                            f"機器人壓縮檔下載失敗({self.setting['LASTEST']['DATA_URL']})\n"
                            f"取得的狀態碼為：{resp.status_code}"
                        ))
                    if resp.headers['Content-Type'] not in ['application/x-msdownload', 'application/x-7z-compressed']:
                        raise HeaderError((
                            f"機器人壓縮檔下載失敗({self.setting['LASTEST']['DATA_URL']})\n"
                            f"取得的檔案類型為：{resp.headers['Content-Type']}"
                        ))
                    total = float(resp.headers['Content-Length']) + file_size
                    total = total // int(self.setting['CHUNK_SIZE'])
                    for chunk in resp.iter_content(chunk_size=int(self.setting['CHUNK_SIZE'])):
                        f.write(chunk)
                        i += 1
                        self.progressbar['value'] = 100 * i / total
                        self.root.update_idletasks()
                    resp.close()
                if filetype.guess(str(download_path)) is None:
                    logger.warning('main.EXE 內容錯誤：')
                    logger.warning(download_path.read_bytes())
                    download_path.unlink()
                    continue
                if filetype.guess(str(download_path)).extension not in ['exe', '7z']:
                    logger.warning('main.EXE 內容錯誤：')
                    logger.warning(download_path.read_bytes())
                    download_path.unlink()
                    continue
                return True
            except HeaderError as e:
                resp.close()
                self.var_txt = str(e)
                time.sleep(1)
                continue
            except (socket.timeout, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                logger.warning(f'--- {e.__class__.__name__}： {e} ----------')
                self.var_txt = f'第 {i+1} 分割檔下載失敗(連線異常)，請檢查網路是否正常。'
                continue

    def extract_robot(self, download_path, extract_path):
        try:
            if not extract_path.exists():
                self.var_txt = f'=== 解压缩机器人 === V{self.setting["LASTEST"]["VERSION"]}'
                if filetype.guess(str(download_path)).extension == 'exe':
                    self.btn_update.configure(text='继续', state='normal')
                    self.var_txt = f'请依跳出视窗操作，直接进行解压缩，解压完毕后再按继续键。'
                    self.var_txt = f'注意：请勿修改解压缩目录。'
                    subprocess.Popen(str(download_path))
                    return False
                elif filetype.guess(str(download_path)).extension == '7z':
                    with py7zr.SevenZipFile(str(download_path), mode='r') as zf:
                        zf.extractall('data')
                    return True
                else:
                    self.var_txt = f'档案格式异常，请联系开发团队'
                    messagebox.showerror(title='错误', message=f'档案格式异常，请联系开发团队', parent=self)
                    return False
        except FileNotFoundError as e:
            logger.critical(f'下載目錄：{download_path}')
            logger.critical(f'解壓目錄：{extract_path}')
            logger.critical(f'{e.__class__.__name__}: {e}')
            messagebox.showerror(title='错误', message=f'更新机器人失败(档案不存在)，請聯繫開發團隊', parent=self)
            return False

    def copy_setting(self, curr_setting, new_setting):
        try:
            for f in curr_setting['CONFIG_FILES']:
                shutil.copy(
                    str(Path(f'data/{curr_setting["DIR_PATH"]}/{f}')),
                    str(Path(f'data/{new_setting["DIR_PATH"]}/{f}')),
                )
            return True
        except FileNotFoundError as e:
            logger.info(f'金鑰檔找不到，原因:{e}')
            messagebox.WARNING(title='提示', message=f'请绑定金钥', parent=self)
            return False

    def fn_update(self):
        '''下載、啟動最新版本，並遷移金钥档'''
        # 定義變數 下載目錄、解壓目錄
        download_path = Path(f'data/main.{self.setting["LASTEST"]["TYPE"]}')
        extract_path = Path(f'data/{self.setting["LASTEST"]["DIR_PATH"]}')
        # 文字框 空兩行
        self.txt.configure(state='normal')
        self.txt.insert('end', '\n\n')
        self.txt.configure(state='disabled')
        for i in range(RETRY_TIMES):
            try:
                # 按鈕設為不可點選，避免連續點選造成錯誤
                self.btn_update.configure(state='disabled')
                self.btn_ignore.configure(state='disabled')
                # 下載新版本
                down_result = self.download_robot(i, download_path)
                if down_result is False:
                    # 第 RETRY_TIMES 次失敗，跳錯誤結束
                    if i+1 == RETRY_TIMES:
                        messagebox.showerror(title='错误', message=f'更新机器人失败(连线异常)，请检查网路是否正常', parent=self)
                        return
                    # 暫停 1 秒後重試
                    time.sleep(1)
                    continue
                time.sleep(.2)

                # 解壓縮機器人
                extract_result = self.extract_robot(download_path, extract_path)
                if extract_result is False:
                    return
                time.sleep(.2)

                # 刪除下載的壓縮檔，下次啟動的時候才不會不能運行
                download_path.unlink()
                time.sleep(.2)

                # 搬移金钥檔
                if not self.setting['CURRENT']:
                    self.var_txt = '找不到当前金钥档，请手动设置机器人设定'
                elif self.setting['LASTEST']['API_VERSION'] != self.setting['CURRENT']['API_VERSION']:
                    self.var_txt = '参数版本不同, 请手动进行设定'
                else:
                    self.var_txt = '=== 迁移金钥档 ==='
                    copy_result = self.copy_setting(
                        curr_setting=self.setting['CURRENT'],
                        new_setting=self.setting['LASTEST']
                    )
                time.sleep(.2)

                # 保存自動更新機器人設定檔
                self.var_txt = f'=== 更新当前版本号 === V{self.setting["LASTEST"]["VERSION"]}'
                self.setting['CURRENT'] = copy.deepcopy(self.setting['LASTEST'])
                self.save_config(self.setting)
                time.sleep(.2)

                # 啟動
                self.var_txt = '=== 更新完成，即将启动机器人... ==='
                start_result = self.start_robot(self.setting['LASTEST'])
                if start_result is False:
                    self.setting['CURRENT'] = {}
                    self.save_config(self.setting)
                    continue
                time.sleep(1)

                # 關閉本視窗
                self.root.quit()
                return

            except Exception as e:
                logger.critical('\n' + traceback.format_exc())
                messagebox.showerror(title='错误', message=f'{e.__class__.__name__}: {e}', parent=self)
                return
            finally:
                self.btn_update.configure(state='normal')


def main():
    # 初始化機器人資料夾
    if not Path('data').exists():
        Path('data').mkdir()

    # 檢查是否有更新
    setting = MainWindow.check_lastest_version()
    if not setting:
        return

    # 未更新直接啟動當前版本
    if setting['major'] is setting['minor'] is setting['micro'] is True:
        root = tk.Tk()
        root.withdraw()
        start_result = MainWindow.start_robot(setting['CURRENT'])
        root.quit()
        if start_result is False:
            setting['CURRENT'] = {}
            MainWindow.save_config(setting)
        else:
            return

    # 讀取ENV檔
    env_path = Path('.env')
    for line in env_path.read_text(encoding='utf8').split('\n'):
        if '=' not in line:
            continue
        line = line.split('=')
        key = line[0].strip()
        value = '='.join(line[1:]).strip()
        setattr(builtins, key, value)

    # 有更新則跳出更新視窗
    root = tk.Tk()
    root.title(f'{builtins.APP_NAME} V{builtins.VERSION} ({Path(".").absolute()})')
    MainWindow(root, setting)
    root.mainloop()


if __name__ == '__main__':
    main()