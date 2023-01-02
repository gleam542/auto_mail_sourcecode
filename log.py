from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import datetime
import logging

class WindowHandler(logging.StreamHandler):
    def __init__(self, message):
        super().__init__()
        self.message = message

    def emit(self, record):
        self.message.set(record.getMessage())


def load_logger():
    global logger
    # 檢查目錄存在
    if not Path('config').exists():
        Path('config').mkdir()
    if not Path('config/log').exists():
        Path('config/log').mkdir()

    # 設定log檔格式
    fmt = logging.Formatter(
        '%(asctime)s %(levelname)7s [%(filename)10s:%(lineno)4s - %(funcName)15s] %(message)s',
        datefmt=r'%Y-%m-%d %H:%M:%S'
    )

    # 檔案輸出
    filehdlr = TimedRotatingFileHandler(f'config/log/紀錄.log' ,when='midnight', backupCount=90, encoding='utf-8')
    filehdlr.suffix = r'%Y-%m-%d_%H-%M-%S'
    filehdlr.setFormatter(fmt)

    # 標準輸出
    cnshdlr = logging.StreamHandler()
    cnshdlr.setFormatter(fmt)

    # 獲取logger
    logger = logging.getLogger('robot')

    # 增加輸出
    logger.addHandler(filehdlr)
    logger.addHandler(cnshdlr)

    # 設定層級
    logger.setLevel(logging.DEBUG)
    cnshdlr.setLevel(logging.DEBUG)
    filehdlr.setLevel(logging.DEBUG)


if not globals().get('logger'):
    load_logger()
